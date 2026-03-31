import { writeFileSync } from 'fs';
import { buildFloorGrid, GRID_COLS, GRID_ROWS, TILE_MAP } from './campus-layout';
import { ALL_PROPS } from './campus-props';
import { WANDER_POINTS } from './campus-wander';

const floor = buildFloorGrid();

// Build propImages map (unique prop IDs → sprite paths)
const propImages: Record<string, string> = {};
for (const p of ALL_PROPS) {
  if (!propImages[p.id]) {
    propImages[p.id] = `world_assets/props/${p.id}.png`;
  }
}

const world = {
  gridCols: GRID_COLS,
  gridRows: GRID_ROWS,
  floor,
  tiles: TILE_MAP,
  props: ALL_PROPS,
  propImages,
  wanderPoints: WANDER_POINTS,
};

const outPath = 'public/worlds/easy-company/world.json';
writeFileSync(outPath, JSON.stringify(world, null, 2));
console.log(`Written ${outPath} — ${GRID_COLS}×${GRID_ROWS}, ${ALL_PROPS.length} props, ${WANDER_POINTS.length} wander points`);
