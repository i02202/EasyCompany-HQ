# Easy Company HQ — Campus Expansion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-scale 40×40 tile tech campus with 13 zones, zoom controls, context-aware avatar behavior, and a hidden "Architect's Office" — all on the MiniVRS platform.

**Architecture:** Hand-craft a large `world.json` (40×40) since MiniVRS generator caps at 16×16. Generate ~25 new props via fal.ai CLI. Monkey-patch zoom onto `@miniverse/core`'s Camera via canvas wheel events in `main.ts`. The Architect's Office sits in a deadspace-surrounded island — its occupant is placed via direct API heartbeat, bypassing pathfinding.

**Tech Stack:** MiniVRS (core@0.2.6 + server@0.2.8), Vite 5, TypeScript 5, fal.ai for asset generation

---

## File Structure

### Files to Create
| File | Responsibility |
|------|---------------|
| `src/campus-layout.ts` | 40×40 floor grid definition, zone boundaries, tile assignments |
| `src/campus-props.ts` | All prop placements with anchors, organized by zone |
| `src/campus-wander.ts` | Wander points per zone for idle behavior |
| `src/zoom.ts` | Mouse wheel zoom + keyboard zoom + smooth transitions |
| `src/architect.ts` | Architect's Office logic — heartbeat injection, camera snap |
| `src/branding.ts` | Status bar rendering, zone labels |
| `src/build-world.ts` | Node script to assemble campus-layout + campus-props + campus-wander into world.json |

### Files to Modify
| File | Changes |
|------|---------|
| `src/main.ts` | Import zoom, architect, branding modules; update canvas size to 40×40; map custom sprites to agent IDs |
| `index.html` | Rebrand to "Easy Company HQ"; update styles for larger viewport; add minimap container |
| `public/worlds/easy-company/world.json` | Replace with 40×40 generated output |
| `public/worlds/easy-company/plan.json` | Update with new zone metadata |

### Assets to Generate (fal.ai)
| Category | Files | Output Directory |
|----------|-------|-----------------|
| 8 new textures | `concrete_dark.png`, `epoxy_gray.png`, `wood_warm.png`, `grass_green.png`, `noc_dark.png`, `pool_water.png`, `rooftop_tile.png`, `architect_floor.png` | `public/worlds/easy-company/world_assets/tiles/` |
| ~25 new props | See Task 3 for full list | `public/worlds/easy-company/world_assets/props/` |

---

## Campus Zone Map (40×40 Grid)

```
      0         10        20        30        39
   0  ┌─────────┬─────────┬─────────┬─────────┐
      │  DATA   │ AUDITOR │  NOC /  │ SCRUM   │
      │ CENTER  │   IUM   │WAR ROOM │  ROOM   │
   8  │(basement│(basement│         │         │
      │ sim)    │ sim)    │         │         │
  10  ├─────────┴────┬────┴─────────┴─────────┤
      │   OPEN       │  CEO    │  HUDDLE     │
      │  COWORK      │ OFFICE  │   PODS      │
      │  (desks)     │(private)│ (glass)     │
  18  │              │         │             │
      ├──────┬───────┼─────────┼─────────────┤
  20  │SNACK │ CAFÉ  │  GAMING LOUNGE        │
      │ BAR  │       │ (ping-pong, arcade)   │
      │      │       │                       │
  25  ├──────┴───────┼───────────────────────┤
      │  COCKTAIL    │    GREEN AREA         │
      │  TERRACE     │  (pool, lounge,       │
      │  (rooftop    │   vestidores)         │
  32  │   sim)       │                       │
      ├──────────────┴───────────────────────┤
  34  │                                       │
      │           ~ deadspace ~               │
  37  │    ┌───────────┐                      │
      │    │ ARCHITECT │                      │
      │    │  OFFICE   │                      │
  39  └────┴───────────┴──────────────────────┘
```

**Zone Coordinates (row, col ranges):**

**Note:** Row 0, row 39, col 0, col 39 are wall tiles. Zone coordinates below are walkable interiors.

| Zone | Rows | Cols | Floor Texture | Anchor Types |
|------|------|------|---------------|-------------|
| Data Center | 1–8 | 1–9 | `epoxy_gray` | utility |
| Auditorium | 1–8 | 11–19 | `noc_dark` | social |
| NOC / War Room | 1–8 | 21–29 | `noc_dark` | work |
| Scrum Room | 1–8 | 31–38 | `main_floor` | work, social |
| Open Cowork | 11–18 | 1–14 | `concrete_dark` | work |
| CEO Office | 11–18 | 16–22 | `wood_warm` | work |
| Huddle Pods | 11–18 | 24–38 | `main_floor` | social |
| Snack Bar | 20–24 | 1–5 | `wood_warm` | utility |
| Café | 20–24 | 7–13 | `wood_warm` | social, rest |
| Gaming Lounge | 20–24 | 15–38 | `concrete_dark` | social |
| Cocktail Terrace | 26–32 | 1–14 | `rooftop_tile` | social, rest |
| Green Area | 26–32 | 16–38 | `grass_green` | rest |
| Architect's Office | 37–38 | 5–13 | `architect_floor` | work (special) |
| Deadspace/Corridors | various | various | `""` or `main_wall` | — |

---

## Task Breakdown

### Task 1: Generate New Textures (8 tiles)

**Files:**
- Create: `public/worlds/easy-company/world_assets/tiles/concrete_dark.png`
- Create: `public/worlds/easy-company/world_assets/tiles/epoxy_gray.png`
- Create: `public/worlds/easy-company/world_assets/tiles/wood_warm.png`
- Create: `public/worlds/easy-company/world_assets/tiles/grass_green.png`
- Create: `public/worlds/easy-company/world_assets/tiles/noc_dark.png`
- Create: `public/worlds/easy-company/world_assets/tiles/pool_water.png`
- Create: `public/worlds/easy-company/world_assets/tiles/rooftop_tile.png`
- Create: `public/worlds/easy-company/world_assets/tiles/architect_floor.png`

- [ ] **Step 1: Generate all 8 textures via fal.ai CLI**

Run each in parallel (4 at a time to avoid rate limits):

```bash
FAL_KEY="..." npx miniverse-generate texture \
  --prompt "dark polished industrial concrete floor, very dark gray, subtle texture, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/concrete_dark.png

FAL_KEY="..." npx miniverse-generate texture \
  --prompt "light gray epoxy resin floor, slight metallic sheen, clean data center floor, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/epoxy_gray.png

FAL_KEY="..." npx miniverse-generate texture \
  --prompt "warm dark walnut wood floor planks, horizontal grain, cozy premium feel, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/wood_warm.png

FAL_KEY="..." npx miniverse-generate texture \
  --prompt "lush green grass lawn, natural texture, outdoor garden, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/grass_green.png
```

Then:

