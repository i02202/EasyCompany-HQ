/**
 * Isometric coordinate system for the 40×40 campus grid.
 *
 * Uses standard diamond projection:
 *   screenX = (col - row) * (TILE_W / 2)
 *   screenY = (col + row) * (TILE_H / 2)
 *
 * Ground diamond: 128×64px (matching SmallScaleInt tile footprint).
 * Full sprite height: 256px (128px ground + vertical depth for tall objects).
 */

/** Diamond width in pixels (isometric tile width) */
export const TILE_W = 128;

/** Diamond height in pixels (ground-level only, NOT full sprite height) */
export const TILE_H = 64;

/** Full sprite height for tall objects (SmallScaleInt format) */
export const SPRITE_H = 256;

export interface ScreenPoint {
  x: number;
  y: number;
}

export interface GridPoint {
  col: number;
  row: number;
}

/**
 * Convert grid coordinates (col, row) → screen position (pixels).
 * Returns the CENTER of the diamond on screen.
 */
export function gridToScreen(col: number, row: number): ScreenPoint {
  return {
    x: (col - row) * (TILE_W / 2),
    y: (col + row) * (TILE_H / 2),
  };
}

/**
 * Convert screen position (pixels) → grid coordinates.
 * Returns fractional grid position (use Math.floor for tile index).
 */
export function screenToGrid(screenX: number, screenY: number): GridPoint {
  return {
    col: (screenX / (TILE_W / 2) + screenY / (TILE_H / 2)) / 2,
    row: (screenY / (TILE_H / 2) - screenX / (TILE_W / 2)) / 2,
  };
}

/**
 * Snap fractional grid coords to nearest whole tile.
 */
export function snapToTile(col: number, row: number): GridPoint {
  return {
    col: Math.floor(col),
    row: Math.floor(row),
  };
}

/**
 * Get the 4 corner points of a diamond tile at (col, row) in screen space.
 * Useful for drawing the diamond outline.
 */
export function getDiamondCorners(col: number, row: number): [ScreenPoint, ScreenPoint, ScreenPoint, ScreenPoint] {
  const center = gridToScreen(col + 0.5, row + 0.5);
  const hw = TILE_W / 2;
  const hh = TILE_H / 2;
  return [
    { x: center.x, y: center.y - hh },     // top
    { x: center.x + hw, y: center.y },      // right
    { x: center.x, y: center.y + hh },      // bottom
    { x: center.x - hw, y: center.y },      // left
  ];
}

/**
 * Calculate world bounds for a grid of given dimensions.
 */
export function getWorldBounds(cols: number, rows: number): {
  minX: number; minY: number; width: number; height: number;
} {
  // Top-left tile (0,0) → top corner of diamond
  const topLeft = gridToScreen(0, rows);  // leftmost point
  const topRight = gridToScreen(cols, 0); // rightmost point
  const top = gridToScreen(0, 0);         // topmost point
  const bottom = gridToScreen(cols, rows); // bottommost point

  const minX = topLeft.x - TILE_W / 2;
  const minY = top.y - TILE_H / 2;
  const maxX = topRight.x + TILE_W / 2;
  const maxY = bottom.y + TILE_H / 2 + SPRITE_H; // extra room for tall sprites

  return {
    minX,
    minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}
