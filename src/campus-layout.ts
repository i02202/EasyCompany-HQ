/**
 * 40×40 campus floor grid.
 * Each cell is a tile key string. Empty string = deadspace (non-walkable dark area).
 *
 * Zone boundaries follow the map in the plan:
 *   Rows  0–9:  Data Center (0-9) | Auditorium (10-19) | NOC (20-29) | Scrum (30-39)
 *   Rows 10–19: Open Cowork (0-14) | CEO (15-22) | Huddle Pods (23-39)
 *   Rows 20–24: Snack (0-5) | Café (6-13) | Gaming (14-39)
 *   Rows 25–32: Terrace (0-14) | Green Area (15-39)
 *   Rows 33:    Deadspace
 *   Rows 34–38, Cols 4–14: Architect's Office (island, surrounded by deadspace)
 */

export const GRID_COLS = 40;
export const GRID_ROWS = 40;

interface ZoneDef {
  name: string;
  rowStart: number; rowEnd: number;
  colStart: number; colEnd: number;
  tile: string;
}

export const ZONES: ZoneDef[] = [
  // Underground simulation (rows 0-9)
  { name: 'data_center',  rowStart: 1, rowEnd: 8,  colStart: 1,  colEnd: 9,  tile: 'epoxy_gray' },
  { name: 'auditorium',   rowStart: 1, rowEnd: 8,  colStart: 11, colEnd: 19, tile: 'noc_dark' },
  { name: 'noc_war_room', rowStart: 1, rowEnd: 8,  colStart: 21, colEnd: 29, tile: 'noc_dark' },
  { name: 'scrum_room',   rowStart: 1, rowEnd: 8,  colStart: 31, colEnd: 38, tile: 'main_floor' },

  // Main floor (rows 10-19)
  { name: 'open_cowork',  rowStart: 11, rowEnd: 18, colStart: 1,  colEnd: 14, tile: 'concrete_dark' },
  { name: 'ceo_office',   rowStart: 11, rowEnd: 18, colStart: 16, colEnd: 22, tile: 'wood_warm' },
  { name: 'huddle_pods',  rowStart: 11, rowEnd: 18, colStart: 24, colEnd: 38, tile: 'main_floor' },

  // Social floor (rows 20-24)
  { name: 'snack_bar',    rowStart: 20, rowEnd: 24, colStart: 1,  colEnd: 5,  tile: 'wood_warm' },
  { name: 'cafe',         rowStart: 20, rowEnd: 24, colStart: 7,  colEnd: 13, tile: 'wood_warm' },
  { name: 'gaming_lounge',rowStart: 20, rowEnd: 24, colStart: 15, colEnd: 38, tile: 'concrete_dark' },

  // Outdoor simulation (rows 26-32)
  { name: 'terrace',      rowStart: 26, rowEnd: 32, colStart: 1,  colEnd: 14, tile: 'rooftop_tile' },
  { name: 'green_area',   rowStart: 26, rowEnd: 32, colStart: 16, colEnd: 38, tile: 'grass_green' },

  // Architect's Office — isolated island (rows 34-38, cols 4-14)
  { name: 'architect',    rowStart: 34, rowEnd: 38, colStart: 4,  colEnd: 14, tile: 'architect_floor' },
];

