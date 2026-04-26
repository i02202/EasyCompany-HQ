"""
Campus Factory AI — MCP Gateway (Nexus Router Pattern)
======================================================
OpenAI-compatible proxy that sits between CrewAI/LiteLLM and Ollama.

Key features:
  1. Tool calling injection — converts OpenAI `tools` param into system prompt
     instructions for models that lack native tool support (e.g., gemma3:12b)
  2. Response parsing — extracts tool calls from model text output and converts
     back to OpenAI `tool_calls` format
  3. Observability — tracks tokens, latency, errors per agent/model
  4. Model routing — future: route different agents to different models

Flow:
  CrewAI Agent → LiteLLM → Gateway (:6000) → Ollama (:11434)

Endpoints (OpenAI-compatible):
  POST /v1/chat/completions  — main chat endpoint with tool injection
  GET  /v1/models            — proxy Ollama model list
  GET  /api/metrics           — observability dashboard data
  POST /api/metrics/reset     — reset counters

Usage:
  python -m factory_ai.gateway          # standalone
  from factory_ai.gateway import app    # import in server.py
"""
import asyncio
import json
import re
import time
import uuid
import urllib.request
import urllib.error
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from factory_ai.config import OLLAMA_BASE_URL

# ─── Config ───────────────────────────────────────────────────────────────────
GATEWAY_PORT = 6000
# Default Ollama options — critical: num_ctx controls VRAM usage
# Without this, models default to their full context (gemma3: 131k → CPU fallback)
# 16384 is needed for multi-agent crews: each agent receives previous outputs as context.
# qwen3:8b at 16K ctx uses ~6GB VRAM (KV cache scales linearly with context).
DEFAULT_OLLAMA_OPTIONS = {"num_ctx": 16384}

# Ollama HTTP timeout — must accommodate slow inference on modest hardware.
# qwen3:8b on RTX 4060 with large context can take 10-15 min for one call.
OLLAMA_HTTP_TIMEOUT = 1200  # 20 minutes

# Models known to support native tool calling in Ollama
# These get passed through WITHOUT prompt injection
NATIVE_TOOL_MODELS = {
    "qwen3", "qwen2.5", "qwen2", "llama3.1", "llama3.2", "llama3.3",
    "mistral", "mixtral", "command-r", "firefunction",
    "gemma4",  # Gemma 4 has native tool support
}

# Models that need tool calling injected via system prompt
# gemma3 is the main target — no native tool support in Ollama
INJECT_TOOL_MODELS = {
    "gemma3", "gemma2", "phi3", "phi4", "deepseek",
}


def _model_needs_injection(model: str) -> bool:
    """Check if a model needs tool calling injected via prompt."""
    base = model.split("/")[-1].split(":")[0].lower()
    if any(base.startswith(n) for n in NATIVE_TOOL_MODELS):
        return False
    return True


# ─── Tool Call Prompt Injection ───────────────────────────────────────────────

_TOOL_SYSTEM_HEADER = (
    "You have access to the following tools. To use a tool, respond with a JSON object "
    "in this EXACT format (no other text before or after):\n\n"
    "```tool_call\n"
    '{"name": "<tool_name>", "arguments": {"param": "value"}}\n'
    "```\n\n"
    "If you need to call multiple tools, use multiple ```tool_call``` blocks.\n\n"
    "If you don't need any tool, respond normally with text.\n\n"
    "Available tools:\n"
)


def _build_tool_definitions(tools: list[dict]) -> str:
    """Convert OpenAI tools array to readable text for prompt injection."""
    lines = []
    for tool in tools:
        fn = tool.get("function", tool)
        name = fn.get("name", "unknown")
        desc = fn.get("description", "")
        params = fn.get("parameters", {})
        props = params.get("properties", {})
        required = params.get("required", [])

        param_lines = []
        for pname, pinfo in props.items():
            ptype = pinfo.get("type", "string")
            pdesc = pinfo.get("description", "")
            req = " (required)" if pname in required else ""
            param_lines.append(f"    - {pname}: {ptype}{req} — {pdesc}")

        lines.append(f"- **{name}**: {desc}")
        if param_lines:
            lines.append("  Parameters:")
            lines.extend(param_lines)
        lines.append("")

    return "\n".join(lines)


