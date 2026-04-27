/**
 * CampusScene — main isometric campus rendering.
 *
 * Phase A: Renders floor grid as colored diamonds + zone labels.
 * Phase B: Hybrid props (Pixel Salvaje tiles + geometric), glass/solid walls,
 *          proper doorways, zone separations with distinct wall types.
 * Phase C: Adds agent characters with 8-dir movement.
 */
import Phaser from 'phaser';
import { buildFloorGrid, GRID_COLS, GRID_ROWS, ZONES } from '../../campus-layout';
import { getDiamondCorners, gridToScreen, TILE_W, TILE_H } from '../systems/IsometricGrid';
import { getTileColor, ZONE_ACCENT_COLORS } from '../data/TileMapper';
import { CameraController } from '../systems/CameraController';
import { ALL_PROPS } from '../../campus-props';
import { placeAllProps } from '../entities/PropSprite';

// ── Wall type definitions per zone ──
type WallType = 'glass' | 'frosted' | 'solid' | 'none';

interface WallConfig {
  type: WallType;
  color: number;
  alpha: number;
  height: number;
}

const WALL_CONFIGS: Record<WallType, WallConfig> = {
  glass:   { type: 'glass',   color: 0x8ab4d8, alpha: 0.10, height: 22 },
  frosted: { type: 'frosted', color: 0xa0c0e0, alpha: 0.18, height: 22 },
  solid:   { type: 'solid',   color: 0x4a5060, alpha: 0.70, height: 24 },
  none:    { type: 'none',    color: 0, alpha: 0, height: 0 },
};

/** Zone name → wall type for its boundaries */
const ZONE_WALL_TYPES: Record<string, WallType> = {
  data_center:   'solid',    // Security: solid walls
  auditorium:    'solid',    // Soundproofing
  noc_war_room:  'frosted',  // Visible but private
  scrum_room:    'glass',    // Full transparency
  open_cowork:   'glass',    // Open feel with definition
  ceo_office:    'frosted',  // Executive privacy
  huddle_pods:   'glass',    // Collaboration visibility
  snack_bar:     'none',     // Open social area
  cafe:          'none',     // Open social area
  gaming_lounge: 'glass',    // Visible fun zone
  terrace:       'none',     // Outdoor, no walls
  green_area:    'none',     // Outdoor, no walls
  architect:     'solid',    // Isolated bunker
};

/** Corridor entry points between zones — where doors are placed */
interface DoorDef {
  col: number;
  row: number;
  orientation: 'h' | 'v'; // horizontal or vertical door
  type: 'glass' | 'solid' | 'open'; // door style
}

const DOORS: DoorDef[] = [
  // Underground floor — vertical corridors between zones
  { col: 10, row: 4, orientation: 'v', type: 'solid' },    // Data Center ↔ Auditorium
  { col: 20, row: 4, orientation: 'v', type: 'glass' },    // Auditorium ↔ NOC
  { col: 30, row: 4, orientation: 'v', type: 'glass' },    // NOC ↔ Scrum

  // Main floor horizontal corridor (rows 9-10) — entry to each zone
  { col: 5, row: 9, orientation: 'h', type: 'solid' },     // Data Center entrance
  { col: 15, row: 9, orientation: 'h', type: 'glass' },    // Auditorium entrance
  { col: 25, row: 9, orientation: 'h', type: 'glass' },    // NOC entrance
  { col: 35, row: 9, orientation: 'h', type: 'glass' },    // Scrum entrance

  // Main floor — vertical corridors
  { col: 15, row: 14, orientation: 'v', type: 'glass' },   // Cowork ↔ CEO
  { col: 23, row: 14, orientation: 'v', type: 'glass' },   // CEO ↔ Huddle

  // Social floor corridor (row 19)
  { col: 7, row: 19, orientation: 'h', type: 'open' },     // Cowork → Snack
  { col: 19, row: 19, orientation: 'h', type: 'open' },    // CEO → Café
  { col: 31, row: 19, orientation: 'h', type: 'open' },    // Huddle → Gaming

  // Social floor — vertical corridors
  { col: 6, row: 22, orientation: 'v', type: 'open' },     // Snack ↔ Café
  { col: 14, row: 22, orientation: 'v', type: 'open' },    // Café ↔ Gaming

  // Outdoor corridor (row 25)
  { col: 7, row: 25, orientation: 'h', type: 'open' },     // Snack → Terrace
  { col: 26, row: 25, orientation: 'h', type: 'open' },    // Gaming → Green Area
];