/** Corridors connecting zones — 2-tile wide paths */
export const CORRIDORS: { row: number; colStart: number; colEnd: number; tile: string }[] = [
  // Horizontal corridor between underground and main floor (row 9-10)
  ...Array.from({ length: 2 }, (_, i) => ({ row: 9 + i, colStart: 1, colEnd: 38, tile: 'main_floor' })),
  // Horizontal corridor between main and social (row 19)
  { row: 19, colStart: 1, colEnd: 38, tile: 'main_floor' },
  // Horizontal corridor between social and outdoor (row 25)
  { row: 25, colStart: 1, colEnd: 38, tile: 'main_floor' },
  // Vertical corridor between data center and auditorium (col 10)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 1 + i, colStart: 10, colEnd: 10, tile: 'main_floor' })),
  // Vertical corridor between auditorium and NOC (col 20)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 1 + i, colStart: 20, colEnd: 20, tile: 'main_floor' })),
  // Vertical corridor between NOC and Scrum (col 30)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 1 + i, colStart: 30, colEnd: 30, tile: 'main_floor' })),
  // Vertical corridor cowork to CEO (col 15)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 11 + i, colStart: 15, colEnd: 15, tile: 'main_floor' })),
  // Vertical corridor CEO to huddle (col 23)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 11 + i, colStart: 23, colEnd: 23, tile: 'main_floor' })),
  // Vertical corridor snack to café (col 6)
  ...Array.from({ length: 5 }, (_, i) => ({ row: 20 + i, colStart: 6, colEnd: 6, tile: 'main_floor' })),
  // Vertical corridor café to gaming (col 14)
  ...Array.from({ length: 5 }, (_, i) => ({ row: 20 + i, colStart: 14, colEnd: 14, tile: 'main_floor' })),
  // Vertical terrace to green (col 15)
  ...Array.from({ length: 7 }, (_, i) => ({ row: 26 + i, colStart: 15, colEnd: 15, tile: 'main_floor' })),
];

export function buildFloorGrid(): string[][] {
  // Start with all deadspace
  const grid: string[][] = Array.from({ length: GRID_ROWS }, () =>
    Array(GRID_COLS).fill('')
  );

  // Outer wall border (row 0, row 39, col 0, col 39)
  for (let c = 0; c < GRID_COLS; c++) {
    grid[0][c] = 'main_wall';
    grid[GRID_ROWS - 1][c] = 'main_wall';
  }
  for (let r = 0; r < GRID_ROWS; r++) {
    grid[r][0] = 'main_wall';
    grid[r][GRID_COLS - 1] = 'main_wall';
  }

  // Fill zones
  for (const z of ZONES) {
    for (let r = z.rowStart; r <= z.rowEnd; r++) {
      for (let c = z.colStart; c <= z.colEnd; c++) {
        grid[r][c] = z.tile;
      }
    }
  }

  // Fill corridors
  for (const cor of CORRIDORS) {
    for (let c = cor.colStart; c <= cor.colEnd; c++) {
      grid[cor.row][c] = cor.tile;
    }
  }

  // Pool water (3×5 block inside green area)
  for (let r = 28; r <= 30; r++) {
    for (let c = 20; c <= 24; c++) {
      grid[r][c] = 'pool_water';
    }
  }

  // Architect border ring (noc_dark around the island to make it visible against deadspace)
  for (let c = 3; c <= 15; c++) { grid[33][c] = 'noc_dark'; grid[39][c] = 'noc_dark'; }
  for (let r = 33; r <= 39; r++) { grid[r][3] = 'noc_dark'; grid[r][15] = 'noc_dark'; }

  return grid;
}

/** Tile key → relative path in world_assets/tiles/ */
export const TILE_MAP: Record<string, string> = {
  main_floor: 'world_assets/tiles/main_floor.png',
  main_wall: 'world_assets/tiles/main_wall.png',
  accent_floor_tile: 'world_assets/tiles/accent_floor_tile.png',
  accent_wall_panel: 'world_assets/tiles/accent_wall_panel.png',
  concrete_dark: 'world_assets/tiles/concrete_dark.png',
  epoxy_gray: 'world_assets/tiles/epoxy_gray.png',
  wood_warm: 'world_assets/tiles/wood_warm.png',
  grass_green: 'world_assets/tiles/grass_green.png',
  noc_dark: 'world_assets/tiles/noc_dark.png',
  pool_water: 'world_assets/tiles/pool_water.png',
  rooftop_tile: 'world_assets/tiles/rooftop_tile.png',
  architect_floor: 'world_assets/tiles/architect_floor.png',
};
