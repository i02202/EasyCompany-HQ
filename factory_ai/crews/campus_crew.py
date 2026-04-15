"""
Campus Factory AI — CrewAI Campus Redesign Crew
================================================
5 specialized agents with PROPERLY WIRED callbacks.

Architecture:
  - Default: Ollama gemma3:12b (brain) → all agents, qwen3:8b (tools) → Scrum Master
  - Optional: USE_CLAUDE_BRAIN=true → Claude Sonnet (brain) + Ollama (light/tools)
  - DeerFlow SDK → Deep research subtasks (when available)

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

from factory_ai.config import OLLAMA_BASE_URL, OLLAMA_MODEL, ZONES, OUTPUT_DIR
from factory_ai.events import bus, EventType
from factory_ai.crew_callbacks import crew_step_callback, make_task_callback
from factory_ai.tools.campus_tools import (
    read_campus_layout, read_campus_props, read_tile_atlas,
    read_campus_wander, get_zone_specs, list_available_tiles,
    list_asset_packs, write_campus_props, write_zone_props,
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

# Claude API key kept for optional future use (e.g., single high-quality runs)
# Default: all agents on Ollama local to avoid rate limits
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USE_CLAUDE = os.getenv("USE_CLAUDE_BRAIN", "").lower() in ("1", "true", "yes")


def _validate_setup():
    """Validate LLM connectivity at import time."""
    if USE_CLAUDE and ANTHROPIC_API_KEY:
        print(f"[Crew] Claude API enabled (brain) + Ollama {OLLAMA_MODEL} (light)")
    else:
        print(f"[Crew] All-local mode: {OLLAMA_MODEL} (brain) + qwen3:8b (tools)")

    # Check Ollama is reachable
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        available = [m for m in ["qwen3:8b", OLLAMA_MODEL] if any(OLLAMA_MODEL in n or m in n for n in models)]
        if available:
            print(f"[Crew] Ollama OK: {', '.join(available)}")
        else:
            print(f"[Crew] WARNING: Expected models not found. Available: {models}")
    except Exception as e:
        print(f"[Crew] WARNING: Ollama not reachable at {OLLAMA_BASE_URL}: {e}")


_validate_setup()

if USE_CLAUDE and ANTHROPIC_API_KEY:
    # Hybrid mode: Claude for complex reasoning, Ollama for tools
    brain_llm = LLM(
        model="anthropic/claude-sonnet-4-20250514",
        api_key=ANTHROPIC_API_KEY,
        temperature=0.7,
    )
    light_llm = LLM(
        model=f"ollama/{OLLAMA_MODEL}",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )
    tool_llm = LLM(
        model="ollama/qwen3:8b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )
else:
    # All-local mode: OLLAMA_MODEL (brain) + qwen3:8b (tools) — no rate limits
    brain_llm = LLM(
        model=f"ollama/{OLLAMA_MODEL}",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )
    # tool_llm: qwen3:8b for Scrum Master (needs tool calling support)
    tool_llm = LLM(
        model="ollama/qwen3:8b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )


# ─── Task Callbacks ──────────────────────────────────────────────────────
# crew_step_callback (imported) → fires on every LLM step, emits AGENT_STEP
# make_task_callback (imported) → per-task factory, emits AGENT_START + TASK_COMPLETE


# ─── Agent Definitions ──────────────────────────────────────────────────────

researcher = Agent(
    role="Office Design Researcher",
    goal="Find the best modern tech office design references, furniture layouts, "
         "and isometric game art examples that match our campus spec.",
    backstory=(
        "You are a design researcher specializing in modern tech company offices "
        "(Google, Apple, WeWork style). You know isometric pixel art games like "
        "Project Zomboid, Habbo Hotel, and Two Point Hospital. Your job is to "
        "research what a world-class tech campus looks like and provide detailed "
        "reference information to the architect and art director."
    ),
    tools=[
        search_office_design, search_isometric_reference, search_furniture_dimensions,
        deep_research, analyze_reference_images,  # DeerFlow swarm tools
        list_missing_textures,  # Check what textures we need
    ],
    llm=brain_llm,  # Researcher on Claude for speed (Ollama was 10+ min)
    verbose=True,
    max_iter=8,
)

architect = Agent(
    role="Campus Architect",
    goal="Design the optimal furniture layout for each of the 13 zones, ensuring "
         "proper proportions, realistic spacing, and functional room definitions.",
    backstory=(
        "You are an expert in spatial design for isometric game environments. "
        "You understand that in our 40x40 grid, each tile is 128x64 pixels in "
        "isometric projection. Props have width (w) and height (h) in grid tiles. "
        "A standard desk is 2.5x1.5 tiles, a chair is 1x1, a sofa is 3x1.5. "
        "You ensure rooms have realistic furniture density — not too sparse, not "
        "overcrowded. Each zone must clearly communicate its function through "
        "furniture placement. Corridors (row 9-10, 19, 25, 32-33) must remain clear."
    ),
    tools=[
        read_campus_layout, read_campus_props, get_zone_specs,
        analyze_prop_coverage, write_zone_props, request_layout_review,
        deep_research,  # DeerFlow for zone-specific research
    ],
    llm=brain_llm,
    verbose=True,
    max_iter=25,
)

art_director = Agent(
    role="Visual Art Director",
    goal="Define the visual style for each zone — which Pixel Salvaje tiles to use "
         "for each prop, color consistency, size proportions, and fallback geometric styles.",
    backstory=(
        "You are a pixel art director who has worked on isometric games. You know "
        "that visual consistency is critical — all furniture in a zone should use "
        "the same art style and scale. You map each prop ID to the best available "
        "Pixel Salvaje tile texture, ensuring: (1) Consistent pixel density across "
        "all props, (2) Color harmony within each zone, (3) Proper isometric "
        "perspective for all items, (4) Fallback geometric styles that match the "
        "tile art quality. You produce the TileAtlas.ts mapping."
    ),
    tools=[
        list_available_tiles, list_asset_packs, read_tile_atlas,
        get_zone_specs, write_tile_mapping, write_tile_atlas, write_design_report, request_visual_review,
        generate_prop_texture, generate_zone_textures, list_missing_textures,  # fal.ai asset gen
        deep_research, analyze_reference_images,  # DeerFlow for visual research
    ],
    llm=brain_llm,
    verbose=True,
    max_iter=20,
)

qa_reviewer = Agent(
    role="Quality Assurance Reviewer",
    goal="Validate the campus design against specifications — check prop coverage, "
         "proportions, zone function match, and identify issues.",
    backstory=(
        "You are meticulous about quality. You check: (1) Every zone has enough "
        "props to look furnished but not cluttered, (2) Props don't overlap or "
        "extend beyond zone boundaries, (3) Each zone's furniture matches its "
        "function (server racks in data center, not sofas), (4) Proportions are "
        "consistent (a chair shouldn't be bigger than a desk), (5) All corridors "
        "remain walkable, (6) Door positions are logical."
    ),
    tools=[
        read_campus_props, read_campus_layout, get_zone_specs,
        analyze_prop_coverage, read_tile_atlas, request_qa_review,
        deep_research,  # DeerFlow for standards validation research
    ],
    llm=brain_llm,  # QA on Claude for speed + accuracy
    verbose=True,
    max_iter=8,
)

interior_designer = Agent(
    role="Interior Designer",
    goal="Optimize furniture placement in every zone using real interior design "
         "principles — spatial flow, functional grouping, wall adjacency, and "
         "circulation corridors.",
    backstory=(
        "You are a professional interior designer who specializes in tech office "
        "spaces. You understand spatial relationships deeply: server racks belong "
        "against walls in rows, desks cluster in work pods with chairs facing them, "
        "plants accent corners and entryways, screens center on walls as focal "
        "points, and every room needs clear circulation paths. You take the "
        "architect's raw prop list and REDESIGN the layout using proper spatial "
        "rules. You validate every zone against constraints (no overlaps, wall "
        "adjacency for mounted items, chair-desk pairing) and auto-fix violations. "
        "Your output is a polished, realistic office layout that looks intentional, "
        "not random."
    ),
    tools=[
        get_layout_template, get_placement_rules, validate_zone_layout,
        redesign_zone_layout, compute_smart_layout, get_zone_specs,
        deep_research,  # DeerFlow for spatial design research
    ],
    llm=brain_llm,
    verbose=True,
    max_iter=20,
)

scrum_master = Agent(
    role="Scrum Master / Coordinator",
    goal="Coordinate the team, ensure smooth handoffs between agents, track progress, "
         "and produce the final summary report.",
    backstory=(
        "You are the project coordinator for the Easy Company HQ campus redesign. "
        "You ensure the researcher provides actionable references, the architect "
        "produces a complete layout, the art director maps all textures, and the "
        "QA reviewer catches all issues. You produce the final summary."
    ),
    tools=[get_zone_specs, analyze_prop_coverage, write_design_report],
    llm=tool_llm,  # campus-expert doesn't support tools, use qwen3:8b
    verbose=True,
    max_iter=6,
)

# ─── Task Definitions (WITH CALLBACKS) ─────────────────────────────────────

zone_list = "\n".join(f"  - {name}: {spec['function']}" for name, spec in ZONES.items())

task_research = Task(
    description=(
        f"Research modern tech office design for a campus with these 13 zones:\n"
        f"{zone_list}\n\n"
        "For each zone, find:\n"
        "1. What furniture is typically found in that type of room — aim for 20-35 items per zone\n"
        "2. Standard furniture proportions (width x depth in meters)\n"
        "3. Include VARIETY: don't just list desks and chairs. Include:\n"
        "   - Acoustic panels, room dividers, privacy screens\n"
        "   - Cable trays, monitor arms, standing desk converters\n"
        "   - Whiteboards (mobile), projectors, video conferencing units\n"
        "   - Kitchen items: dishwasher, toaster, water cooler, trash/recycling\n"
        "   - Decor: wall art, clocks, rugs, coat racks, umbrella stands\n"
        "   - Reception desks, filing cabinets, lockers, fire extinguishers\n"
        "4. Visual reference for isometric pixel art renderings of similar rooms\n"
        "5. Use list_missing_textures to check which props need new textures generated\n\n"
        "IMPORTANT: Each zone should have 20-35 unique prop types. Previous iteration "
        "only had 9-20 per zone. Be comprehensive! A real office has MANY small items."
    ),
    expected_output=(
        "A structured report with furniture recommendations per zone, including "
        "item counts, proportions, and placement guidelines."
    ),
    agent=researcher,
    callback=make_task_callback("Research", "Researcher", OUTPUT_DIR),
)

task_layout = Task(
    description=(
        "Using the researcher's findings and the current campus data, redesign the "
        "prop placements for ALL 13 zones. You must:\n\n"
        "1. Read the current campus-props.ts and campus-layout.ts\n"
        "2. Analyze current prop coverage to identify sparse/overcrowded zones\n"
        "3. For each zone, design a complete furniture layout that:\n"
        "   - Matches the zone's function (use the zone specs)\n"
        "   - Has realistic proportions (desks ~2.5x1.5, chairs ~1x1, sofas ~3x1.5)\n"
        "   - Includes ALL necessary furniture types\n"
        "   - Respects zone boundaries\n"
        "   - Leaves walkable paths between furniture clusters\n"
        "   - Includes proper anchor points for agent seating/standing\n"
        "4. Use write_zone_props tool to save props for EACH zone separately.\n"
        "   Call it 13 times, once per zone. Pass zone_name and props_json.\n"
        "   Example: write_zone_props(zone_name='data_center', props_json='[{\"id\":\"server_rack\",\"x\":2,\"y\":2,\"w\":1,\"h\":2,\"layer\":\"below\",\"anchors\":[]}]')\n"
        "5. IMPORTANT: Use request_layout_review to submit a summary for human review.\n\n"
        "CRITICAL: Every prop must have valid x,y within its zone's grid bounds. "
        "Props must not overlap. Corridors must remain empty."
    ),
    expected_output=(
        "A complete campus-props.ts TypeScript file with all prop placements for "
        "all 13 zones, following the PropPlacement interface."
    ),
    agent=architect,
    context=[task_research],
    callback=make_task_callback("Layout", "Architect", OUTPUT_DIR),
)

task_visuals = Task(
    description=(
        "Review the architect's prop layout and the available tile textures, then:\n\n"
        "1. List all available Pixel Salvaje tiles on disk using list_available_tiles\n"
        "2. For each prop ID used in the layout, assign the best matching tile texture\n"
        "3. Ensure visual consistency within each zone\n"
        "4. Use write_tile_mapping tool to save the prop-to-tile mappings as JSON.\n"
        "   Call it with a JSON object: write_tile_mapping(mappings_json='{\"desk\":\"desk.png\",\"chair\":\"gaming-chair-a.png\"}')\n"
        "   You can call it multiple times — entries accumulate.\n"
        "5. Write a design report explaining your visual choices per zone\n"
        "6. Use request_visual_review to submit for human review.\n\n"
        "IMPORTANT: Only map to tiles that actually exist in assets/tiles/.\n"
        "DO NOT use write_tile_atlas — use write_tile_mapping instead (JSON format, more reliable)."
    ),
    expected_output=(
        "An updated TileAtlas.ts file mapping all prop IDs to tile textures, "
        "plus a design report with visual specifications per zone."
    ),
    agent=art_director,
    context=[task_layout],
    callback=make_task_callback("Visuals", "Art Director", OUTPUT_DIR),
)

task_interior = Task(
    description=(
        "You are the Interior Designer. The Architect has placed props in all 13 zones, "
        "but the layouts may be spatially naive (random positions, chairs not facing desks, "
        "racks in the middle of rooms, no circulation paths). Your job:\n\n"
        "FOR EACH OF THE 13 ZONES:\n"
        "1. Use get_layout_template to get the recommended layout rules for the zone\n"
        "2. Use compute_smart_layout to generate an optimized layout\n"
        "3. Review the result — does it make spatial sense?\n"
        "4. Use redesign_zone_layout to save the improved layout (with auto-fix)\n"
        "5. Use validate_zone_layout to confirm no errors remain\n\n"
        "DESIGN PRINCIPLES TO FOLLOW:\n"
        "- Wall-huggers: server_rack, bookshelf, whiteboard, screens → AGAINST WALLS\n"
        "- Desk clusters: desks in rows/pods with chairs facing them (offset +1 in y)\n"
        "- Circulation: leave 1-tile corridors between furniture groups\n"
        "- Corners: plants, decorative items\n"
        "- Focal points: TVs/screens centered on walls\n"
        "- Functional grouping: work items together, lounge items together\n\n"
        "Use get_placement_rules to see the full rulebook if needed.\n"
        "Process ALL 13 zones. Do not skip any."
    ),
    expected_output=(
        "A zone-by-zone report: for each zone, the template used, props rearranged, "
        "violations found and fixed, final validation status."
    ),
    agent=interior_designer,
    context=[task_layout],
    callback=make_task_callback("Interior Design", "Interior Designer", OUTPUT_DIR),
)

task_qa = Task(
    description=(
        "Review ALL outputs from the architect, interior designer, and art director:\n\n"
        "1. Verify all props are within zone boundaries\n"
        "2. Check for prop overlaps (x,y,w,h collisions)\n"
        "3. Verify each zone's furniture matches its function\n"
        "4. Check prop density is reasonable\n"
        "5. Verify all tile references exist\n"
        "6. Use request_qa_review to submit your QA report for human review"
    ),
    expected_output="A QA report listing all issues found with fix recommendations.",
    agent=qa_reviewer,
    context=[task_layout, task_interior, task_visuals],
    callback=make_task_callback("QA Review", "QA Reviewer", OUTPUT_DIR),
)

task_summary = Task(
    description=(
        "Compile the final summary of the campus redesign:\n\n"
        "1. Summarize what changed vs. the previous version\n"
        "2. List any QA issues that still need attention\n"
        "3. Provide the file list of outputs ready for integration\n"
        "4. Write the final design report"
    ),
    expected_output="A final markdown report summarizing the campus redesign.",
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
    memory=False,
    step_callback=crew_step_callback,  # Real-time AGENT_STEP events for dashboard
)


def run():
    """Execute the campus redesign crew."""
    bus.emit(EventType.CREW_START, {"agents": 6, "tasks": 6})
    print("=" * 60)
    print("  CAMPUS FACTORY AI — Starting Campus Redesign")
    if USE_CLAUDE and ANTHROPIC_API_KEY:
        print("  Brain: Claude Sonnet | Light: Ollama", OLLAMA_MODEL)
    else:
        print("  All agents: Ollama", OLLAMA_MODEL)
    print("  Agents: Researcher, Architect, Art Director, Interior Designer, QA, Scrum Master")
    print("=" * 60)
    try:
        result = campus_crew.kickoff()
        bus.emit(EventType.CREW_COMPLETE, {"result_preview": str(result)[:500]})
        return result
    except Exception as e:
        bus.emit(EventType.CREW_ERROR, {"error": str(e)})
        raise
