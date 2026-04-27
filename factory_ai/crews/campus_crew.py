"""
Campus Factory AI — CrewAI Campus Redesign Crew
================================================
6 specialized agents with PROPERLY WIRED callbacks.

Architecture:
  - Default (Gateway mode): gemma3:12b via Gateway (:6000) → Ollama
    Gateway injects tool calling for models without native support + metrics
  - Direct mode (GATEWAY_ENABLED=false): Ollama direct (needs qwen3:8b or similar)
  - Claude mode (USE_CLAUDE_BRAIN=true): Claude Sonnet (brain) + Ollama (tools)
  - DeerFlow SDK → Deep research subtasks (Researcher agent only)

Each Task has a .callback that emits events to the EventBus,
which feeds the dashboard, Telegram bot, and training data collector.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env BEFORE any os.getenv calls
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

from crewai import Agent, Task, Crew, Process, LLM

# Fix httpx pool timeout — LiteLLM uses httpx internally but defaults pool=5s,
# which kills connections during long Ollama inferences (20-90s).
# We set both sync and async clients because CrewAI uses both paths internally.
# Verified by reading litellm/llms/openai/common_utils.py (1.83.0):
#   _get_sync_http_client()  → returns litellm.client_session if not None
#   _get_async_http_client() → returns litellm.aclient_session if not None
import httpx
import litellm
# 1200s aligns with Gateway's OLLAMA_HTTP_TIMEOUT — qwen3:8b on RTX 4060 with
# 16K context can take 10-15 min for the first call of each agent (cumulative context grows).
_HTTPX_TIMEOUT = httpx.Timeout(1200.0, connect=10.0, read=1200.0, write=30.0, pool=1200.0)
litellm.client_session = httpx.Client(timeout=_HTTPX_TIMEOUT)
litellm.aclient_session = httpx.AsyncClient(timeout=_HTTPX_TIMEOUT)

from factory_ai.config import OLLAMA_BASE_URL, OLLAMA_MODEL, ZONES, OUTPUT_DIR, GATEWAY_URL, GATEWAY_ENABLED
from factory_ai.events import bus, EventType
from factory_ai.crew_callbacks import crew_step_callback, make_task_callback
from factory_ai.tools.campus_tools import (
    read_campus_layout, read_campus_props, read_tile_atlas,
    read_campus_wander, get_zone_specs, read_zone_research, list_available_tiles,
    list_asset_packs, write_campus_props, write_zone_props, write_all_zone_props,
    write_tile_atlas, write_tile_mapping, write_design_report, analyze_prop_coverage,
)
from factory_ai.tools.research_tools import (
    search_office_design, search_isometric_reference, search_furniture_dimensions,
)
from factory_ai.tools.review_tools import (
    request_layout_review, request_visual_review, request_qa_review,
)
from factory_ai.tools.deerflow_tools import (
    deep_research, analyze_reference_images, is_available as deerflow_available,
)
from factory_ai.tools.interior_tools import (
    get_layout_template, get_placement_rules, validate_zone_layout,
    redesign_zone_layout, compute_smart_layout,
)
from factory_ai.tools.asset_gen_tools import (
    generate_prop_texture, generate_zone_textures, list_missing_textures,
)

# ─── LLM Configuration ─────────────────────────────────────────────────────
#
# Three modes:
#   1. Gateway mode (default): CrewAI → Gateway (:6000) → Ollama
#      - Tool calling injection for models without native support (gemma3)
#      - Observability: token tracking, latency per agent
#      - Single brain_llm for ALL agents (gemma3:12b handles tools via gateway)
#
#   2. Direct Ollama mode (GATEWAY_ENABLED=false): CrewAI → Ollama directly
#      - Requires a model with native tool calling (qwen3:8b)
#      - No metrics, no tool injection
#
#   3. Claude mode (USE_CLAUDE_BRAIN=true): Claude API for brain + Ollama for light
#

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USE_CLAUDE = os.getenv("USE_CLAUDE_BRAIN", "").lower() in ("1", "true", "yes")

# Shared Ollama options
_ollama_opts = {"num_ctx": 8192}


def _validate_setup():
    """Validate LLM connectivity at import time."""
    if USE_CLAUDE and ANTHROPIC_API_KEY:
        print(f"[Crew] Claude API enabled (brain) + Ollama {OLLAMA_MODEL} (light)")
    elif GATEWAY_ENABLED:
        print(f"[Crew] Gateway mode: {OLLAMA_MODEL} via {GATEWAY_URL} (tool injection + metrics)")
    else:
        print(f"[Crew] Direct Ollama mode: {OLLAMA_MODEL} (needs native tool support)")

    # Check Ollama is reachable
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        if OLLAMA_MODEL.split(":")[0] in " ".join(models):
            print(f"[Crew] Ollama OK: {OLLAMA_MODEL} found")
        else:
            print(f"[Crew] WARNING: {OLLAMA_MODEL} not found. Available: {models}")
    except Exception as e:
        print(f"[Crew] WARNING: Ollama not reachable at {OLLAMA_BASE_URL}: {e}")

    # Check Gateway if enabled
    if GATEWAY_ENABLED:
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{GATEWAY_URL}/api/health", timeout=3)
            data = json.loads(resp.read())
            print(f"[Crew] Gateway OK: {data.get('status', '?')}")
        except Exception as e:
            print(f"[Crew] WARNING: Gateway not reachable at {GATEWAY_URL}: {e}")


_validate_setup()

if USE_CLAUDE and ANTHROPIC_API_KEY:
    # Hybrid mode: Claude for complex reasoning, Ollama for light tasks
    brain_llm = LLM(
        # Use the alias (without date suffix) so we always get the latest stable
        # Sonnet 4.x. Hard-coded date strings get retired by Anthropic.
        model="anthropic/claude-sonnet-4-5",
        api_key=ANTHROPIC_API_KEY,
        temperature=0.7,
        # 429 rate-limit handling: LiteLLM auto-respects Anthropic's Retry-After
        # header. With tier-1 default (30K input tokens/min), the Architect's
        # cumulative-context calls easily exceed quota — this lets us recover
        # instead of crashing the crew on first hit.
        num_retries=5,
    )
    tool_llm = LLM(
        model=f"ollama/{OLLAMA_MODEL}",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
        timeout=600,
        extra_body={"options": _ollama_opts},
    )
elif GATEWAY_ENABLED:
    # Gateway mode: ALL agents use the same LLM routed through gateway
    # Gateway handles tool calling injection for models like gemma3:12b
    # LiteLLM sees it as an "OpenAI-compatible" endpoint
    brain_llm = LLM(
        model=f"openai/{OLLAMA_MODEL}",   # LiteLLM "openai/" prefix → custom base_url
        base_url=f"{GATEWAY_URL}/v1",
        api_key="not-needed",             # Gateway doesn't require auth
        temperature=0.7,
        # Must exceed Gateway's OLLAMA_HTTP_TIMEOUT (1200s). LiteLLM retries 3×;
        # at timeout=600 a single stuck call burns 30 min before crew_error fires.
        timeout=1800,
    )
    # With gateway, gemma3 can do tools — no need for separate tool_llm
    tool_llm = brain_llm
else:
    # Direct Ollama mode — model must support native tool calling
    brain_llm = LLM(
        model=f"ollama/{OLLAMA_MODEL}",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
        timeout=600,
        extra_body={"options": _ollama_opts},
    )
    tool_llm = brain_llm


# ─── Task Callbacks ──────────────────────────────────────────────────────
# crew_step_callback (imported) → fires on every LLM step, emits AGENT_STEP
# make_task_callback (imported) → per-task factory, emits AGENT_START + TASK_COMPLETE


# ─── Agent Definitions (loaded from .md files) ──────────────────────────────
# Agents are defined declaratively in factory_ai/agents/*.md
# Edit those files to change agent behavior — no Python changes needed.

from factory_ai.agent_loader import load_all_agents, register_tools
from factory_ai.memory import build_memory_prompt

# Register all tools so the loader can resolve names from .md files
register_tools({
    "read_campus_layout": read_campus_layout,
    "read_campus_props": read_campus_props,
    "read_tile_atlas": read_tile_atlas,
    "read_campus_wander": read_campus_wander,
    "get_zone_specs": get_zone_specs,
    "read_zone_research": read_zone_research,
    "list_available_tiles": list_available_tiles,
    "list_asset_packs": list_asset_packs,
    "write_campus_props": write_campus_props,
    "write_zone_props": write_zone_props,
    "write_all_zone_props": write_all_zone_props,
    "write_tile_atlas": write_tile_atlas,
    "write_tile_mapping": write_tile_mapping,
    "write_design_report": write_design_report,
    "analyze_prop_coverage": analyze_prop_coverage,
    "search_office_design": search_office_design,
    "search_isometric_reference": search_isometric_reference,
    "search_furniture_dimensions": search_furniture_dimensions,
    "request_layout_review": request_layout_review,
    "request_visual_review": request_visual_review,
    "request_qa_review": request_qa_review,
    "deep_research": deep_research,
    "analyze_reference_images": analyze_reference_images,
    "get_layout_template": get_layout_template,
    "get_placement_rules": get_placement_rules,
    "validate_zone_layout": validate_zone_layout,
    "redesign_zone_layout": redesign_zone_layout,
    "compute_smart_layout": compute_smart_layout,
    "generate_prop_texture": generate_prop_texture,
    "generate_zone_textures": generate_zone_textures,
    "list_missing_textures": list_missing_textures,
})

# Load agents from .md files
_agents = load_all_agents({"brain": brain_llm, "tool": tool_llm})

researcher = _agents["researcher"]
architect = _agents["architect"]
art_director = _agents["art_director"]
interior_designer = _agents["interior_designer"]
qa_reviewer = _agents["qa_reviewer"]
scrum_master = _agents["scrum_master"]

# Inject MemPalace memories into agent backstories (enriches with past learnings)
for name, agent in _agents.items():
    memory_ctx = build_memory_prompt(name)
    if memory_ctx:
        agent.backstory = (agent.backstory or "") + memory_ctx
        print(f"[Crew] MemPalace: injected memories for {name}")

# ─── Task Definitions (WITH CALLBACKS) ─────────────────────────────────────

zone_list = "\n".join(f"  - {name}: {spec['function']}" for name, spec in ZONES.items())

task_research = Task(
    description=(
        f"Research furniture for these 13 zones:\n{zone_list}\n\n"
        "Per zone: list 20-35 prop types with dimensions (w x d in meters). "
        "Include variety: acoustic panels, cable trays, whiteboards, kitchen items, decor, lockers. "
        "Use deep_research for comprehensive info. Use list_missing_textures to check gaps."
    ),
    expected_output="Structured furniture report per zone: items, proportions, placement notes.",
    agent=researcher,
    callback=make_task_callback("Research", "Researcher", OUTPUT_DIR),
)

task_layout = Task(
    description=(
        "Design prop placements for all 13 zones, ONE ZONE AT A TIME to keep prompts small.\n"
        "Zones: data_center, auditorium, noc_war_room, scrum_room, open_cowork, ceo_office, "
        "huddle_pods, snack_bar, cafe, gaming_lounge, terrace, green_area, architect.\n\n"
        "Per zone: call read_zone_research(zone) → get furniture list + placement_notes → "
        "design layout with realistic proportions, no overlaps, walkable paths → "
        "call write_zone_props(zone, props_json).\n\n"
        "Constraints: props within zone bounds (use get_zone_specs once if needed); "
        "corridors at rows 9-10, 19, 25, 32-33 stay empty.\n\n"
        "After all 13 zones written, call request_layout_review."
    ),
    expected_output="All 13 zones saved via write_zone_props + layout review submitted.",
    agent=architect,
    # NO context=[task_research] on purpose — Architect pulls per-zone slices via
    # read_zone_research instead. Keeps prompt under num_ctx (12288) at every iter.
    callback=make_task_callback("Layout", "Architect", OUTPUT_DIR),
)

task_visuals = Task(
    description=(
        "Map each prop ID to a Pixel Salvaje tile texture.\n"
        "1. Use list_available_tiles to see what exists on disk\n"
        "2. Use write_tile_mapping to save prop→tile JSON mappings\n"
        "3. Write a design report, then request_visual_review\n"
        "Only map to tiles that exist in assets/tiles/. Use write_tile_mapping (not write_tile_atlas)."
    ),
    expected_output="Tile mappings saved + design report + visual review submitted.",
    agent=art_director,
    context=[task_layout],
    callback=make_task_callback("Visuals", "Art Director", OUTPUT_DIR),
)

task_interior = Task(
    description=(
        "Optimize prop placement for all 13 zones using interior design principles.\n"
        "Per zone: get_layout_template → compute_smart_layout → redesign_zone_layout → validate_zone_layout.\n"
        "Rules: racks/shelves against walls, desks in clusters, 1-tile circulation paths, "
        "plants in corners, screens as focal points. Process ALL 13 zones."
    ),
    expected_output="Zone-by-zone report: template used, props rearranged, validation status.",
    agent=interior_designer,
    context=[task_layout],
    callback=make_task_callback("Interior Design", "Interior Designer", OUTPUT_DIR),
)

task_qa = Task(
    description=(
        "Validate all outputs: check props within bounds, no overlaps, function match, "
        "density OK, tile refs exist. Use request_qa_review to submit report."
    ),
    expected_output="QA report with issues found and fix recommendations.",
    agent=qa_reviewer,
    context=[task_layout, task_interior, task_visuals],
    callback=make_task_callback("QA Review", "QA Reviewer", OUTPUT_DIR),
)

task_summary = Task(
    description="Compile final summary: changes vs previous, pending QA issues, output file list. Write design report.",
    expected_output="Final markdown report summarizing the campus redesign.",
    agent=scrum_master,
    context=[task_layout, task_interior, task_visuals, task_qa],
    callback=make_task_callback("Summary", "Scrum Master", OUTPUT_DIR),
)

# ─── Crew Assembly ──────────────────────────────────────────────────────────

campus_crew = Crew(
    agents=[researcher, architect, art_director, interior_designer, qa_reviewer, scrum_master],
    tasks=[task_research, task_layout, task_interior, task_visuals, task_qa, task_summary],
    process=Process.sequential,
    verbose=True,
    memory=False,  # Disabled: requires /v1/embeddings (not in Gateway). We use MemPalace instead.
    step_callback=crew_step_callback,  # Real-time AGENT_STEP events for dashboard
)


def run():
    """Execute the campus redesign crew."""
    from factory_ai.memory import remember, remember_shared

    bus.emit(EventType.CREW_START, {"agents": 6, "tasks": 6})
    mode = "Gateway" if GATEWAY_ENABLED else ("Claude" if USE_CLAUDE else "Direct")
    print("=" * 60)
    print("  CAMPUS FACTORY AI — Starting Campus Redesign")
    print(f"  Mode: {mode} | Model: {OLLAMA_MODEL}")
    print("  Agents: Researcher, Architect, Art Director, Interior Designer, QA, Scrum Master")
    print("=" * 60)
    try:
        result = campus_crew.kickoff()
        bus.emit(EventType.CREW_COMPLETE, {"result_preview": str(result)[:500]})

        # Save learnings to MemPalace for future runs
        remember_shared(
            f"Crew run completed successfully with {OLLAMA_MODEL} in {mode} mode.",
            source_agent="system",
            category="milestone",
        )

        return result
    except Exception as e:
        bus.emit(EventType.CREW_ERROR, {"error": str(e)})
        # Remember failures too — helps avoid repeating mistakes
        remember_shared(
            f"Crew run failed: {str(e)[:200]}",
            source_agent="system",
            category="mistake",
        )
        raise