def _inject_tools_into_messages(
    messages: list[dict], tools: list[dict]
) -> list[dict]:
    """Prepend tool definitions as a system message."""
    tool_defs = _build_tool_definitions(tools)
    system_msg = _TOOL_SYSTEM_HEADER + tool_defs

    # Check if there's already a system message
    injected = list(messages)
    if injected and injected[0].get("role") == "system":
        injected[0] = {
            **injected[0],
            "content": injected[0]["content"] + "\n\n" + system_msg,
        }
    else:
        injected.insert(0, {"role": "system", "content": system_msg})

    return injected


# ─── Tool Call Response Parsing ───────────────────────────────────────────────

# Pattern to find ```tool_call``` block boundaries (captures start position)
_TOOL_BLOCK_RE = re.compile(r"```tool_call\s*\n?", re.DOTALL)
_TOOL_BLOCK_END_RE = re.compile(r"\s*```")

# JSON decoder for nested brace matching (handles {"args": {"key": "val"}} correctly)
_JSON_DECODER = json.JSONDecoder()


def _extract_json_at(text: str, pos: int) -> tuple[dict | None, int]:
    """Extract a JSON object starting at `pos` using Python's parser.

    Unlike regex {.*?}, this correctly handles nested braces.
    Returns (parsed_dict, end_pos) or (None, pos) on failure.
    """
    # Skip whitespace
    while pos < len(text) and text[pos] in " \t\r\n":
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        return None, pos
    try:
        obj, end = _JSON_DECODER.raw_decode(text, pos)
        if isinstance(obj, dict):
            return obj, end
    except (json.JSONDecodeError, ValueError):
        pass
    return None, pos


def _make_tool_call(parsed: dict, index: int) -> dict:
    """Convert a parsed tool call dict to OpenAI format with unique ID."""
    return {
        "id": f"call_gw_{uuid.uuid4().hex[:12]}",
        "type": "function",
        "function": {
            "name": parsed.get("name", ""),
            "arguments": json.dumps(parsed.get("arguments", {})),
        },
    }


def _parse_tool_calls(content: str) -> tuple[list[dict], str]:
    """Extract tool calls from model response text.

    Uses json.JSONDecoder.raw_decode() instead of regex to correctly
    handle nested JSON in tool arguments (e.g., {"filter": {"key": "val"}}).

    Returns:
        (tool_calls, remaining_text) — tool_calls in OpenAI format
    """
    tool_calls = []
    remaining = content

    # Strategy 1: Find ```tool_call ... ``` blocks and parse JSON inside
    blocks_found = False
    segments_to_remove = []  # (start, end) spans to strip from remaining

    for block_match in _TOOL_BLOCK_RE.finditer(content):
        block_start = block_match.start()
        json_start = block_match.end()

        parsed, json_end = _extract_json_at(content, json_start)
        if parsed is None:
            continue

        # Find closing ```
        end_match = _TOOL_BLOCK_END_RE.match(content, json_end)
        block_end = end_match.end() if end_match else json_end

        blocks_found = True
        segments_to_remove.append((block_start, block_end))
        tool_calls.append(_make_tool_call(parsed, len(tool_calls)))

    if blocks_found:
        # Remove blocks from remaining text (reverse order to preserve positions)
        remaining_parts = []
        prev = 0
        for start, end in segments_to_remove:
            remaining_parts.append(content[prev:start])
            prev = end
        remaining_parts.append(content[prev:])
        remaining = "".join(remaining_parts).strip()
        return tool_calls, remaining

    # Strategy 2: Fallback — look for raw {"name": "...", "arguments": {...}} JSON
    # Use raw_decode to find JSON objects that look like tool calls
    pos = 0
    raw_segments = []
    while pos < len(content):
        idx = content.find('{"name"', pos)
        if idx == -1:
            break
        parsed, end = _extract_json_at(content, idx)
        if parsed and "name" in parsed:
            tool_calls.append(_make_tool_call(parsed, len(tool_calls)))
            raw_segments.append((idx, end))
            pos = end
        else:
            pos = idx + 1

    if tool_calls:
        remaining_parts = []
        prev = 0
        for start, end in raw_segments:
            remaining_parts.append(content[prev:start])
            prev = end
        remaining_parts.append(content[prev:])
        remaining = "".join(remaining_parts).strip()

    return tool_calls, remaining