```bash
FAL_KEY="..." npx miniverse-generate texture \
  --prompt "very dark navy blue floor tile, barely visible grid lines, NOC war room floor, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/noc_dark.png

FAL_KEY="..." npx miniverse-generate texture \
  --prompt "clear turquoise swimming pool water surface, subtle ripples, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/pool_water.png

FAL_KEY="..." npx miniverse-generate texture \
  --prompt "modern rooftop terrace floor, dark slate paver tiles, geometric pattern, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/rooftop_tile.png

FAL_KEY="..." npx miniverse-generate texture \
  --prompt "mysterious dark floor with faint glowing circuit board traces, matrix style, green glow on black, top-down view" \
  --output public/worlds/easy-company/world_assets/tiles/architect_floor.png
```

- [ ] **Step 2: Verify all 8 textures exist**

```bash
ls -la public/worlds/easy-company/world_assets/tiles/
```

Expected: 14 total PNG files (6 existing + 8 new)

- [ ] **Step 3: Commit**

```bash
git add public/worlds/easy-company/world_assets/tiles/
git commit -m "feat(assets): generate 8 zone-specific floor textures"
```

---

### Task 2: Generate New Props — Batch 1: Entertainment & Social (8 props)

**Files:**
- Create: `public/worlds/easy-company/world_assets/props/ping_pong_table.png`
- Create: `public/worlds/easy-company/world_assets/props/arcade_cabinet.png`
- Create: `public/worlds/easy-company/world_assets/props/bean_bag.png`
- Create: `public/worlds/easy-company/world_assets/props/karaoke_machine.png`
- Create: `public/worlds/easy-company/world_assets/props/cocktail_bar.png`
- Create: `public/worlds/easy-company/world_assets/props/string_lights.png`
- Create: `public/worlds/easy-company/world_assets/props/neon_sign_play.png`
- Create: `public/worlds/easy-company/world_assets/props/neon_sign_hack.png`

- [ ] **Step 1: Generate entertainment props (4 parallel)**

```bash
FAL_KEY="..." npx miniverse-generate object \
  --prompt "sleek black ping pong table, neon green edge lines, no net visible, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/ping_pong_table.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "retro arcade cabinet, glowing purple and blue neon trim, dark screen, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/arcade_cabinet.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "large bean bag chair, dark gray fabric, relaxed shape, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/bean_bag.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "karaoke machine with microphone stand, LED display showing lyrics, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/karaoke_machine.png
```

- [ ] **Step 2: Generate social/terrace props (4 parallel)**

```bash
FAL_KEY="..." npx miniverse-generate object \
  --prompt "modern cocktail bar counter, dark wood top, brass rail, bottles on shelves behind, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/cocktail_bar.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "string of warm white fairy lights, draped horizontally, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/string_lights.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "wall-mounted neon sign glowing pink text PLAY, industrial font, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/neon_sign_play.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "wall-mounted neon sign glowing cyan text HACK, industrial font, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/neon_sign_hack.png
```

- [ ] **Step 3: Verify and commit**

```bash
ls public/worlds/easy-company/world_assets/props/ | wc -l
git add public/worlds/easy-company/world_assets/props/
git commit -m "feat(assets): generate entertainment & social props"
```

---

### Task 3: Generate New Props — Batch 2: Office & Infrastructure (9 props)

**Files:**
- Create: `public/worlds/easy-company/world_assets/props/espresso_machine.png`
- Create: `public/worlds/easy-company/world_assets/props/bar_counter.png`
- Create: `public/worlds/easy-company/world_assets/props/bar_stool.png`
- Create: `public/worlds/easy-company/world_assets/props/fridge.png`
- Create: `public/worlds/easy-company/world_assets/props/scrum_table.png`
- Create: `public/worlds/easy-company/world_assets/props/video_camera.png`
- Create: `public/worlds/easy-company/world_assets/props/huddle_glass_wall.png`
- Create: `public/worlds/easy-company/world_assets/props/biometric_panel.png`
- Create: `public/worlds/easy-company/world_assets/props/noc_screen_wall.png`

- [ ] **Step 1: Generate office infrastructure props (5 parallel)**

```bash
FAL_KEY="..." npx miniverse-generate object \
  --prompt "modern espresso coffee machine, stainless steel and black, drip tray, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/espresso_machine.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "long breakfast bar counter, light wood top, dark base, minimalist, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/bar_counter.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "modern tall bar stool, matte black metal frame, dark gray cushion, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/bar_stool.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "large industrial refrigerator, stainless steel door, dark handle, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/fridge.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "large oval conference table, dark brushed metal, seats 8-10 people, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/scrum_table.png
```

- [ ] **Step 2: Generate tech/security props (4 parallel)**

```bash
FAL_KEY="..." npx miniverse-generate object \
  --prompt "video conference camera on tripod, professional black, small LED light, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/video_camera.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "frosted glass office partition wall, frameless, subtle blue tint, tall, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/huddle_glass_wall.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "biometric access control panel on wall, fingerprint scanner, LED indicator, dark metal, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/biometric_panel.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "massive wall of monitors showing data dashboards, 4x3 grid of screens, blue/green data visualizations, dark frame, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/noc_screen_wall.png
```

- [ ] **Step 3: Commit**

```bash
git add public/worlds/easy-company/world_assets/props/
git commit -m "feat(assets): generate office & infrastructure props"
```

---

### Task 4: Generate New Props — Batch 3: Outdoor & Architect (8 props)

**Files:**
- Create: `public/worlds/easy-company/world_assets/props/pool_edge.png`
- Create: `public/worlds/easy-company/world_assets/props/lounge_chair.png`
- Create: `public/worlds/easy-company/world_assets/props/changing_room_door.png`
- Create: `public/worlds/easy-company/world_assets/props/podium.png`
- Create: `public/worlds/easy-company/world_assets/props/panoramic_screen.png`
- Create: `public/worlds/easy-company/world_assets/props/auditorium_seats.png`
- Create: `public/worlds/easy-company/world_assets/props/architect_monitors.png`
- Create: `public/worlds/easy-company/world_assets/props/data_cables.png`

- [ ] **Step 1: Generate outdoor props (3 parallel)**

```bash
FAL_KEY="..." npx miniverse-generate object \
  --prompt "small rectangular pool edge with turquoise water visible, stone border, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/pool_edge.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "outdoor lounge chair, white frame, gray cushion, relaxed recline position, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/lounge_chair.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "changing room door, dark wood with occupied/vacant indicator light, minimalist, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/changing_room_door.png
```

- [ ] **Step 2: Generate auditorium props (3 parallel)**

```bash
FAL_KEY="..." npx miniverse-generate object \
  --prompt "presentation podium, modern dark acrylic with subtle LED edge lighting, microphone, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/podium.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "wide curved panoramic projection screen, dark frame, showing abstract data visualization, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/panoramic_screen.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "row of tiered auditorium seats, dark upholstery, modern design, 4 seats in a row, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/auditorium_seats.png
```

- [ ] **Step 3: Generate Architect's Office props (2 parallel)**

```bash
FAL_KEY="..." npx miniverse-generate object \
  --prompt "wall of surveillance monitors showing multiple video feeds, 6 screens in 2x3 grid, green and blue glowing data, dark mysterious room, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/architect_monitors.png

FAL_KEY="..." npx miniverse-generate object \
  --prompt "bundle of glowing fiber optic data cables, green luminous strands running along floor, matrix style, pixel art, top-down view" \
  --output public/worlds/easy-company/world_assets/props/data_cables.png
```

