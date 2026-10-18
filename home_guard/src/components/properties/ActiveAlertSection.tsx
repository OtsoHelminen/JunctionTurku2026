import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import type { AlertEntry } from './alert';
import { FONTS, useTheme } from '../../theme/ThemeContext';
import { URGENCY_STYLES } from '../../theme/urgency';

const COLLAPSED_COUNT = 3;

interface ActiveAlertSectionProps {
  /** Already filtered and sorted by urgency. */
  alerts: AlertEntry[];
}

export default function ActiveAlertSection({ alerts }: ActiveAlertSectionProps) {
  const { colors } = useTheme();
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
          <Pressable
            style={styles.showAllButton}
            onPress={() => setShowAll((value) => !value)}
            android_ripple={{ color: colors.accentSoft, borderless: true }}
            accessibilityRole="button"
          >
            <Text style={[styles.showAll, { color: colors.accentText }]}>
              {showAll ? 'Show less' : 'Show all'}
            </Text>
          </Pressable>
        )}
      </View>

      {visibleAlerts.length === 0 ? (
        <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.line }]}>
          <MaterialIcons name="check-circle" size={26} color={colors.accentText} />
          <Text style={[styles.emptyText, { color: colors.muted }]}>No active alerts</Text>
        </View>
      ) : (
        visibleAlerts.map((alert) => {
          const urgency = URGENCY_STYLES[alert.urgency];
          const isExpanded = expandedIds.has(alert.id);
          const isFilled = urgency.fill !== null;
          const textColor = isFilled ? urgency.onFill : colors.text;
          const subtitleColor = isFilled ? urgency.onFill : colors.muted;

          return (
            <View
              key={alert.id}
              style={[styles.cardShell, isFilled && { boxShadow: urgency.shadow ?? undefined }]}
            >
              <Pressable
                style={[
                  styles.card,
                  isFilled
                    ? {
                        backgroundColor: urgency.fill ?? undefined,
                        borderColor: urgency.fill ?? undefined,
                      }
                    : { backgroundColor: colors.surface, borderColor: colors.line },
                ]}
                onPress={() => toggleExpanded(alert.id)}
                android_ripple={{ color: isFilled ? 'rgba(0,0,0,0.12)' : colors.accentSoft }}
                accessibilityRole="button"
                accessibilityLabel={`${urgency.label}: ${alert.title}`}
                accessibilityHint={isExpanded ? 'Collapse alert' : 'Expand alert'}
                accessibilityState={{ expanded: isExpanded }}
              >
                <MaterialIcons name="error" size={26} color={textColor} />
                <View style={styles.cardBody}>
                  <Text
                    style={[styles.cardTitle, { color: textColor }]}
                    numberOfLines={isExpanded ? undefined : 2}
                  >
                    {alert.title}
                  </Text>
                  {alert.subtitle ? (
                    <Text
                      style={[styles.cardSubtitle, { color: subtitleColor }]}
                      numberOfLines={isExpanded ? undefined : 2}
                    >
                      {alert.subtitle}
                    </Text>
                  ) : null}
                </View>
                <View style={styles.cardSide}>
                  {isFilled ? (
                    <View style={[styles.chip, { backgroundColor: urgency.onFill }]}>
                      <Text style={[styles.chipText, { color: '#FFFFFF' }]}>{urgency.label}</Text>
                    </View>
                  ) : urgency.tag ? (
                    <View style={[styles.chip, { backgroundColor: urgency.tag }]}>
                      <Text style={[styles.chipText, { color: urgency.onFill }]}>
                        {urgency.label}
                      </Text>
                    </View>
                  ) : (
                    <View
                      style={[
                        styles.chip,
                        styles.chipOutlined,
                        { backgroundColor: colors.surface2, borderColor: colors.line },
                      ]}
                    >
                      <Text style={[styles.chipText, { color: colors.text }]}>{urgency.label}</Text>
                    </View>
                  )}
                  <MaterialIcons
                    name={isExpanded ? 'expand-less' : 'expand-more'}
                    size={24}
                    color={isFilled ? urgency.onFill : colors.muted}
                  />
                </View>
              </Pressable>
            </View>
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: 12,
  },
  headingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  heading: {
    fontFamily: FONTS.heading,
    fontSize: 20,
  },
  showAllButton: {
    minHeight: 48,
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  showAll: {
    fontFamily: FONTS.bodyBold,
    fontSize: 15,
  },
  cardShell: {
    borderRadius: 18,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    overflow: 'hidden',
  },
  cardBody: {
    flex: 1,
    gap: 4,
  },
  cardTitle: {
    fontFamily: FONTS.bodyBold,
    fontSize: 18,
    lineHeight: 22.5,
  },
  cardSubtitle: {
    fontFamily: FONTS.body,
    fontSize: 15,
    lineHeight: 20,
  },
  cardSide: {
    alignItems: 'flex-end',
    gap: 10,
  },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  chipOutlined: {
    borderWidth: 1,
  },
  chipText: {
    fontFamily: FONTS.bodyBold,
    fontSize: 13,
  },
  emptyText: {
    flex: 1,
    alignSelf: 'center',
    fontFamily: FONTS.body,
    fontSize: 16,
  },
});