# ─── Observability ────────────────────────────────────────────────────────────

@dataclass
class RequestMetric:
    model: str = ""
    agent: str = ""  # extracted from messages if available
    timestamp: str = ""
    duration_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tool_calls_injected: bool = False
    tool_calls_parsed: int = 0
    error: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class MetricsCollector:
    """Collect and aggregate request metrics."""

    def __init__(self, max_history: int = 500):
        self._history: deque[RequestMetric] = deque(maxlen=max_history)
        self._lock = __import__("threading").Lock()
        self._totals: dict[str, dict[str, int | float]] = defaultdict(
            lambda: {"requests": 0, "tokens": 0, "errors": 0, "duration_ms": 0}
        )

    def record(self, metric: RequestMetric):
        with self._lock:
            self._history.append(metric)
            key = f"{metric.model}:{metric.agent or 'unknown'}"
            self._totals[key]["requests"] += 1
            self._totals[key]["tokens"] += metric.total_tokens
            self._totals[key]["duration_ms"] += metric.duration_ms
            if metric.error:
                self._totals[key]["errors"] += 1

    def get_summary(self) -> dict:
        with self._lock:
            return {
                "total_requests": len(self._history),
                "by_model_agent": dict(self._totals),
                "recent": [asdict(m) for m in list(self._history)[-20:]],
            }

    def reset(self):
        with self._lock:
            self._history.clear()
            self._totals.clear()


metrics = MetricsCollector()


def _extract_agent_hint(messages: list[dict]) -> str:
    """Try to extract the agent name from the system message."""
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            # CrewAI typically includes "You are <Role>" in system
            match = re.search(r"You are (?:a |an |the )?(.+?)[\.\n]", content)
            if match:
                return match.group(1)[:50]
    return ""


# ─── Ollama Proxy ─────────────────────────────────────────────────────────────

