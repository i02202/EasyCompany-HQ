/**
 * PropSprite — hybrid renderer for campus props.
 *
 * Rendering priority:
 *   1. Pixel Salvaje tile texture (if mapped in TileAtlas)
 *   2. Enhanced geometric fallback (modern tech-office shapes)
 *
 * All props use isometric diamond projection and depth sorting.
 */
import Phaser from 'phaser';
import { gridToScreen, TILE_W, TILE_H } from '../systems/IsometricGrid';
import { getPropStyle, type PropShape } from '../data/PropMapper';
import { pickTile, type TileEntry } from '../data/TileAtlas';

interface PropPlacement {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  layer: 'below' | 'above';
  anchors: { name: string; ox: number; oy: number; type: string }[];
}

const DEPTH_BASE = 10;
const DEPTH_ABOVE_BONUS = 5;

function calcDepth(gridX: number, gridY: number, w: number, h: number, layer: 'below' | 'above'): number {
  const bottomRow = gridY + h;
  const bottomCol = gridX + w;
  const depth = DEPTH_BASE + (bottomRow + bottomCol) * TILE_H;
  return layer === 'above' ? depth + DEPTH_ABOVE_BONUS : depth;
}

/**
 * Place a single prop — tries tile texture first, falls back to geometric.
 */
export function placeProp(
  scene: Phaser.Scene,
  prop: PropPlacement,
): Phaser.GameObjects.GameObject {
  const depth = calcDepth(prop.x, prop.y, prop.w, prop.h, prop.layer);
  const centerCol = prop.x + prop.w / 2;
  const centerRow = prop.y + prop.h / 2;
  const screen = gridToScreen(centerCol, centerRow);

  // Try tile texture first
  const tile = pickTile(prop.id, prop.x, prop.y);
  if (tile && scene.textures.exists(tile.textureKey)) {
    return placeTileSprite(scene, prop, tile, screen, depth);
  }

  // Geometric fallback
  return placeGeometric(scene, prop, screen, depth);
}

// ────────────────────────────────────────────────────
// Tile-based rendering (Pixel Salvaje)
// ────────────────────────────────────────────────────

function placeTileSprite(
  scene: Phaser.Scene,
  prop: PropPlacement,
  tile: TileEntry,
  screen: { x: number; y: number },
  depth: number,
): Phaser.GameObjects.GameObject {
  // Door sprite sheets need special handling (5 frames in 640×128)
  if (prop.id === 'changing_room_door') {
    return placeDoorSprite(scene, tile, screen, depth);
  }

  const sprite = scene.add.image(screen.x, screen.y, tile.textureKey);

  // Scale tile to fit the isometric footprint
  const targetW = (prop.w + prop.h) * (TILE_W / 2);
  // Scale proportionally based on footprint width
  const scale = (targetW / tile.nativeW) * 0.75;

  sprite.setScale(scale);
  sprite.setOrigin(0.5, 0.7); // Anchor bottom-center-ish for isometric alignment
  sprite.setDepth(depth);

  return sprite;
}

function placeDoorSprite(
  scene: Phaser.Scene,
  tile: TileEntry,
  screen: { x: number; y: number },
  depth: number,
): Phaser.GameObjects.GameObject {
  // Door sheet is 640×128 = 5 frames of 128×128, show the closed frame (first)
  const frameW = 128;
  const key = tile.textureKey + '_frame0';

  if (!scene.textures.exists(key)) {
    // Crop first frame from sprite sheet
    const tex = scene.textures.get(tile.textureKey);
    tex.add('closed', 0, 0, 0, frameW, tile.nativeH);
  }

  const sprite = scene.add.image(screen.x, screen.y, tile.textureKey, 'closed');
  sprite.setScale(0.6);
  sprite.setOrigin(0.5, 0.7);
  sprite.setDepth(depth);

  return sprite;
}

// ────────────────────────────────────────────────────
// Geometric rendering (enhanced fallback)
// ────────────────────────────────────────────────────