- [ ] **Step 4: Commit**

```bash
git add public/worlds/easy-company/world_assets/props/
git commit -m "feat(assets): generate outdoor, auditorium & architect props"
```

---

### Task 5: Build Campus Layout Generator Script

**Files:**
- Create: `src/build-world.ts`
- Create: `src/campus-layout.ts`

This script generates the 40×40 `world.json` programmatically so we can iterate on the layout without hand-editing a 1600-cell grid.

- [ ] **Step 1: Create `src/campus-layout.ts` — the 40×40 floor grid**

```typescript
/**
 * 40×40 campus floor grid.
 * Each cell is a tile key string. Empty string = deadspace (non-walkable dark area).
 *
 * Zone boundaries follow the map in the plan:
 *   Rows  0–9:  Data Center (0-9) | Auditorium (10-19) | NOC (20-29) | Scrum (30-39)
 *   Rows 10–19: Open Cowork (0-14) | CEO (15-22) | Huddle Pods (23-39)
 *   Rows 20–24: Snack (0-5) | Café (6-13) | Gaming (14-39)
 *   Rows 25–32: Terrace (0-14) | Green Area (15-39)
 *   Rows 33–36: Deadspace corridor
 *   Rows 37–39, Cols 4–14: Architect's Office (island)
 */

export const GRID_COLS = 40;
export const GRID_ROWS = 40;

interface ZoneDef {
  name: string;
  rowStart: number; rowEnd: number;
  colStart: number; colEnd: number;
  tile: string;
}

export const ZONES: ZoneDef[] = [
  // Underground simulation (rows 0-9)
  { name: 'data_center',  rowStart: 1, rowEnd: 8,  colStart: 1,  colEnd: 9,  tile: 'epoxy_gray' },
  { name: 'auditorium',   rowStart: 1, rowEnd: 8,  colStart: 11, colEnd: 19, tile: 'noc_dark' },
  { name: 'noc_war_room', rowStart: 1, rowEnd: 8,  colStart: 21, colEnd: 29, tile: 'noc_dark' },
  { name: 'scrum_room',   rowStart: 1, rowEnd: 8,  colStart: 31, colEnd: 38, tile: 'main_floor' },

  // Main floor (rows 10-19)
  { name: 'open_cowork',  rowStart: 11, rowEnd: 18, colStart: 1,  colEnd: 14, tile: 'concrete_dark' },
  { name: 'ceo_office',   rowStart: 11, rowEnd: 18, colStart: 16, colEnd: 22, tile: 'wood_warm' },
  { name: 'huddle_pods',  rowStart: 11, rowEnd: 18, colStart: 24, colEnd: 38, tile: 'main_floor' },

  // Social floor (rows 20-24)
  { name: 'snack_bar',    rowStart: 20, rowEnd: 24, colStart: 1,  colEnd: 5,  tile: 'wood_warm' },
  { name: 'cafe',         rowStart: 20, rowEnd: 24, colStart: 7,  colEnd: 13, tile: 'wood_warm' },
  { name: 'gaming_lounge',rowStart: 20, rowEnd: 24, colStart: 15, colEnd: 38, tile: 'concrete_dark' },

  // Outdoor simulation (rows 26-32)
  { name: 'terrace',      rowStart: 26, rowEnd: 32, colStart: 1,  colEnd: 14, tile: 'rooftop_tile' },
  { name: 'green_area',   rowStart: 26, rowEnd: 32, colStart: 16, colEnd: 38, tile: 'grass_green' },

  // Architect's Office — isolated island (rows 37-39)
  { name: 'architect',    rowStart: 37, rowEnd: 38, colStart: 5,  colEnd: 13, tile: 'architect_floor' },
];

/** Corridors connecting zones — 2-tile wide paths */
export const CORRIDORS: { row: number; colStart: number; colEnd: number; tile: string }[] = [
  // Horizontal corridor between underground and main floor (row 9-10)
  ...Array.from({ length: 2 }, (_, i) => ({ row: 9 + i, colStart: 1, colEnd: 38, tile: 'main_floor' })),
  // Horizontal corridor between main and social (row 19)
  { row: 19, colStart: 1, colEnd: 38, tile: 'main_floor' },
  // Horizontal corridor between social and outdoor (row 25)
  { row: 25, colStart: 1, colEnd: 38, tile: 'main_floor' },
  // Vertical corridor between data center and auditorium (col 10)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 1 + i, colStart: 10, colEnd: 10, tile: 'main_floor' })),
  // Vertical corridor between auditorium and NOC (col 20)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 1 + i, colStart: 20, colEnd: 20, tile: 'main_floor' })),
  // Vertical corridor between NOC and Scrum (col 30)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 1 + i, colStart: 30, colEnd: 30, tile: 'main_floor' })),
  // Vertical corridor cowork to CEO (col 15)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 11 + i, colStart: 15, colEnd: 15, tile: 'main_floor' })),
  // Vertical corridor CEO to huddle (col 23)
  ...Array.from({ length: 8 }, (_, i) => ({ row: 11 + i, colStart: 23, colEnd: 23, tile: 'main_floor' })),
  // Vertical corridor snack to café (col 6)
  ...Array.from({ length: 5 }, (_, i) => ({ row: 20 + i, colStart: 6, colEnd: 6, tile: 'main_floor' })),
  // Vertical corridor café to gaming (col 14)
  ...Array.from({ length: 5 }, (_, i) => ({ row: 20 + i, colStart: 14, colEnd: 14, tile: 'main_floor' })),
  // Vertical terrace to green (col 15)
  ...Array.from({ length: 7 }, (_, i) => ({ row: 26 + i, colStart: 15, colEnd: 15, tile: 'main_floor' })),
];

export function buildFloorGrid(): string[][] {
  // Start with all deadspace
  const grid: string[][] = Array.from({ length: GRID_ROWS }, () =>
    Array(GRID_COLS).fill('')
  );

  // Outer wall border (row 0, row 39, col 0, col 39)
  for (let c = 0; c < GRID_COLS; c++) {
    grid[0][c] = 'main_wall';
    grid[GRID_ROWS - 1][c] = 'main_wall';
  }
  for (let r = 0; r < GRID_ROWS; r++) {
    grid[r][0] = 'main_wall';
    grid[r][GRID_COLS - 1] = 'main_wall';
  }

  // Fill zones
  for (const z of ZONES) {
    for (let r = z.rowStart; r <= z.rowEnd; r++) {
      for (let c = z.colStart; c <= z.colEnd; c++) {
        grid[r][c] = z.tile;
      }
    }
  }

  // Fill corridors
  for (const cor of CORRIDORS) {
    for (let c = cor.colStart; c <= cor.colEnd; c++) {
      grid[cor.row][c] = cor.tile;
    }
  }

  return grid;
}

/** Tile key → relative path in world_assets/tiles/ */
export const TILE_MAP: Record<string, string> = {
  main_floor: 'world_assets/tiles/main_floor.png',
  main_wall: 'world_assets/tiles/main_wall.png',
  accent_floor_tile: 'world_assets/tiles/accent_floor_tile.png',
  accent_wall_panel: 'world_assets/tiles/accent_wall_panel.png',
  concrete_dark: 'world_assets/tiles/concrete_dark.png',
  epoxy_gray: 'world_assets/tiles/epoxy_gray.png',
  wood_warm: 'world_assets/tiles/wood_warm.png',
  grass_green: 'world_assets/tiles/grass_green.png',
  noc_dark: 'world_assets/tiles/noc_dark.png',
  pool_water: 'world_assets/tiles/pool_water.png',
  rooftop_tile: 'world_assets/tiles/rooftop_tile.png',
  architect_floor: 'world_assets/tiles/architect_floor.png',
};
```