export class CampusScene extends Phaser.Scene {
  private cameraCtrl!: CameraController;
  private floorGrid!: string[][];

  constructor() {
    super({ key: 'CampusScene' });
  }

  create(): void {
    this.floorGrid = buildFloorGrid();

    // Layer 0: Floor tiles
    this.renderFloor();

    // Layer 1: Zone border outlines
    this.renderGridOverlay();

    // Layer 2: Zone labels
    this.renderZoneLabels();

    // Layer 5: Zone wall separations (glass, frosted, solid)
    this.renderZoneWalls();

    // Layer 6: Doors at corridor entry points
    this.renderDoors();

    // Layer 7-15: Props (furniture, equipment, decorations)
    placeAllProps(this, ALL_PROPS);

    // Initialize camera controller (zoom, pan, hotkeys)
    this.cameraCtrl = new CameraController(this);

    // HUD info text
    this.addInfoText();
  }

  /**
   * Render all floor tiles as colored isometric diamonds.
   */
  private renderFloor(): void {
    const gfx = this.add.graphics();
    gfx.setDepth(0);

    for (let row = 0; row < GRID_ROWS; row++) {
      for (let col = 0; col < GRID_COLS; col++) {
        const tileKey = this.floorGrid[row]?.[col] ?? '';
        const color = getTileColor(tileKey);
        const corners = getDiamondCorners(col, row);

        gfx.fillStyle(color, tileKey ? 1 : 0.3);
        gfx.beginPath();
        gfx.moveTo(corners[0].x, corners[0].y);
        gfx.lineTo(corners[1].x, corners[1].y);
        gfx.lineTo(corners[2].x, corners[2].y);
        gfx.lineTo(corners[3].x, corners[3].y);
        gfx.closePath();
        gfx.fillPath();

        if (tileKey) {
          gfx.lineStyle(0.5, 0xffffff, 0.1);
          gfx.beginPath();
          gfx.moveTo(corners[0].x, corners[0].y);
          gfx.lineTo(corners[1].x, corners[1].y);
          gfx.lineTo(corners[2].x, corners[2].y);
          gfx.lineTo(corners[3].x, corners[3].y);
          gfx.closePath();
          gfx.strokePath();
        }
      }
    }
  }

  /**
   * Render zone border outlines for visual separation.
   */
  private renderGridOverlay(): void {
    const gfx = this.add.graphics();
    gfx.setDepth(1);

    for (const zone of ZONES) {
      const accentColor = ZONE_ACCENT_COLORS[zone.name] ?? 0xffffff;
      gfx.lineStyle(1.5, accentColor, 0.25);

      gfx.beginPath();
      for (let c = zone.colStart; c <= zone.colEnd; c++) {
        const dc = getDiamondCorners(c, zone.rowStart);
        if (c === zone.colStart) gfx.moveTo(dc[3].x, dc[3].y);
        gfx.lineTo(dc[0].x, dc[0].y);
        gfx.lineTo(dc[1].x, dc[1].y);
      }
      for (let r = zone.rowStart; r <= zone.rowEnd; r++) {
        const dc = getDiamondCorners(zone.colEnd, r);
        gfx.lineTo(dc[1].x, dc[1].y);
        gfx.lineTo(dc[2].x, dc[2].y);
      }
      for (let c = zone.colEnd; c >= zone.colStart; c--) {
        const dc = getDiamondCorners(c, zone.rowEnd);
        gfx.lineTo(dc[2].x, dc[2].y);
        gfx.lineTo(dc[3].x, dc[3].y);
      }
      for (let r = zone.rowEnd; r >= zone.rowStart; r--) {
        const dc = getDiamondCorners(zone.colStart, r);
        gfx.lineTo(dc[3].x, dc[3].y);
        gfx.lineTo(dc[0].x, dc[0].y);
      }
      gfx.closePath();
      gfx.strokePath();
    }
  }

