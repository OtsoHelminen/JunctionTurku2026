import React, { useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
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
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  if (experts.length === 0) return null;

  const toggleExpanded = (key: string) => {
    setExpandedKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // The alert payload has no contact details yet, so this only confirms the tap
  const contactExpert = (expert: ExpertSuggestion) => {
    Alert.alert(
      `Contact ${expert.name ?? expert.profession}`,
      'Contact requests are not available yet.'
    );
  };

  return (
    <View style={styles.section}>
      <Text style={[styles.heading, { color: colors.text }]}>Order help</Text>
      {experts.map((expert) => {
        const price = formatPriceRange(expert.priceMin, expert.priceMax);
        const isExpanded = expandedKeys.has(expert.key);
        return (
          <View key={expert.key} style={styles.item}>
            <Pressable
              style={styles.row}
              onPress={() => toggleExpanded(expert.key)}
              android_ripple={{ color: colors.accentSoft }}
              accessibilityRole="button"
              accessibilityLabel={expert.profession}
              accessibilityHint={isExpanded ? 'Hide contact options' : 'Show contact options'}
              accessibilityState={{ expanded: isExpanded }}
            >
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
              <MaterialIcons
                name={isExpanded ? 'expand-more' : 'chevron-right'}
                size={24}
                color={colors.muted}
              />
            </Pressable>
            {isExpanded && (
              <Pressable
                style={({ pressed }) => [
                  styles.contactButton,
                  { backgroundColor: colors.accent },
                  pressed && styles.pressed,
                ]}
                onPress={() => contactExpert(expert)}
                accessibilityRole="button"
                accessibilityLabel={`Contact ${expert.name ?? expert.profession} now`}
              >
                <MaterialIcons name="call" size={22} color={colors.onAccent} />
                <Text style={[styles.contactButtonText, { color: colors.onAccent }]}>
                  Contact now
                </Text>
              </Pressable>
            )}
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
  item: {
    gap: 10,
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
  contactButton: {
    height: 52,
    borderRadius: 26,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  pressed: {
    opacity: 0.85,
  },
  contactButtonText: {
    fontFamily: FONTS.bodyBold,
    fontSize: 17,
  },
});
