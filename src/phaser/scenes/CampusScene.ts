/**
 * CampusScene — main isometric campus rendering.
 *
 * Phase A: Renders floor grid as colored diamonds + zone labels.
 * Phase B: Adds SmallScaleInt furniture sprites.
 * Phase C: Adds agent characters with 8-dir movement.
 */
import Phaser from 'phaser';
import { buildFloorGrid, GRID_COLS, GRID_ROWS, ZONES } from '../../campus-layout';
import { getDiamondCorners, gridToScreen, TILE_W, TILE_H } from '../systems/IsometricGrid';
import { getTileColor, DEADSPACE_COLOR, ZONE_ACCENT_COLORS } from '../data/TileMapper';
import { CameraController } from '../systems/CameraController';

export class CampusScene extends Phaser.Scene {
  private cameraCtrl!: CameraController;
  private floorGrid!: string[][];

  constructor() {
    super({ key: 'CampusScene' });
  }

  create(): void {
    this.floorGrid = buildFloorGrid();

    // Render the isometric floor
    this.renderFloor();

    // Render zone labels
    this.renderZoneLabels();

    // Render grid lines (subtle, for debugging/orientation)
    this.renderGridOverlay();

    // Initialize camera controller (zoom, pan, hotkeys)
    this.cameraCtrl = new CameraController(this);

    // Info text
    this.addInfoText();
  }

  /**
   * Render all floor tiles as colored isometric diamonds.
   * Uses a single Graphics object for performance.
   */
  private renderFloor(): void {
    const gfx = this.add.graphics();
    gfx.setDepth(0);

    for (let row = 0; row < GRID_ROWS; row++) {
      for (let col = 0; col < GRID_COLS; col++) {
        const tileKey = this.floorGrid[row]?.[col] ?? '';
        const color = getTileColor(tileKey);

        const corners = getDiamondCorners(col, row);

        // Fill diamond
        gfx.fillStyle(color, tileKey ? 1 : 0.3);
        gfx.beginPath();
        gfx.moveTo(corners[0].x, corners[0].y);
        gfx.lineTo(corners[1].x, corners[1].y);
        gfx.lineTo(corners[2].x, corners[2].y);
        gfx.lineTo(corners[3].x, corners[3].y);
        gfx.closePath();
        gfx.fillPath();

        // Thin border for non-deadspace tiles
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

      // Draw zone border as isometric outline
      const corners = this.getZoneBorderCorners(zone);
      gfx.beginPath();

      // Top edge (col varies, row = rowStart)
      for (let c = zone.colStart; c <= zone.colEnd; c++) {
        const dc = getDiamondCorners(c, zone.rowStart);
        if (c === zone.colStart) gfx.moveTo(dc[3].x, dc[3].y); // left corner of first
        gfx.lineTo(dc[0].x, dc[0].y); // top
        gfx.lineTo(dc[1].x, dc[1].y); // right
      }
      // Right edge (col = colEnd, row varies)
      for (let r = zone.rowStart; r <= zone.rowEnd; r++) {
        const dc = getDiamondCorners(zone.colEnd, r);
        gfx.lineTo(dc[1].x, dc[1].y); // right
        gfx.lineTo(dc[2].x, dc[2].y); // bottom
      }
      // Bottom edge (col varies, row = rowEnd) — reverse
      for (let c = zone.colEnd; c >= zone.colStart; c--) {
        const dc = getDiamondCorners(c, zone.rowEnd);
        gfx.lineTo(dc[2].x, dc[2].y); // bottom
        gfx.lineTo(dc[3].x, dc[3].y); // left
      }
      // Left edge (col = colStart, row varies) — reverse
      for (let r = zone.rowEnd; r >= zone.rowStart; r--) {
        const dc = getDiamondCorners(zone.colStart, r);
        gfx.lineTo(dc[3].x, dc[3].y); // left
        gfx.lineTo(dc[0].x, dc[0].y); // top
      }

      gfx.closePath();
      gfx.strokePath();
    }
  }

  /**
   * Get the 4 extreme corners of a zone for its isometric bounding box.
   */
  private getZoneBorderCorners(zone: typeof ZONES[number]) {
    const topCorner = getDiamondCorners(zone.colStart, zone.rowStart);
    const rightCorner = getDiamondCorners(zone.colEnd, zone.rowStart);
    const bottomCorner = getDiamondCorners(zone.colEnd, zone.rowEnd);
    const leftCorner = getDiamondCorners(zone.colStart, zone.rowEnd);

    return {
      top: topCorner[0],
      right: rightCorner[1],
      bottom: bottomCorner[2],
      left: leftCorner[3],
    };
  }

  /**
   * Render zone name labels floating above each area.
   */
  private renderZoneLabels(): void {
    for (const zone of ZONES) {
      const centerCol = (zone.colStart + zone.colEnd) / 2;
      const centerRow = (zone.rowStart + zone.rowEnd) / 2;
      const center = gridToScreen(centerCol, centerRow);

      const accentColor = ZONE_ACCENT_COLORS[zone.name] ?? 0xffffff;
      const hexStr = '#' + accentColor.toString(16).padStart(6, '0');

      // Zone name label
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

  /** Convert snake_case zone name to Title Case */
  private formatZoneName(name: string): string {
    return name
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  /**
   * Add HUD info text (fixed to camera, not world).
   */
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
    info.setScrollFactor(0); // Fixed to camera
    info.setDepth(200);
  }
}
