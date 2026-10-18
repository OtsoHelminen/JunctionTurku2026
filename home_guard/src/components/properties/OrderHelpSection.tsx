import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { formatPriceRange } from './alert';
import type { ExpertSuggestion } from './alert';
import { FONTS, useTheme } from '../../theme/ThemeContext';

type IconName = React.ComponentProps<typeof MaterialIcons>['name'];

function iconForProfession(profession: string): IconName {
  const value = profession.toLowerCase();
  if (value.includes('roof')) return 'roofing';
  if (value.includes('plumb')) return 'plumbing';
  if (value.includes('chimney') || value.includes('sweep')) return 'local-fire-department';
  if (value.includes('electric')) return 'electrical-services';
  return 'construction';
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
                { backgroundColor: colors.surface, borderColor: colors.line },
              ]}
            >
              <MaterialIcons
                name={iconForProfession(expert.profession)}
                size={30}
                color={colors.text}
              />
            </View>
            <View style={styles.rowBody}>
              <Text style={[styles.profession, { color: colors.text }]}>{expert.profession}</Text>
              {expert.name ? (
                <Text style={[styles.meta, { color: colors.muted }]}>{expert.name}</Text>
              ) : null}
              {price ? <Text style={[styles.meta, { color: colors.muted }]}>{price}</Text> : null}
            </View>
            <MaterialIcons name="chevron-right" size={24} color={colors.muted} />
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: 12,
  },
  heading: {
    fontFamily: FONTS.heading,
    fontSize: 20,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    minHeight: 64,
  },
  iconTile: {
    width: 60,
    height: 60,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowBody: {
    flex: 1,
    gap: 2,
  },
  profession: {
    fontFamily: FONTS.bodyBold,
    fontSize: 18,
  },
  meta: {
    fontFamily: FONTS.body,
    fontSize: 15,
  },
});
