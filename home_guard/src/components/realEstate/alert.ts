export type Urgency = 'immediate' | 'today' | 'this_week' | 'monitor';

/** Most urgent first. Used for sorting. */
export const URGENCY_ORDER: Urgency[] = ['immediate', 'today', 'this_week', 'monitor'];

export interface AlertExpert {
  profession: string;
  name: string | null;
  priceMin: number | null;
  priceMax: number | null;
}

/** The only fields of a notification the UI cares about. */
export interface AlertEntry {
  id: number;
  houseId: number | null;
  status: string;
  urgency: Urgency;
  title: string;
  subtitle: string;
  createdAt: number;
  expert: AlertExpert | null;
}

export interface ExpertSuggestion extends AlertExpert {
  key: string;
  urgency: Urgency;
}

interface NotificationContentLike {
  title?: string | null;
  body?: string | null;
  data?: unknown;
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const asString = (value: unknown): string | null =>
  typeof value === 'string' && value.trim() ? value.trim() : null;

const asNumber = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;

const isUrgency = (value: unknown): value is Urgency =>
  typeof value === 'string' && (URGENCY_ORDER as string[]).includes(value);

/**
 * Turns a push notification into an AlertEntry.
 * Returns null for notifications that are not alerts.
 */
export function parseAlertNotification(content: NotificationContentLike): AlertEntry | null {
  const data = content.data;
  if (!isRecord(data) || data.kind !== 'alert') return null;

  const id = asNumber(data.alert_id);
  if (id === null) return null;

  const rawExpert = isRecord(data.expert) ? data.expert : null;
  const profession = asString(rawExpert?.profession);
  const firstBodyLine = asString(content.body?.split('\n')[0]);
  const created = typeof data.created_at === 'string' ? Date.parse(data.created_at) : NaN;

  return {
    id,
    houseId: asNumber(data.house_id),
    status: asString(data.status) ?? 'active',
    urgency: isUrgency(data.urgency) ? data.urgency : 'monitor',
    // Card title: what to do. Card subtitle: why.
    title: asString(data.recommendation) ?? firstBodyLine ?? asString(content.title) ?? 'Warning',
    subtitle: asString(data.message) ?? '',
    createdAt: Number.isNaN(created) ? Date.now() : created,
    expert: profession
      ? {
          profession,
          name: asString(rawExpert?.example_name),
          priceMin: asNumber(rawExpert?.price_min_eur),
          priceMax: asNumber(rawExpert?.price_max_eur),
        }
      : null,
  };
}

/** Sorts by urgency (immediate -> monitor), newest first within the same urgency. */
export function sortAlerts(alerts: AlertEntry[]): AlertEntry[] {
  return [...alerts].sort(
    (a, b) =>
      URGENCY_ORDER.indexOf(a.urgency) - URGENCY_ORDER.indexOf(b.urgency) ||
      b.createdAt - a.createdAt
  );
}

/**
 * One suggestion per profession, taken from the most urgent alert.
 * Expects alerts that are already sorted with sortAlerts.
 */
export function getExpertSuggestions(sortedAlerts: AlertEntry[]): ExpertSuggestion[] {
  const seen = new Set<string>();
  const suggestions: ExpertSuggestion[] = [];

  for (const alert of sortedAlerts) {
    if (!alert.expert) continue;
    const key = alert.expert.profession.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    suggestions.push({ ...alert.expert, key, urgency: alert.urgency });
  }

  return suggestions;
}

export function formatPriceRange(min: number | null, max: number | null): string | null {
  if (min !== null && max !== null) return `${min}–${max} €`;
  if (min !== null) return `from ${min} €`;
  if (max !== null) return `up to ${max} €`;
  return null;
}
