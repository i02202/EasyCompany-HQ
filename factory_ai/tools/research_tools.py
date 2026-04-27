"""
Campus Factory AI — Web research tools for the Researcher agent.
Uses DuckDuckGo (ddgs) for searching, with hardcoded fallback data
for when search is rate-limited or unavailable.
"""
from crewai.tools import tool

try:
    from ddgs import DDGS
    HAS_DDG = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDG = True
    except ImportError:
        HAS_DDG = False

# Hardcoded reference data — fallback when search fails
OFFICE_REFERENCE_DATA = {
    "data_center": "Server racks (42U, 600x1070mm), cable trays, raised floor tiles, cooling units (CRAC), biometric door, monitoring wall with 4-6 screens, fire suppression panel. Density: 1 rack per 3m2.",
    "auditorium": "Tiered seating (450mm seat width, 900mm row spacing), podium (1200x600mm), projection screen (3-4m wide), ceiling speakers, ambient LED strips. 40-60 seats for medium room.",
    "noc_war_room": "L-shaped desks with 3 monitors each (2400x800mm per station), central war-table (2400x1200mm), wall dashboards (3x55in screens), red/amber alert lighting. 6-8 workstations.",
    "scrum_room": "Whiteboard walls (full wall coverage), standing desks (1200x600mm), sprint board (1800x1200mm), sticky note areas, bean bags for retro. Mobile furniture.",
    "open_cowork": "Hot-desks (1400x700mm, 1800mm between rows), monitor arms, ergonomic chairs (Herman Miller style), phone booths (1200x1200mm), plants as dividers. 12-16 desks.",
    "ceo_office": "Executive desk (2000x1000mm), leather chair, L-shaped sofa (2400x1800mm), bookshelf wall, small meeting table (1200mm round) with 4 chairs, art/awards display.",
    "huddle_pods": "4-person pods: round table (1000mm diameter), 4 chairs, wall-mounted screen (32in), acoustic panels. 3-4 pods in the zone. Soundproofing glass walls.",
    "snack_bar": "Counter (2400x600mm), 4 bar stools, full-size fridge, microwave, coffee machine (Nespresso/drip), snack shelving, waste bins. Compact efficient layout.",
    "cafe": "Bistro tables (600mm round, 2 per table), 4-top tables (900mm square), mix of chairs, plants, pendant lighting, counter with register. 6-8 tables total.",
    "gaming_lounge": "Gaming PCs (3-4 stations with 27in monitors), console area (TV 65in + sofa), bean bags (4-6), arcade cabinet, speakers, RGB LED strips. Casual relaxed layout.",
    "terrace": "Outdoor dining tables (1500mm round with umbrella), lounge chairs (sun loungers), planters with tall grasses, string lights overhead. Weather-resistant materials.",
    "green_area": "Large trees (canopy 3-4m), garden benches (1500mm), walking path (1200mm wide gravel), meditation circle (2m diameter), herb garden planters. Natural organic layout.",
    "architect": "Drafting tables (1500x1000mm, tilted), blueprint display wall, scale model showcase table (2000x1000mm), reference library shelf, task lighting. Creative studio feel.",
}

ISOMETRIC_REFERENCE = (
    "Isometric pixel art office references:\n"
    "- Habbo Hotel: 32x32 tile grid, furniture is 1-3 tiles, bright colors, clean outlines\n"
    "- Two Point Hospital: 64px tiles, detailed furniture sprites, consistent lighting from top-left\n"
    "- Project Zomboid: 128x64 isometric, realistic proportions, muted palette, strong shadows\n"
    "- Pixel Salvaje style: 128x64 tiles, modern furniture, clean isometric perspective, wood/metal/fabric textures\n"
    "- Key rules: consistent light source (NW), 2:1 width:height ratio for floor tiles, "
    "furniture depth conveyed through shadow and overlap, 1 tile = ~0.5m real world\n"
    "- Our grid: 128x64px per tile, diamond projection, props sized in tile units (desk=2.5x1.5, chair=1x1, sofa=3x1.5)"
)

