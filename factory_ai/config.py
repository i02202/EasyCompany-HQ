"""
Campus Factory AI — Configuration
Shared config for all agents and tools.
"""
import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
FACTORY_ROOT = Path(__file__).parent
OUTPUT_DIR = FACTORY_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
TILES_DIR = ASSETS_DIR / "tiles"
PACKS_DIR = ASSETS_DIR / "packs"
SRC_DIR = PROJECT_ROOT / "src"

# Campus data files (the agents will read and rewrite these)
CAMPUS_LAYOUT = SRC_DIR / "campus-layout.ts"
CAMPUS_PROPS = SRC_DIR / "campus-props.ts"
CAMPUS_WANDER = SRC_DIR / "campus-wander.ts"
TILE_ATLAS = SRC_DIR / "phaser" / "data" / "TileAtlas.ts"
PROP_SPRITE = SRC_DIR / "phaser" / "entities" / "PropSprite.ts"

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

# DeerFlow
DEERFLOW_URL = os.getenv("DEERFLOW_URL", "http://localhost:8001")

# API Keys (optional — for asset generation)
FAL_KEY = os.getenv("FAL_KEY", "")
PIXELLAB_API_KEY = os.getenv("PIXELLAB_API_KEY", "")

# Campus spec
GRID_COLS = 40
GRID_ROWS = 40
TILE_W = 128  # isometric tile width in pixels
TILE_H = 64   # isometric tile height in pixels

ZONES = {
    "data_center":   {"rows": (1, 8),   "cols": (1, 9),   "tile": "epoxy_gray",     "wall": "solid",   "function": "Server racks, cooling units, biometric access, monitoring displays"},
    "auditorium":    {"rows": (1, 8),   "cols": (11, 19), "tile": "noc_dark",       "wall": "solid",   "function": "Tiered seating, podium, projection screen, sound system"},
    "noc_war_room":  {"rows": (1, 8),   "cols": (21, 29), "tile": "noc_dark",       "wall": "frosted", "function": "Multi-monitor workstations, alert dashboards, war-table"},
    "scrum_room":    {"rows": (1, 8),   "cols": (31, 38), "tile": "main_floor",     "wall": "glass",   "function": "Whiteboard walls, standing desks, sprint boards, sticky notes"},
    "open_cowork":   {"rows": (11, 18), "cols": (1, 14),  "tile": "concrete_dark",  "wall": "glass",   "function": "Hot-desking, monitor arms, ergonomic chairs, phone booths"},
    "ceo_office":    {"rows": (11, 18), "cols": (16, 22), "tile": "wood_warm",      "wall": "frosted", "function": "Executive desk, lounge sofa, bookshelf, meeting corner"},
    "huddle_pods":   {"rows": (11, 18), "cols": (24, 38), "tile": "main_floor",     "wall": "glass",   "function": "4-person pods with round tables, screens, soundproofing"},
    "snack_bar":     {"rows": (20, 24), "cols": (1, 5),   "tile": "wood_warm",      "wall": "none",    "function": "Counter, bar stools, fridge, microwave, coffee machine"},
    "cafe":          {"rows": (20, 24), "cols": (7, 13),  "tile": "wood_warm",      "wall": "none",    "function": "Café tables, bistro chairs, plants, ambient lighting"},
    "gaming_lounge": {"rows": (20, 24), "cols": (15, 38), "tile": "concrete_dark",  "wall": "glass",   "function": "Gaming PCs, console area, bean bags, big TVs, speakers"},
    "terrace":       {"rows": (26, 31), "cols": (1, 14),  "tile": "stone_outdoor",  "wall": "none",    "function": "Outdoor seating, umbrellas, planters, lounge chairs"},
    "green_area":    {"rows": (26, 31), "cols": (16, 38), "tile": "grass_manicured","wall": "none",    "function": "Trees, garden benches, walking path, meditation spots"},
    "architect":     {"rows": (34, 38), "cols": (4, 14),  "tile": "wood_warm",      "wall": "solid",   "function": "Drafting tables, blueprint displays, model showcase, private studio"},
}

# Available Pixel Salvaje tiles (what we actually have in assets/tiles/)
AVAILABLE_TILES = [
    "desk.png", "desk-wide.png", "monitor-imac.png", "monitor-b.png",
    "gaming-chair-a.png", "gaming-chair-b.png", "gaming-chair-c.png",
    "office-chair-white.png", "office-chair-teal.png",
    "sofa-a.png", "sofa-b.png", "sofa-c.png",
    "fridge.png", "coffee-machine.png",
    "plant-tree.png", "plant-fern.png", "plant-bush.png",
    "table-round.png", "table-square.png", "table-long.png",
    "stool.png", "stool-bar.png",
    "big-tv.png", "laptop.png", "speaker.png",
    "bookshelf.png", "bookshelf-tall.png",
    "door-black-sheet.png", "door-glass.png",
    "whiteboard.png", "printer.png",
    "server-rack.png", "server-tower.png",
]
