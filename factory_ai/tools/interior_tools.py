"""
Interior Design Tools — Spatial Placement Engine
=================================================
Provides the Interior Designer agent with:
  1. Layout templates per zone type (B)
  2. Rule-based placement within templates (A)
  3. Constraint validation + correction loop (C)

The engine places furniture using real interior design principles:
  - Wall-huggers (racks, shelving, screens) against edges
  - Desk clusters with chairs facing them
  - Circulation corridors (1-tile minimum)
  - Focal points (TVs, screens) centered on walls
  - Nature (plants) at corners and entries
  - Grouping by function (work, lounge, storage)
"""
import json
import math
from typing import Optional
from crewai.tools import tool

from factory_ai.config import OUTPUT_DIR, ZONES


# ─── Layout Templates ─────────────────────────────────────────────────────
# Each template defines placement RULES, not absolute positions.
# Rules are relative to zone bounds and adapt to any zone size.

LAYOUT_TEMPLATES = {
    "server_room": {
        "description": "Rows of racks with cooling on walls, monitoring desk near door",
        "rules": [
            {"category": "rack", "strategy": "grid_rows", "wall": "top", "spacing": 2, "margin": 1},
            {"category": "cooling", "strategy": "wall_spaced", "wall": "left", "spacing": 3},
            {"category": "monitor_station", "strategy": "corner", "corner": "bottom_right"},
            {"category": "security", "strategy": "wall_single", "wall": "top", "position": "start"},
            {"category": "display", "strategy": "wall_centered", "wall": "top"},
        ],
    },
    "meeting_room": {
        "description": "Central table with chairs around it, whiteboard on wall, screen opposite",
        "rules": [
            {"category": "table", "strategy": "center", "size": "large"},
            {"category": "chair", "strategy": "surround_table", "spacing": 1},
            {"category": "board", "strategy": "wall_centered", "wall": "left"},
            {"category": "screen", "strategy": "wall_centered", "wall": "right"},
            {"category": "plant", "strategy": "corners", "count": 2},
        ],
    },
    "open_office": {
        "description": "Desk clusters in rows with aisles, phone booths on edges",
        "rules": [
            {"category": "desk_cluster", "strategy": "parallel_rows", "aisle_width": 2, "cluster_size": 3},
            {"category": "chair", "strategy": "paired_with_desk", "offset_y": 1},
            {"category": "phone_booth", "strategy": "wall_spaced", "wall": "right", "spacing": 4},
            {"category": "plant", "strategy": "aisle_ends"},
            {"category": "storage", "strategy": "wall_spaced", "wall": "bottom", "spacing": 3},
        ],
    },
    "lounge": {
        "description": "Conversation clusters with sofas facing each other, coffee tables between",
        "rules": [
            {"category": "sofa_group", "strategy": "clusters", "cluster_count": "auto", "min_spacing": 3},
            {"category": "coffee_table", "strategy": "cluster_center"},
            {"category": "bean_bag", "strategy": "scatter", "near": "walls", "count": "auto"},
            {"category": "entertainment", "strategy": "wall_centered", "wall": "longest"},
            {"category": "plant", "strategy": "corners", "count": "auto"},
        ],
    },
    "cafe_dining": {
        "description": "Table-chair groups in a grid pattern with service counter on one side",
        "rules": [
            {"category": "counter", "strategy": "wall_full", "wall": "top"},
            {"category": "table_group", "strategy": "grid", "spacing": 3, "margin": 2},
            {"category": "chair", "strategy": "around_tables", "count_per_table": 2},
            {"category": "appliance", "strategy": "behind_counter"},
            {"category": "plant", "strategy": "scatter", "count": 2},
        ],
    },
    "executive": {
        "description": "Large desk facing door, lounge area, bookshelf wall, meeting corner",
        "rules": [
            {"category": "desk", "strategy": "focal_point", "position": "back_center"},
            {"category": "chair", "strategy": "behind_desk"},
            {"category": "bookshelf", "strategy": "wall_full", "wall": "top"},
            {"category": "lounge_set", "strategy": "corner_group", "corner": "bottom_left"},
            {"category": "meeting_set", "strategy": "corner_group", "corner": "bottom_right"},
            {"category": "plant", "strategy": "flanking", "target": "desk"},
            {"category": "decor", "strategy": "wall_accents"},
        ],
    },
    "outdoor": {
        "description": "Seating groups with nature, paths between, lighting at intervals",
        "rules": [
            {"category": "seating_group", "strategy": "scattered_clusters", "min_spacing": 4},
            {"category": "tree", "strategy": "organic_scatter", "density": 0.08},
            {"category": "planter", "strategy": "path_edges"},
            {"category": "lighting", "strategy": "grid", "spacing": 5},
            {"category": "feature", "strategy": "center"},
        ],
    },
    "tech_entertainment": {
        "description": "Gaming stations in rows, consoles with seating areas, open play space",
        "rules": [
            {"category": "pc_station", "strategy": "parallel_rows", "wall": "top", "spacing": 2},
            {"category": "console_area", "strategy": "clusters", "cluster_count": 2},
            {"category": "seating", "strategy": "facing_screens"},
            {"category": "game_table", "strategy": "center_area"},
            {"category": "bean_bag", "strategy": "scatter", "count": 4},
            {"category": "sound", "strategy": "corners"},
        ],
    },
    "creative_studio": {
        "description": "Drafting tables angled, material storage on walls, display area",
        "rules": [
            {"category": "workstation", "strategy": "angled_rows", "angle": 30, "spacing": 2},
            {"category": "stool", "strategy": "paired_with_workstation"},
            {"category": "storage", "strategy": "wall_full", "wall": "right"},
            {"category": "display", "strategy": "wall_centered", "wall": "left"},
            {"category": "reference", "strategy": "wall_section", "wall": "bottom"},
        ],
    },
    "huddle_pods": {
        "description": "Repeating pod units with glass walls, table and chairs per pod",
        "rules": [
            {"category": "pod_wall", "strategy": "pod_grid", "pod_size": 4, "margin": 1},
            {"category": "table", "strategy": "pod_center"},
            {"category": "chair", "strategy": "pod_surround", "count_per_pod": 4},
            {"category": "screen", "strategy": "pod_wall_mount"},
            {"category": "plant", "strategy": "between_pods"},
        ],
    },
}

