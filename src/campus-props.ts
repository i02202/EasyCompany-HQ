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

// ─── Architect's Office (rows 34-38, cols 4-14) ───
const architectProps: PropPlacement[] = [
  // Top row: monitors wall
  { id: 'architect_monitors', x: 5, y: 34, w: 4, h: 2, layer: 'below', anchors: [] },
  { id: 'architect_monitors', x: 10, y: 34, w: 4, h: 2, layer: 'below', anchors: [] },
  // Center: the architect's desk
  { id: 'desk_monitor', x: 8, y: 36, w: 2, h: 1, layer: 'below', anchors: [
    { name: 'architect_seat', ox: 1, oy: 1.5, type: 'work' },
  ]},
  { id: 'ergonomic_chair', x: 8.5, y: 37.5, w: 1, h: 1, layer: 'above', anchors: [] },
  // Data cables running along the edges
  { id: 'data_cables', x: 4.5, y: 36, w: 2, h: 2, layer: 'below', anchors: [] },
  { id: 'data_cables', x: 12.5, y: 36, w: 2, h: 2, layer: 'below', anchors: [] },
  // Bottom: more data cables
  { id: 'data_cables', x: 6, y: 38, w: 3, h: 1, layer: 'below', anchors: [] },
  { id: 'data_cables', x: 10, y: 38, w: 3, h: 1, layer: 'below', anchors: [] },
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
