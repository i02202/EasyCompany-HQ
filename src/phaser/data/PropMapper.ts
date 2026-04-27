/**
 * PropMapper — defines visual style for each prop type.
 *
 * Phase B approach: Modern tech-office styled geometric shapes.
 * No zombie-era SmallScaleInt tiles — instead, each prop has a
 * shape type (desk, chair, screen, table, etc.) rendered as clean
 * geometric isometric forms with corporate colors.
 *
 * Future: Replace with custom-generated tiles via PixelLab API
 * matching the modern office aesthetic.
 */

/**
 * Shape types define how the prop is rendered geometrically.
 * Each shape type has a distinct visual treatment in PropSprite.
 */
export type PropShape =
  | 'desk'           // Flat surface with monitor silhouette
  | 'chair'          // Small rounded shape
  | 'table'          // Flat surface, no monitor
  | 'sofa'           // Wide, low, rounded
  | 'screen'         // Tall, thin, glowing rectangle
  | 'rack'           // Tall vertical with indicator lights
  | 'cabinet'        // Medium box with front detail
  | 'counter'        // Long horizontal surface
  | 'stool'          // Very small seat
  | 'appliance'      // Small box with detail
  | 'plant'          // Organic round shape (green)
  | 'glass_wall'     // Transparent vertical panel
  | 'whiteboard'     // Flat white rectangle, wall-mounted
  | 'door'           // Tall rectangle frame
  | 'pool'           // Flat water surface
  | 'lights'         // Thin horizontal line (decorative)
  | 'neon'           // Glowing text sign
  | 'camera'         // Tiny mounted device
  | 'cables'         // Low ground detail
  | 'bean_bag'       // Low rounded blob
  | 'generic';       // Default fallback

export interface PropStyle {
  shape: PropShape;
  /** Primary color (fill) */
  color: number;
  /** Accent/highlight color */
  accent: number;
  /** Label shown on hover or at zoom */
  label: string;
  /** Glow effect (for screens, neon, indicators) */
  glow?: boolean;
}

/**
 * Master prop ID → visual style mapping.
 *
 * Color palette: modern tech office
 *   - Desks/tables: white-gray (0xd0d4dc, 0xc8ccd4)
 *   - Chairs: dark charcoal (0x3a3e48)
 *   - Screens: dark with blue glow (0x1a1e28 + 0x4a9eff)
 *   - Racks: dark with green LEDs (0x2a2e38 + 0x4aff7a)
 *   - Glass: pale blue transparent (0x8ab4d8)
 *   - Plants: fresh green (0x4aaa5a)
 *   - Sofas: warm gray/navy (0x4a5068)
 */
