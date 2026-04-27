/**
 * Camera controller for the isometric campus view.
 *
 * Features:
 *   - Scroll wheel zoom (cursor-centric)
 *   - Left-click drag to pan
 *   - F key: fit entire map
 *   - A key: snap to Architect's Office
 *   - 1-9 keys: snap to zones
 *   - Touch: pinch-to-zoom + drag-to-pan
 */
import Phaser from 'phaser';
import { gridToScreen, getWorldBounds, TILE_W, TILE_H } from './IsometricGrid';
import { GRID_COLS, GRID_ROWS, ZONES } from '../../campus-layout';

const ZOOM_MIN = 0.15;
const ZOOM_MAX = 3.0;
const ZOOM_STEP = 0.1;
const PAN_THRESHOLD = 3; // px before starting drag

export class CameraController {
  private scene: Phaser.Scene;
  private camera: Phaser.Cameras.Scene2D.Camera;
  private isDragging = false;
  private dragStart = { x: 0, y: 0 };
  private worldBounds: { minX: number; minY: number; width: number; height: number };

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.camera = scene.cameras.main;
    this.worldBounds = getWorldBounds(GRID_COLS, GRID_ROWS);

    // No camera bounds — at low zoom the viewport exceeds world size,
    // and Phaser's bounds clamping breaks centering. We handle scroll freely.

    this.setupMouseControls();
    this.setupKeyboardControls();

    // Delay fitToScreen by one frame so Phaser has finalized camera dimensions
    scene.time.delayedCall(0, () => this.fitToScreen());
  }

  private setupMouseControls(): void {
    const input = this.scene.input;

    // Scroll wheel zoom (cursor-centric)
    input.on('wheel', (_pointer: Phaser.Input.Pointer, _go: unknown[], _dx: number, dy: number) => {
      const pointer = this.scene.input.activePointer;
      const oldZoom = this.camera.zoom;
      const newZoom = Phaser.Math.Clamp(
        oldZoom - Math.sign(dy) * ZOOM_STEP * oldZoom,
        ZOOM_MIN,
        ZOOM_MAX,
      );

      // Cursor-centric zoom: keep the world point under cursor fixed
      const worldBefore = this.camera.getWorldPoint(pointer.x, pointer.y);
      this.camera.setZoom(newZoom);
      const worldAfter = this.camera.getWorldPoint(pointer.x, pointer.y);

      this.camera.scrollX += worldBefore.x - worldAfter.x;
      this.camera.scrollY += worldBefore.y - worldAfter.y;
    });

    // Left-click drag to pan
    input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      if (pointer.leftButtonDown()) {
        this.dragStart = { x: pointer.x, y: pointer.y };
        this.isDragging = false;
      }
    });

    input.on('pointermove', (pointer: Phaser.Input.Pointer) => {
      if (!pointer.leftButtonDown()) return;

      const dx = pointer.x - this.dragStart.x;
      const dy = pointer.y - this.dragStart.y;

      if (!this.isDragging && Math.sqrt(dx * dx + dy * dy) > PAN_THRESHOLD) {
        this.isDragging = true;
      }

      if (this.isDragging) {
        this.camera.scrollX -= (pointer.x - pointer.prevPosition.x) / this.camera.zoom;
        this.camera.scrollY -= (pointer.y - pointer.prevPosition.y) / this.camera.zoom;
      }
    });

    input.on('pointerup', () => {
      this.isDragging = false;
    });
  }

  private setupKeyboardControls(): void {
    const keyboard = this.scene.input.keyboard;
    if (!keyboard) return;

    // F = fit all
    keyboard.on('keydown-F', () => this.fitToScreen());

    // A = snap to Architect
    keyboard.on('keydown-A', () => {
      const arch = gridToScreen(9, 36);
      this.panTo(arch.x, arch.y, 1.5);
    });

    // 0 = reset zoom
    keyboard.on('keydown-ZERO', () => this.fitToScreen());

    // 1-9 = snap to zones (in order)
    const zoneKeys = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'];
    zoneKeys.forEach((key, i) => {
      keyboard.on(`keydown-${key}`, () => {
        if (i < ZONES.length) {
          this.snapToZone(i);
        }
      });
    });
  }

  /** Fit the main campus (rows 0-32) into viewport. Architect is accessed via 'A' key. */
  fitToScreen(): void {
    const cam = this.camera;

    // Use main campus bounds (rows 0-32, all cols) — exclude Architect island
    const mainBounds = getWorldBounds(GRID_COLS, 33); // rows 0-32
    const zx = cam.width / mainBounds.width;
    const zy = cam.height / mainBounds.height;
    const zoom = Math.min(zx, zy) * 0.9; // 90% fill

    cam.setZoom(Phaser.Math.Clamp(zoom, ZOOM_MIN, ZOOM_MAX));

    // Center on main campus
    const centerX = mainBounds.minX + mainBounds.width / 2;
    const centerY = mainBounds.minY + mainBounds.height / 2;
    cam.centerOn(centerX, centerY);
  }

  /** Snap camera to a world coordinate with optional zoom */
  panTo(worldX: number, worldY: number, zoom?: number): void {
    if (zoom !== undefined) {
      this.camera.setZoom(Phaser.Math.Clamp(zoom, ZOOM_MIN, ZOOM_MAX));
    }
    this.camera.centerOn(worldX, worldY);
  }

  /** Snap camera to a zone by index */
  snapToZone(index: number): void {
    const zone = ZONES[index];
    if (!zone) return;

    const centerCol = (zone.colStart + zone.colEnd) / 2;
    const centerRow = (zone.rowStart + zone.rowEnd) / 2;
    const center = gridToScreen(centerCol, centerRow);

    // Calculate zoom to fit the zone
    const zoneCols = zone.colEnd - zone.colStart + 1;
    const zoneRows = zone.rowEnd - zone.rowStart + 1;
    const zoneW = (zoneCols + zoneRows) * TILE_W / 2;
    const zoneH = (zoneCols + zoneRows) * TILE_H / 2;
    const zx = this.camera.width / zoneW;
    const zy = this.camera.height / zoneH;
    const zoom = Math.min(zx, zy) * 0.7;

    this.panTo(center.x, center.y, Phaser.Math.Clamp(zoom, ZOOM_MIN, ZOOM_MAX));
  }

  /** Is the user currently dragging the camera? */
  get dragging(): boolean {
    return this.isDragging;
  }
}
