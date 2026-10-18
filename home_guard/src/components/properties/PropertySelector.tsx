import React from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import type { PropertyEntry } from './types';
import { FONTS, useTheme } from '../../theme/ThemeContext';

interface PropertySelectorProps {
  entries: PropertyEntry[];
  isLoading: boolean;
  selectedId: number | null;
  error: string;
  onSelect: (id: number) => void;
  onAdd: () => void;
  onRetry: () => void;
}

export default function PropertySelector({
  entries,
  isLoading,
  selectedId,
  error,
  onSelect,
  onAdd,
  onRetry,
}: PropertySelectorProps) {
  const { colors } = useTheme();

  return (
    <View style={styles.section}>
      <View style={styles.headingRow}>
        <Text style={[styles.heading, { color: colors.text }]}>Properties</Text>
        {isLoading && <ActivityIndicator size="small" color={colors.accentText} />}
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.propertyList}
        accessibilityLabel="Properties"
      >
        {entries.map((property) => {
          const isSelected = selectedId === property.id;
          return (
            <Pressable
              key={property.id}
              style={styles.propertyItem}
              onPress={() => onSelect(property.id)}
              accessibilityRole="button"
              accessibilityLabel={property.address}
              accessibilityState={{ selected: isSelected }}
            >
              <View
                style={[
                  styles.propertyTile,
                  { backgroundColor: colors.surface, borderColor: colors.line },
                  isSelected && { borderColor: colors.accent, borderWidth: 2 },
                ]}
              >
                <MaterialIcons
                  name="home"
                  size={34}
                  color={isSelected ? colors.accentText : colors.muted}
                />
              </View>
              <Text
                style={[
                  styles.propertyLabel,
                  { color: colors.text, fontFamily: isSelected ? FONTS.bodyBold : FONTS.body },
                ]}
                numberOfLines={1}
              >
                {property.address}
              </Text>
            </Pressable>
          );
        })}

        <Pressable
          style={styles.propertyItem}
          onPress={onAdd}
          accessibilityRole="button"
          accessibilityLabel="Add a property"
        >
          <View
            style={[
              styles.propertyTile,
              styles.addPropertyTile,
              { borderColor: colors.accentText },
            ]}
          >
            <MaterialIcons name="add" size={36} color={colors.accentText} />
          </View>
          <Text style={[styles.propertyLabel, { color: colors.muted }]}>Add property</Text>
        </Pressable>
      </ScrollView>
      {error ? (
        <View style={styles.errorRow}>
          <MaterialIcons name="error" size={20} color={colors.error} />
          <View style={styles.errorBody}>
            <Text style={[styles.errorText, { color: colors.error }]}>{error}</Text>
            {!isLoading && (
              <Pressable
                style={styles.retryButton}
                onPress={onRetry}
                android_ripple={{ color: colors.accentSoft, borderless: true }}
                accessibilityRole="button"
                accessibilityLabel="Try loading properties again"
              >
                <Text style={[styles.retryText, { color: colors.accentText }]}>Try again</Text>
              </Pressable>
            )}
          </View>
        </View>
      ) : null}
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
    gap: 8,
  },
  heading: {
    fontFamily: FONTS.heading,
    fontSize: 20,
  },
  propertyList: {
    gap: 12,
  },
  propertyItem: {
    width: 112,
    alignItems: 'center',
    gap: 6,
  },
  propertyTile: {
    width: 112,
    height: 96,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addPropertyTile: {
    borderWidth: 2,
    borderStyle: 'dashed',
  },
  propertyLabel: {
    width: '100%',
    fontFamily: FONTS.body,
    fontSize: 15,
    textAlign: 'center',
  },
  errorRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  errorBody: {
    flex: 1,
    alignItems: 'flex-start',
  },
  retryButton: {
    minHeight: 48,
    justifyContent: 'center',
  },
  retryText: {
    fontFamily: FONTS.bodyBold,
    fontSize: 15,
  },
  errorText: {
    fontFamily: FONTS.body,
    fontSize: 14,
    lineHeight: 19,
  },
});