const PROP_STYLES: Record<string, PropStyle> = {
  // ── Office furniture ──
  desk_monitor: {
    shape: 'desk', color: 0xd0d4dc, accent: 0x4a9eff, label: 'Desk',
    glow: true,
  },
  ergonomic_chair: {
    shape: 'chair', color: 0x3a3e48, accent: 0x5a5e68, label: 'Chair',
  },
  lounge_sofa: {
    shape: 'sofa', color: 0x4a5068, accent: 0x5a6078, label: 'Sofa',
  },
  coffee_table: {
    shape: 'table', color: 0xc8ccd4, accent: 0xb0b4bc, label: 'Table',
  },
  scrum_table: {
    shape: 'table', color: 0xd0d4dc, accent: 0xb8bcc4, label: 'Table',
  },
  lounge_chair: {
    shape: 'chair', color: 0x4a5060, accent: 0x5a6070, label: 'Chair',
  },

  // ── Kitchen / bar ──
  fridge: {
    shape: 'cabinet', color: 0xb8bcc8, accent: 0x4a9eff, label: 'Fridge',
  },
  bar_counter: {
    shape: 'counter', color: 0x8a6a3a, accent: 0x6a5a2a, label: 'Bar',
  },
  bar_stool: {
    shape: 'stool', color: 0x3a3e48, accent: 0x5a5e68, label: '',
  },
  espresso_machine: {
    shape: 'appliance', color: 0x2a2e38, accent: 0xff6a3a, label: 'Coffee',
  },
  cocktail_bar: {
    shape: 'counter', color: 0x6a4a2a, accent: 0xffd700, label: 'Bar',
  },

  // ── Tech / data ──
  server_rack: {
    shape: 'rack', color: 0x2a2e38, accent: 0x4aff7a, label: 'Server',
    glow: true,
  },
  data_display_wall: {
    shape: 'screen', color: 0x1a1e28, accent: 0x4a9eff, label: 'Display',
    glow: true,
  },
  noc_screen_wall: {
    shape: 'screen', color: 0x1a1e28, accent: 0xff4a4a, label: 'NOC',
    glow: true,
  },
  panoramic_screen: {
    shape: 'screen', color: 0x1a1e28, accent: 0x4a9eff, label: 'Screen',
    glow: true,
  },
  architect_monitors: {
    shape: 'screen', color: 0x1a1e28, accent: 0xe94560, label: 'Monitors',
    glow: true,
  },
  data_cables: {
    shape: 'cables', color: 0x2a2e38, accent: 0x3a4a5a, label: '',
  },
  biometric_panel: {
    shape: 'appliance', color: 0x2a3a4a, accent: 0x4aff7a, label: 'Bio',
    glow: true,
  },
  video_camera: {
    shape: 'camera', color: 0x3a3e48, accent: 0xff3a3a, label: '',
    glow: true,
  },

  // ── Walls / partitions ──
  huddle_glass_wall: {
    shape: 'glass_wall', color: 0x8ab4d8, accent: 0xaad4f8, label: '',
  },
  whiteboard_glass: {
    shape: 'whiteboard', color: 0xe8ecf4, accent: 0xd0d4dc, label: 'Board',
  },
  changing_room_door: {
    shape: 'door', color: 0x6a7080, accent: 0x8a9098, label: '',
  },

  // ── Plants ──
  tall_plant: {
    shape: 'plant', color: 0x4aaa5a, accent: 0x3a8a4a, label: '',
  },

  // ── Entertainment ──
  arcade_cabinet: {
    shape: 'cabinet', color: 0x2a2e38, accent: 0xff4aff, label: 'Arcade',
    glow: true,
  },
  karaoke_machine: {
    shape: 'cabinet', color: 0x2a2e38, accent: 0xffaa2a, label: 'Karaoke',
    glow: true,
  },
  ping_pong_table: {
    shape: 'table', color: 0x2a6a4a, accent: 0xffffff, label: 'Ping Pong',
  },
  bean_bag: {
    shape: 'bean_bag', color: 0xaa5a3a, accent: 0xba6a4a, label: '',
  },
  neon_sign_play: {
    shape: 'neon', color: 0xff3a7a, accent: 0xff6a9a, label: 'PLAY',
    glow: true,
  },
  neon_sign_hack: {
    shape: 'neon', color: 0x3aff7a, accent: 0x6affaa, label: 'HACK',
    glow: true,
  },

  // ── Presentation ──
  podium: {
    shape: 'cabinet', color: 0x8a8a9a, accent: 0x4a9eff, label: 'Podium',
  },
  auditorium_seats: {
    shape: 'sofa', color: 0x4a4a5a, accent: 0x5a5a6a, label: 'Seats',
  },

  // ── Outdoor / recreation ──
  pool_edge: {
    shape: 'pool', color: 0x2a7aba, accent: 0x4a9ada, label: 'Pool',
    glow: true,
  },
  string_lights: {
    shape: 'lights', color: 0xffd700, accent: 0xffee88, label: '',
    glow: true,
  },
};

/**
 * Get the visual style for a prop ID.
 */
export function getPropStyle(propId: string): PropStyle {
  return PROP_STYLES[propId] ?? {
    shape: 'generic',
    color: 0x6a6a7a,
    accent: 0x8a8a9a,
    label: propId.replace(/_/g, ' '),
  };
}
