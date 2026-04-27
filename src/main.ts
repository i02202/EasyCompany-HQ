/**
 * Easy Company HQ — Isometric Phaser 3 entry point.
 *
 * Replaces the MiniVRS renderer with Phaser 3 isometric view.
 * Data files (campus-layout, campus-props, campus-wander) are reused 1:1.
 */
import Phaser from 'phaser';
import { gameConfig } from './phaser/config';

// Boot Phaser
const game = new Phaser.Game(gameConfig);

// Handle window resize
window.addEventListener('resize', () => {
  game.scale.resize(window.innerWidth, window.innerHeight);
});

// Expose for debugging
(window as any).__easyCompanyGame = game;
