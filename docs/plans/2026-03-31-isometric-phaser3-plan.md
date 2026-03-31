# Plan: Rebuild Isométrico Phaser 3 — Easy Company HQ

**Branch:** `feat/isometric-phaser3`
**Fecha:** 2026-03-31
**Objetivo:** Reconstruir el portal Easy Company HQ desde MiniVRS (top-down 2D) a **Phaser 3 isométrico** con calidad visual nivel Project Zomboid. Sin elementos de supervivencia — solo la calidad artística aplicada a un campus tech.

---

## 1. Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                    Navegador (Vite + TS)                 │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │  Phaser 3    │   │   Zustand    │   │  React UI   │ │
│  │  Game Canvas │◄──┤   Store      │──►│  Overlay    │ │
│  │  (isométrico)│   │  (estado)    │   │  (paneles)  │ │
│  └──────┬───────┘   └──────┬───────┘   └─────────────┘ │
│         │                  │                             │
│         ▼                  ▼                             │
│  ┌──────────────┐   ┌──────────────┐                    │
│  │  Capa Assets │   │  WebSocket   │                    │
│  │  SmallScale  │   │  Protocolo   │                    │
│  │  + PixelLab  │   │  (shared)    │                    │
│  └──────────────┘   └──────┬───────┘                    │
│                            │                             │
└────────────────────────────┼─────────────────────────────┘
                             ▼
                     AmerClaw-Web4 (Go)
                     ws://host:18890/ws/portal