  /**
   * Render zone-specific wall separations.
   * Each zone gets walls based on its function (glass, frosted, solid, or none).
   */
  private renderZoneWalls(): void {
    for (const zone of ZONES) {
      const wallType = ZONE_WALL_TYPES[zone.name] ?? 'none';
      if (wallType === 'none') continue;

      const cfg = WALL_CONFIGS[wallType];
      const gfx = this.add.graphics();
      gfx.setDepth(5);

      // Draw walls on all 4 edges
      this.drawWallEdge(gfx, zone.colStart, zone.colEnd, zone.rowStart, 'top', cfg);
      this.drawWallEdge(gfx, zone.colStart, zone.colEnd, zone.rowEnd, 'bottom', cfg);
      this.drawWallVertEdge(gfx, zone.colStart, zone.rowStart, zone.rowEnd, 'left', cfg);
      this.drawWallVertEdge(gfx, zone.colEnd, zone.rowStart, zone.rowEnd, 'right', cfg);
    }
  }

  /**
   * Draw wall along a horizontal zone edge.
   */
  private drawWallEdge(
    gfx: Phaser.GameObjects.Graphics,
    colStart: number, colEnd: number, row: number,
    edge: 'top' | 'bottom',
    cfg: WallConfig,
  ): void {
    const h = cfg.height;
    const frameColor = cfg.type === 'solid' ? 0x3a3e48 : 0xc0d8f0;

    for (let c = colStart; c <= colEnd; c++) {
      const dc = getDiamondCorners(c, row);
      const left = edge === 'top' ? dc[3] : dc[2];
      const right = edge === 'top' ? dc[0] : dc[1];

      // Wall panel
      gfx.fillStyle(cfg.color, cfg.alpha);
      gfx.beginPath();
      gfx.moveTo(left.x, left.y - h);
      gfx.lineTo(right.x, right.y - h);
      gfx.lineTo(right.x, right.y);
      gfx.lineTo(left.x, left.y);
      gfx.closePath();
      gfx.fillPath();

      // Top frame edge
      gfx.lineStyle(cfg.type === 'solid' ? 1.2 : 0.8, frameColor, cfg.type === 'solid' ? 0.6 : 0.3);
      gfx.beginPath();
      gfx.moveTo(left.x, left.y - h);
      gfx.lineTo(right.x, right.y - h);
      gfx.strokePath();

      // Bottom frame edge (for solid walls)
      if (cfg.type === 'solid') {
        gfx.lineStyle(1, frameColor, 0.4);
        gfx.beginPath();
        gfx.moveTo(left.x, left.y);
        gfx.lineTo(right.x, right.y);
        gfx.strokePath();
      }

      // Reflection highlights (glass/frosted only)
      if (cfg.type !== 'solid' && c % 3 === 0) {
        gfx.lineStyle(0.5, 0xffffff, cfg.type === 'frosted' ? 0.08 : 0.12);
        const mx = (left.x + right.x) / 2;
        const my = (left.y + right.y) / 2;
        gfx.beginPath();
        gfx.moveTo(mx - 3, my - h + 4);
        gfx.lineTo(mx + 3, my - 4);
        gfx.strokePath();
      }

      // Frosted texture pattern
      if (cfg.type === 'frosted' && c % 2 === 0) {
        gfx.lineStyle(0.3, 0xffffff, 0.06);
        const mx = (left.x + right.x) / 2;
        const my = (left.y + right.y) / 2;
        for (let i = 0; i < 3; i++) {
          gfx.beginPath();
          gfx.moveTo(mx - 4 + i * 3, my - h + 3);
          gfx.lineTo(mx - 4 + i * 3, my - 3);
          gfx.strokePath();
        }
      }
    }

    // Vertical frame posts at endpoints
    this.drawFramePosts(gfx, colStart, colEnd, row, edge, h, frameColor, cfg.type);
  }