# Map zone names to layout templates
ZONE_TEMPLATE_MAP = {
    "data_center": "server_room",
    "auditorium": "meeting_room",
    "noc_war_room": "meeting_room",
    "scrum_room": "meeting_room",
    "open_cowork": "open_office",
    "ceo_office": "executive",
    "huddle_pods": "huddle_pods",
    "snack_bar": "cafe_dining",
    "cafe": "cafe_dining",
    "gaming_lounge": "tech_entertainment",
    "terrace": "outdoor",
    "green_area": "outdoor",
    "architect": "creative_studio",
}

# Prop classification — which props belong to which layout category
PROP_CATEGORIES = {
    # Racks & Infrastructure
    "rack": ["server_rack"],
    "cooling": ["cooling_unit", "crac_cooling_unit"],
    "security": ["biometric_panel", "fire_suppression_panel"],
    # Monitoring
    "monitor_station": ["monitoring_desk", "noc_desk"],
    "display": ["monitoring_wall", "noc_screen_wall", "data_display_wall",
                 "projection_screen", "alert_dashboard", "big_tv", "presentation_display"],
    # Desks
    "desk": ["executive_desk", "standing_desk", "hot_desk"],
    "desk_cluster": ["standing_desk", "hot_desk", "desk_monitor"],
    "workstation": ["drafting_table", "monitor_workstation"],
    # Seating
    "chair": ["ergonomic_chair", "meeting_chair", "pod_chair", "executive_chair",
              "bistro_chair", "drafting_stool", "mobile_stool"],
    "sofa_group": ["l_shaped_sofa", "lounge_chair"],
    "bean_bag": ["bean_bag"],
    "seating": ["lounge_chair", "garden_bench"],
    "stool": ["drafting_stool", "bar_stool", "mobile_stool"],
    # Tables
    "table": ["round_table", "meeting_table", "war_table"],
    "coffee_table": ["coffee_table"],
    "table_group": ["cafe_table", "bistro_table"],
    "game_table": ["pool_table", "foosball_table"],
    # Walls & Boards
    "board": ["whiteboard_wall", "sprint_board", "cork_board"],
    "pod_wall": ["huddle_glass_wall"],
    "screen": ["wall_screen", "whiteboard"],
    # Counter & Appliances
    "counter": ["l_counter", "service_counter"],
    "appliance": ["espresso_machine", "commercial_fridge", "microwave",
                   "coffee_machine", "prep_sink", "vending_machine"],
    # Storage
    "storage": ["storage_locker", "storage_cabinet", "blueprint_storage",
                "material_library", "bookshelf", "ups_cabinet"],
    # Tech Entertainment
    "pc_station": ["gaming_pc_station"],
    "console_area": ["console_station", "console_tv", "vr_station"],
    "sound": ["sound_system", "ceiling_speaker"],
    "entertainment": ["arcade_cabinet", "rgb_led_strip"],
    # Plants & Nature
    "plant": ["tall_plant", "planter_varied"],
    "tree": ["mature_tree"],
    "planter": ["planter_varied", "flower_bed", "herb_garden", "vine_trellis"],
    "feature": ["zen_rock_arrangement", "water_fountain", "fire_pit",
                "meditation_circle", "hammock", "pergola"],
    # Outdoor
    "seating_group": ["outdoor_dining_set", "lounge_chair"],
    "lighting": ["outdoor_lighting", "pendant_light", "stage_lighting"],
    # Misc
    "phone_booth": ["phone_booth"],
    "decor": ["art_display", "sticky_note_dispenser", "snack_display"],
    "reference": ["material_library", "blueprint_storage"],
    "lounge_set": ["l_shaped_sofa", "coffee_table"],
    "meeting_set": ["meeting_table", "meeting_chair"],
}


