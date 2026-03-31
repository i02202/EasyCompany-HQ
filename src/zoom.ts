import type { Miniverse } from '@miniverse/core';

const ZOOM_MIN = 0.3;
const ZOOM_MAX = 3.0;
const ZOOM_STEP = 0.15;
const ZOOM_SMOOTH = 0.12; // lerp factor

let targetZoom = 1.0;
let currentZoom = 1.0;

export function initZoom(mv: Miniverse): void {
  const canvas = mv.getCanvas();
  const camera = (mv as any).renderer.camera;
  const renderer = (mv as any).renderer;

  // Zoom toward mouse cursor (keeps point under cursor stable)
  canvas.addEventListener('wheel', (e: WheelEvent) => {
    e.preventDefault();
    const direction = e.deltaY > 0 ? -1 : 1;
    const oldZoom = targetZoom;
    targetZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, targetZoom + direction * ZOOM_STEP));

    // Zoom toward cursor: adjust camera so world point under cursor stays fixed
    if (targetZoom !== oldZoom) {
      const rect = canvas.getBoundingClientRect();
      const cssScale = rect.width / canvas.width;
      const canvasX = (e.clientX - rect.left) / cssScale;
      const canvasY = (e.clientY - rect.top) / cssScale;
      // World point under cursor at old zoom
      const worldX = canvasX / currentZoom + camera.x;
      const worldY = canvasY / currentZoom + camera.y;
      // Shift camera so same world point stays under cursor at new zoom
      const newCamX = worldX - canvasX / targetZoom;
      const newCamY = worldY - canvasY / targetZoom;
      camera.snapTo(newCamX, newCamY);
    }
  }, { passive: false });

  // Keyboard zoom: + / - / 0
  document.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
    if (e.key === '=' || e.key === '+') {
      targetZoom = Math.min(ZOOM_MAX, targetZoom + ZOOM_STEP);
    } else if (e.key === '-') {
      targetZoom = Math.max(ZOOM_MIN, targetZoom - ZOOM_STEP);
    } else if (e.key === '0') {
      targetZoom = 1.0;
    } else if (e.key === 'f' || e.key === 'F') {
      fitToScreen(canvas, camera);
    }
  });

  // Left-click drag to pan (most intuitive)
  let isPanning = false;
  let panStartX = 0, panStartY = 0;
  let camStartX = 0, camStartY = 0;
  let hasMoved = false;

  canvas.addEventListener('mousedown', (e: MouseEvent) => {
    if (e.button === 0 || e.button === 1 || e.button === 2) {
      isPanning = true;
      hasMoved = false;
      panStartX = e.clientX;
      panStartY = e.clientY;
      camStartX = camera.x;
      camStartY = camera.y;
      canvas.style.cursor = 'grabbing';
      if (e.button !== 0) e.preventDefault();
    }
  });

  canvas.addEventListener('mousemove', (e: MouseEvent) => {
    if (!isPanning) {
      canvas.style.cursor = 'grab';
      return;
    }
    const dx = e.clientX - panStartX;
    const dy = e.clientY - panStartY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasMoved = true;
    if (!hasMoved) return;
    const rect = canvas.getBoundingClientRect();
    const cssScale = rect.width / canvas.width;
    camera.snapTo(
      camStartX - dx / cssScale / currentZoom,
      camStartY - dy / cssScale / currentZoom,
    );
  });

  const endPan = () => {
    isPanning = false;
    canvas.style.cursor = 'grab';
  };
  canvas.addEventListener('mouseup', endPan);
  canvas.addEventListener('mouseleave', endPan);
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());

  // Touch: pinch-to-zoom + drag-to-pan
  let lastTouchDist = 0;
  let lastTouchX = 0, lastTouchY = 0;

  canvas.addEventListener('touchstart', (e: TouchEvent) => {
    if (e.touches.length === 1) {
      isPanning = true;
      hasMoved = false;
      panStartX = e.touches[0].clientX;
      panStartY = e.touches[0].clientY;
      camStartX = camera.x;
      camStartY = camera.y;
    } else if (e.touches.length === 2) {
      isPanning = false;
      const dx = e.touches[1].clientX - e.touches[0].clientX;
      const dy = e.touches[1].clientY - e.touches[0].clientY;
      lastTouchDist = Math.hypot(dx, dy);
      lastTouchX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      lastTouchY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    }
    e.preventDefault();
  }, { passive: false });

  canvas.addEventListener('touchmove', (e: TouchEvent) => {
    if (e.touches.length === 1 && isPanning) {
      const rect = canvas.getBoundingClientRect();
      const cssScale = rect.width / canvas.width;
      const dx = e.touches[0].clientX - panStartX;
      const dy = e.touches[0].clientY - panStartY;
      camera.snapTo(
        camStartX - dx / cssScale / currentZoom,
        camStartY - dy / cssScale / currentZoom,
      );
    } else if (e.touches.length === 2) {
      const dx = e.touches[1].clientX - e.touches[0].clientX;
      const dy = e.touches[1].clientY - e.touches[0].clientY;
      const dist = Math.hypot(dx, dy);
      if (lastTouchDist > 0) {
        const scale = dist / lastTouchDist;
        targetZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, targetZoom * scale));
      }
      lastTouchDist = dist;
    }
    e.preventDefault();
  }, { passive: false });

  canvas.addEventListener('touchend', () => { isPanning = false; lastTouchDist = 0; });

  // Smooth zoom via render layer
  mv.addLayer({
    order: -1,
    render: () => {
      currentZoom += (targetZoom - currentZoom) * ZOOM_SMOOTH;
      camera.zoom = currentZoom;
    },
  });

  // Start zoomed out to show entire campus
  canvas.style.cursor = 'grab';
  setTimeout(() => fitToScreen(canvas, camera), 100);
}

/** Zoom to fit the entire 40×40 world in the canvas */
function fitToScreen(canvas: HTMLCanvasElement, camera: any): void {
  const worldW = 40 * 32; // gridCols * tileSize
  const worldH = 40 * 32;
  const fitZoom = Math.min(canvas.width / worldW, canvas.height / worldH);
  targetZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, fitZoom));
  // Center camera on the world
  const offsetX = (canvas.width / targetZoom - worldW) / 2;
  const offsetY = (canvas.height / targetZoom - worldH) / 2;
  camera.snapTo(-offsetX, -offsetY);
}

export function setZoom(level: number): void {
  targetZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, level));
}

export function getZoom(): number {
  return currentZoom;
}