function placeGeometric(
  scene: Phaser.Scene,
  prop: PropPlacement,
  screen: { x: number; y: number },
  depth: number,
): Phaser.GameObjects.GameObject {
  const style = getPropStyle(prop.id);

  // Isometric footprint dimensions
  const isoW = (prop.w + prop.h) * (TILE_W / 2);
  const isoH = (prop.w + prop.h) * (TILE_H / 2);
  const hw = isoW / 2;
  const hh = isoH / 2;

  const gfx = scene.add.graphics();
  gfx.setDepth(depth);

  const shapeDrawers: Record<PropShape, () => void> = {
    desk: () => drawDesk(gfx, screen, hw, hh, style),
    chair: () => drawChair(gfx, screen, hw, hh, style),
    table: () => drawTable(gfx, screen, hw, hh, style),
    sofa: () => drawSofa(gfx, screen, hw, hh, style),
    screen: () => drawScreen(gfx, screen, hw, hh, style),
    rack: () => drawRack(gfx, screen, hw, hh, style),
    cabinet: () => drawCabinet(gfx, screen, hw, hh, style),
    counter: () => drawCounter(gfx, screen, hw, hh, style),
    stool: () => drawStool(gfx, screen, hw, hh, style),
    appliance: () => drawAppliance(gfx, screen, hw, hh, style),
    plant: () => drawPlant(gfx, screen, hw, hh, style),
    glass_wall: () => drawGlassWall(gfx, screen, hw, hh, style),
    whiteboard: () => drawWhiteboard(gfx, screen, hw, hh, style),
    door: () => drawDoor(gfx, screen, hw, hh, style),
    pool: () => drawPool(gfx, screen, hw, hh, style),
    lights: () => drawLights(gfx, screen, hw, hh, style),
    neon: () => drawNeon(gfx, screen, hw, hh, style),
    camera: () => drawCamera(gfx, screen, hw, hh, style),
    cables: () => drawCables(gfx, screen, hw, hh, style),
    bean_bag: () => drawBeanBag(gfx, screen, hw, hh, style),
    generic: () => drawGeneric(gfx, screen, hw, hh, style),
  };

  (shapeDrawers[style.shape] ?? shapeDrawers.generic)();

  // Add label if present
  if (style.label) {
    const label = scene.add.text(screen.x, screen.y + 2, style.label, {
      fontFamily: 'Courier New, monospace',
      fontSize: '7px',
      color: '#' + style.accent.toString(16).padStart(6, '0'),
      stroke: '#000000',
      strokeThickness: 2,
    });
    label.setOrigin(0.5);
    label.setDepth(depth + 1);
    label.setAlpha(0.6);
  }

  return gfx;
}

// ────────────────────────────────────────────────────
// Shape drawing functions (enhanced geometric fallback)
// ────────────────────────────────────────────────────

interface Pos { x: number; y: number }
interface Style { color: number; accent: number; glow?: boolean }

/** Draw a filled isometric diamond */
function diamond(gfx: Phaser.GameObjects.Graphics, cx: number, cy: number, hw: number, hh: number, color: number, alpha: number) {
  gfx.fillStyle(color, alpha);
  gfx.beginPath();
  gfx.moveTo(cx, cy - hh);
  gfx.lineTo(cx + hw, cy);
  gfx.lineTo(cx, cy + hh);
  gfx.lineTo(cx - hw, cy);
  gfx.closePath();
  gfx.fillPath();
}

/** Darken a color by a factor */
function darken(c: number, f: number): number {
  const r = Math.floor(((c >> 16) & 0xff) * f);
  const g = Math.floor(((c >> 8) & 0xff) * f);
  const b = Math.floor((c & 0xff) * f);
  return (r << 16) | (g << 8) | b;
}

