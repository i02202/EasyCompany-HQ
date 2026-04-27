/**
 * Maps campus-layout tile keys to rendering colors (Phase A)
 * and later to SmallScaleInt atlas frame names (Phase B).
 *
 * Phase A: Returns hex colors for diamond drawing.
 * Phase B: Will return atlas frame keys + file paths.
 */

/** Tile key → color for Phase A floor rendering (brightened for visibility) */
export const TILE_COLORS: Record<string, number> = {
  main_floor:        0x5a5a7f,  // gray-blue office floor
  main_wall:         0x2a2a4e,  // dark walls
  concrete_dark:     0x4a4a5f,  // dark concrete
  epoxy_gray:        0x6a6a8a,  // server room epoxy
  wood_warm:         0x8a6a3a,  // warm wood
  noc_dark:          0x252545,  // dark operations room
  grass_green:       0x3a8a3a,  // outdoor grass
  pool_water:        0x2a6aaa,  // water
  rooftop_tile:      0x7a7a5a,  // terrace paving
  architect_floor:   0x1a1a3a,  // architect dark floor
};

/** Default color for unknown tile keys */
export const DEFAULT_TILE_COLOR = 0x3a3a55;

/** Deadspace color (empty cells) */
export const DEADSPACE_COLOR = 0x0e0e1a;

/** Get rendering color for a tile key */
export function getTileColor(tileKey: string): number {
  if (!tileKey) return DEADSPACE_COLOR;
  return TILE_COLORS[tileKey] ?? DEFAULT_TILE_COLOR;
}

/**
 * Zone accent colors for labels and minimap.
 * Brighter than floor colors for visibility.
 */
export const ZONE_ACCENT_COLORS: Record<string, number> = {
  data_center:   0x4ade80,  // green — tech
  auditorium:    0xfbbf24,  // amber — presentation
  noc_war_room:  0xef4444,  // red — alert
  scrum_room:    0x60a5fa,  // blue — collaboration
  open_cowork:   0xa78bfa,  // purple — creative
  ceo_office:    0xf97316,  // orange — executive
  huddle_pods:   0x22d3ee,  // cyan — meetings
  snack_bar:     0xfb923c,  // light orange — food
  cafe:          0x8b5cf6,  // violet — social
  gaming_lounge: 0xf472b6,  // pink — fun
  terrace:       0xfcd34d,  // yellow — outdoor
  green_area:    0x34d399,  // emerald — nature
  architect:     0xe94560,  // red — special
};