def _proxy_to_ollama(endpoint: str, payload: dict | None = None, method: str = "POST") -> dict:
    """Forward request to Ollama and return parsed JSON response."""
    url = f"{OLLAMA_BASE_URL}{endpoint}"
    if payload:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
    else:
        req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=e.code, detail=body)
    except urllib.error.URLError as e:
        raise HTTPException(status_code=502, detail=f"Ollama unreachable: {e}")


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Factory AI Gateway — Nexus Router")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions with tool calling injection."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    start = time.time()
    model = body.get("model", "gemma3:12b")
    messages = body.get("messages", [])
    tools = body.get("tools", [])
    stream = body.get("stream", False)

    # Strip "ollama/" prefix that LiteLLM adds
    ollama_model = model.replace("ollama/", "")

    metric = RequestMetric(
        model=ollama_model,
        agent=_extract_agent_hint(messages),
    )

    needs_injection = tools and _model_needs_injection(ollama_model)

    # Build Ollama /api/chat payload
    ollama_payload: dict[str, Any] = {
        "model": ollama_model,
        "stream": False,  # We handle streaming separately if needed
        "options": {**DEFAULT_OLLAMA_OPTIONS, **body.get("extra_body", {}).get("options", {})},
    }

    if needs_injection:
        # Inject tools into system prompt, don't pass tools to Ollama
        ollama_payload["messages"] = _inject_tools_into_messages(messages, tools)
        metric.tool_calls_injected = True
    else:
        # Model supports native tools — pass through
        ollama_payload["messages"] = messages
        if tools:
            ollama_payload["tools"] = tools

    # Forward to Ollama
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: _proxy_to_ollama("/api/chat", ollama_payload)
        )
    except HTTPException as e:
        metric.error = str(e.detail)
        metric.duration_ms = int((time.time() - start) * 1000)
        metrics.record(metric)
        raise

    # Extract response
    message = result.get("message", {})
    content = message.get("content", "")
    native_tool_calls = message.get("tool_calls", [])

    # Parse tool calls from text if we injected
    parsed_tool_calls = []
    final_content = content
    if needs_injection and content:
        parsed_tool_calls, final_content = _parse_tool_calls(content)
        metric.tool_calls_parsed = len(parsed_tool_calls)

    # Normalize native tool calls to OpenAI format (Ollama uses different schema)
    if native_tool_calls:
        normalized_native = []
        for i, tc in enumerate(native_tool_calls):
            fn = tc.get("function", tc)
            normalized_native.append({
                "id": tc.get("id", f"call_gw_{uuid.uuid4().hex[:12]}"),
                "type": "function",
                "function": {
                    "name": fn.get("name", ""),
                    "arguments": json.dumps(fn.get("arguments", {}))
                        if isinstance(fn.get("arguments"), dict)
                        else fn.get("arguments", "{}"),
                },
            })
        final_tool_calls = normalized_native
    else:
        final_tool_calls = parsed_tool_calls

    # Collect metrics from Ollama response
    metric.prompt_tokens = result.get("prompt_eval_count", 0)
    metric.completion_tokens = result.get("eval_count", 0)
    metric.total_tokens = metric.prompt_tokens + metric.completion_tokens
    metric.duration_ms = int((time.time() - start) * 1000)
    metrics.record(metric)

    # Build OpenAI-compatible response
    response = {
        "id": f"chatcmpl-gw-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": final_content if final_content else None,
                },
                "finish_reason": "tool_calls" if final_tool_calls else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": metric.prompt_tokens,
            "completion_tokens": metric.completion_tokens,
            "total_tokens": metric.total_tokens,
        },
        "_gateway": {
            "tool_injection": needs_injection,
            "tool_calls_parsed": len(parsed_tool_calls),
            "duration_ms": metric.duration_ms,
            "ollama_model": ollama_model,
        },
    }

    if final_tool_calls:
        response["choices"][0]["message"]["tool_calls"] = final_tool_calls

    return response


@app.get("/v1/models")
async def list_models():
    """Proxy Ollama model list in OpenAI format."""
    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(
            None, lambda: _proxy_to_ollama("/api/tags", method="GET")
        )
    except HTTPException:
        return {"object": "list", "data": []}

    models = []
    for m in data.get("models", []):
        name = m.get("name", "")
        models.append({
            "id": f"ollama/{name}",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "ollama",
            "_supports_tools": not _model_needs_injection(name),
            "_size_gb": round(m.get("size", 0) / 1e9, 1),
        })
    return {"object": "list", "data": models}


# ─── Observability Endpoints ──────────────────────────────────────────────────

@app.get("/api/metrics")
async def get_metrics():
    """Return aggregated gateway metrics."""
    return metrics.get_summary()


@app.post("/api/metrics/reset")
async def reset_metrics():
    """Reset all metric counters."""
    metrics.reset()
    return {"status": "reset"}


@app.get("/api/health")
async def health():
    """Health check — also verifies Ollama connectivity."""
    ollama_ok = False
    ollama_models = []
    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            None, lambda: _proxy_to_ollama("/api/tags", method="GET")
        )
        ollama_ok = True
        ollama_models = [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"[Gateway] Health check — Ollama unreachable: {e}")

    return {
        "status": "ok",
        "ollama_url": OLLAMA_BASE_URL,
        "ollama_connected": ollama_ok,
        "ollama_models": ollama_models,
        "tool_injection_models": sorted(INJECT_TOOL_MODELS),
        "native_tool_models": sorted(NATIVE_TOOL_MODELS),
    }


# ─── Standalone Runner ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print(f"[Gateway] Starting on port {GATEWAY_PORT}")
    print(f"[Gateway] Proxying to Ollama at {OLLAMA_BASE_URL}")
    print(f"[Gateway] Tool injection for: {sorted(INJECT_TOOL_MODELS)}")
    print(f"[Gateway] Native tool pass-through for: {sorted(NATIVE_TOOL_MODELS)}")
    uvicorn.run(app, host="0.0.0.0", port=GATEWAY_PORT)