/** Draw an isometric box (top + right face + left face) with outline */
function isoBox(gfx: Phaser.GameObjects.Graphics, cx: number, cy: number, hw: number, hh: number, height: number, color: number, alpha: number) {
  // Top face
  gfx.fillStyle(color, alpha);
  gfx.beginPath();
  gfx.moveTo(cx, cy - hh - height);
  gfx.lineTo(cx + hw, cy - height);
  gfx.lineTo(cx, cy + hh - height);
  gfx.lineTo(cx - hw, cy - height);
  gfx.closePath();
  gfx.fillPath();

  // Right face (darker)
  gfx.fillStyle(darken(color, 0.7), alpha);
  gfx.beginPath();
  gfx.moveTo(cx + hw, cy - height);
  gfx.lineTo(cx, cy + hh - height);
  gfx.lineTo(cx, cy + hh);
  gfx.lineTo(cx + hw, cy);
  gfx.closePath();
  gfx.fillPath();

  // Left face (darkest)
  gfx.fillStyle(darken(color, 0.5), alpha);
  gfx.beginPath();
  gfx.moveTo(cx - hw, cy - height);
  gfx.lineTo(cx, cy + hh - height);
  gfx.lineTo(cx, cy + hh);
  gfx.lineTo(cx - hw, cy);
  gfx.closePath();
  gfx.fillPath();

  // Dark outline for pixel-art consistency
  gfx.lineStyle(1, 0x1a1a2a, 0.4);
  gfx.beginPath();
  // Top face outline
  gfx.moveTo(cx, cy - hh - height);
  gfx.lineTo(cx + hw, cy - height);
  gfx.lineTo(cx, cy + hh - height);
  gfx.lineTo(cx - hw, cy - height);
  gfx.closePath();
  gfx.strokePath();
  // Right edge
  gfx.beginPath();
  gfx.moveTo(cx + hw, cy - height);
  gfx.lineTo(cx + hw, cy);
  gfx.lineTo(cx, cy + hh);
  gfx.lineTo(cx, cy + hh - height);
  gfx.strokePath();
  // Left edge
  gfx.beginPath();
  gfx.moveTo(cx - hw, cy - height);
  gfx.lineTo(cx - hw, cy);
  gfx.lineTo(cx, cy + hh);
  gfx.strokePath();
}

// ── DESK: flat surface with monitor silhouette ──
function drawDesk(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.85, hh * 0.85, 6, style.color, 0.85);
  const mw = hw * 0.35;
  const mh = hh * 0.2;
  isoBox(gfx, pos.x, pos.y - 4, mw, mh, 14, 0x1a1e28, 0.9);
  if (style.glow) {
    gfx.fillStyle(style.accent, 0.5);
    gfx.beginPath();
    gfx.moveTo(pos.x, pos.y - 4 - mh - 14);
    gfx.lineTo(pos.x + mw, pos.y - 4 - 14);
    gfx.lineTo(pos.x, pos.y - 4 + mh - 14);
    gfx.lineTo(pos.x - mw, pos.y - 4 - 14);
    gfx.closePath();
    gfx.fillPath();
  }
}

// ── CHAIR: small dark rounded box ──
function drawChair(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  const s = 0.5;
  isoBox(gfx, pos.x, pos.y, hw * s, hh * s, 8, style.color, 0.8);
  const bw = hw * 0.15;
  const bh = hh * 0.4;
  isoBox(gfx, pos.x - hw * 0.2, pos.y - 3, bw, bh, 10, style.color, 0.7);
}

// ── TABLE: flat clean surface ──
function drawTable(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.9, hh * 0.9, 5, style.color, 0.8);
}

// ── SOFA: wide low cushioned shape ──
function drawSofa(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.85, hh * 0.7, 7, style.color, 0.8);
  isoBox(gfx, pos.x - hw * 0.25, pos.y - 2, hw * 0.2, hh * 0.6, 10, style.accent, 0.6);
}

// ── SCREEN: tall thin glowing panel ──
function drawScreen(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  diamond(gfx, pos.x, pos.y, hw * 0.3, hh * 0.3, style.color, 0.4);
  isoBox(gfx, pos.x, pos.y, hw * 0.8, hh * 0.15, 24, style.color, 0.9);
  if (style.glow) {
    gfx.fillStyle(style.accent, 0.4);
    gfx.beginPath();
    gfx.moveTo(pos.x, pos.y - hh * 0.15 - 24);
    gfx.lineTo(pos.x + hw * 0.8, pos.y - 24);
    gfx.lineTo(pos.x, pos.y + hh * 0.15 - 24);
    gfx.lineTo(pos.x - hw * 0.8, pos.y - 24);
    gfx.closePath();
    gfx.fillPath();
    gfx.fillStyle(style.accent, 0.08);
    gfx.fillCircle(pos.x, pos.y - 18, hw * 0.6);
  }
}

// ── RACK: tall server cabinet with LED indicators ──
function drawRack(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.7, hh * 0.7, 28, style.color, 0.9);
  if (style.glow) {
    for (let i = 0; i < 3; i++) {
      const ly = pos.y - 8 - i * 7;
      gfx.fillStyle(style.accent, 0.8);
      gfx.fillCircle(pos.x + hw * 0.2, ly, 1.5);
      gfx.fillStyle(style.accent, 0.15);
      gfx.fillCircle(pos.x + hw * 0.2, ly, 4);
    }
  }
  gfx.lineStyle(0.5, 0xffffff, 0.1);
  for (let i = 0; i < 4; i++) {
    const ly = pos.y - 4 - i * 5;
    gfx.beginPath();
    gfx.moveTo(pos.x + hw * 0.15, ly);
    gfx.lineTo(pos.x + hw * 0.55, ly - hh * 0.15);
    gfx.strokePath();
  }
}

