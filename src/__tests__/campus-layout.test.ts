import { describe, it, expect } from 'vitest';
import { buildFloorGrid, ZONES } from '../campus-layout';

describe('buildFloorGrid', () => {
  const grid = buildFloorGrid();

  it('returns a 40×40 grid', () => {
    expect(grid.length).toBe(40);
    grid.forEach((row) => expect(row.length).toBe(40));
  });

  it('has wall tiles on all borders', () => {
    for (let c = 0; c < 40; c++) {
      expect(grid[0][c]).toBe('main_wall');
      expect(grid[39][c]).toBe('main_wall');
    }
    for (let r = 0; r < 40; r++) {
      expect(grid[r][0]).toBe('main_wall');
      expect(grid[r][39]).toBe('main_wall');
    }
  });

  it('fills Data Center zone with epoxy_gray', () => {
    // Data Center: rows 1-8, cols 1-9
    expect(grid[4][5]).toBe('epoxy_gray');
  });

  it('fills Architect Office with architect_floor', () => {
    // Architect: rows 37-38, cols 5-13
    expect(grid[38][9]).toBe('architect_floor');
  });

  it('has deadspace (empty) around Architect Office', () => {
    // Row 34-36 should be empty (deadspace buffer)
    expect(grid[35][9]).toBe('');
  });

  it('fills pool tiles with pool_water', () => {
    expect(grid[29][22]).toBe('pool_water');
  });

  it('border walls are not overwritten by Architect zone', () => {
    for (let c = 0; c < 40; c++) {
      expect(grid[39][c]).toBe('main_wall');
    }
  });
});
