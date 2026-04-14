"""
Campus Factory AI — DeerFlow Integration
==========================================
Uses DeerFlow's embedded SDK (DeerFlowClient) for deep research tasks.
DeerFlow provides: multi-agent orchestration, web search, memory, sandbox.

This wraps DeerFlow as CrewAI tools so our agents can delegate
complex research to DeerFlow's subagent swarm.

Integration decision (2026-04-13):
  HTTP fallback is preferred over SDK import to avoid langchain/langgraph
  dependency conflicts with CrewAI. Start DeerFlow server separately when needed:
    cd C:\\Users\\Daniel Amer\\deer-flow && npm run dev
"""
import sys
import os
from pathlib import Path
from crewai.tools import tool

# Add DeerFlow to path
DEERFLOW_ROOT = Path(os.getenv("DEERFLOW_ROOT", r"C:\Users\Daniel Amer\deer-flow"))
DEERFLOW_HARNESS = DEERFLOW_ROOT / "backend" / "packages" / "harness"

_deerflow_available = False
_client = None

if DEERFLOW_HARNESS.exists():
    sys.path.insert(0, str(DEERFLOW_HARNESS))
    try:
        from deerflow.client import DeerFlowClient
        _deerflow_available = True
        print("[DeerFlow] SDK found and imported")
    except ImportError as e:
        print(f"[DeerFlow] SDK import failed: {e}")
        print("[DeerFlow] Falling back to HTTP API mode")


def _get_client() -> "DeerFlowClient | None":
    """Lazy-init DeerFlow client."""
    global _client
    if not _deerflow_available:
        return None
    if _client is None:
        try:
            _client = DeerFlowClient(
                model_name="qwen3-8b",
                thinking_enabled=False,
                subagent_enabled=True,
            )
            print("[DeerFlow] Client initialized")
        except Exception as e:
            print(f"[DeerFlow] Client init failed: {e}")
            return None
    return _client


def _deerflow_query(prompt: str, timeout: int = 120) -> str:
    """Send a query to DeerFlow and get the response."""
    client = _get_client()
    if client is None:
        return "[DeerFlow not available — install at C:\\Users\\Daniel Amer\\deer-flow]"

    try:
        response = client.chat(prompt)
        if isinstance(response, str):
            return response
        return str(response)
    except Exception as e:
        return f"[DeerFlow error: {e}]"


def _deerflow_http_query(prompt: str) -> str:
    """Fallback: query DeerFlow via HTTP API."""
    import urllib.request
    import json

    try:
        url = "http://localhost:2026/api/langgraph/runs"
        data = json.dumps({
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "config": {"configurable": {"model_name": "qwen3-8b"}},
        }).encode()
        req = urllib.request.Request(url, data, {"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        # Extract last AI message
        messages = result.get("output", {}).get("messages", [])
        for msg in reversed(messages):
            if msg.get("type") == "ai":
                return msg.get("content", str(msg))
        return str(result)[:2000]
    except Exception as e:
        return f"[DeerFlow HTTP error: {e}]"


@tool("deep_research")
def deep_research(topic: str) -> str:
    """
    Use DeerFlow's multi-agent swarm for deep research on a topic.
    DeerFlow has web search, memory, and can spawn subagents.
    Use this for complex research that requires multiple search queries
    and synthesis. Returns a comprehensive research report.
    """
    prompt = (
        f"Research the following topic thoroughly and provide a comprehensive report "
        f"with specific details, measurements, and examples:\n\n{topic}\n\n"
        f"Focus on practical, actionable information. Include specific numbers, "
        f"dimensions, and real-world examples."
    )

    if _deerflow_available:
        return _deerflow_query(prompt)
    else:
        return _deerflow_http_query(prompt)


@tool("analyze_reference_images")
def analyze_reference_images(description: str) -> str:
    """
    Use DeerFlow to search and analyze reference images for isometric
    office design. Describe what you're looking for and get back
    a synthesis of visual patterns and design elements.
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

    if _deerflow_available:
        return _deerflow_query(prompt)
    else:
        return _deerflow_http_query(prompt)


def is_available() -> bool:
    """Check if DeerFlow is available."""
    return _deerflow_available