# ─── Constraint Definitions ───────────────────────────────────────────────

CONSTRAINTS = [
    {
        "name": "no_overlap",
        "description": "No two props may occupy the same cell",
        "severity": "error",
    },
    {
        "name": "within_bounds",
        "description": "All props must be within zone boundaries",
        "severity": "error",
    },
    {
        "name": "circulation",
        "description": "At least 1-tile corridor must exist between furniture groups",
        "severity": "warning",
    },
    {
        "name": "wall_adjacency",
        "description": "Wall-mounted items must be on edge cells",
        "severity": "error",
    },
    {
        "name": "chair_desk_pairing",
        "description": "Chairs should be adjacent to a desk or table",
        "severity": "warning",
    },
    {
        "name": "density",
        "description": "Zone density should be 0.08-0.35 (props/tile)",
        "severity": "warning",
    },
]

WALL_HUGGERS = {
    "server_rack", "cooling_unit", "crac_cooling_unit", "bookshelf",
    "monitoring_wall", "noc_screen_wall", "data_display_wall",
    "whiteboard_wall", "huddle_glass_wall", "storage_locker",
    "storage_cabinet", "blueprint_storage", "material_library",
    "biometric_panel", "fire_suppression_panel", "vending_machine",
    "ups_cabinet",
}

CHAIR_LIKE = {
    "ergonomic_chair", "executive_chair", "meeting_chair", "pod_chair",
    "drafting_stool", "mobile_stool", "bar_stool", "bistro_chair",
    "gaming_chair",
}