// ── CABINET: medium box with front detail ──
function drawCabinet(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.7, hh * 0.7, 16, style.color, 0.85);
  if (style.glow) {
    gfx.fillStyle(style.accent, 0.5);
    gfx.fillRect(pos.x - 1, pos.y - 14, 2, 8);
  }
}

// ── COUNTER: long horizontal surface ──
function drawCounter(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.9, hh * 0.5, 10, style.color, 0.85);
  gfx.lineStyle(1, style.accent, 0.4);
  gfx.beginPath();
  gfx.moveTo(pos.x, pos.y - hh * 0.5 - 10);
  gfx.lineTo(pos.x + hw * 0.9, pos.y - 10);
  gfx.strokePath();
}

// ── STOOL: very small seat ──
function drawStool(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.35, hh * 0.35, 8, style.color, 0.75);
}

// ── APPLIANCE: small box with accent detail ──
function drawAppliance(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.5, hh * 0.5, 10, style.color, 0.8);
  if (style.glow) {
    gfx.fillStyle(style.accent, 0.6);
    gfx.fillCircle(pos.x, pos.y - 8, 2);
  }
}

// ── PLANT: organic green rounded shape ──
function drawPlant(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y + 2, hw * 0.3, hh * 0.3, 6, 0x6a5a4a, 0.7);
  gfx.fillStyle(style.color, 0.7);
  gfx.fillCircle(pos.x, pos.y - 10, hw * 0.35);
  gfx.fillStyle(style.accent, 0.5);
  gfx.fillCircle(pos.x - 3, pos.y - 13, hw * 0.25);
  gfx.fillCircle(pos.x + 4, pos.y - 8, hw * 0.2);
}

// ── GLASS WALL: transparent pane with edge glow ──
function drawGlassWall(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  gfx.fillStyle(style.color, 0.15);
  gfx.beginPath();
  gfx.moveTo(pos.x - hw * 0.1, pos.y - 24);
  gfx.lineTo(pos.x + hw * 0.1, pos.y - 24);
  gfx.lineTo(pos.x + hw * 0.1, pos.y + hh);
  gfx.lineTo(pos.x - hw * 0.1, pos.y + hh);
  gfx.closePath();
  gfx.fillPath();
  gfx.lineStyle(1.5, style.accent, 0.5);
  gfx.beginPath();
  gfx.moveTo(pos.x, pos.y - 24);
  gfx.lineTo(pos.x, pos.y + hh);
  gfx.strokePath();
  gfx.lineStyle(1, style.accent, 0.3);
  gfx.beginPath();
  gfx.moveTo(pos.x - hw * 0.1, pos.y - 24);
  gfx.lineTo(pos.x + hw * 0.1, pos.y - 24);
  gfx.strokePath();
  gfx.lineStyle(0.5, 0xffffff, 0.15);
  gfx.beginPath();
  gfx.moveTo(pos.x - 2, pos.y - 20);
  gfx.lineTo(pos.x - 2, pos.y + hh - 4);
  gfx.strokePath();
}

// ── WHITEBOARD: flat white panel ──
function drawWhiteboard(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.8, hh * 0.1, 16, style.color, 0.85);
  gfx.lineStyle(1, style.accent, 0.5);
  gfx.beginPath();
  gfx.moveTo(pos.x, pos.y - hh * 0.1 - 16);
  gfx.lineTo(pos.x + hw * 0.8, pos.y - 16);
  gfx.lineTo(pos.x, pos.y + hh * 0.1 - 16);
  gfx.lineTo(pos.x - hw * 0.8, pos.y - 16);
  gfx.closePath();
  gfx.strokePath();
}

// ── DOOR: tall frame ──
function drawDoor(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.5, hh * 0.15, 22, style.color, 0.7);
  gfx.fillStyle(style.accent, 0.6);
  gfx.fillCircle(pos.x + hw * 0.2, pos.y - 10, 1.5);
}

