import type { Miniverse } from '@miniverse/core';

const ZOOM_MIN = 0.4;
const ZOOM_MAX = 3.0;
const ZOOM_STEP = 0.1;
const ZOOM_SMOOTH = 0.15; // lerp factor

let targetZoom = 1.0;
let currentZoom = 1.0;

export function initZoom(mv: Miniverse): void {
  const canvas = mv.getCanvas();
  const camera = (mv as any).renderer.camera;

  // Mouse wheel zoom
  canvas.addEventListener('wheel', (e: WheelEvent) => {
    e.preventDefault();
    const direction = e.deltaY > 0 ? -1 : 1;
    targetZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, targetZoom + direction * ZOOM_STEP));
  }, { passive: false });

  // Keyboard zoom: + / -
  document.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
    if (e.key === '=' || e.key === '+') {
      targetZoom = Math.min(ZOOM_MAX, targetZoom + ZOOM_STEP);
    } else if (e.key === '-') {
      targetZoom = Math.max(ZOOM_MIN, targetZoom - ZOOM_STEP);
    } else if (e.key === '0') {
      targetZoom = 1.0; // Reset zoom
    }
  });

  // Smooth zoom via render layer (runs every frame)
  mv.addLayer({
    order: -1, // Before everything
    render: () => {
      currentZoom += (targetZoom - currentZoom) * ZOOM_SMOOTH;
      camera.zoom = currentZoom;
    },
  });
}

export function setZoom(level: number): void {
  targetZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, level));
}

export function getZoom(): number {
  return currentZoom;
}