- [ ] **Step 2: Verify grid builds correctly**

```bash
npx tsx -e "import { buildFloorGrid, GRID_COLS, GRID_ROWS } from './src/campus-layout'; const g = buildFloorGrid(); console.log('Grid:', GRID_ROWS, 'x', GRID_COLS); console.log('Non-empty:', g.flat().filter(t => t !== '').length); console.log('Architect zone:', g[38][9]);"
```

Expected: Grid 40×40, ~900+ non-empty tiles, Architect zone = `architect_floor`

- [ ] **Step 3: Commit**

```bash
git add src/campus-layout.ts
git commit -m "feat(campus): define 40x40 floor grid with 13 zones"
```

---

### Task 6: Define All Prop Placements by Zone

**Files:**
- Create: `src/campus-props.ts`

- [ ] **Step 1: Create prop placement definitions**

This file defines every prop placement with explicit anchors. Each zone gets its own section. The format matches MiniVRS `world.json` props array.

```typescript
interface PropPlacement {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  layer: 'below' | 'above';
  anchors: { name: string; ox: number; oy: number; type: 'work' | 'rest' | 'social' | 'utility' | 'wander' }[];
}

// ─── Data Center (rows 1-8, cols 1-9) ───
const dataCenterProps: PropPlacement[] = [
  { id: 'server_rack', x: 2, y: 2, w: 1, h: 2, layer: 'below', anchors: [{ name: 'dc_rack_0', ox: 0.5, oy: 2.5, type: 'utility' }] },
  { id: 'server_rack', x: 4, y: 2, w: 1, h: 2, layer: 'below', anchors: [{ name: 'dc_rack_1', ox: 0.5, oy: 2.5, type: 'utility' }] },
  { id: 'server_rack', x: 6, y: 2, w: 1, h: 2, layer: 'below', anchors: [{ name: 'dc_rack_2', ox: 0.5, oy: 2.5, type: 'utility' }] },
  { id: 'server_rack', x: 8, y: 2, w: 1, h: 2, layer: 'below', anchors: [{ name: 'dc_rack_3', ox: 0.5, oy: 2.5, type: 'utility' }] },
  { id: 'server_rack', x: 2, y: 5, w: 1, h: 2, layer: 'below', anchors: [{ name: 'dc_rack_4', ox: 0.5, oy: 2.5, type: 'utility' }] },
  { id: 'server_rack', x: 4, y: 5, w: 1, h: 2, layer: 'below', anchors: [{ name: 'dc_rack_5', ox: 0.5, oy: 2.5, type: 'utility' }] },
  { id: 'biometric_panel', x: 1, y: 1, w: 0.5, h: 1, layer: 'below', anchors: [] },
  { id: 'data_display_wall', x: 6, y: 5, w: 3, h: 1.5, layer: 'below', anchors: [{ name: 'dc_display', ox: 1.5, oy: 2, type: 'work' }] },
];

// ─── NOC / War Room (rows 1-8, cols 21-29) ───
const nocProps: PropPlacement[] = [
  { id: 'noc_screen_wall', x: 22, y: 1, w: 6, h: 2, layer: 'below', anchors: [] },
  { id: 'desk_monitor', x: 22, y: 4, w: 2.5, h: 1.5, layer: 'below', anchors: [{ name: 'noc_desk_0', ox: 1.25, oy: 2, type: 'work' }] },
  { id: 'desk_monitor', x: 25, y: 4, w: 2.5, h: 1.5, layer: 'below', anchors: [{ name: 'noc_desk_1', ox: 1.25, oy: 2, type: 'work' }] },
  { id: 'ergonomic_chair', x: 23, y: 6.5, w: 1, h: 1, layer: 'above', anchors: [] },
  { id: 'ergonomic_chair', x: 26, y: 6.5, w: 1, h: 1, layer: 'above', anchors: [] },
  { id: 'desk_monitor', x: 22, y: 7, w: 2.5, h: 1.5, layer: 'below', anchors: [{ name: 'noc_desk_2', ox: 1.25, oy: -0.5, type: 'work' }] },
  { id: 'desk_monitor', x: 25, y: 7, w: 2.5, h: 1.5, layer: 'below', anchors: [{ name: 'noc_desk_3', ox: 1.25, oy: -0.5, type: 'work' }] },
];

// ─── Open Cowork (rows 11-18, cols 1-14) ───
const coworkProps: PropPlacement[] = Array.from({ length: 6 }, (_, i) => {
  const col = 2 + (i % 3) * 4;
  const row = 12 + Math.floor(i / 3) * 4;
  return [
    { id: 'desk_monitor', x: col, y: row, w: 2.5, h: 1.5, layer: 'below' as const,
      anchors: [{ name: `cowork_desk_${i}`, ox: 1.25, oy: 2, type: 'work' as const }] },
    { id: 'ergonomic_chair', x: col + 0.75, y: row + 2, w: 1, h: 1, layer: 'above' as const, anchors: [] },
  ];
}).flat();

// ─── CEO Office (rows 11-18, cols 16-22) ───
const ceoProps: PropPlacement[] = [
  { id: 'desk_monitor', x: 17, y: 12, w: 3, h: 2, layer: 'below', anchors: [{ name: 'ceo_desk', ox: 1.5, oy: 2.5, type: 'work' }] },
  { id: 'ergonomic_chair', x: 18, y: 14.5, w: 1, h: 1, layer: 'above', anchors: [] },
  { id: 'lounge_sofa', x: 17, y: 17, w: 3, h: 1.5, layer: 'below', anchors: [{ name: 'ceo_sofa', ox: 1.5, oy: 0, type: 'rest' }] },
  { id: 'coffee_table', x: 19, y: 15.5, w: 1.5, h: 1.5, layer: 'below', anchors: [] },
  { id: 'tall_plant', x: 16, y: 11, w: 1, h: 1, layer: 'below', anchors: [] },
  { id: 'tall_plant', x: 22, y: 11, w: 1, h: 1, layer: 'below', anchors: [] },
];

// ─── Huddle Pods (rows 11-18, cols 24-38) ───
const huddleProps: PropPlacement[] = [
  // Pod 1
  { id: 'huddle_glass_wall', x: 24, y: 11, w: 0.5, h: 4, layer: 'below', anchors: [] },
  { id: 'huddle_glass_wall', x: 29, y: 11, w: 0.5, h: 4, layer: 'below', anchors: [] },
  { id: 'scrum_table', x: 25, y: 12, w: 3, h: 2, layer: 'below', anchors: [
    { name: 'huddle_0_a', ox: 0, oy: 2.5, type: 'social' },
    { name: 'huddle_0_b', ox: 3, oy: 2.5, type: 'social' },
  ]},
  // Pod 2
  { id: 'huddle_glass_wall', x: 31, y: 11, w: 0.5, h: 4, layer: 'below', anchors: [] },
  { id: 'huddle_glass_wall', x: 36, y: 11, w: 0.5, h: 4, layer: 'below', anchors: [] },
  { id: 'scrum_table', x: 32, y: 12, w: 3, h: 2, layer: 'below', anchors: [
    { name: 'huddle_1_a', ox: 0, oy: 2.5, type: 'social' },
    { name: 'huddle_1_b', ox: 3, oy: 2.5, type: 'social' },
  ]},
  // Pod 3 (lower row)
  { id: 'huddle_glass_wall', x: 24, y: 16, w: 0.5, h: 3, layer: 'below', anchors: [] },
  { id: 'huddle_glass_wall', x: 29, y: 16, w: 0.5, h: 3, layer: 'below', anchors: [] },
  { id: 'whiteboard_glass', x: 25, y: 16.5, w: 3, h: 1, layer: 'below', anchors: [{ name: 'huddle_wb', ox: 1.5, oy: 1.5, type: 'social' }] },
];

// ─── Scrum Room (rows 1-8, cols 31-38) ───
const scrumProps: PropPlacement[] = [
  { id: 'scrum_table', x: 32, y: 3, w: 5, h: 3, layer: 'below', anchors: [
    { name: 'scrum_seat_0', ox: 0, oy: 3.5, type: 'work' },
    { name: 'scrum_seat_1', ox: 2.5, oy: 3.5, type: 'work' },
    { name: 'scrum_seat_2', ox: 5, oy: 3.5, type: 'work' },
    { name: 'scrum_seat_3', ox: 0, oy: -0.5, type: 'work' },
    { name: 'scrum_seat_4', ox: 2.5, oy: -0.5, type: 'work' },
    { name: 'scrum_seat_5', ox: 5, oy: -0.5, type: 'work' },
  ]},
  { id: 'whiteboard_glass', x: 31, y: 1, w: 3, h: 1, layer: 'below', anchors: [] },
  { id: 'data_display_wall', x: 35, y: 1, w: 3, h: 1.5, layer: 'below', anchors: [] },
  { id: 'video_camera', x: 37, y: 7, w: 0.5, h: 0.5, layer: 'above', anchors: [] },
  { id: 'video_camera', x: 31, y: 7, w: 0.5, h: 0.5, layer: 'above', anchors: [] },
];

// ─── Snack Bar (rows 20-24, cols 1-5) ───
const snackProps: PropPlacement[] = [
  { id: 'bar_counter', x: 1.5, y: 21, w: 3.5, h: 1, layer: 'below', anchors: [
    { name: 'snack_seat_0', ox: 1, oy: 1.5, type: 'utility' },
    { name: 'snack_seat_1', ox: 2.5, oy: 1.5, type: 'utility' },
  ]},
  { id: 'bar_stool', x: 2, y: 22.5, w: 0.8, h: 0.8, layer: 'above', anchors: [] },
  { id: 'bar_stool', x: 3.5, y: 22.5, w: 0.8, h: 0.8, layer: 'above', anchors: [] },
  { id: 'espresso_machine', x: 1.5, y: 20, w: 1.5, h: 1, layer: 'below', anchors: [] },
  { id: 'fridge', x: 4, y: 20, w: 1, h: 1.5, layer: 'below', anchors: [] },
];

// ─── Café (rows 20-24, cols 7-13) ───
const cafeProps: PropPlacement[] = [
  { id: 'coffee_table', x: 8, y: 21, w: 1.5, h: 1.5, layer: 'below', anchors: [
    { name: 'cafe_seat_0', ox: -0.5, oy: 0.5, type: 'social' },
    { name: 'cafe_seat_1', ox: 2, oy: 0.5, type: 'social' },
  ]},
  { id: 'coffee_table', x: 11, y: 21, w: 1.5, h: 1.5, layer: 'below', anchors: [
    { name: 'cafe_seat_2', ox: -0.5, oy: 0.5, type: 'social' },
    { name: 'cafe_seat_3', ox: 2, oy: 0.5, type: 'social' },
  ]},
  { id: 'lounge_sofa', x: 8, y: 23, w: 2, h: 1.5, layer: 'below', anchors: [{ name: 'cafe_rest_0', ox: 1, oy: 0, type: 'rest' }] },
  { id: 'tall_plant', x: 7, y: 20, w: 1, h: 1, layer: 'below', anchors: [] },
];

// ─── Gaming Lounge (rows 20-24, cols 15-38) ───
const gamingProps: PropPlacement[] = [
  { id: 'ping_pong_table', x: 17, y: 21, w: 4, h: 2, layer: 'below', anchors: [
    { name: 'pong_player_0', ox: -0.5, oy: 1, type: 'social' },
    { name: 'pong_player_1', ox: 4.5, oy: 1, type: 'social' },
  ]},
  { id: 'arcade_cabinet', x: 23, y: 20.5, w: 1, h: 1.5, layer: 'below', anchors: [{ name: 'arcade_0', ox: 0.5, oy: 2, type: 'social' }] },
  { id: 'arcade_cabinet', x: 25, y: 20.5, w: 1, h: 1.5, layer: 'below', anchors: [{ name: 'arcade_1', ox: 0.5, oy: 2, type: 'social' }] },
  { id: 'arcade_cabinet', x: 27, y: 20.5, w: 1, h: 1.5, layer: 'below', anchors: [{ name: 'arcade_2', ox: 0.5, oy: 2, type: 'social' }] },
  { id: 'bean_bag', x: 30, y: 21, w: 1.5, h: 1.5, layer: 'below', anchors: [{ name: 'bean_0', ox: 0.75, oy: 0, type: 'rest' }] },
  { id: 'bean_bag', x: 32, y: 21, w: 1.5, h: 1.5, layer: 'below', anchors: [{ name: 'bean_1', ox: 0.75, oy: 0, type: 'rest' }] },
  { id: 'bean_bag', x: 34, y: 22, w: 1.5, h: 1.5, layer: 'below', anchors: [{ name: 'bean_2', ox: 0.75, oy: 0, type: 'rest' }] },
  { id: 'neon_sign_play', x: 16, y: 20, w: 2, h: 1, layer: 'below', anchors: [] },
  { id: 'neon_sign_hack', x: 36, y: 20, w: 2, h: 1, layer: 'below', anchors: [] },
];

// ─── Auditorium (rows 1-8, cols 11-19) ───
const auditoriumProps: PropPlacement[] = [
  { id: 'panoramic_screen', x: 12, y: 1, w: 6, h: 1.5, layer: 'below', anchors: [] },
  { id: 'podium', x: 14.5, y: 3, w: 1, h: 1, layer: 'below', anchors: [{ name: 'podium_speaker', ox: 0.5, oy: 1.5, type: 'social' }] },
  { id: 'auditorium_seats', x: 12, y: 5, w: 6, h: 1, layer: 'below', anchors: [
    { name: 'aud_seat_0', ox: 1, oy: 0, type: 'social' },
    { name: 'aud_seat_1', ox: 3, oy: 0, type: 'social' },
    { name: 'aud_seat_2', ox: 5, oy: 0, type: 'social' },
  ]},
  { id: 'auditorium_seats', x: 12, y: 7, w: 6, h: 1, layer: 'below', anchors: [
    { name: 'aud_seat_3', ox: 1, oy: 0, type: 'social' },
    { name: 'aud_seat_4', ox: 3, oy: 0, type: 'social' },
    { name: 'aud_seat_5', ox: 5, oy: 0, type: 'social' },
  ]},
];

// ─── Cocktail Terrace (rows 26-32, cols 1-14) ───
const terraceProps: PropPlacement[] = [
  { id: 'cocktail_bar', x: 2, y: 27, w: 4, h: 1.5, layer: 'below', anchors: [
    { name: 'bar_seat_0', ox: 1, oy: 2, type: 'social' },
    { name: 'bar_seat_1', ox: 3, oy: 2, type: 'social' },
  ]},
  { id: 'karaoke_machine', x: 8, y: 27, w: 1.5, h: 2, layer: 'below', anchors: [{ name: 'karaoke_0', ox: 0.75, oy: 2.5, type: 'social' }] },
  { id: 'string_lights', x: 1, y: 26, w: 13, h: 0.5, layer: 'above', anchors: [] },
  { id: 'lounge_sofa', x: 2, y: 30, w: 3, h: 1.5, layer: 'below', anchors: [{ name: 'terrace_rest_0', ox: 1.5, oy: 0, type: 'rest' }] },
  { id: 'lounge_sofa', x: 7, y: 30, w: 3, h: 1.5, layer: 'below', anchors: [{ name: 'terrace_rest_1', ox: 1.5, oy: 0, type: 'rest' }] },
  { id: 'coffee_table', x: 11, y: 30, w: 1.5, h: 1.5, layer: 'below', anchors: [] },
];

// ─── Green Area (rows 26-32, cols 16-38) ───
const greenAreaProps: PropPlacement[] = [
  // Pool area (3x5 tiles of pool_water in floor grid, props are edges)
  { id: 'pool_edge', x: 20, y: 28, w: 5, h: 3, layer: 'below', anchors: [
    { name: 'pool_rest_0', ox: -1, oy: 0, type: 'rest' },
    { name: 'pool_rest_1', ox: 5, oy: 0, type: 'rest' },
    { name: 'pool_rest_2', ox: -1, oy: 2, type: 'rest' },
    { name: 'pool_rest_3', ox: 5, oy: 2, type: 'rest' },
  ]},
  { id: 'lounge_chair', x: 26, y: 27, w: 1, h: 2, layer: 'below', anchors: [{ name: 'pool_rest_0', ox: 0.5, oy: 0, type: 'rest' }] },
  { id: 'lounge_chair', x: 28, y: 27, w: 1, h: 2, layer: 'below', anchors: [{ name: 'pool_rest_1', ox: 0.5, oy: 0, type: 'rest' }] },
  { id: 'lounge_chair', x: 30, y: 27, w: 1, h: 2, layer: 'below', anchors: [{ name: 'pool_rest_2', ox: 0.5, oy: 0, type: 'rest' }] },
  { id: 'changing_room_door', x: 33, y: 27, w: 1, h: 2, layer: 'below', anchors: [] },
  { id: 'changing_room_door', x: 35, y: 27, w: 1, h: 2, layer: 'below', anchors: [] },
  { id: 'tall_plant', x: 17, y: 26, w: 1, h: 1, layer: 'below', anchors: [] },
  { id: 'tall_plant', x: 37, y: 26, w: 1, h: 1, layer: 'below', anchors: [] },
  { id: 'tall_plant', x: 17, y: 31, w: 1, h: 1, layer: 'below', anchors: [] },
];

// ─── Architect's Office (rows 37-38, cols 5-13) ───
const architectProps: PropPlacement[] = [
  { id: 'architect_monitors', x: 6, y: 37, w: 6, h: 1, layer: 'below', anchors: [
    { name: 'architect_seat', ox: 3, oy: 1.5, type: 'work' },
  ]},
  { id: 'data_cables', x: 5, y: 37.5, w: 8, h: 0.5, layer: 'below', anchors: [] },
  { id: 'ergonomic_chair', x: 8.5, y: 37.5, w: 1, h: 1, layer: 'above', anchors: [] },
];

export const ALL_PROPS: PropPlacement[] = [
  ...dataCenterProps,
  ...nocProps,
  ...coworkProps,
  ...ceoProps,
  ...huddleProps,
  ...scrumProps,
  ...snackProps,
  ...cafeProps,
  ...gamingProps,
  ...auditoriumProps,
  ...terraceProps,
  ...greenAreaProps,
  ...architectProps,
];
```