DESK_LIKE = {
    "standing_desk", "hot_desk", "executive_desk", "drafting_table",
    "desk_monitor", "monitoring_desk", "noc_desk", "round_table",
    "meeting_table", "cafe_table", "bistro_table", "war_table",
}


# ─── Placement Engine ─────────────────────────────────────────────────────

def _zone_bounds(zone_name: str) -> tuple:
    """Return (r0, r1, c0, c1) for a zone."""
    spec = ZONES[zone_name]
    return spec["rows"][0], spec["rows"][1], spec["cols"][0], spec["cols"][1]


def _place_wall(items: list, zone_name: str, wall: str, spacing: int = 2,
                margin: int = 1) -> list:
    """Place items along a wall edge with given spacing."""
    r0, r1, c0, c1 = _zone_bounds(zone_name)
    placed = []
    if wall == "top":
        y = r0 + margin
        for i, item in enumerate(items):
            x = c0 + margin + i * spacing
            if x <= c1 - margin:
                placed.append({**item, "x": x, "y": y})
    elif wall == "bottom":
        y = r1 - margin
        for i, item in enumerate(items):
            x = c0 + margin + i * spacing
            if x <= c1 - margin:
                placed.append({**item, "x": x, "y": y})
    elif wall == "left":
        x = c0 + margin
        for i, item in enumerate(items):
            y = r0 + margin + i * spacing
            if y <= r1 - margin:
                placed.append({**item, "x": x, "y": y})
    elif wall == "right":
        x = c1 - margin
        for i, item in enumerate(items):
            y = r0 + margin + i * spacing
            if y <= r1 - margin:
                placed.append({**item, "x": x, "y": y})
    return placed


def _place_grid(items: list, zone_name: str, spacing: int = 2,
                margin: int = 2) -> list:
    """Place items in a grid pattern within the zone."""
    r0, r1, c0, c1 = _zone_bounds(zone_name)
    placed = []
    idx = 0
    y = r0 + margin
    while y <= r1 - margin and idx < len(items):
        x = c0 + margin
        while x <= c1 - margin and idx < len(items):
            placed.append({**items[idx], "x": x, "y": y})
            idx += 1
            x += spacing
        y += spacing
    return placed


def _place_center(item: dict, zone_name: str) -> list:
    """Place a single item at zone center."""
    r0, r1, c0, c1 = _zone_bounds(zone_name)
    cx = (c0 + c1) / 2
    cy = (r0 + r1) / 2
    return [{**item, "x": round(cx, 1), "y": round(cy, 1)}]


def _place_corners(items: list, zone_name: str) -> list:
    """Place items in corners of the zone (inset by 1)."""
    r0, r1, c0, c1 = _zone_bounds(zone_name)
    corners = [
        (c0 + 1, r0 + 1),  # top-left
        (c1 - 1, r0 + 1),  # top-right
        (c0 + 1, r1 - 1),  # bottom-left
        (c1 - 1, r1 - 1),  # bottom-right
    ]
    placed = []
    for i, item in enumerate(items):
        if i < len(corners):
            placed.append({**item, "x": corners[i][0], "y": corners[i][1]})
    return placed


def _place_paired(chairs: list, desks: list, offset_y: float = 1.0) -> list:
    """Place chairs facing desks (offset by 1 tile in y)."""
    placed = []
    for i, chair in enumerate(chairs):
        if i < len(desks):
            placed.append({
                **chair,
                "x": desks[i]["x"],
                "y": desks[i]["y"] + offset_y,
            })
    return placed


def _place_surrounding(chairs: list, table: dict, spacing: float = 1.0) -> list:
    """Place chairs around a central table."""
    offsets = [
        (0, -spacing),       # top
        (0, spacing),        # bottom
        (-spacing, 0),       # left
        (spacing, 0),        # right
        (-spacing, -spacing),
        (spacing, -spacing),
        (-spacing, spacing),
        (spacing, spacing),
    ]
    placed = []
    for i, chair in enumerate(chairs):
        if i < len(offsets):
            placed.append({
                **chair,
                "x": round(table["x"] + offsets[i][0], 1),
                "y": round(table["y"] + offsets[i][1], 1),
            })
    return placed


