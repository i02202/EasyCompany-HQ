"""
Campus Factory AI — Declarative Agent Loader
=============================================
Loads agent definitions from .md files in factory_ai/agents/ and converts
them to CrewAI Agent objects.

Each .md file has YAML frontmatter with:
  - role, goal, backstory (agent identity)
  - llm: "brain" | "tool" (which LLM to use)
  - max_iter: int
  - verbose: bool
  - tools: list of tool function names

This decouples agent config from Python code — edit a .md to change behavior,
no code changes needed. Inspired by EvoNexus (38 agents as .md files).
"""
import re
from pathlib import Path
from typing import Any

import yaml
from crewai import Agent

from factory_ai.config import FACTORY_ROOT

AGENTS_DIR = FACTORY_ROOT / "agents"

# ─── Tool Registry ───────────────────────────────────────────────────────────
# Maps tool function names (as strings in .md files) to actual tool objects.
# Populated by register_tools() at crew build time.

_tool_registry: dict[str, Any] = {}


def register_tools(tools_map: dict[str, Any]):
    """Register available tools so the loader can resolve names from .md files."""
    _tool_registry.update(tools_map)


def _resolve_tools(tool_names: list[str]) -> list:
    """Convert tool name strings to actual tool objects."""
    resolved = []
    for name in tool_names:
        if name in _tool_registry:
            resolved.append(_tool_registry[name])
        else:
            print(f"[AgentLoader] WARNING: Tool '{name}' not found in registry, skipping")
    return resolved


# ─── YAML Frontmatter Parser ─────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---", re.DOTALL)

_REQUIRED_FIELDS = {"role", "goal", "backstory"}


def _parse_agent_file(path: Path) -> dict:
    """Parse a .md agent file and return the YAML frontmatter as a dict."""
    content = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError(f"No YAML frontmatter found in {path}")
    config = yaml.safe_load(match.group(1))
    # Validate required fields with clear error messages
    missing = _REQUIRED_FIELDS - set(config or {})
    if missing:
        raise ValueError(f"Missing required fields {missing} in {path.name}")
    return config


# ─── Agent Builder ────────────────────────────────────────────────────────────

def load_agent(
    path: Path,
    llm_map: dict[str, Any],
) -> Agent:
    """Load a single agent from a .md file.

    Args:
        path: Path to the .md agent definition file
        llm_map: Maps "brain"/"tool" to LLM instances
    """
    config = _parse_agent_file(path)

    llm_key = config.get("llm", "brain")
    llm = llm_map.get(llm_key)
    if llm is None:
        raise ValueError(f"LLM '{llm_key}' not found in llm_map for agent {path.name}")

    tool_names = config.get("tools", [])
    # Guard: YAML scalar "tools: foo" becomes a string, not a list
    if isinstance(tool_names, str):
        tool_names = [tool_names]
    elif not isinstance(tool_names, list):
        tool_names = []
    tools = _resolve_tools(tool_names)

    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=tools,
        llm=llm,
        verbose=config.get("verbose", True),
        max_iter=config.get("max_iter", 6),
    )


def load_all_agents(
    llm_map: dict[str, Any],
    agents_dir: Path | None = None,
) -> dict[str, Agent]:
    """Load all agent .md files from a directory.

    Returns a dict mapping filename stem (e.g., 'researcher') to Agent.
    Files are loaded in alphabetical order.
    """
    directory = agents_dir or AGENTS_DIR
    if not directory.exists():
        raise FileNotFoundError(f"Agents directory not found: {directory}")

    agents = {}
    for md_file in sorted(directory.glob("*.md")):
        try:
            agent = load_agent(md_file, llm_map)
            agents[md_file.stem] = agent
            print(f"[AgentLoader] Loaded: {md_file.stem} ({agent.role})")
        except Exception as e:
            print(f"[AgentLoader] ERROR loading {md_file.name}: {e}")

    return agents
