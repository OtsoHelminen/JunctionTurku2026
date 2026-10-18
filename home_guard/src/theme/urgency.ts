import type { Urgency } from '../components/properties/alert';

export interface UrgencyStyle {
  label: string;
  /** Solid card fill, or null for a regular surface card */
  fill: string | null;
  /** Text and icons on the fill */
  onFill: string;
  /** Card shadow for filled cards */
  shadow: string | null;
  /** Tag background on surface cards, null = use theme surface2 with a line border */
  tag: string | null;
}

// Same in both themes. These are the only saturated colours in the UI.
export const URGENCY_STYLES: Record<Urgency, UrgencyStyle> = {
  immediate: {
    label: 'Act now',
    fill: '#FF4A3D',
    onFill: '#1A0200',
    shadow: '0px 10px 28px rgba(255,74,61,0.32)',
    tag: null,
  },
  today: {
    label: 'Today',
    fill: '#FF8A1F',
    onFill: '#1A0A00',
    shadow: '0px 8px 24px rgba(255,138,31,0.28)',
    tag: null,
  },
  this_week: {
    label: 'This week',
    fill: null,
    onFill: '#1A1200',
    shadow: null,
    tag: '#FFC53D',
  },
  monitor: {
    label: 'Monitor',
    fill: null,
    onFill: '',
    shadow: null,
    tag: null,
  },
};