FURNITURE_DIMENSIONS = {
    # Desks
    "desk": "Standard office desk: 1400x700mm (2.5x1.5 tiles). Executive desk: 2000x1000mm (3.5x2 tiles). Standing desk: 1200x600mm (2x1 tiles).",
    "standing_desk": "Sit-stand desk: 1400x700mm (2.5x1.5 tiles). Standing desk converter: 800x500mm (1.5x1 tile, sits on desk).",
    "reception_desk": "L-shaped reception: 2400x1200mm (4x2 tiles). Straight reception counter: 1800x600mm (3x1 tiles).",
    "drafting_table": "Architect drafting table: 1500x1000mm (2.5x2 tiles). Tilted surface, with task lamp.",
    # Chairs & seating
    "chair": "Office chair: 650x650mm (1x1 tile). Gaming chair: 700x700mm (1x1 tile). Bar stool: 400x400mm (1x1 tile).",
    "bean_bag": "Bean bag chair: 900x900mm (1.5x1.5 tiles). Floor cushion: 600x600mm (1x1 tile).",
    "bench": "Garden bench: 1500x500mm (2.5x1 tiles). Indoor bench: 1200x400mm (2x1 tiles).",
    "lounge_chair": "Sun lounger: 1800x600mm (3x1 tiles). Recliner: 800x900mm (1.5x1.5 tiles).",
    # Sofas
    "sofa": "2-seater sofa: 1500x800mm (2.5x1.5 tiles). 3-seater: 2000x800mm (3.5x1.5 tiles). L-shaped: 2400x1800mm corner piece.",
    # Tables
    "table": "Round meeting: 1200mm dia (2x2 tiles). Bistro: 600mm dia (1x1). Long conference: 3000x1200mm (5x2 tiles). Square: 900x900mm (1.5x1.5).",
    "coffee_table": "Coffee table: 1200x600mm (2x1 tiles). Side table: 500x500mm (1x1 tile).",
    # Tech
    "server_rack": "42U rack: 600x1070mm (1x2 tiles). Depth is critical — leave 1 tile clearance behind for cabling.",
    "monitor": "Single monitor: 600x200mm on desk. iMac: 500x200mm. Dual setup: 1200x200mm. Wall-mount TV: 1400x800mm (2x1 tiles).",
    "monitor_arm": "Dual monitor arm: clamps to desk, 600x200mm footprint. Frees desk space.",
    "laptop": "Laptop: 350x250mm (1x0.5 tiles). Laptop + stand: 400x300mm (1x1 tile).",
    "projector": "Ceiling projector: 350x250mm (1x1 tile). Projector screen: 2400x1800mm (4x1 tiles, wall-mounted).",
    "video_conf": "Video conferencing unit: 600x300mm (1x1 tile). Camera + speaker bar combo. Wall or table mounted.",
    "gaming_pc": "Gaming PC setup: desk + tower + dual monitors: 1800x800mm (3x1.5 tiles). RGB lighting.",
    "arcade_cabinet": "Arcade machine: 700x800mm (1.5x1.5 tiles). Tall visual (3 tiles height).",
    "speaker": "Floor speaker: 300x300mm (1x1 tile). Soundbar: 900x100mm (1.5x0.5 tiles, wall-mounted).",
    # Storage
    "bookshelf": "Standard: 900x350mm (1.5x0.5 tiles, drawn as 1x1 in iso). Tall: 900x350x2000mm (1x1 tile, 3 tiles height visual).",
    "filing_cabinet": "2-drawer: 400x600mm (1x1 tile). 4-drawer: 400x600mm (1x1 tile, taller visual).",
    "coat_rack": "Standing coat rack: 400x400mm (1x1 tile). Wall-mounted: 1200x200mm (2x0.5).",
    "locker": "Gym-style locker: 300x500mm (1x1 tile). Row of 4: 1200x500mm (2x1 tiles).",
    "umbrella_stand": "Umbrella stand: 250x250mm (1x1 tile). Near entrance doors.",
    # Appliances
    "fridge": "Office fridge: 600x600mm (1x1 tile). Full size: 600x700mm (1x1 tile, tall visual).",
    "coffee_machine": "Countertop: 400x300mm (1x1 tile). Commercial espresso: 600x500mm (1x1 tile).",
    "microwave": "Microwave: 500x350mm (1x1 tile). On counter or shelf.",
    "water_cooler": "Water dispenser: 350x350mm (1x1 tile). Floor-standing, near kitchenette.",
    "dishwasher": "Under-counter dishwasher: 600x600mm (1x1 tile). Part of kitchenette counter.",
    "toaster": "Toaster oven: 400x300mm (1x1 tile). On counter.",
    "vending_machine": "Snack/drink vending: 700x800mm (1.5x1.5 tiles). Tall visual.",
    "trash_bin": "Recycling station: 900x400mm (1.5x1 tiles). Separate bins for waste/recycle/compost.",
    # Boards & displays
    "whiteboard": "Standard: 1800x1200mm (3x0.5 tiles, wall-mounted). Mobile: 1200x900mm (2x0.5 tiles).",
    "sprint_board": "Kanban board: 1800x1200mm (3x1 tiles, wall-mounted). With sticky note areas.",
    "display_screen": "Digital signage: 55in wall-mount (1200x700mm, 2x1 tiles). Multi-screen wall: 3x55in (4x2 tiles).",
    # Dividers & acoustic
    "room_divider": "Office divider/screen: 1200x1800mm (2x0.5 tiles, freestanding). Creates visual separation.",
    "acoustic_panel": "Sound-absorbing panel: 1200x600mm (2x1 tiles, wall-mounted). For meeting rooms and pods.",
    "privacy_screen": "Desk privacy screen: 1200x500mm. Clips to desk, not a separate prop.",
    "phone_booth": "Single phone booth: 1200x1200mm (2x2 tiles). Soundproofed, with stool and shelf.",
    # Plants & decor
    "plant": "Potted fern: 400x400mm (1x1 tile). Tree: 600x600mm base (1x1 tile, 2-3 tiles height). Bush/planter: 800x400mm (1.5x1).",
    "planter_box": "Long planter: 1200x400mm (2x1 tiles). Used as room divider or wall accent.",
    "wall_art": "Framed art: 800x600mm (1.5x1 tiles, wall-mounted). Gallery wall: 2400x1200mm (4x2).",
    "clock": "Wall clock: 300x300mm (1x1 tile, wall-mounted). Decorative only.",
    "rug": "Area rug: 2000x3000mm (3.5x5 tiles). Under seating groups. Round rug: 2000mm dia (3x3 tiles).",
    # Outdoor
    "umbrella": "Patio umbrella: 2700mm dia (4x4 tiles). Provides shade over outdoor seating.",
    "planter_tall": "Tall planter with grasses: 600x600mm (1x1 tile). 1.5m height visual. For terrace borders.",
    "fire_pit": "Outdoor fire pit: 900mm dia (1.5x1.5 tiles). Decorative focal point.",
    "string_lights": "Overhead string lights: spanning area. Decorative, no floor footprint.",
    # Doors & access
    "door": "Standard: 900mm wide (1.5 tiles). Double: 1800mm (3 tiles). Glass sliding: 2400mm (4 tiles).",
    "turnstile": "Security turnstile: 1200x500mm (2x1 tiles). For data center / secure areas.",
    # Misc
    "cable_tray": "Under-desk cable management: 1200x150mm. Wall-mounted cable channel: full length.",
    "fire_extinguisher": "Wall-mounted: 200x200mm (1x1 tile). Required near kitchenette and data center.",
    "printer": "Office printer/MFP: 600x500mm (1x1 tile). Shared, near open workspace.",
    "paper_shredder": "Paper shredder: 400x300mm (1x1 tile). Near printer station.",
    "meditation_cushion": "Meditation zafu: 400x400mm (1x1 tile). In green area meditation circle.",
}


