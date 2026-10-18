import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { FONTS, useTheme } from '../theme/ThemeContext';

export type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

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
  const color = isActive ? colors.accentText : colors.muted;

  return (
    <Pressable
      style={styles.tab}
      onPress={onPress}
      android_ripple={{ color: colors.accentSoft, borderless: true }}
      accessibilityRole="tab"
      accessibilityLabel={label}
      accessibilityState={{ selected: isActive }}
    >
      <View style={[styles.pill, isActive && { backgroundColor: colors.accentSoft }]}>
        <MaterialCommunityIcons
          name={isActive ? activeIcon : inactiveIcon}
          size={24}
          color={color}
        />
      </View>
      <Text style={[styles.label, { color, fontFamily: isActive ? FONTS.bodyBold : FONTS.body }]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  pill: {
    width: 60,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: 13,
  },
});
