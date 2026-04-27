"""
Campus Factory AI — DeerFlow Integration
==========================================
Uses DeerFlow's HTTP API for deep research tasks.
DeerFlow provides: multi-agent orchestration, web search, memory, sandbox.

This wraps DeerFlow as CrewAI tools so our agents can delegate
complex research to DeerFlow's subagent swarm.

Integration:
  HTTP mode preferred to avoid langchain/langgraph dependency conflicts.
  Start DeerFlow server separately:
    cd C:\\Users\\Daniel Amer\\deer-flow && npm run dev
  Gateway runs on port 8001, langgraph dev on 2024.
"""
import json
import os
import threading
import urllib.request
from pathlib import Path
from crewai.tools import tool

from factory_ai.config import DEERFLOW_URL
from factory_ai.events import bus, EventType

# DeerFlow availability — checked via HTTP health
_deerflow_available = None  # None = not yet checked
_health_lock = threading.Lock()


def _check_health() -> bool:
    """Check if DeerFlow gateway is reachable."""
    global _deerflow_available
    for endpoint in ["/api/models", "/docs", "/"]:
        try:
            resp = urllib.request.urlopen(f"{DEERFLOW_URL}{endpoint}", timeout=3)
            if resp.status == 200:
                _deerflow_available = True
                return True
        except Exception:
            continue
    _deerflow_available = False
    return False


def _deerflow_http_query(prompt: str) -> str:
    """Query DeerFlow via HTTP API with event emission."""
    bus.emit(EventType.AGENT_STEP, {
        "agent": "DeerFlow",
        "agent_name": "DeerFlow",
        "step_type": "tool_call",
        "tool": "deep_research",
        "content": f"Querying: {prompt[:100]}...",
    })

    try:
        # DeerFlow Gateway stateless run endpoint
        url = f"{DEERFLOW_URL}/api/runs/wait"
        data = json.dumps({
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "context": {"model_name": "qwen3-8b"},
        }).encode()
        req = urllib.request.Request(url, data, {"Content-Type": "application/json"})
        # DeerFlow multi-agent pipeline: Planner → Researcher → Synthesizer
        # Each step = 1 LLM call (~60-120s on local qwen3:8b with thinking) + web search
        # Total: 5-10 minutes per query on RTX 4060
        resp = urllib.request.urlopen(req, timeout=600)
        result = json.loads(resp.read())

        # Extract last AI message from the run output
        # Response format varies: check common patterns
        content = ""
        if isinstance(result, dict):
            # Pattern 1: {output: {messages: [...]}}
            messages = result.get("output", {}).get("messages", [])
            if not messages:
                # Pattern 2: {messages: [...]}
                messages = result.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("type") in ("ai", "assistant"):
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        # Content might be a list of blocks
                        content = " ".join(
                            b.get("text", str(b)) for b in content if isinstance(b, dict)
                        )
                    break
            if not content:
                content = str(result)[:2000]
        else:
            content = str(result)[:2000]

        bus.emit(EventType.AGENT_STEP, {
            "agent": "DeerFlow",
            "agent_name": "DeerFlow",
            "step_type": "finish",
            "tool": "deep_research",
            "content": content[:200],
        })
        return content

    except Exception as e:
        error_msg = f"[DeerFlow HTTP error: {e}]"
        bus.emit(EventType.AGENT_STEP, {
            "agent": "DeerFlow",
            "agent_name": "DeerFlow",
            "step_type": "finish",
            "tool": "deep_research",
            "content": error_msg,
        })
        return error_msg


def _fallback_research(prompt: str) -> str:
    """Fallback when DeerFlow is unavailable: use DDG search."""
    bus.emit(EventType.AGENT_STEP, {
        "agent": "DeerFlow",
        "agent_name": "DeerFlow",
        "step_type": "tool_call",
        "tool": "fallback_search",
        "content": f"DeerFlow unavailable, using DDG: {prompt[:80]}",
    })

    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(prompt, max_results=5))
            if results:
                summary = "\n\n".join(
                    f"**{r.get('title', '')}**\n{r.get('body', '')}"
                    for r in results
                )
                return f"[DeerFlow offline — DDG results]\n\n{summary}"
    except Exception as e:
        print(f"[DeerFlow fallback] DDG search failed: {e}")

    return f"[DeerFlow not available at {DEERFLOW_URL}. Start the DeerFlow server and retry.]"


@tool("deep_research")
def deep_research(topic: str) -> str:
    """
    Use DeerFlow's multi-agent swarm for deep research on a topic.
    DeerFlow has web search, memory, and can spawn subagents.
    Use this for complex research that requires multiple search queries
    and synthesis. Returns a comprehensive research report.
    Falls back to DuckDuckGo search if DeerFlow is unavailable.
    """
    prompt = (
        f"Research the following topic thoroughly and provide a comprehensive report "
        f"with specific details, measurements, and examples:\n\n{topic}\n\n"
        f"Focus on practical, actionable information. Include specific numbers, "
        f"dimensions, and real-world examples."
    )

    # Check health on first call or if previously unavailable
    with _health_lock:
        if _deerflow_available is None or not _deerflow_available:
            _check_health()
        available = _deerflow_available

    if available:
        return _deerflow_http_query(prompt)
    else:
        return _fallback_research(prompt)


@tool("analyze_reference_images")
def analyze_reference_images(description: str) -> str:
    """
    Use DeerFlow to search and analyze reference images for isometric
    office design. Describe what you're looking for and get back
    a synthesis of visual patterns and design elements.
    Falls back to DuckDuckGo if DeerFlow is unavailable.
    """
    prompt = (
        f"Search for and analyze reference images related to: {description}\n\n"
        f"For each reference found, describe:\n"
        f"1. Visual style (pixel art, 3D render, etc.)\n"
        f"2. Color palette used\n"
        f"3. Furniture arrangement patterns\n"
        f"4. How isometric perspective is handled\n"
        f"5. Key design elements that make it look professional"
    )

    with _health_lock:
        if _deerflow_available is None or not _deerflow_available:
            _check_health()
        available = _deerflow_available

    if available:
        return _deerflow_http_query(prompt)
    else:
        return _fallback_research(prompt)


def is_available() -> bool:
    """Check if DeerFlow is available (lazy health check)."""
    with _health_lock:
        if _deerflow_available is None:
            _check_health()
        return bool(_deerflow_available)