- [ ] **Step 2: Commit**

```bash
git add src/campus-props.ts
git commit -m "feat(campus): define all prop placements for 13 zones"
```

---

### Task 7: Define Wander Points

**Files:**
- Create: `src/campus-wander.ts`

- [ ] **Step 1: Create wander point definitions**

```typescript
export interface WanderPoint {
  name: string;
  x: number;
  y: number;
}

export const WANDER_POINTS: WanderPoint[] = [
  // Data Center
  { name: 'wander_dc_aisle', x: 5, y: 4 },
  // Auditorium
  { name: 'wander_aud_entrance', x: 15, y: 8 },
  // NOC
  { name: 'wander_noc_center', x: 25, y: 5 },
  // Scrum
  { name: 'wander_scrum_door', x: 32, y: 8 },
  // Open Cowork
  { name: 'wander_cowork_a', x: 5, y: 14 },
  { name: 'wander_cowork_b', x: 10, y: 17 },
  // CEO Office
  { name: 'wander_ceo_entry', x: 16, y: 15 },
  // Huddle Pods
  { name: 'wander_huddle_hall', x: 30, y: 15 },
  // Snack Bar
  { name: 'wander_snack', x: 3, y: 23 },
  // Café
  { name: 'wander_cafe', x: 10, y: 23 },
  // Gaming Lounge
  { name: 'wander_gaming_a', x: 20, y: 23 },
  { name: 'wander_gaming_b', x: 32, y: 23 },
  // Terrace
  { name: 'wander_terrace_bar', x: 5, y: 29 },
  { name: 'wander_terrace_stage', x: 10, y: 29 },
  // Green Area
  { name: 'wander_pool', x: 23, y: 30 },
  { name: 'wander_garden', x: 32, y: 30 },
  // Corridors (high-traffic intersections)
  { name: 'wander_main_corridor_a', x: 10, y: 9 },
  { name: 'wander_main_corridor_b', x: 25, y: 19 },
  { name: 'wander_main_corridor_c', x: 10, y: 25 },
];
```

