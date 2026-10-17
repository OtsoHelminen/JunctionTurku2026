import React from 'react';
import { StyleSheet, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeContext';

export type IconName = keyof typeof Ionicons.glyphMap;

interface TabItemProps {
  label: string;
  activeIcon: IconName;
  inactiveIcon: IconName;
  isActive: boolean;
  onPress: () => void;
}

export default function TabItem({
  label,
  activeIcon,
  inactiveIcon,
  isActive,
  onPress,
}: TabItemProps) {
  const { colors } = useTheme();
  const iconColor = isActive ? '#2563eb' : colors.mutedText;
  const iconName = isActive ? activeIcon : inactiveIcon;

  return (
    <TouchableOpacity
      style={styles.tab}
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityState={{ selected: isActive }}
    >
      <Ionicons name={iconName} size={22} color={iconColor} style={styles.icon} />
      <Text style={[styles.label, { color: colors.mutedText }, isActive && styles.activeLabel]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
  },
  icon: {
    marginBottom: 4,
  },
  label: {
    fontSize: 12,
    fontWeight: '500',
    color: '#64748b',
  },
  activeLabel: {
    color: '#2563eb',
    fontWeight: '700',
  },
});