# ─── Constraint Validator ─────────────────────────────────────────────────

def validate_layout(props: list, zone_name: str) -> list:
    """
    Validate a prop layout against all constraints.
    Returns list of {constraint, severity, message, fix_hint}.
    """
    violations = []
    r0, r1, c0, c1 = _zone_bounds(zone_name)
    area = (r1 - r0 + 1) * (c1 - c0 + 1)

    # 1. No overlap — check for props occupying same cell
    occupied = {}
    for p in props:
        key = f"{round(p['x'])}-{round(p['y'])}"
        if key in occupied:
            violations.append({
                "constraint": "no_overlap",
                "severity": "error",
                "message": f"{p['id']} overlaps with {occupied[key]} at ({p['x']}, {p['y']})",
                "fix_hint": f"Move {p['id']} by +1 in x or y",
            })
        else:
            occupied[key] = p["id"]

    # 2. Within bounds
    for p in props:
        px, py = p["x"], p["y"]
        pw = p.get("w", 1)
        ph = p.get("h", 1)
        if px < c0 or px + pw - 1 > c1 or py < r0 or py + ph - 1 > r1:
            violations.append({
                "constraint": "within_bounds",
                "severity": "error",
                "message": f"{p['id']} at ({px}, {py}) is outside zone {zone_name} bounds",
                "fix_hint": f"Clamp to [{c0}-{c1}, {r0}-{r1}]",
            })

    # 3. Wall adjacency for wall-huggers
    for p in props:
        if p["id"] in WALL_HUGGERS:
            on_edge = (
                round(p["x"]) == c0 or round(p["x"]) == c1 or
                round(p["y"]) == r0 or round(p["y"]) == r1 or
                round(p["x"]) == c0 + 1 or round(p["x"]) == c1 - 1 or
                round(p["y"]) == r0 + 1 or round(p["y"]) == r1 - 1
            )
            if not on_edge:
                violations.append({
                    "constraint": "wall_adjacency",
                    "severity": "warning",
                    "message": f"{p['id']} should be against a wall but is at ({p['x']}, {p['y']})",
                    "fix_hint": "Move to nearest wall edge",
                })

    # 4. Chair-desk pairing
    desk_positions = {(round(p["x"]), round(p["y"])) for p in props if p["id"] in DESK_LIKE}
    for p in props:
        if p["id"] in CHAIR_LIKE:
            px, py = round(p["x"]), round(p["y"])
            has_adjacent_desk = any(
                abs(px - dx) <= 2 and abs(py - dy) <= 2
                for dx, dy in desk_positions
            )
            if not has_adjacent_desk and desk_positions:
                violations.append({
                    "constraint": "chair_desk_pairing",
                    "severity": "warning",
                    "message": f"{p['id']} at ({p['x']}, {p['y']}) has no desk/table within 2 tiles",
                    "fix_hint": "Move chair adjacent to nearest desk",
                })

    # 5. Density check
    density = len(props) / area if area > 0 else 0
    if density < 0.08:
        violations.append({
            "constraint": "density",
            "severity": "warning",
            "message": f"Zone {zone_name} is sparse: {density:.2f} props/tile ({len(props)} props in {area} tiles)",
            "fix_hint": "Add more props to fill the space",
        })
    elif density > 0.35:
        violations.append({
            "constraint": "density",
            "severity": "warning",
            "message": f"Zone {zone_name} is overcrowded: {density:.2f} props/tile",
            "fix_hint": "Remove some props or increase spacing",
        })

    return violations


