import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { formatPriceRange } from './alert';
import type { ExpertSuggestion } from './alert';
import { useTheme } from '../../theme/ThemeContext';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

function iconForProfession(profession: string): IconName {
  const value = profession.toLowerCase();
  if (value.includes('roof')) return 'home-outline';
  if (value.includes('plumb')) return 'water-outline';
  if (value.includes('chimney') || value.includes('sweep')) return 'flame-outline';
  if (value.includes('electric')) return 'flash-outline';
  return 'construct-outline';
}

interface OrderHelpSectionProps {
  experts: ExpertSuggestion[];
}

export default function OrderHelpSection({ experts }: OrderHelpSectionProps) {
  const { colors } = useTheme();
  if (experts.length === 0) return null;

  return (
    <View style={styles.section}>
      <Text style={[styles.heading, { color: colors.text }]}>Order help</Text>
      {experts.map((expert) => {
        const price = formatPriceRange(expert.priceMin, expert.priceMax);
        return (
          <View key={expert.key} style={styles.row}>
            <View
              style={[
                styles.iconTile,
                { backgroundColor: colors.surface, borderColor: colors.border },
              ]}
            >
              <Ionicons
                name={iconForProfession(expert.profession)}
                size={28}
                color={colors.secondaryText}
              />
            </View>
            <View style={styles.rowBody}>
              <Text style={[styles.profession, { color: colors.text }]}>{expert.profession}</Text>
              {expert.name ? (
                <Text style={[styles.name, { color: colors.secondaryText }]}>{expert.name}</Text>
              ) : null}
              {price ? (
                <View style={styles.priceRow}>
                  <Ionicons name="cash-outline" size={14} color={colors.mutedText} />
                  <Text style={[styles.price, { color: colors.mutedText }]}>{price}</Text>
                </View>
              ) : null}
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    marginBottom: 24,
  },
  heading: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 14,
    marginBottom: 14,
  },
  iconTile: {
    width: 56,
    height: 56,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowBody: {
    flex: 1,
  },
  profession: {
    fontSize: 15,
    fontWeight: '600',
    color: '#0f172a',
  },
  name: {
    marginTop: 2,
    fontSize: 13,
    color: '#475569',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  price: {
    fontSize: 12,
    color: '#64748b',
  },
});
