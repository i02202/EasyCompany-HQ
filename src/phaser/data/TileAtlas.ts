/**
 * TileAtlas — maps prop IDs to Pixel Salvaje tile textures.
 *
 * Each entry defines:
 *   - textureKey: Phaser texture key (matches PreloadScene)
 *   - file: path relative to /assets/tiles/
 *   - nativeSize: pixel dimensions of the source PNG
 *   - variants: alternative textures for visual diversity (rotations, colors)
 *
 * Props NOT in this atlas fall back to geometric rendering in PropSprite.
 */

export interface TileEntry {
  textureKey: string;
  file: string;
  nativeW: number;
  nativeH: number;
}

export interface TileMapping {
  /** Primary tile */
  primary: TileEntry;
  /** Alternative tiles for visual variety (random pick per instance) */
  variants?: TileEntry[];
}

// ── Tile size classes ──
// 128×128: desks, sofas, tables, fridge, big TV, shelving, carpet, windows
//  64×64:  monitors, chairs, PC tower, keyboard, stool, speaker, lamp(scaled), console, microwave, poster
//  32×32:  plants, lamps, small items
// 640×128: door sprite sheets (5 frames × 128px)

const TILES_PATH = 'assets/tiles';

function tile(key: string, file: string, w: number, h: number): TileEntry {
  return { textureKey: key, file: `${TILES_PATH}/${file}`, nativeW: w, nativeH: h };
}

/**
 * Master mapping: prop ID → tile texture(s).
 * Only props with real Pixel Salvaje tiles are listed here.
 */
export const TILE_ATLAS: Record<string, TileMapping> = {
  // ── Desks ──
  desk_monitor: {
    primary: tile('desk', 'desk.png', 128, 128),
    variants: [tile('desk-alt', 'desk-alt.png', 128, 128)],
  },

  // ── Monitors / Screens (placed ON desks or walls) ──
  architect_monitors: {
    primary: tile('monitor-curved', 'monitor-curved.png', 64, 64),
    variants: [
      tile('monitor-flat', 'monitor-flat.png', 64, 64),
      tile('monitor-flat-b', 'monitor-flat-b.png', 64, 64),
    ],
  },
  data_display_wall: {
    primary: tile('big-tv', 'big-tv.png', 128, 128),
  },
  noc_screen_wall: {
    primary: tile('big-tv', 'big-tv.png', 128, 128),
  },
  panoramic_screen: {
    primary: tile('big-tv', 'big-tv.png', 128, 128),
  },

  // ── Chairs ──
  ergonomic_chair: {
    primary: tile('gaming-chair-a', 'gaming-chair-a.png', 66, 64),
    variants: [
      tile('gaming-chair-b', 'gaming-chair-b.png', 66, 64),
      tile('gaming-chair-c', 'gaming-chair-c.png', 66, 64),
      tile('gaming-chair-d', 'gaming-chair-d.png', 66, 64),
    ],
  },
  lounge_chair: {
    primary: tile('chair-a', 'chair-a.png', 64, 64),
    variants: [
      tile('chair-b', 'chair-b.png', 64, 64),
      tile('chair-c', 'chair-c.png', 64, 64),
      tile('chair-d', 'chair-d.png', 64, 64),
    ],
  },

  // ── Sofas ──
  lounge_sofa: {
    primary: tile('sofa-a', 'sofa-a.png', 128, 128),
    variants: [
      tile('sofa-b', 'sofa-b.png', 128, 128),
      tile('sofa-c', 'sofa-c.png', 128, 128),
      tile('sofa-d', 'sofa-d.png', 128, 128),
    ],
  },

  // ── Tables ──
  coffee_table: {
    primary: tile('table-small', 'table-small.png', 128, 128),
  },
  scrum_table: {
    primary: tile('table-large', 'table-large.png', 128, 128),
  },

  // ── Kitchen / Bar ──
  fridge: {
    primary: tile('fridge', 'fridge.png', 128, 128),
    variants: [tile('fridge-alt', 'fridge-alt.png', 128, 128)],
  },
  espresso_machine: {
    primary: tile('microwave', 'microwave.png', 64, 64),
  },
  bar_stool: {
    primary: tile('stool', 'stool.png', 64, 64),
  },

  // ── Plants ──
  tall_plant: {
    primary: tile('plant-tree', 'plant-tree.png', 32, 32),
    variants: [
      tile('plant-bush', 'plant-bush.png', 32, 32),
      tile('cactus', 'cactus.png', 32, 32),
    ],
  },

  // ── Doors ──
  changing_room_door: {
    primary: tile('door-black-sheet', 'door-black-sheet.png', 640, 128),
  },

  // ── Auditorium ──
  auditorium_seats: {
    primary: tile('sofa-a', 'sofa-a.png', 128, 128),
  },

  // ── Entertainment ──
  karaoke_machine: {
    primary: tile('speaker', 'speaker.png', 64, 64),
  },
};

/**
 * Get all unique tile entries that need to be preloaded.
 */
export function getAllTileEntries(): TileEntry[] {
  const seen = new Set<string>();
  const entries: TileEntry[] = [];

  for (const mapping of Object.values(TILE_ATLAS)) {
    const all = [mapping.primary, ...(mapping.variants ?? [])];
    for (const entry of all) {
      if (!seen.has(entry.textureKey)) {
        seen.add(entry.textureKey);
        entries.push(entry);
      }
    }
  }

  return entries;
}

/**
 * Get tile mapping for a prop ID, or null if geometric fallback should be used.
 */
export function getTileMapping(propId: string): TileMapping | null {
  return TILE_ATLAS[propId] ?? null;
}

/**
 * Pick a tile entry for a prop (primary or random variant for visual variety).
 * Uses a deterministic seed based on grid position for consistency.
 */
export function pickTile(propId: string, gridX: number, gridY: number): TileEntry | null {
  const mapping = getTileMapping(propId);
  if (!mapping) return null;

  if (!mapping.variants || mapping.variants.length === 0) {
    return mapping.primary;
  }

  // Deterministic pseudo-random based on position
  const seed = Math.abs((gridX * 7919 + gridY * 6271) | 0);
  const all = [mapping.primary, ...mapping.variants];
  return all[seed % all.length];
}