  /**
   * Draw wall along a vertical zone edge.
   */
  private drawWallVertEdge(
    gfx: Phaser.GameObjects.Graphics,
    col: number, rowStart: number, rowEnd: number,
    edge: 'left' | 'right',
    cfg: WallConfig,
  ): void {
    const h = cfg.height;
    const frameColor = cfg.type === 'solid' ? 0x3a3e48 : 0xc0d8f0;

    for (let r = rowStart; r <= rowEnd; r++) {
      const dc = getDiamondCorners(col, r);
      const top = edge === 'left' ? dc[3] : dc[0];
      const bottom = edge === 'left' ? dc[2] : dc[1];

      gfx.fillStyle(cfg.color, cfg.alpha);
      gfx.beginPath();
      gfx.moveTo(top.x, top.y - h);
      gfx.lineTo(bottom.x, bottom.y - h);
      gfx.lineTo(bottom.x, bottom.y);
      gfx.lineTo(top.x, top.y);
      gfx.closePath();
      gfx.fillPath();

      gfx.lineStyle(cfg.type === 'solid' ? 1.2 : 0.8, frameColor, cfg.type === 'solid' ? 0.6 : 0.3);
      gfx.beginPath();
      gfx.moveTo(top.x, top.y - h);
      gfx.lineTo(bottom.x, bottom.y - h);
      gfx.strokePath();

      if (cfg.type === 'solid') {
        gfx.lineStyle(1, frameColor, 0.4);
        gfx.beginPath();
        gfx.moveTo(top.x, top.y);
        gfx.lineTo(bottom.x, bottom.y);
        gfx.strokePath();
      }

      if (cfg.type !== 'solid' && r % 3 === 0) {
        gfx.lineStyle(0.5, 0xffffff, cfg.type === 'frosted' ? 0.08 : 0.12);
        const mx = (top.x + bottom.x) / 2;
        const my = (top.y + bottom.y) / 2;
        gfx.beginPath();
        gfx.moveTo(mx - 2, my - h + 5);
        gfx.lineTo(mx + 2, my - 3);
        gfx.strokePath();
      }

      if (cfg.type === 'frosted' && r % 2 === 0) {
        gfx.lineStyle(0.3, 0xffffff, 0.06);
        const mx = (top.x + bottom.x) / 2;
        const my = (top.y + bottom.y) / 2;
        for (let i = 0; i < 3; i++) {
          gfx.beginPath();
          gfx.moveTo(mx - 3 + i * 2, my - h + 3);
          gfx.lineTo(mx - 3 + i * 2, my - 3);
          gfx.strokePath();
        }
      }
    }

    // Vertical frame posts
    const startCorner = getDiamondCorners(col, rowStart);
    const endCorner = getDiamondCorners(col, rowEnd);
    const postStart = edge === 'left' ? startCorner[3] : startCorner[0];
    const postEnd = edge === 'left' ? endCorner[2] : endCorner[1];

    gfx.lineStyle(cfg.type === 'solid' ? 1.5 : 1.2, frameColor, cfg.type === 'solid' ? 0.7 : 0.4);
    gfx.beginPath();
    gfx.moveTo(postStart.x, postStart.y);
    gfx.lineTo(postStart.x, postStart.y - h);
    gfx.strokePath();
    gfx.beginPath();
    gfx.moveTo(postEnd.x, postEnd.y);
    gfx.lineTo(postEnd.x, postEnd.y - h);
    gfx.strokePath();
  }

  /**
   * Draw vertical frame posts at wall endpoints.
   */
  private drawFramePosts(
    gfx: Phaser.GameObjects.Graphics,
    colStart: number, colEnd: number, row: number,
    edge: 'top' | 'bottom', h: number, frameColor: number, type: string,
  ): void {
    const startCorner = getDiamondCorners(colStart, row);
    const endCorner = getDiamondCorners(colEnd, row);
    const postStart = edge === 'top' ? startCorner[3] : startCorner[2];
    const postEnd = edge === 'top' ? endCorner[0] : endCorner[1];

    gfx.lineStyle(type === 'solid' ? 1.5 : 1.2, frameColor, type === 'solid' ? 0.7 : 0.4);
    gfx.beginPath();
    gfx.moveTo(postStart.x, postStart.y);
    gfx.lineTo(postStart.x, postStart.y - h);
    gfx.strokePath();
    gfx.beginPath();
    gfx.moveTo(postEnd.x, postEnd.y);
    gfx.lineTo(postEnd.x, postEnd.y - h);
    gfx.strokePath();
  }