- [ ] **Step 2: Commit**

```bash
git add src/campus-wander.ts
git commit -m "feat(campus): define 19 wander points across zones"
```

---

### Task 8: Build World Assembler Script

**Files:**
- Create: `src/build-world.ts`

- [ ] **Step 1: Write the world builder**

```typescript
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
```

- [ ] **Step 2: Run it**

```bash
npx tsx src/build-world.ts
```

Expected: `Written public/worlds/easy-company/world.json — 40×40, ~80 props, 19 wander points`

- [ ] **Step 3: Verify world.json**

```bash
node -e "const w=require('./public/worlds/easy-company/world.json'); console.log(w.gridCols, 'x', w.gridRows, '|', w.props.length, 'props |', Object.keys(w.tiles).length, 'tiles |', w.wanderPoints.length, 'wander');"
```

- [ ] **Step 4: Commit**

```bash
git add src/build-world.ts public/worlds/easy-company/world.json
git commit -m "feat(campus): assemble 40x40 world.json from layout + props + wander"
```

---

### Task 9: Update main.ts for 40×40 Canvas + Custom Sprite Mapping

**Files:**
- Modify: `src/main.ts`

- [ ] **Step 1: Update canvas dimensions and sprite mapping**

The key changes:
1. Canvas size = 40 tiles × 32 px/tile = 1280 pixels wide × 1280 tall (40×40 grid)
2. Map role-specific sprites to agent IDs
3. Use generic `agent_XX` sprites for new/unknown agents

