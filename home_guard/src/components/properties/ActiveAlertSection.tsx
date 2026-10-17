import React, { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { AlertEntry, Urgency } from './alert';
import { useTheme } from '../../theme/ThemeContext';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

const URGENCY_STYLES: Record<
  Urgency,
  { label: string; icon: IconName; accent: string; background: string }
> = {
  immediate: { label: 'Immediate', icon: 'warning', accent: '#dc2626', background: '#fef2f2' },
  today: { label: 'Today', icon: 'alert-circle', accent: '#ea580c', background: '#fff7ed' },
  this_week: { label: 'This week', icon: 'time', accent: '#ca8a04', background: '#fefce8' },
  monitor: { label: 'Monitor', icon: 'eye', accent: '#2563eb', background: '#eff6ff' },
};

const COLLAPSED_COUNT = 3;

interface ActiveAlertSectionProps {
  /** Already filtered and sorted by urgency. */
  alerts: AlertEntry[];
}

export default function ActiveAlertSection({ alerts }: ActiveAlertSectionProps) {
  const { colors, isDark } = useTheme();
  const [showAll, setShowAll] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const visibleAlerts = showAll ? alerts : alerts.slice(0, COLLAPSED_COUNT);
  const canToggle = alerts.length > COLLAPSED_COUNT;

  const toggleExpanded = (id: number) => {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <View style={styles.section}>
      <View style={styles.headingRow}>
        <Text style={[styles.heading, { color: colors.text }]}>Active alerts</Text>
        {canToggle && (
          <TouchableOpacity
            onPress={() => setShowAll((value) => !value)}
            hitSlop={8}
            accessibilityRole="button"
          >
            <Text style={[styles.showAll, { color: colors.secondaryText }]}>
              {showAll ? 'Show less' : 'Show All'}
            </Text>
          </TouchableOpacity>
        )}
      </View>

      {visibleAlerts.length === 0 ? (
        <View
          style={[
            styles.emptyCard,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
        >
          <Ionicons name="checkmark-circle" size={24} color="#16a34a" />
          <Text style={[styles.emptyText, { color: colors.secondaryText }]}>No active alerts</Text>
        </View>
      ) : (
        visibleAlerts.map((alert) => {
          const urgency = URGENCY_STYLES[alert.urgency];
          const isExpanded = expandedIds.has(alert.id);
          return (
            <TouchableOpacity
              key={alert.id}
              style={[
                styles.card,
                {
                  backgroundColor: isDark ? colors.surface : urgency.background,
                  borderLeftColor: urgency.accent,
                },
              ]}
              onPress={() => toggleExpanded(alert.id)}
              activeOpacity={0.85}
              accessibilityRole="button"
              accessibilityLabel={`${urgency.label}: ${alert.title}`}
              accessibilityHint={isExpanded ? 'Collapse alert' : 'Expand alert'}
              accessibilityState={{ expanded: isExpanded }}
            >
              <Ionicons name={urgency.icon} size={26} color={urgency.accent} />
              <View style={styles.cardBody}>
                <Text
                  style={[styles.cardTitle, { color: colors.text }]}
                  numberOfLines={isExpanded ? undefined : 2}
                >
                  {alert.title}
                </Text>
                {alert.subtitle ? (
                  <Text
                    style={[styles.cardSubtitle, { color: colors.secondaryText }]}
                    numberOfLines={isExpanded ? undefined : 2}
                  >
                    {alert.subtitle}
                  </Text>
                ) : null}
              </View>
              <View style={styles.cardSide}>
                <View style={[styles.chip, { backgroundColor: urgency.accent }]}>
                  <Text style={styles.chipText}>{urgency.label}</Text>
                </View>
                <Ionicons
                  name={isExpanded ? 'chevron-up' : 'chevron-down'}
                  size={18}
                  color={colors.mutedText}
                />
              </View>
            </TouchableOpacity>
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    marginBottom: 24,
  },
  headingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  heading: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0f172a',
  },
  showAll: {
    fontSize: 14,
    fontWeight: '500',
    color: '#334155',
  },
  card: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    padding: 14,
    marginBottom: 10,
    borderRadius: 14,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardBody: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#0f172a',
  },
  cardSubtitle: {
    marginTop: 2,
    fontSize: 13,
    color: '#475569',
  },
  cardSide: {
    alignItems: 'flex-end',
    gap: 8,
  },
  chip: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
  },
  chipText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#ffffff',
  },
  emptyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 14,
    borderRadius: 14,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  emptyText: {
    fontSize: 14,
    color: '#475569',
  },
});