  /**
   * Render doors at corridor entry points.
   */
  private renderDoors(): void {
    const gfx = this.add.graphics();
    gfx.setDepth(6);

    for (const door of DOORS) {
      const center = gridToScreen(door.col + 0.5, door.row + 0.5);
      const h = 24;

      if (door.type === 'open') {
        // Open doorway — just frame posts
        this.drawDoorFrame(gfx, center, door.orientation, h, 0x8a8a9a);
        continue;
      }

      const isGlass = door.type === 'glass';
      const doorColor = isGlass ? 0x8ab4d8 : 0x5a6070;
      const doorAlpha = isGlass ? 0.15 : 0.65;
      const frameClr = isGlass ? 0xc0d8f0 : 0x3a3e48;
      const doorW = TILE_W * 0.4;
      const doorH = TILE_H * 0.2;

      // Door panel
      if (door.orientation === 'h') {
        // Horizontal door — spans left-right
        gfx.fillStyle(doorColor, doorAlpha);
        gfx.beginPath();
        gfx.moveTo(center.x - doorW / 2, center.y - doorH / 2 - h);
        gfx.lineTo(center.x + doorW / 2, center.y + doorH / 2 - h);
        gfx.lineTo(center.x + doorW / 2, center.y + doorH / 2);
        gfx.lineTo(center.x - doorW / 2, center.y - doorH / 2);
        gfx.closePath();
        gfx.fillPath();
      } else {
        // Vertical door — spans top-bottom
        gfx.fillStyle(doorColor, doorAlpha);
        gfx.beginPath();
        gfx.moveTo(center.x - doorW / 2, center.y + doorH / 2 - h);
        gfx.lineTo(center.x + doorW / 2, center.y - doorH / 2 - h);
        gfx.lineTo(center.x + doorW / 2, center.y - doorH / 2);
        gfx.lineTo(center.x - doorW / 2, center.y + doorH / 2);
        gfx.closePath();
        gfx.fillPath();
      }

      // Door frame
      this.drawDoorFrame(gfx, center, door.orientation, h, frameClr);

      // Handle
      gfx.fillStyle(isGlass ? 0xaaaacc : 0xccccdd, 0.8);
      gfx.fillCircle(center.x + 3, center.y - h / 2, 1.5);

      // Glass door reflection
      if (isGlass) {
        gfx.lineStyle(0.4, 0xffffff, 0.15);
        gfx.beginPath();
        gfx.moveTo(center.x - 4, center.y - h + 4);
        gfx.lineTo(center.x + 2, center.y - 6);
        gfx.strokePath();
      }
    }
  }

  /**
   * Draw door frame posts.
   */
  private drawDoorFrame(
    gfx: Phaser.GameObjects.Graphics,
    center: { x: number; y: number },
    orientation: 'h' | 'v',
    h: number,
    frameColor: number,
  ): void {
    const offset = orientation === 'h'
      ? { dx: TILE_W * 0.22, dy: TILE_H * 0.11 }
      : { dx: TILE_W * 0.22, dy: -TILE_H * 0.11 };

    gfx.lineStyle(1.5, frameColor, 0.6);
    // Left post
    gfx.beginPath();
    gfx.moveTo(center.x - offset.dx, center.y - offset.dy);
    gfx.lineTo(center.x - offset.dx, center.y - offset.dy - h);
    gfx.strokePath();
    // Right post
    gfx.beginPath();
    gfx.moveTo(center.x + offset.dx, center.y + offset.dy);
    gfx.lineTo(center.x + offset.dx, center.y + offset.dy - h);
    gfx.strokePath();
    // Top lintel
    gfx.lineStyle(1.2, frameColor, 0.5);
    gfx.beginPath();
    gfx.moveTo(center.x - offset.dx, center.y - offset.dy - h);
    gfx.lineTo(center.x + offset.dx, center.y + offset.dy - h);
    gfx.strokePath();
  }

  /**
   * Render zone name labels.
   */
  private renderZoneLabels(): void {
    for (const zone of ZONES) {
      const centerCol = (zone.colStart + zone.colEnd) / 2;
      const centerRow = (zone.rowStart + zone.rowEnd) / 2;
      const center = gridToScreen(centerCol, centerRow);

      const accentColor = ZONE_ACCENT_COLORS[zone.name] ?? 0xffffff;
      const hexStr = '#' + accentColor.toString(16).padStart(6, '0');

      const label = this.add.text(center.x, center.y - 12, this.formatZoneName(zone.name), {
        fontFamily: 'Courier New, monospace',
        fontSize: '11px',
        color: hexStr,
        stroke: '#000000',
        strokeThickness: 3,
      });
      label.setOrigin(0.5);
      label.setDepth(100);
      label.setAlpha(0.8);
    }
  }

  private formatZoneName(name: string): string {
    return name
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  private addInfoText(): void {
    const info = this.add.text(16, 16, [
      'EASY COMPANY HQ — Isometric View',
      '',
      'Scroll: zoom · Drag: pan · F: fit all',
      'A: architect · 1-9: zones',
    ].join('\n'), {
      fontFamily: 'Courier New, monospace',
      fontSize: '11px',
      color: '#555555',
      lineSpacing: 4,
    });
    info.setScrollFactor(0);
    info.setDepth(200);
  }
}
