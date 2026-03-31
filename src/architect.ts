import type { Miniverse } from '@miniverse/core';
import { setZoom } from './zoom';

const ARCHITECT_AGENT = 'architect';
const ARCHITECT_TILE = { x: 9, y: 37 }; // Center of the office in tile coords (rows 37-38)

/**
 * Initialize the Architect's Office.
 * - Sends a permanent heartbeat for the architect agent
 * - Binds 'A' key to snap camera to Architect's Office
 * - The architect never moves (always "working")
 */
export function initArchitect(mv: Miniverse, serverUrl: string): void {
  // Send heartbeat to spawn architect in the hidden room
  const heartbeat = () => {
    fetch(`${serverUrl}/api/heartbeat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent: ARCHITECT_AGENT,
        name: 'The Architect',
        state: 'working',
        task: 'Observing all systems',
        energy: 1,
      }),
    }).catch(() => {});
  };

  // Initial spawn + keep-alive every 30s
  heartbeat();
  setInterval(heartbeat, 30_000);

  // Keyboard shortcut: 'A' to snap camera to Architect's Office
  document.addEventListener('keydown', (e: KeyboardEvent) => {
    // Skip when user is typing in an input field or the MiniVRS editor
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
    if (e.key === 'a' || e.key === 'A') {
      const camera = (mv as any).renderer.camera;
      const tileSize = 32;
      // Center camera on architect tile
      const targetX = ARCHITECT_TILE.x * tileSize - (mv as any).renderer.canvas.width / (2 * camera.zoom);
      const targetY = ARCHITECT_TILE.y * tileSize - (mv as any).renderer.canvas.height / (2 * camera.zoom);
      camera.setPosition(targetX, targetY);
      setZoom(2.0); // Zoom in to see the office
    }
  });
}
