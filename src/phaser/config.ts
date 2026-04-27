/**
 * Phaser 3 game configuration for Easy Company HQ.
 */
import Phaser from 'phaser';
import { BootScene } from './scenes/BootScene';
import { PreloadScene } from './scenes/PreloadScene';
import { CampusScene } from './scenes/CampusScene';

export const gameConfig: Phaser.Types.Core.GameConfig = {
  type: Phaser.WEBGL,
  parent: 'game-container',
  backgroundColor: '#050508',
  pixelArt: true,
  antialias: false,
  roundPixels: true,
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: '100%',
    height: '100%',
  },
  scene: [BootScene, PreloadScene, CampusScene],
  // Disable Phaser's default keyboard capture so it doesn't conflict with HTML inputs
  input: {
    keyboard: {
      target: window,
    },
  },
};
