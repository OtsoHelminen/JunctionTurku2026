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
import type { RealEstateEntry } from './types';

interface RealEstateSelectorProps {
  entries: RealEstateEntry[];
  isLoading: boolean;
  selectedId: number | null;
  error: string;
  onSelect: (id: number) => void;
  onAdd: () => void;
}

export default function RealEstateSelector({
  entries,
  isLoading,
  selectedId,
  error,
  onSelect,
  onAdd,
}: RealEstateSelectorProps) {
  return (
    <>
      <Text style={styles.realEstatesHeading}>Real estates</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.realEstateList}
        accessibilityLabel="Real estates"
      >
        {isLoading && (
          <View style={styles.realEstateLoading}>
            <ActivityIndicator size="small" color="#2563eb" />
          </View>
        )}
        {entries.map((realEstate) => {
          const isSelected = selectedId === realEstate.id;
          return (
            <TouchableOpacity
              key={realEstate.id}
              style={styles.realEstateItem}
              onPress={() => onSelect(realEstate.id)}
              activeOpacity={0.75}
              accessibilityRole="button"
              accessibilityLabel={realEstate.address}
              accessibilityState={{ selected: isSelected }}
            >
              <View style={[styles.realEstateTile, isSelected && styles.realEstateTileSelected]}>
                <Ionicons name="home" size={28} color={isSelected ? '#2563eb' : '#64748b'} />
              </View>
              <Text style={styles.realEstateAddress} numberOfLines={1}>
                {realEstate.address}
              </Text>
            </TouchableOpacity>
          );
        })}

        <TouchableOpacity
          style={styles.realEstateItem}
          onPress={onAdd}
          activeOpacity={0.75}
          accessibilityRole="button"
          accessibilityLabel="Add a real estate"
        >
          <View style={[styles.realEstateTile, styles.addRealEstateTile]}>
            <Ionicons name="add" size={30} color="#2563eb" />
          </View>
          <Text style={styles.realEstateAddress}>Add real estate</Text>
        </TouchableOpacity>
      </ScrollView>
      {error ? <Text style={styles.realEstateError}>{error}</Text> : null}
    </>
  );
}

const styles = StyleSheet.create({
  realEstatesHeading: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: 12,
  },
  realEstateList: {
    gap: 14,
    paddingBottom: 24,
  },
  realEstateItem: {
    width: 82,
    alignItems: 'center',
  },
  realEstateTile: {
    width: 68,
    height: 68,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  realEstateTileSelected: {
    borderColor: '#2563eb',
    backgroundColor: '#eff6ff',
  },
  addRealEstateTile: {
    borderStyle: 'dashed',
    borderColor: '#93c5fd',
  },
  realEstateAddress: {
    width: '100%',
    marginTop: 6,
    fontSize: 11,
    color: '#475569',
    textAlign: 'center',
  },
  realEstateLoading: {
    width: 68,
    height: 68,
    alignItems: 'center',
    justifyContent: 'center',
  },
  realEstateError: {
    marginTop: -14,
    marginBottom: 14,
    color: '#b91c1c',
    fontSize: 13,
  },
});
