import { defineConfig } from 'vite';

export default defineConfig({
  // Phaser 3 needs no special Vite plugins.
  // The old MiniVRS plugins (world-save, generate, tiles-list, citizens-list)
  // are removed — they'll return if needed for editor mode.
  build: {
    target: 'esnext',
    sourcemap: true,
  },
});
