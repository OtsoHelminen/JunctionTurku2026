import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { formatPriceRange } from './alert';
import type { ExpertSuggestion } from './alert';

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
  if (experts.length === 0) return null;

  return (
    <View style={styles.section}>
      <Text style={styles.heading}>Order help</Text>
      {experts.map((expert) => {
        const price = formatPriceRange(expert.priceMin, expert.priceMax);
        return (
          <View key={expert.key} style={styles.row}>
            <View style={styles.iconTile}>
              <Ionicons name={iconForProfession(expert.profession)} size={28} color="#334155" />
            </View>
            <View style={styles.rowBody}>
              <Text style={styles.profession}>{expert.profession}</Text>
              {expert.name ? <Text style={styles.name}>{expert.name}</Text> : null}
              {price ? (
                <View style={styles.priceRow}>
                  <Ionicons name="cash-outline" size={14} color="#64748b" />
                  <Text style={styles.price}>{price}</Text>
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
    alignItems: 'center',
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
