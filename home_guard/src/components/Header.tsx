import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { FONTS, useTheme } from '../theme/ThemeContext';

interface HeaderProps {
  title: string;
}

export default function Header({ title }: HeaderProps) {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();

  return (
    <View style={{ paddingTop: insets.top, backgroundColor: colors.header }}>
      <View style={styles.bar}>
        <Image
          source={require('../../assets/images/homeguard-logo.png')}
          style={styles.logo}
          accessibilityIgnoresInvertColors
        />
        <Text style={[styles.title, { color: colors.onHeader }]} accessibilityRole="header">
          {title}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    height: 60,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 18,
  },
  logo: {
    width: 30,
    height: 30,
    borderRadius: 15,
  },
  title: {
    fontFamily: FONTS.heading,
    fontSize: 24,
  },
});