_SEARCH_POOL = None
_SEARCH_TIMEOUT_S = 5  # DDGS hangs frequently — bail fast and use curated fallback.


def _try_search(query: str, max_results: int = 5) -> list[dict]:
    """Attempt DDG search with hard timeout. Returns [] on failure.

    DDGS itself accepts no timeout argument and can hang indefinitely on slow
    or rate-limited endpoints. Wrapping in a ThreadPoolExecutor.future gives us
    a portable per-call deadline that works on Windows (unlike signal.alarm).
    """
    if not HAS_DDG:
        return []

    global _SEARCH_POOL
    if _SEARCH_POOL is None:
        from concurrent.futures import ThreadPoolExecutor
        # max_workers=4 caps parallel DDG calls so Claude's parallel tool use
        # doesn't open 10 concurrent DDG sockets (which guarantees rate-limit).
        _SEARCH_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ddgs")

    def _do_search() -> list[dict]:
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception:
            return []

    try:
        future = _SEARCH_POOL.submit(_do_search)
        return future.result(timeout=_SEARCH_TIMEOUT_S)
    except Exception:
        # TimeoutError, or anything else — fall back silently.
        return []


def _format_results(results: list[dict]) -> str:
    out = []
    for r in results:
        out.append(f"**{r.get('title', 'N/A')}**\n{r.get('href', '')}\n{r.get('body', '')}\n")
    return "\n---\n".join(out)


