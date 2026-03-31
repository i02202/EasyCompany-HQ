import type { Miniverse } from '@miniverse/core';
import { setZoom } from './zoom';

const ARCHITECT_AGENT = 'architect';
const ARCHITECT_TILE = { x: 9, y: 36 }; // Center of the office in tile coords (rows 34-38)

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
      const canvas = (mv as any).renderer.canvas;
      const tileSize = 32;
      // Set zoom first so viewport calc is correct
      setZoom(1.5);
      const zoom = 1.5;
      // Center camera on the architect zone (cols 4-14, rows 34-38 → center at col 9, row 36)
      const worldX = ARCHITECT_TILE.x * tileSize;
      const worldY = ARCHITECT_TILE.y * tileSize;
      const camX = worldX - canvas.width / (2 * zoom);
      const camY = worldY - canvas.height / (2 * zoom);
      camera.snapTo(camX, camY);
    }
  });
}