// ── POOL: flat glowing water ──
function drawPool(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  diamond(gfx, pos.x, pos.y, hw * 0.95, hh * 0.95, style.color, 0.6);
  diamond(gfx, pos.x - 4, pos.y + 2, hw * 0.3, hh * 0.2, style.accent, 0.3);
  diamond(gfx, pos.x + 6, pos.y - 1, hw * 0.2, hh * 0.15, style.accent, 0.2);
  if (style.glow) {
    gfx.fillStyle(style.accent, 0.08);
    gfx.fillCircle(pos.x, pos.y, hw * 0.7);
  }
  gfx.lineStyle(1.5, 0xc8ccd4, 0.6);
  gfx.beginPath();
  gfx.moveTo(pos.x, pos.y - hh * 0.95);
  gfx.lineTo(pos.x + hw * 0.95, pos.y);
  gfx.lineTo(pos.x, pos.y + hh * 0.95);
  gfx.lineTo(pos.x - hw * 0.95, pos.y);
  gfx.closePath();
  gfx.strokePath();
}

// ── LIGHTS: string of lights ──
function drawLights(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, _hh: number, style: Style) {
  gfx.lineStyle(1, style.color, 0.6);
  gfx.beginPath();
  gfx.moveTo(pos.x - hw * 0.8, pos.y);
  gfx.lineTo(pos.x + hw * 0.8, pos.y);
  gfx.strokePath();
  const count = Math.max(3, Math.floor(hw / 8));
  for (let i = 0; i < count; i++) {
    const lx = pos.x - hw * 0.7 + (hw * 1.4 * i) / (count - 1);
    gfx.fillStyle(style.accent, 0.7);
    gfx.fillCircle(lx, pos.y + 1, 2);
    if (style.glow) {
      gfx.fillStyle(style.accent, 0.15);
      gfx.fillCircle(lx, pos.y + 1, 5);
    }
  }
}

// ── NEON: glowing sign ──
function drawNeon(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, _hh: number, style: Style) {
  gfx.fillStyle(0x1a1a2a, 0.6);
  gfx.fillRoundedRect(pos.x - hw * 0.5, pos.y - 10, hw, 14, 3);
  if (style.glow) {
    gfx.fillStyle(style.color, 0.12);
    gfx.fillCircle(pos.x, pos.y - 3, hw * 0.5);
  }
}

// ── CAMERA: tiny mounted dot ──
function drawCamera(gfx: Phaser.GameObjects.Graphics, pos: Pos, _hw: number, _hh: number, style: Style) {
  gfx.fillStyle(style.color, 0.8);
  gfx.fillCircle(pos.x, pos.y, 3);
  gfx.fillStyle(style.accent, 0.9);
  gfx.fillCircle(pos.x, pos.y, 1.5);
  if (style.glow) {
    gfx.fillStyle(style.accent, 0.15);
    gfx.fillCircle(pos.x, pos.y, 6);
  }
}

// ── CABLES: low ground detail ──
function drawCables(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, _hh: number, style: Style) {
  gfx.lineStyle(2, style.color, 0.4);
  gfx.beginPath();
  gfx.moveTo(pos.x - hw * 0.6, pos.y);
  gfx.lineTo(pos.x - hw * 0.2, pos.y + 2);
  gfx.lineTo(pos.x + hw * 0.2, pos.y - 1);
  gfx.lineTo(pos.x + hw * 0.6, pos.y + 1);
  gfx.strokePath();
  gfx.lineStyle(1.5, style.accent, 0.3);
  gfx.beginPath();
  gfx.moveTo(pos.x - hw * 0.5, pos.y + 3);
  gfx.lineTo(pos.x + hw * 0.5, pos.y + 2);
  gfx.strokePath();
}

// ── BEAN BAG: low rounded blob ──
function drawBeanBag(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  gfx.fillStyle(style.color, 0.7);
  gfx.fillEllipse(pos.x, pos.y - 2, hw * 0.7, hh * 0.6);
  gfx.fillStyle(style.accent, 0.3);
  gfx.fillEllipse(pos.x - 2, pos.y - 4, hw * 0.4, hh * 0.3);
}

// ── GENERIC: simple isometric box ──
function drawGeneric(gfx: Phaser.GameObjects.Graphics, pos: Pos, hw: number, hh: number, style: Style) {
  isoBox(gfx, pos.x, pos.y, hw * 0.7, hh * 0.7, 10, style.color, 0.7);
}

/**
 * Place all props from an array into the scene.
 */
export function placeAllProps(
  scene: Phaser.Scene,
  props: PropPlacement[],
): Phaser.GameObjects.GameObject[] {
  return props.map(prop => placeProp(scene, prop));
}