@tool("search_office_design")
def search_office_design(query: str) -> str:
    """Search for modern office/campus design references for a specific zone or topic.
    Returns web results plus curated reference data."""
    results = _try_search(f"modern tech office {query}", max_results=5)

    output_parts = []
    if results:
        output_parts.append("## Web Results\n" + _format_results(results))

    # Always include curated reference data
    output_parts.append("## Curated Office Design Reference")
    query_lower = query.lower()
    for zone, data in OFFICE_REFERENCE_DATA.items():
        if zone.replace("_", " ") in query_lower or query_lower in zone or not results:
            output_parts.append(f"**{zone}**: {data}")

    return "\n\n".join(output_parts) if output_parts else "No results found."


@tool("search_isometric_reference")
def search_isometric_reference(query: str) -> str:
    """Search for isometric pixel art references and game interior design examples."""
    results = _try_search(f"isometric pixel art office {query}", max_results=5)

    output_parts = []
    if results:
        output_parts.append("## Web Results\n" + _format_results(results))

    # Always include curated isometric reference
    output_parts.append("## Isometric Art Reference\n" + ISOMETRIC_REFERENCE)

    return "\n\n".join(output_parts)


@tool("search_furniture_dimensions")
def search_furniture_dimensions(furniture_type: str) -> str:
    """Get standard furniture dimensions for realistic prop sizing.
    Returns dimensions in mm and equivalent tile units."""
    results = _try_search(f"standard {furniture_type} dimensions cm office furniture", max_results=3)

    output_parts = []
    if results:
        output_parts.append("## Web Results\n" + _format_results(results))

    # Always include curated dimensions
    output_parts.append("## Reference Dimensions (Grid: 128x64px per tile, ~0.5m per tile)")
    ft_lower = furniture_type.lower()
    matched = False
    for key, data in FURNITURE_DIMENSIONS.items():
        if key in ft_lower or ft_lower in key:
            output_parts.append(f"**{key}**: {data}")
            matched = True
    if not matched:
        # Return all dimensions as reference
        for key, data in FURNITURE_DIMENSIONS.items():
            output_parts.append(f"**{key}**: {data}")

    return "\n\n".join(output_parts)