Replace the sprite discovery section in `main.ts`:

```typescript
// ─── Sprite mapping: role → custom sprite, fallback to agent_XX pool ───
const ROLE_SPRITES: Record<string, string> = {
  ceo: 'ceo', cto: 'cto', cfo: 'cfo', trader: 'trader',
  researcher: 'researcher', hr: 'hr', security: 'security', media: 'media',
};
const GENERIC_SPRITES = Array.from({ length: 12 }, (_, i) =>
  `agent_${String(i + 1).padStart(2, '0')}`
);
let nextGenericIdx = 0;

function getSpriteForAgent(agentId: string): string {
  const role = ROLE_SPRITES[agentId];
  if (role) return role;
  const sprite = GENERIC_SPRITES[nextGenericIdx % GENERIC_SPRITES.length];
  nextGenericIdx++;
  return sprite;
}
```

Update the citizen-building loop to use `getSpriteForAgent()` when constructing citizen configs from the server's `/api/agents` response:

```typescript
// Replace the existing citizen-building code with:
const agentsRes = await fetch(`http://localhost:4321/api/agents`);
const agents: { agent: string; name: string; state: string }[] = await agentsRes.json();

const citizens = agents.map((a) => {
  const spriteKey = getSpriteForAgent(a.agent); // ← uses role map or generic pool
  return {
    id: a.agent,
    name: a.name,
    spriteSheet: `${spriteKey}_walk`,
    actionsSpriteSheet: `${spriteKey}_actions`,
    state: a.state ?? 'idle',
  };
});
```

Update `Miniverse` config to use full 40×40 dimensions:

```typescript
const mv = new Miniverse({
  container,
  world: WORLD_ID,
  scene: 'main',
  signal: { type: 'websocket', url: 'ws://localhost:4321/ws' },
  citizens,
  scale: 2,
  width: gridCols * tileSize,   // 40 * 32 = 1280
  height: gridRows * tileSize,  // 40 * 32 = 1280
  sceneConfig,
  spriteSheets,
  objects: [],
});
```

- [ ] **Step 2: Start dev server and verify rendering**

```bash
npm run dev
```

Send test heartbeat:
```bash
curl -X POST http://localhost:4321/api/heartbeat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"ceo","name":"Marcus Chen","state":"working","task":"Q1 review"}'
```

Expected: 40×40 world renders in browser, CEO appears at assigned desk

- [ ] **Step 3: Commit**

```bash
git add src/main.ts
git commit -m "feat: update main.ts for 40x40 campus + role-based sprite mapping"
```

---

### Task 10: Implement Zoom Controls

**Files:**
- Create: `src/zoom.ts`
- Modify: `src/main.ts` (import and init zoom)

- [ ] **Step 1: Create zoom module**

```typescript
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
```

- [ ] **Step 2: Wire zoom into main.ts**

Add after `mv.start()`:

```typescript
import { initZoom } from './zoom';
// ... after await mv.start();
initZoom(mv);
```

- [ ] **Step 3: Test zoom**

Start dev server. Scroll mouse wheel up/down over canvas.

Expected: World smoothly zooms in/out between 0.4x and 3.0x. Press `0` to reset.

- [ ] **Step 4: Commit**

```bash
git add src/zoom.ts src/main.ts
git commit -m "feat: add smooth mouse wheel + keyboard zoom controls"
```

---

### Task 11: Implement Architect's Office Logic

**Files:**
- Create: `src/architect.ts`
- Modify: `src/main.ts` (import and init architect)

The Architect's Office is a deadspace-surrounded island at rows 37-39, cols 5-13. No agent can pathfind there. The user's avatar ("architect") is placed via heartbeat and camera can snap to it with a keyboard shortcut.

- [ ] **Step 1: Create architect module**

```typescript
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
```

- [ ] **Step 2: Wire architect into main.ts**

```typescript
import { initArchitect } from './architect';
// ... after initZoom(mv);
initArchitect(mv, 'http://localhost:4321');
```

- [ ] **Step 3: Test**

Start dev server. Press 'A'. Camera should snap to the bottom-center of the map showing the hidden office with "The Architect" avatar.

- [ ] **Step 4: Commit**

```bash
git add src/architect.ts src/main.ts
git commit -m "feat: add Architect's hidden office with camera snap (A key)"
```

---

### Task 12: Rebrand UI — "Easy Company HQ"

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Update branding and styles**

Changes to `index.html`:
1. Title: "Easy Company HQ"
2. Header: "EASY COMPANY HQ" (styled with neon accent)
3. Subtitle: "real-time agent visualization"
4. Larger viewport for 40×40 world (scrollable)
5. Add keyboard hints for zoom and architect

```html
<title>Easy Company HQ</title>
```

```html
<h1>easy company hq</h1>
<p class="subtitle">real-time agent visualization</p>
```

Update `#miniverse-container` style for larger canvas:
```css
#miniverse-container {
  border: 2px solid #333;
  border-radius: 4px;
  overflow: hidden;
  background: #0f0f23;
  display: inline-block;
  line-height: 0;
  max-width: 90vw;
  max-height: 80vh;
}
```

Add hints:
```html
<p class="hint">
  <b>Scroll</b> zoom · <b>+/-</b> zoom · <b>0</b> reset · <b>A</b> architect · <b>E</b> editor
</p>
```

