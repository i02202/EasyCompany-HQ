"""
Campus Factory AI — Tools for reading/writing campus data files.
These tools let CrewAI agents inspect and modify the campus layout,
props, and tile atlas.
"""
from crewai.tools import tool
from pathlib import Path
import json
import re

from factory_ai.config import (
    CAMPUS_LAYOUT, CAMPUS_PROPS, TILE_ATLAS, CAMPUS_WANDER,
    ZONES, AVAILABLE_TILES, PROJECT_ROOT, TILES_DIR, OUTPUT_DIR,
)


# ─── File Cache (avoids re-reading 5KB+ files on every agent iteration) ────
_file_cache: dict[str, str] = {}


def _cached_read(path: Path) -> str:
    """Read file with in-memory cache — cleared when crew restarts."""
    key = str(path)
    if key not in _file_cache:
        _file_cache[key] = path.read_text(encoding="utf-8")
    return _file_cache[key]


def clear_file_cache():
    """Call on crew start to ensure fresh reads."""
    _file_cache.clear()


@tool("read_campus_layout")
def read_campus_layout() -> str:
    """Read the current campus-layout.ts file (zone definitions and grid)."""
    return _cached_read(CAMPUS_LAYOUT)


@tool("read_campus_props")
def read_campus_props() -> str:
    """Read the current campus-props.ts file (all prop placements per zone)."""
    return _cached_read(CAMPUS_PROPS)


@tool("read_tile_atlas")
def read_tile_atlas() -> str:
    """Read the TileAtlas.ts file that maps prop IDs to tile texture files."""
    return _cached_read(TILE_ATLAS)


@tool("read_campus_wander")
def read_campus_wander() -> str:
    """Read the campus-wander.ts file with wander points for agent movement."""
    return _cached_read(CAMPUS_WANDER)


@tool("get_zone_specs")
def get_zone_specs() -> str:
    """Get the full specification of all 13 campus zones with their grid bounds,
    floor tiles, wall types, and intended function."""
    return json.dumps(ZONES, indent=2)


@tool("list_available_tiles")
def list_available_tiles() -> str:
    """List all Pixel Salvaje tile PNG files available in assets/tiles/.
    These are the actual textures that can be used for props."""
    actual = [f.name for f in TILES_DIR.glob("*.png")] if TILES_DIR.exists() else []
    return json.dumps({
        "cataloged": AVAILABLE_TILES,
        "actual_on_disk": actual,
        "tiles_dir": str(TILES_DIR),
    }, indent=2)


@tool("list_asset_packs")
def list_asset_packs() -> str:
    """List all purchased asset pack directories and their contents summary."""
    packs_dir = PROJECT_ROOT / "assets" / "packs"
    if not packs_dir.exists():
        return "No assets/packs/ directory found"
    result = {}
    for pack in packs_dir.iterdir():
        if pack.is_dir():
            pngs = list(pack.rglob("*.png"))
            result[pack.name] = {
                "total_pngs": len(pngs),
                "sample_files": [str(p.relative_to(pack)) for p in pngs[:10]],
            }
    return json.dumps(result, indent=2)


@tool("write_zone_props")
def write_zone_props(zone_name: str, props_json: str) -> str:
    """Write prop placements for a SINGLE zone. Call this once per zone.
    zone_name: e.g. 'data_center', 'ceo_office', etc.
    props_json: JSON array of prop objects, each with: id, x, y, w, h, layer, anchors.
    Example: [{"id":"desk","x":3,"y":2,"w":2.5,"h":1.5,"layer":"below","anchors":[{"name":"seat","ox":1,"oy":0.5,"type":"work"}]}]
    """
    out_dir = OUTPUT_DIR / "zones"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{zone_name}.json"
    out.write_text(props_json, encoding="utf-8")
    # Also append to combined file
    combined = OUTPUT_DIR / "all_props.jsonl"
    with open(combined, "a", encoding="utf-8") as f:
        f.write(json.dumps({"zone": zone_name, "props": json.loads(props_json)}) + "\n")
    try:
        count = len(json.loads(props_json))
    except Exception:
        count = "?"
    return f"Zone '{zone_name}' written: {count} props saved to {out}. Call this for each remaining zone."


