"""
Campus Factory AI — Asset Generation Tools
============================================
Uses fal.ai API to generate new prop textures on demand.
Produces 128x128 isometric pixel art PNGs for props that
don't have existing Pixel Salvaje tiles.
"""
import os
import json
import urllib.request
from pathlib import Path
from crewai.tools import tool

from factory_ai.config import FAL_KEY, TILES_DIR, OUTPUT_DIR
from factory_ai.events import bus, EventType


def _generate_image(prompt: str, filename: str, size: int = 128) -> str:
    """Generate an image via fal.ai Flux Schnell and save to tiles dir."""
    if not FAL_KEY:
        return f"[fal.ai not configured — set FAL_KEY in .env] Would generate: {filename}"

    TILES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TILES_DIR / filename

    # Skip if already exists
    if output_path.exists():
        return f"Texture already exists: {filename}"

    try:
        url = "https://fal.run/fal-ai/flux/schnell"
        payload = json.dumps({
            "prompt": prompt,
            "image_size": {"width": size, "height": size},
            "num_images": 1,
            "enable_safety_checker": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Key {FAL_KEY}",
            },
        )

        bus.emit(EventType.AGENT_STEP, {
            "agent": "Art Director",
            "agent_name": "Art Director",
            "step_type": "tool_call",
            "tool": "generate_prop_texture",
            "content": f"Generating {filename}: {prompt[:60]}...",
        })

        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())

        # Download the generated image
        images = result.get("images", [])
        if images:
            img_url = images[0].get("url", "")
            if img_url:
                img_data = urllib.request.urlopen(img_url, timeout=30).read()
                output_path.write_bytes(img_data)
                bus.emit(EventType.FILE_WRITTEN, {"filename": filename})
                return f"Generated and saved: {filename} ({len(img_data)} bytes)"

        return f"[fal.ai returned no images for: {filename}]"

    except Exception as e:
        return f"[fal.ai generation error: {e}] Prompt: {prompt[:80]}"


@tool("generate_prop_texture")
def generate_prop_texture(prop_name: str, style: str) -> str:
    """Generate a new isometric prop texture using fal.ai image generation.
    Use this when a prop doesn't have an existing tile in assets/tiles/.
    The prop_name should be descriptive (e.g., 'standing_desk', 'acoustic_panel').
    The style should describe the visual theme (e.g., 'modern tech office').
    Returns the path to the saved PNG file."""

    if not style:
        style = "modern tech office"
    filename = f"{prop_name.replace(' ', '-').lower()}.png"
    prompt = (
        f"isometric pixel art {prop_name}, 128x64 perspective, "
        f"transparent background, game asset sprite, "
        f"{style}, clean lines, consistent lighting from top-left, "
        f"modern minimalist design, high quality pixel art"
    )
    return _generate_image(prompt, filename, size=128)


@tool("generate_zone_textures")
def generate_zone_textures(zone_name: str, prop_list: str) -> str:
    """Generate textures for multiple props in a zone at once.
    prop_list should be comma-separated prop names.
    Only generates textures that don't already exist.
    Returns a summary of generated vs existing textures."""

    props = [p.strip() for p in prop_list.split(",") if p.strip()]
    results = []
    generated = 0
    existing = 0

    for prop in props:
        filename = f"{prop.replace(' ', '-').lower()}.png"
        if (TILES_DIR / filename).exists():
            results.append(f"  [exists] {filename}")
            existing += 1
        else:
            prompt = (
                f"isometric pixel art {prop}, 128x64 perspective, "
                f"transparent background, game asset sprite, "
                f"modern tech office, clean lines, pixel art"
            )
            result = _generate_image(prompt, filename, size=128)
            results.append(f"  [new] {result}")
            generated += 1

    summary = (
        f"Zone '{zone_name}': {generated} generated, {existing} already existed\n"
        + "\n".join(results)
    )
    return summary


@tool("list_missing_textures")
def list_missing_textures(prop_ids: str) -> str:
    """Check which prop IDs are missing textures in assets/tiles/.
    prop_ids should be comma-separated. Returns list of missing ones
    so the Art Director knows what to generate."""

    props = [p.strip() for p in prop_ids.split(",") if p.strip()]
    existing_tiles = set()
    if TILES_DIR.exists():
        existing_tiles = {f.stem.lower() for f in TILES_DIR.glob("*.png")}

    missing = []
    found = []
    for prop in props:
        prop_clean = prop.replace("_", "-").lower()
        # Check exact match and common variants
        variants = [prop_clean, prop.replace("-", "_").lower(), prop.lower()]
        if any(v in existing_tiles for v in variants):
            found.append(prop)
        else:
            missing.append(prop)

    return (
        f"Found textures for {len(found)}/{len(props)} props.\n"
        f"Missing textures ({len(missing)}): {', '.join(missing) if missing else 'none'}\n"
        f"Existing: {', '.join(found)}"
    )
