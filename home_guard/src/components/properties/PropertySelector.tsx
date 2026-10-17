import React from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { PropertyEntry } from './types';

interface PropertySelectorProps {
  entries: PropertyEntry[];
  isLoading: boolean;
  selectedId: number | null;
  error: string;
  onSelect: (id: number) => void;
  onAdd: () => void;
}

export default function PropertySelector({
  entries,
  isLoading,
  selectedId,
  error,
  onSelect,
  onAdd,
}: PropertySelectorProps) {
  return (
    <>
      <View style={styles.propertiesHeadingRow}>
        <Text style={styles.propertiesHeading}>Properties</Text>
        {isLoading && <ActivityIndicator size="small" color="#2563eb" />}
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
            <TouchableOpacity
              key={property.id}
              style={styles.propertyItem}
              onPress={() => onSelect(property.id)}
              activeOpacity={0.75}
              accessibilityRole="button"
              accessibilityLabel={property.address}
              accessibilityState={{ selected: isSelected }}
            >
              <View style={[styles.propertyTile, isSelected && styles.propertyTileSelected]}>
                <Ionicons name="home" size={28} color={isSelected ? '#2563eb' : '#64748b'} />
              </View>
              <Text style={styles.propertyAddress} numberOfLines={1}>
                {property.address}
              </Text>
            </TouchableOpacity>
          );
        })}

        <TouchableOpacity
          style={styles.propertyItem}
          onPress={onAdd}
          activeOpacity={0.75}
          accessibilityRole="button"
          accessibilityLabel="Add a property"
        >
          <View style={[styles.propertyTile, styles.addPropertyTile]}>
            <Ionicons name="add" size={30} color="#2563eb" />
          </View>
          <Text style={styles.propertyAddress}>Add property</Text>
        </TouchableOpacity>
      </ScrollView>
      {error ? <Text style={styles.propertyError}>{error}</Text> : null}
    </>
  );
}

const styles = StyleSheet.create({
  propertiesHeadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  propertiesHeading: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0f172a',
  },
  propertyList: {
    gap: 14,
  },
  propertyItem: {
    width: 82,
    alignItems: 'center',
  },
  propertyTile: {
    width: 68,
    height: 68,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  propertyTileSelected: {
    borderColor: '#2563eb',
    backgroundColor: '#eff6ff',
  },
  addPropertyTile: {
    borderStyle: 'dashed',
    borderColor: '#93c5fd',
  },
  propertyAddress: {
    width: '100%',
    marginTop: 6,
    fontSize: 11,
    color: '#475569',
    textAlign: 'center',
  },
  propertyError: {
    marginTop: -14,
    marginBottom: 14,
    color: '#b91c1c',
    fontSize: 13,
  },
});