```

### Lo que se mantiene (datos portables — cero reescritura)
| Archivo | Propósito | Estrategia |
|---------|-----------|------------|
| `campus-layout.ts` | Grid 40×40, 13 zonas, corredores, claves de tiles | Importar directo — coords del grid se mapean 1:1 a coords isométricas |
| `campus-props.ts` | 92 props con anclas | Importar directo — traducir (x,y) a coords mundo iso |
| `campus-wander.ts` | 19 puntos de vagabundeo | Importar directo — mismos targets de pathfinding |
| `shared-protocol.md` | Contrato WebSocket (6 tipos de mensaje) | Sin cambios — el protocolo es agnóstico al motor |
| Stores Zustand | Estado de agentes, event store, personalidad | Sin cambios — capa de UI es independiente del renderer |
| React overlay | AgentPanel, tooltips, barras de progreso | Sin cambios — se monta encima del canvas via CSS |

### Lo que se reemplaza
| Actual | Nuevo |
|--------|-------|
| Renderer MiniVRS (Canvas 2D) | Phaser 3 con plugin isométrico de tilemap |
| Camera MiniVRS (zoom.ts custom) | Camera built-in de Phaser 3 (zoom, pan, bounds) |
| Sprites MiniVRS (32×32 flat) | SmallScaleInt 128×256 isométrico + PixelLab 8-dir personajes |
| EasyStar.js en grid plano | EasyStar.js en grid iso (mismo algoritmo, coords iso) |

---

## 2. Inventario de Assets & Pipeline

### 2.1 Packs de Tiles (SmallScaleInt — 128×256px isométricos)

| Pack | Tiles | Uso en campus |
|------|-------|---------------|
| **zombie-interior** | 504 objetos × 4 dirs | Muebles de oficina, escritorios, sillas, estantes, monitores, puertas, paredes, cocina |
| **zombie-city** | 251 tiles × 4 dirs | Exteriores: autos (terraza/parking), muros, flora, suelos, techos |
| **zombie-rural** | 467 tiles (256×512) | Outdoor: árboles, flora, acantilados para Área Verde, decoración piscina |

#### Mapeo clave de tiles (zombie-interior → zonas del campus)

| Prop actual | Tile(s) SmallScaleInt | Categoría |
|-------------|----------------------|-----------|
| `server_rack` | Factory/ServerRack o variantes Shelf | Factory |
| `desk_monitor` | Combo Table + Monitor | Table, Screen |
| `ergonomic_chair` | Variantes Chair_Office (5 tipos) | Chair |
| `lounge_sofa` | Variantes Couch (9 tipos) | Couch |
| `coffee_table` | Variantes Table_Coffee | Table |
| `scrum_table` | Table_Conference (largo) | Table |
| `huddle_glass_wall` | Door_Glass / Wall_Glass | Door, Wall |
| `bar_counter` | Kitchen_Counter + variantes Bar | Kitchen |
| `espresso_machine` | Variantes Kitchen_Appliance | Kitchen |
| `fridge` | Fridge_S / Fridge_N | Kitchen |
| `arcade_cabinet` | VendingMachine o custom | Vending |
| `pool_edge` | Custom (sin match directo — usar tile suelo + overlay agua) | — |
| `tall_plant` | Variantes Potted_Plant | Decor |
| `panoramic_screen` | Variantes TV / Screen_Wall | Screen |
| `data_display_wall` | Variantes Monitor_Wall / Screen | Screen |

#### Tiles que requieren creación custom (PixelLab API)
- `architect_monitors` — pared de monitores de vigilancia
- `neon_sign_play` / `neon_sign_hack` — letreros neón
- `string_lights` — luces decorativas
- `karaoke_machine` — prop de entretenimiento
- `ping_pong_table` — prop de recreación
- `biometric_panel` — escáner de seguridad
- `data_cables` — manojos de cables
- `pool_water` — tile de agua animado

### 2.2 Sprites de Personajes (PixelLab API — 128×128px, 8 direcciones)

| Agente | Estado | Directorio sprites |
|--------|--------|--------------------|
| `ceo` | Generando | `assets/characters/ceo/` |
| `cto` | Generando | `assets/characters/cto/` |
| `cfo` | Generando | `assets/characters/cfo/` |
| `trader` | Generando | `assets/characters/trader/` |
| `researcher` | Generando | `assets/characters/researcher/` |
| `hr` | Generando | `assets/characters/hr/` |
| `security` | Generando | `assets/characters/security/` |
| `media` | Generando | `assets/characters/media/` |

Cada agente tiene 8 PNGs: `S.png`, `SW.png`, `W.png`, `NW.png`, `N.png`, `NE.png`, `E.png`, `SE.png`.

### 2.3 ❌ Packs incompatibles (NO USAR)

| Pack | Razón |
|------|-------|
| **Pixel Salvaje** (TinyHouse) | 64×64px — escala incorrecta, mezclar con 128×256 se vería terrible |
| **Character Knight** | Estilo fantasía medieval, no encaja con campus tech |
| **Character Thug** | Estilo 16-bit con outline, inconsistente con SmallScaleInt |

### 2.4 Pipeline de construcción de assets

```
assets/packs/zombie-interior/   ─┐
assets/packs/zombie-city/       ─┼─► scripts/build-atlas.ts ──► public/atlas/
assets/packs/zombie-rural/      ─┘     (texture atlases)
assets/characters/*/            ──────► public/atlas/characters.json
```

Usar **Phaser 3 texture packer** o `free-tex-packer-core` para generar sprite atlases:
- Un atlas por categoría de zona (muebles, paredes, decoración, exterior)
- Un atlas para todos los 8 agentes × 8 direcciones = 64 frames
- Formato atlas: JSON Hash (nativo de Phaser)

---

## 3. Setup de Phaser 3

### 3.1 Dependencias a agregar

```json
{
  "dependencies": {
    "phaser": "^3.87.0"
  },
  "devDependencies": {
    "free-tex-packer-core": "^0.3.0"
  }
}
```

Eliminar tras la migración: `@miniverse/core`, `@miniverse/server`, `@miniverse/generate`

### 3.2 Configuración del juego

```typescript
// src/phaser/config.ts
import Phaser from 'phaser';

export const gameConfig: Phaser.Types.Core.GameConfig = {
  type: Phaser.WEBGL,          // Acelerado por GPU
  parent: 'game-container',
  width: window.innerWidth,
  height: window.innerHeight,
  backgroundColor: '#0a0a0a',
  pixelArt: true,              // Sin anti-aliasing — pixel art nítido
  scale: {
    mode: Phaser.Scale.RESIZE, // Auto-resize con el navegador
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  scene: [BootScene, PreloadScene, CampusScene],
};
```

### 3.3 Estructura de escenas

```
src/phaser/
├── config.ts              — Configuración del juego
├── scenes/
│   ├── BootScene.ts       — Barra de carga, settings globales
│   ├── PreloadScene.ts    — Cargar todos los atlases, tilemaps, audio
│   └── CampusScene.ts     — Escena principal (tilemap + agentes)
├── entities/
│   ├── AgentSprite.ts     — Personaje con animación 8-dir + máquina de estados
│   └── PropSprite.ts      — Prop interactivo (click → panel de info)
├── systems/
│   ├── IsometricGrid.ts   — Transforms cartesiano ↔ isométrico
│   ├── Pathfinder.ts      — Wrapper EasyStar.js para grid iso
│   ├── CameraController.ts — Zoom, pan, snap-to-zona, minimap
│   └── DepthSorter.ts     — Y-sort para superposición correcta de sprites
├── data/
│   ├── TileMapper.ts      — Mapea claves de campus-layout → nombres de frames del atlas
│   └── PropMapper.ts      — Mapea IDs de campus-props → sprites SmallScaleInt
└── bridge/
    ├── ZustandBridge.ts   — Sincroniza entidades Phaser ↔ store Zustand
    └── WebSocketBridge.ts — Conecta Phaser al protocolo AmerClaw
```

---

## 4. Sistema de Coordenadas Isométricas

### 4.1 La transformación

Los tiles SmallScaleInt son **128×256px** en proyección isométrica estándar:

```
      Ancho tile:  128px (ancho del diamante)
      Alto tile:   256px (alto del diamante — incluye profundidad vertical)

      Tile de suelo efectivo: 128×64px (la huella del diamante)
      Los 192px extra de altura son para objetos altos (paredes, muebles)
```

**Transformada Cartesiano → Isométrico:**

```typescript
// Para un tile en posición de grid (col, row):
const TILE_W = 128;
const TILE_H = 64;  // Alto del diamante de suelo (no la altura total del sprite)

function cartToIso(col: number, row: number): { screenX: number; screenY: number } {
  return {
    screenX: (col - row) * (TILE_W / 2),
    screenY: (col + row) * (TILE_H / 2),
  };
}

function isoToCart(screenX: number, screenY: number): { col: number; row: number } {
  return {
    col: Math.floor((screenX / (TILE_W / 2) + screenY / (TILE_H / 2)) / 2),
    row: Math.floor((screenY / (TILE_H / 2) - screenX / (TILE_W / 2)) / 2),
  };
}
```

### 4.2 Dimensiones del mapa en espacio isométrico

Grid actual: **40 columnas × 40 filas**

```
Tamaño del mapa isométrico:
  Ancho:  (40 + 40) * 64 = 5120px
  Alto:   (40 + 40) * 32 = 2560px (nivel del suelo)
                         + ~256px (sprites más altos)
                         ≈ 2816px total
```

Límites del mundo de la cámara: `(-2560, 0, 5120, 2816)`

### 4.3 Ordenamiento de profundidad (depth sorting)

En vista isométrica, los sprites más cercanos a la cámara (valores más altos de `row + col`) deben renderizarse encima:

```typescript
// En CampusScene.update():
this.children.sort('y', Phaser.GameObjects.SORT_ASCENDING);
// Más depth manual para props en capa 'above'
```

---

## 5. Implementación Zona por Zona

### Fase A: Infraestructura Core (Hito 1)

| Paso | Tarea | Archivos | Est. |
|------|-------|----------|------|
| A.1 | Setup proyecto Phaser 3, plugin Vite | `src/phaser/config.ts`, `vite.config.ts` | 2h |
| A.2 | Escenas Boot + Preload | `scenes/Boot.ts`, `scenes/Preload.ts` | 1h |
| A.3 | Sistema IsometricGrid + transforms de coords | `systems/IsometricGrid.ts` | 2h |
| A.4 | Tilemap de suelo desde `campus-layout.ts` | `CampusScene.ts`, `TileMapper.ts` | 3h |
| A.5 | Controlador de cámara (zoom, pan, límites) | `systems/CameraController.ts` | 2h |
| A.6 | Script de construcción de atlas de texturas | `scripts/build-atlas.ts` | 2h |

**Entregable:** Campus isométrico vacío con zonas de suelo coloreadas, navegación de cámara funcionando.

### Fase B: Props y Muebles (Hito 2)

| Paso | Tarea | Archivos | Est. |
|------|-------|----------|------|
| B.1 | PropMapper: mapear 30+ IDs de props → frames SmallScaleInt | `data/PropMapper.ts` | 3h |
| B.2 | Entidad PropSprite con interacción click | `entities/PropSprite.ts` | 2h |
| B.3 | Colocar los 92 props desde `campus-props.ts` | `CampusScene.ts` | 2h |
| B.4 | Depth sorter para layering correcto | `systems/DepthSorter.ts` | 1h |
| B.5 | Props custom vía PixelLab API (neones, cables, etc.) | `scripts/generate-props.ts` | 3h |
| B.6 | Segmentos de pared entre zonas | `data/WallMapper.ts` | 2h |

**Entregable:** Campus completamente amueblado con las 13 zonas visualmente distintas.

### Fase C: Personajes Agentes (Hito 3)

| Paso | Tarea | Archivos | Est. |
|------|-------|----------|------|
| C.1 | Atlas de personajes desde sprites PixelLab 8-dir | `scripts/build-atlas.ts` (extender) | 1h |
| C.2 | AgentSprite con animación de caminar 8-dir | `entities/AgentSprite.ts` | 3h |
| C.3 | Pathfinder (EasyStar.js en grid iso) | `systems/Pathfinder.ts` | 2h |
| C.4 | Máquina de estados del agente (idle, caminando, trabajando, social) | `entities/AgentSprite.ts` | 2h |
| C.5 | Bridge WebSocket → spawn/mover agentes | `bridge/WebSocketBridge.ts` | 2h |
| C.6 | Bridge Zustand → sincronizar estado con React overlay | `bridge/ZustandBridge.ts` | 2h |

**Entregable:** 8 agentes caminando entre zonas, respondiendo a heartbeats de AmerClaw.

### Fase D: Pulido y Atmósfera (Hito 4)

| Paso | Tarea | Archivos | Est. |
|------|-------|----------|------|
| D.1 | Modo nocturno: oscurecer zonas, efectos de brillo | `systems/Lighting.ts` | 2h |
| D.2 | Animaciones ambientales (parpadeo pantallas, brillo agua, balanceo plantas) | `systems/Ambience.ts` | 3h |
| D.3 | Etiquetas de zona (texto flotante sobre cada área) | `CampusScene.ts` | 1h |
| D.4 | Minimapa en esquina | `systems/CameraController.ts` | 2h |
| D.5 | Efectos de partículas (partículas datos en DC, vapor café) | `systems/Particles.ts` | 2h |
| D.6 | Diseño de sonido: ambiente oficina, audio por zona | `systems/Audio.ts` | 2h |
| D.7 | Oficina del Arquitecto: animación especial de revelación | `CampusScene.ts` | 1h |

**Entregable:** Experiencia visual de calidad producción con atmósfera nivel PZ.

### Fase E: Integración y Cutover (Hito 5)

| Paso | Tarea | Archivos | Est. |
|------|-------|----------|------|
| E.1 | Eliminar dependencias MiniVRS | `package.json`, borrar viejo `src/main.ts` | 1h |
| E.2 | Reconectar React overlay (AgentPanel, tooltips) | `src/App.tsx`, componentes overlay | 2h |
| E.3 | Atajos de teclado (F=ajustar, A=arquitecto, teclas de zona) | `systems/CameraController.ts` | 1h |
| E.4 | Testing de rendimiento (60fps mínimo a 1080p) | Manual + debug overlay de Phaser | 2h |
| E.5 | Soporte touch móvil (pinch zoom, tap select) | `systems/CameraController.ts` | 2h |
| E.6 | Merge a master | — | 0.5h |

**Entregable:** Reemplazo completo de MiniVRS, todas las features existentes preservadas.

---

## 6. Mapeo de Tiles de Suelo

Claves de tile actuales de `campus-layout.ts` → tiles de suelo SmallScaleInt:

| Clave tile | Visual | Fuente SmallScaleInt |
|------------|--------|---------------------|
| `main_floor` | Piso de oficina gris claro | `zombie-interior/Floor_Tile_Light` |
| `concrete_dark` | Concreto oscuro | `zombie-interior/Floor_Concrete_Dark` |
| `epoxy_gray` | Piso sala de servidores | `zombie-interior/Floor_Industrial` |
| `wood_warm` | Madera cálida (CEO, café) | `zombie-interior/Floor_Wood` |
| `noc_dark` | Sala de operaciones oscura | `zombie-interior/Floor_Dark` |
| `grass_green` | Pasto exterior | `zombie-rural/Grass` o `zombie-city/Ground_Grass` |
| `pool_water` | Agua animada | Tile animado custom (4 frames) |
| `rooftop_tile` | Pavimento terraza | `zombie-city/Ground_Concrete` |
| `architect_floor` | Piso especial oscuro | `zombie-interior/Floor_Lab` |
| `main_wall` | Paredes perimetrales | Variantes `zombie-interior/Wall` (necesitan 4 dirs) |

---

## 7. Estructura de Directorios SmallScaleInt

```
assets/packs/zombie-interior/
├── Chair/         (5 tipos × 4 dirs = 20 PNGs)
├── Table/         (10 tipos × 4 dirs = 40 PNGs)
├── Couch/         (9 tipos × 4 dirs = 36 PNGs)
├── Shelf/         (16 tipos × 4 dirs = 64 PNGs)
├── Screen/        (monitores, TVs)
├── Kitchen/       (3+ tipos de electrodomésticos)
├── Door/          (20 tipos incluyendo vidrio)
├── Wall/          (múltiples variantes)
├── Factory/       (38 items — racks de servidores, maquinaria)
├── Vending/       (máquinas expendedoras)
├── Floor/         (tiles de suelo)
├── Decor/         (plantas, letreros, misc)
└── ...504 objetos únicos en total

assets/packs/zombie-city/
├── Cars/          (vehículos para terraza/parking)
├── Walls/         (paredes exteriores)
├── Flora/         (árboles, arbustos)
├── Ground/        (concreto, asfalto, pasto)
├── Roof/          (elementos de techo)
├── Stairs/        (cambios de elevación)
└── Fence/         (límites)
...251 tiles únicos en total

assets/packs/zombie-rural/
├── Trees/         (árboles grandes para Área Verde)
├── Flora/         (flores, arbustos, cobertura)
├── Cliffs/        (elevación de terreno)
├── Bridges/       (decorativos)
├── Windmill/      (podría ser decoración divertida)
└── ...467 tiles únicos en total (256×512px — ¡doble escala!)
```

> **⚠️ zombie-rural es 256×512px** (doble escala que interior/city). Opciones:
> - Escalar 50% al construir el atlas, o
> - Usar una capa separada de Phaser con `setScale(0.5)` para props rurales

---

## 8. Movimiento de Agentes & Pathfinding

### 8.1 Modelo de movimiento

```typescript
// Heartbeat actual del protocolo:
{ agent: "ceo", state: "walking", task: "Yendo a reunión", energy: 0.8 }

// Movimiento en Phaser:
// 1. Recibir heartbeat con cambio de estado
// 2. Elegir destino de wander points o anclas de props
// 3. Calcular ruta A* en grid iso (EasyStar.js)
// 4. Animar sprite a lo largo de la ruta con dirección correcta
// 5. Al llegar, reproducir animación idle/trabajando
```

### 8.2 Cálculo de dirección

```typescript
const DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE'];

function getDirection(dx: number, dy: number): string {
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);
  // Mapear ángulo a 8 direcciones de brújula
  const index = Math.round(((angle + 180) % 360) / 45) % 8;
  return DIRS[index];
}
```

### 8.3 Grid de caminabilidad

La función existente `buildFloorGrid()` ya produce un grid caminable/no-caminable:
- String vacío (`''`) = no caminable (deadspace)
- Cualquier clave de tile = caminable
- Props con dimensiones `w × h` crean rectángulos de colisión en el grid

```typescript
function buildWalkabilityGrid(): number[][] {
  const floor = buildFloorGrid();
  const grid = floor.map(row => row.map(cell => cell === '' ? 1 : 0)); // 0=caminar, 1=bloquear

  // Marcar huellas de props como bloqueadas
  for (const prop of ALL_PROPS) {
    for (let r = Math.floor(prop.y); r < Math.ceil(prop.y + prop.h); r++) {
      for (let c = Math.floor(prop.x); c < Math.ceil(prop.x + prop.w); c++) {
        if (r >= 0 && r < GRID_ROWS && c >= 0 && c < GRID_COLS) {
          grid[r][c] = 1;
        }
      }
    }
  }
  return grid;
}
```

---

## 9. Cámara y Navegación

### 9.1 Controles

| Input | Acción | API de Phaser |
|-------|--------|--------------|
| Rueda del mouse | Zoom in/out (0.3–3.0×) | `camera.setZoom()` |
| Click izq + arrastrar | Pan | `camera.scrollX/Y` |
| Tecla `F` | Ajustar mapa completo | `camera.centerOn()` + auto-zoom |
| Tecla `A` | Ir al Arquitecto | `camera.pan()` a coords iso de (9,36) |
| Teclas `1`–`9` | Ir a zona | `camera.pan()` al centro de zona |
| Click en agente | Seleccionar → abrir AgentPanel | `sprite.on('pointerdown')` |
| Click en prop | Mostrar tooltip de info | `sprite.on('pointerdown')` |

### 9.2 Minimapa

Esquina inferior derecha, 200×100px, muestra:
- Rectángulos de zona coloreados (coincidiendo con colores de suelo)
- Puntos de agentes (coloreados por rol)
- Rectángulo de viewport (contorno blanco)
- Click para navegar

---

## 10. Integración React Overlay

El overlay React (AgentPanel, tooltips, barras de progreso) se mantiene **exactamente igual**. Se renderiza encima del canvas de Phaser via posicionamiento absoluto.

```
┌──────────────────────────────────────────────┐
│  React root (position: relative)             │
│  ┌────────────────────────────────────────┐  │
│  │  Canvas Phaser (position: absolute)    │  │
│  │  z-index: 0                            │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  React overlay (position: absolute)    │  │
│  │  z-index: 10, pointer-events: none     │  │
│  │  (paneles reciben pointer-events: auto)│  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

**Patrón bridge:** Phaser despacha eventos → ZustandBridge actualiza store → React re-renderiza.

---

## 11. Evaluación de Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Tiles SmallScaleInt no tienen match exacto para todos los props | Medio | Generar props custom vía PixelLab API para las brechas |
| Desajuste de escala zombie-rural 256×512 | Bajo | Escalar 50% al construir o usar `setScale(0.5)` |
| Inconsistencia de calidad de personajes PixelLab entre agentes | Medio | Re-generar con mismas restricciones de estilo/seed, retoque manual |
| Rendimiento con 500+ sprites en pantalla | Bajo | Texture atlases, culling de viewport (Phaser lo hace automático) |
| Costo de pathfinding EasyStar.js en grid 40×40 | Muy Bajo | Grid es pequeño, A* es rápido. Cachear rutas de caminos comunes. |
| Incompatibilidad protocolo WebSocket | Ninguno | Protocolo es agnóstico al motor, mismo contrato |
| Conflictos de z-index con React overlay | Bajo | Resuelto con stacking explícito de z-index |

---

## 12. Estrategia de Testing

| Tipo test | Qué | Herramienta |
|-----------|-----|-------------|
| Unitario | Transforms de coordenadas (cart↔iso) | Vitest |
| Unitario | Generación de grid de caminabilidad | Vitest |
| Unitario | Cálculo de dirección | Vitest |
| Unitario | Lookups TileMapper / PropMapper | Vitest |
| Integración | Escena Phaser carga sin errores | Vitest + jsdom mock |
| Integración | Bridge WebSocket procesa heartbeats | Vitest + WS mock |
| Visual | Las 13 zonas renderizan correctamente | Comparación manual de screenshots |
| Visual | Agente camina suavemente entre zonas | Observación manual |
| Rendimiento | Mantiene 60fps a 1080p | Debug overlay de Phaser |
| E2E | Flujo completo: heartbeat → agente se mueve → panel se abre | Playwright |

---

## 13. Plan de Eliminación de Archivos (Post-Migración)

Después de completar y mergear la Fase E:

```
ELIMINAR:
  src/main.ts              (entry point MiniVRS)
  src/zoom.ts              (cámara custom — reemplazada por cámara Phaser)
  src/renderer.ts          (renderer MiniVRS — si existe)
  public/worlds/           (world JSON MiniVRS — reemplazado por tilemap iso)

CONSERVAR:
  src/campus-layout.ts     (datos — usado por Phaser)
  src/campus-props.ts      (datos — usado por Phaser)
  src/campus-wander.ts     (datos — usado por Phaser)
  src/architect.ts         (lógica — adaptar a API de cámara Phaser)
  src/stores/              (Zustand — sin cambios)
  src/components/          (React overlay — sin cambios)
```

---

## 14. Estimación de Tiempo

| Fase | Duración | Acumulado |
|------|----------|-----------|
| **A. Infraestructura Core** | 12h | 12h |
| **B. Props y Muebles** | 13h | 25h |
| **C. Personajes Agentes** | 12h | 37h |
| **D. Pulido y Atmósfera** | 13h | 50h |
| **E. Integración y Cutover** | 8.5h | 58.5h |

**Total estimado: ~60 horas de desarrollo**

Ejecución recomendada: sprint de 2 semanas a ~4h/día, o 1 semana intensiva.

---

## 15. Criterios de Éxito

- [ ] Las 13 zonas visibles y visualmente distintas en vista isométrica
- [ ] 8 agentes caminando con animación correcta de 8 direcciones
- [ ] Cámara: zoom suave (0.3–3×), pan, hotkeys snap-to-zona
- [ ] Los 92 props colocados con sprites SmallScaleInt o PixelLab
- [ ] Protocolo WebSocket funciona idénticamente (sin cambios en Go)
- [ ] React overlay (AgentPanel, tooltips) funciona encima del canvas Phaser
- [ ] 60fps a resolución 1080p
- [ ] Oficina del Arquitecto accesible con tecla 'A' con animación de revelación
- [ ] Calidad visual comparable a escenas interiores de Project Zomboid
- [ ] Modo nocturno con efectos de brillo en zonas activas