def auto_fix_violations(props: list, zone_name: str, violations: list) -> list:
    """
    Attempt to automatically fix constraint violations.
    Returns corrected props list.
    """
    r0, r1, c0, c1 = _zone_bounds(zone_name)
    fixed = [dict(p) for p in props]  # Deep copy

    for v in violations:
        if v["constraint"] == "within_bounds" and v["severity"] == "error":
            # Clamp to zone bounds
            for p in fixed:
                p["x"] = max(c0, min(c1, p["x"]))
                p["y"] = max(r0, min(r1, p["y"]))

        elif v["constraint"] == "no_overlap" and v["severity"] == "error":
            # Nudge overlapping props
            occupied = set()
            for p in fixed:
                key = (round(p["x"]), round(p["y"]))
                attempts = 0
                while key in occupied and attempts < 8:
                    # Try shifting in a spiral pattern
                    dx = [1, 0, -1, 0, 1, -1, 1, -1][attempts]
                    dy = [0, 1, 0, -1, 1, 1, -1, -1][attempts]
                    p["x"] = round(p["x"] + dx, 1)
                    p["y"] = round(p["y"] + dy, 1)
                    key = (round(p["x"]), round(p["y"]))
                    attempts += 1
                occupied.add(key)

        elif v["constraint"] == "wall_adjacency" and v["severity"] == "warning":
            # Move wall-huggers to nearest wall
            for p in fixed:
                if p["id"] in WALL_HUGGERS:
                    px, py = p["x"], p["y"]
                    distances = {
                        "top": py - r0,
                        "bottom": r1 - py,
                        "left": px - c0,
                        "right": c1 - px,
                    }
                    nearest = min(distances, key=distances.get)
                    if nearest == "top":
                        p["y"] = r0 + 1
                    elif nearest == "bottom":
                        p["y"] = r1 - 1
                    elif nearest == "left":
                        p["x"] = c0 + 1
                    elif nearest == "right":
                        p["x"] = c1 - 1

    return fixed


# ─── CrewAI Tools ─────────────────────────────────────────────────────────

@tool("get_layout_template")
def get_layout_template(zone_name: str) -> str:
    """Get the recommended layout template for a zone. Returns the template
    name, description, and placement rules as JSON."""
    template_key = ZONE_TEMPLATE_MAP.get(zone_name)
    if not template_key:
        return json.dumps({"error": f"No template for zone '{zone_name}'"})

    template = LAYOUT_TEMPLATES[template_key]
    spec = ZONES.get(zone_name, {})
    r0, r1 = spec.get("rows", (0, 0))
    c0, c1 = spec.get("cols", (0, 0))

    return json.dumps({
        "zone": zone_name,
        "template": template_key,
        "description": template["description"],
        "zone_size": {"rows": r1 - r0 + 1, "cols": c1 - c0 + 1,
                      "area": (r1 - r0 + 1) * (c1 - c0 + 1)},
        "zone_bounds": {"r0": r0, "r1": r1, "c0": c0, "c1": c1},
        "zone_function": spec.get("function", ""),
        "wall_type": spec.get("wall", ""),
        "rules": template["rules"],
    }, indent=2)


@tool("get_placement_rules")
def get_placement_rules() -> str:
    """Get all interior design placement rules, prop categories, and constraints.
    Use this to understand how furniture should be placed."""
    return json.dumps({
        "wall_huggers": "Props that must be against walls: " + ", ".join(sorted(WALL_HUGGERS)),
        "chair_desk_pairing": "Chairs must be within 2 tiles of a desk/table",
        "circulation": "Keep 1-tile corridors between furniture groups for walkability",
        "density_range": "Target 0.08-0.35 props per tile",
        "corners": "Plants and decorative items go in corners",
        "focal_points": "Screens and displays should be centered on walls",
        "prop_categories": {k: v for k, v in PROP_CATEGORIES.items()},
        "constraints": CONSTRAINTS,
    }, indent=2)