- [ ] **Step 2: Verify in browser**

Expected: Header shows "EASY COMPANY HQ", hints updated, canvas fits viewport

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: rebrand to Easy Company HQ with updated controls hint"
```

---

### Task 13: Add Camera Pan (Click-Drag)

**Files:**
- Modify: `src/zoom.ts` (add pan alongside zoom)

- [ ] **Step 1: Add pan controls**

Extend `initZoom()` to include click-drag panning:

```typescript
// Middle-click or right-click drag to pan
let isPanning = false;
let panStartX = 0, panStartY = 0;
let camStartX = 0, camStartY = 0;

canvas.addEventListener('mousedown', (e: MouseEvent) => {
  if (e.button === 1 || e.button === 2) { // middle or right click
    isPanning = true;
    panStartX = e.clientX;
    panStartY = e.clientY;
    camStartX = camera.x;
    camStartY = camera.y;
    e.preventDefault();
  }
});

canvas.addEventListener('mousemove', (e: MouseEvent) => {
  if (!isPanning) return;
  const scale = parseFloat(canvas.style.width) / canvas.width;
  const dx = (panStartX - e.clientX) / scale / currentZoom;
  const dy = (panStartY - e.clientY) / scale / currentZoom;
  camera.snapTo(camStartX + dx, camStartY + dy);
});

canvas.addEventListener('mouseup', () => { isPanning = false; });
canvas.addEventListener('mouseleave', () => { isPanning = false; });
canvas.addEventListener('contextmenu', (e) => { e.preventDefault(); }); // disable right-click menu
```

- [ ] **Step 2: Test pan**

Hold middle-click or right-click and drag. Camera should follow mouse movement.

- [ ] **Step 3: Commit**

```bash
git add src/zoom.ts
git commit -m "feat: add right-click/middle-click camera pan"
```

---

### Task 14: Pool Water Tiles in Green Area

**Files:**
- Modify: `src/campus-layout.ts`

- [ ] **Step 1: Add pool water tiles in the green area zone**

In `buildFloorGrid()`, after filling zones, overlay pool_water tiles:

```typescript
// Pool water (3×5 block inside green area)
for (let r = 28; r <= 30; r++) {
  for (let c = 20; c <= 24; c++) {
    grid[r][c] = 'pool_water';
  }
}
```

These tiles are non-walkable water. The `pool_edge` prop in Task 6 (`campus-props.ts`) already covers rows 28–30 with `y: 28, h: 3, layer: 'below'` and rest anchors on adjacent grass tiles, so no additional prop changes are needed here.

- [ ] **Step 2: Rebuild world.json**

```bash
npx tsx src/build-world.ts
```

- [ ] **Step 3: Commit**

```bash
git add src/campus-layout.ts public/worlds/easy-company/world.json
git commit -m "feat: add pool water tiles in green area zone"
```

---

### Task 15: Unit Tests for Campus Layout

**Files:**
- Create: `src/__tests__/campus-layout.test.ts`
- (Requires `vitest` — already in devDependencies)

- [ ] **Step 1: Write tests for `buildFloorGrid()`**

```typescript
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
    // Architect: rows 37-39, cols 5-13
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
```

- [ ] **Step 2: Run tests**

```bash
npx vitest run src/__tests__/campus-layout.test.ts
```

Expected: All 6 tests pass

- [ ] **Step 3: Commit**

```bash
git add src/__tests__/campus-layout.test.ts
git commit -m "test: add unit tests for campus floor grid"
```

---

### Task 16: Integration Test — Full Campus Walkthrough

**Files:** None (testing only)

- [ ] **Step 1: Start dev server**

```bash
npm run dev
```

- [ ] **Step 2: Spawn agents in different zones**

```bash
# CEO in office
curl -X POST http://localhost:4321/api/heartbeat -H 'Content-Type: application/json' \
  -d '{"agent":"ceo","name":"Marcus Chen","state":"working","task":"Q1 review"}'

# Traders in NOC
curl -X POST http://localhost:4321/api/heartbeat -H 'Content-Type: application/json' \
  -d '{"agent":"trader","name":"Jake Ross","state":"working","task":"Monitoring BTC"}'

# CTO thinking in data center
curl -X POST http://localhost:4321/api/heartbeat -H 'Content-Type: application/json' \
  -d '{"agent":"cto","name":"Sarah Kim","state":"thinking","task":"Evaluating infra"}'

# HR socializing in café
curl -X POST http://localhost:4321/api/heartbeat -H 'Content-Type: application/json' \
  -d '{"agent":"hr","name":"Lisa Park","state":"speaking","task":"Team sync"}'

# New agent in gaming lounge
curl -X POST http://localhost:4321/api/heartbeat -H 'Content-Type: application/json' \
  -d '{"agent":"intern_01","name":"Alex Newbie","state":"idle","task":null}'

# Architect (hidden office)
curl -X POST http://localhost:4321/api/heartbeat -H 'Content-Type: application/json' \
  -d '{"agent":"architect","name":"The Architect","state":"working","task":"Observing all systems"}'
```

- [ ] **Step 3: Verify all behaviors**

| Check | Expected |
|-------|----------|
| Zoom in/out (scroll) | Smooth zoom 0.4x–3.0x |
| Pan (right-click drag) | Camera follows drag |
| Press `0` | Zoom resets to 1.0x |
| Press `A` | Camera snaps to Architect's Office |
| CEO at desk | Sitting animation at CEO desk anchor |
| Trader at NOC | Working at NOC desk |
| CTO in data center | Thinking state near utility anchors |
| HR in café | Speaking state at social anchor |
| Intern idle | Wandering between gaming lounge wander points |
| Architect visible | In hidden office, no path to main campus |
| Click agent | Tooltip shows name/state/task |
| Agents don't overlap | Separation steering active |
| Agents don't walk through props | Collision detection working |

- [ ] **Step 4: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: integration test adjustments for campus layout"
```

---

### Task 17: Push to GitHub

- [ ] **Step 1: Push all commits**

```bash
git push origin master
```

- [ ] **Step 2: Verify on GitHub**

```bash
gh repo view i02202/EasyCompany-HQ --web
```

---

## Summary

| Task | What | Estimated fal.ai cost |
|------|------|-----------------------|
| 1 | 8 textures | ~$0.16 |
| 2 | 8 entertainment props | ~$0.32 |
| 3 | 9 office/infra props | ~$0.36 |
| 4 | 8 outdoor/architect props | ~$0.32 |
| 5 | Campus layout code | $0 |
| 6 | Prop placements code | $0 |
| 7 | Wander points code | $0 |
| 8 | World assembler script | $0 |
| 9 | main.ts 40×40 update | $0 |
| 10 | Zoom controls | $0 |
| 11 | Architect's Office | $0 |
| 12 | UI rebrand | $0 |
| 13 | Camera pan | $0 |
| 14 | Pool water tiles | $0 |
| 15 | Unit tests for campus layout | $0 |
| 16 | Integration test | $0 |
| 17 | Push to GitHub | $0 |
| **Total** | **17 tasks** | **~$1.16** |
