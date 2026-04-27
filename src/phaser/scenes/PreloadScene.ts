/**
 * PreloadScene — loads assets and shows a loading bar.
 *
 * Phase A: No external assets to load (floor is drawn via Graphics).
 * Phase B+: Will load texture atlases for SmallScaleInt tiles and characters.
 */
import Phaser from 'phaser';

export class PreloadScene extends Phaser.Scene {
  constructor() {
    super({ key: 'PreloadScene' });
  }

  preload(): void {
    // Loading bar
    const { width, height } = this.cameras.main;
    const barW = width * 0.4;
    const barH = 8;
    const barX = (width - barW) / 2;
    const barY = height / 2;

    const bg = this.add.rectangle(barX + barW / 2, barY, barW, barH, 0x333344);
    bg.setOrigin(0.5, 0.5);

    const fill = this.add.rectangle(barX, barY, 0, barH, 0xe94560);
    fill.setOrigin(0, 0.5);

    const label = this.add.text(width / 2, barY - 30, 'LOADING EASY COMPANY HQ...', {
      fontFamily: 'Courier New, monospace',
      fontSize: '14px',
      color: '#666',
    }).setOrigin(0.5);

    this.load.on('progress', (value: number) => {
      fill.width = barW * value;
    });

    this.load.on('complete', () => {
      bg.destroy();
      fill.destroy();
      label.destroy();
    });

    // Phase B: load atlases here
    // this.load.atlas('furniture', 'atlas/furniture.png', 'atlas/furniture.json');
    // this.load.atlas('characters', 'atlas/characters.png', 'atlas/characters.json');
  }

  create(): void {
    this.scene.start('CampusScene');
  }
}
