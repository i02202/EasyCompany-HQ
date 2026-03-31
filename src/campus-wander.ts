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