@tool("validate_zone_layout")
def validate_zone_layout(zone_name: str) -> str:
    """Validate the current prop layout for a zone against interior design
    constraints. Returns violations with severity and fix hints."""
    zone_file = OUTPUT_DIR / "zones" / f"{zone_name}.json"
    if not zone_file.exists():
        return json.dumps({"error": f"No layout file for zone '{zone_name}'"})

    props = json.loads(zone_file.read_text(encoding="utf-8"))
    violations = validate_layout(props, zone_name)

    errors = [v for v in violations if v["severity"] == "error"]
    warnings = [v for v in violations if v["severity"] == "warning"]

    return json.dumps({
        "zone": zone_name,
        "props_count": len(props),
        "errors": len(errors),
        "warnings": len(warnings),
        "violations": violations,
        "verdict": "PASS" if not errors else "FAIL",
    }, indent=2)


@tool("redesign_zone_layout")
def redesign_zone_layout(zone_name: str, props_json: str) -> str:
    """Apply a new layout to a zone, validate it, auto-fix violations,
    and save the result. Input is JSON array of props with id, x, y, w, h.
    Returns validation result after fixes."""
    try:
        props = json.loads(props_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    if zone_name not in ZONES:
        return json.dumps({"error": f"Unknown zone: {zone_name}"})

    # Validate
    violations = validate_layout(props, zone_name)
    errors = [v for v in violations if v["severity"] == "error"]

    # Auto-fix if errors found
    fix_rounds = 0
    while errors and fix_rounds < 3:
        props = auto_fix_violations(props, zone_name, violations)
        violations = validate_layout(props, zone_name)
        errors = [v for v in violations if v["severity"] == "error"]
        fix_rounds += 1

    # Save
    zone_file = OUTPUT_DIR / "zones" / f"{zone_name}.json"
    zone_file.parent.mkdir(parents=True, exist_ok=True)
    zone_file.write_text(json.dumps(props, indent=2, ensure_ascii=False), encoding="utf-8")

    # Emit event
    from factory_ai.events import bus, EventType
    bus.emit(EventType.FILE_WRITTEN, {
        "file": f"zones/{zone_name}.json",
        "props": len(props),
        "fix_rounds": fix_rounds,
    })

    remaining_warnings = [v for v in violations if v["severity"] == "warning"]
    return json.dumps({
        "zone": zone_name,
        "saved": True,
        "props_count": len(props),
        "fix_rounds_applied": fix_rounds,
        "remaining_warnings": len(remaining_warnings),
        "warnings": remaining_warnings,
        "verdict": "PASS" if not errors else "FAIL_AFTER_FIXES",
    }, indent=2)


@tool("compute_smart_layout")
def compute_smart_layout(zone_name: str) -> str:
    """Automatically compute an optimized furniture layout for a zone using
    the template engine. Reads existing props, applies spatial rules, and
    returns the improved layout as JSON (does NOT save — use redesign_zone_layout
    to save after review)."""
    if zone_name not in ZONES:
        return json.dumps({"error": f"Unknown zone: {zone_name}"})

    spec = ZONES[zone_name]
    r0, r1 = spec["rows"]
    c0, c1 = spec["cols"]
    template_key = ZONE_TEMPLATE_MAP.get(zone_name, "open_office")
    template = LAYOUT_TEMPLATES.get(template_key, LAYOUT_TEMPLATES["open_office"])

    # Read existing props to preserve the prop selection
    zone_file = OUTPUT_DIR / "zones" / f"{zone_name}.json"
    existing = []
    if zone_file.exists():
        existing = json.loads(zone_file.read_text(encoding="utf-8"))

    if not existing:
        return json.dumps({"error": "No existing props to rearrange"})

    # Classify existing props
    classified = {}
    for p in existing:
        pid = p["id"]
        # Find which category this prop belongs to
        cat = "misc"
        for category, members in PROP_CATEGORIES.items():
            if pid in members:
                cat = category
                break
        classified.setdefault(cat, []).append(p)

    # Apply placement rules based on template
    result = []
    placed_positions = set()

    def try_place(prop, x, y):
        key = (round(x), round(y))
        if key not in placed_positions and c0 <= x <= c1 and r0 <= y <= r1:
            placed_positions.add(key)
            result.append({**prop, "x": round(x, 1), "y": round(y, 1)})
            return True
        return False

    # Phase 1: Wall-huggers go to edges first
    for p in existing:
        if p["id"] in WALL_HUGGERS:
            # Find best wall based on template hints
            placed = False
            # Try top wall first, then left, right, bottom
            for wall_y in [r0 + 1, r1 - 1]:
                for x in range(c0 + 1, c1):
                    if try_place(p, x, wall_y):
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                for wall_x in [c0 + 1, c1 - 1]:
                    for y in range(r0 + 1, r1):
                        if try_place(p, wall_x, y):
                            placed = True
                            break
                    if placed:
                        break

    # Phase 2: Desks/tables in organized rows with aisles
    desk_props = [p for p in existing if p["id"] in DESK_LIKE and p not in result]
    row_y = r0 + 2
    col_x = c0 + 2
    for p in desk_props:
        if try_place(p, col_x, row_y):
            col_x += 3  # spacing between desks
            if col_x > c1 - 2:
                col_x = c0 + 2
                row_y += 3  # next row with aisle

    # Phase 3: Chairs paired with desks
    chair_props = [p for p in existing if p["id"] in CHAIR_LIKE and p not in result]
    desk_results = [p for p in result if p["id"] in DESK_LIKE]
    for i, chair in enumerate(chair_props):
        if i < len(desk_results):
            desk = desk_results[i]
            try_place(chair, desk["x"], desk["y"] + 1)
        else:
            # Extra chairs: scatter in remaining space
            for y in range(r0 + 2, r1 - 1):
                placed = False
                for x in range(c0 + 2, c1 - 1):
                    if try_place(chair, x, y):
                        placed = True
                        break
                if placed:
                    break

    # Phase 4: Plants in corners and accent positions
    plant_props = [p for p in existing
                   if p["id"] in ("tall_plant", "planter_varied", "mature_tree",
                                   "flower_bed", "herb_garden")
                   and p not in result]
    corners = [
        (c0 + 1, r0 + 1), (c1 - 1, r0 + 1),
        (c0 + 1, r1 - 1), (c1 - 1, r1 - 1),
    ]
    for i, p in enumerate(plant_props):
        if i < len(corners):
            try_place(p, corners[i][0], corners[i][1])
        else:
            # Mid-points of walls
            try_place(p, (c0 + c1) / 2, r0 + 1) or try_place(p, (c0 + c1) / 2, r1 - 1)

    # Phase 5: Everything else — fill remaining space with spacing
    remaining = [p for p in existing if not any(
        round(p.get("x", -1)) == round(r.get("x", -2)) and
        round(p.get("y", -1)) == round(r.get("y", -2)) and
        p["id"] == r["id"]
        for r in result
    )]
    # Actually check which original props haven't been placed yet
    placed_ids_count = {}
    for r in result:
        placed_ids_count[r["id"]] = placed_ids_count.get(r["id"], 0) + 1
    original_ids_count = {}
    for p in existing:
        original_ids_count[p["id"]] = original_ids_count.get(p["id"], 0) + 1

    for pid, count in original_ids_count.items():
        placed = placed_ids_count.get(pid, 0)
        need = count - placed
        if need > 0:
            candidates = [p for p in existing if p["id"] == pid][:need]
            for p in candidates:
                # Find open spot
                for y in range(r0 + 2, r1 - 1, 2):
                    found = False
                    for x in range(c0 + 2, c1 - 1, 2):
                        if try_place(p, x, y):
                            found = True
                            break
                    if found:
                        break

    return json.dumps({
        "zone": zone_name,
        "template_used": template_key,
        "original_count": len(existing),
        "placed_count": len(result),
        "layout": result,
        "note": "Review and save with redesign_zone_layout tool",
    }, indent=2)