@tool("write_all_zone_props")
def write_all_zone_props(all_zones_json: str) -> str:
    """Write props for ALL zones in one call. Pass a JSON object where keys are zone names
    and values are arrays of prop objects. More efficient than calling write_zone_props 13 times.
    Example: {"data_center": [{"id":"rack","x":2,"y":2,"w":1,"h":2,"layer":"below","anchors":[]}], "ceo_office": [...]}
    """
    out_dir = OUTPUT_DIR / "zones"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        all_zones = json.loads(all_zones_json)
    except Exception as e:
        return f"ERROR: Invalid JSON: {e}"
    combined = OUTPUT_DIR / "all_props.jsonl"
    written = []
    for zone_name, props in all_zones.items():
        out = out_dir / f"{zone_name}.json"
        out.write_text(json.dumps(props, indent=2), encoding="utf-8")
        with open(combined, "a", encoding="utf-8") as f:
            f.write(json.dumps({"zone": zone_name, "props": props}) + "\n")
        written.append(f"{zone_name}({len(props)})")
    return f"Wrote {len(written)} zones: {', '.join(written)}"


@tool("write_campus_props")
def write_campus_props(content: str = "") -> str:
    """Write a new version of campus-props.ts. Pass the full TypeScript content as
    the 'content' parameter. If you can't fit it all, use write_zone_props instead
    to write one zone at a time."""
    if not content or len(content) < 10:
        return "ERROR: content is empty. TIP: Use the write_zone_props tool instead — call it once per zone with a JSON array of props. This is more reliable for large layouts."
    out = OUTPUT_DIR / "campus-props.ts"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return f"Written to {out} ({len(content)} chars). Review before copying to src/."


@tool("write_tile_mapping")
def write_tile_mapping(mappings_json: str) -> str:
    """Write prop-to-tile texture mappings. Pass a JSON object where keys are prop IDs
    and values are tile filenames. Call multiple times if needed — entries accumulate.
    Example: {"desk": "desk.png", "monitor": "monitor-imac.png", "chair": "gaming-chair-a.png"}
    Only map to files that actually exist in assets/tiles/.
    """
    out = OUTPUT_DIR / "tile_mappings.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        new_mappings = json.loads(mappings_json)
    except Exception as e:
        return f"ERROR: Invalid JSON: {e}. Pass a JSON object like {{\"desk\": \"desk.png\"}}."
    existing.update(new_mappings)
    out.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return f"Tile mappings updated: {len(new_mappings)} new, {len(existing)} total. Saved to {out}."


@tool("write_tile_atlas")
def write_tile_atlas(content: str = "") -> str:
    """Write a new version of TileAtlas.ts. Pass the full TypeScript content as
    the 'content' parameter. Saved to factory_ai/output/ for review.
    TIP: If this tool fails, use write_tile_mapping instead to write mappings as JSON."""
    if not content or len(content) < 10:
        return "ERROR: content is empty. TIP: Use write_tile_mapping tool instead — pass a JSON object of prop-to-tile mappings. Example: write_tile_mapping(mappings_json='{\"desk\":\"desk.png\",\"chair\":\"gaming-chair-a.png\"}'). Call it multiple times if needed."
    out = OUTPUT_DIR / "TileAtlas.ts"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return f"Written to {out} ({len(content)} chars). Review before copying to src/phaser/data/."


@tool("write_design_report")
def write_design_report(content: str = "") -> str:
    """Write a design report (markdown) with the Art Director's visual specifications,
    furniture choices, and layout decisions for each zone."""
    if not content or len(content) < 10:
        return "ERROR: content parameter is required. Pass the full markdown report."
    out = OUTPUT_DIR / "design-report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return f"Design report written to {out}"


@tool("analyze_prop_coverage")
def analyze_prop_coverage() -> str:
    """Analyze how well the current props cover each zone — flags zones with
    too few props, missing furniture types, or proportional issues.
    Reads from factory_ai/output/zones/*.json (authoritative source)."""
    zones_dir = OUTPUT_DIR / "zones"

    analysis = {}
    for zname, zspec in ZONES.items():
        r0, r1 = zspec["rows"]
        c0, c1 = zspec["cols"]
        area = (r1 - r0 + 1) * (c1 - c0 + 1)

        zone_file = zones_dir / f"{zname}.json"
        prop_ids: dict[str, int] = {}
        count = 0

        if zone_file.exists():
            try:
                props = json.loads(zone_file.read_text(encoding="utf-8"))
                for prop in props:
                    pid = prop.get("id", "unknown")
                    prop_ids[pid] = prop_ids.get(pid, 0) + 1
                    count += 1
            except (json.JSONDecodeError, KeyError) as e:
                analysis[zname] = {"error": str(e)}
                continue

        density = count / area if area > 0 else 0
        analysis[zname] = {
            "area_tiles": area,
            "prop_count": count,
            "density": round(density, 3),
            "props": prop_ids,
            "function": zspec["function"],
            "issue": "SPARSE" if density < 0.05 else ("OVERCROWDED" if density > 0.3 else "OK"),
        }

    return json.dumps(analysis, indent=2)
