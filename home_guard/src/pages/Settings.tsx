import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import DeveloperTools from '../components/properties/DeveloperTools';
import { FONTS, useTheme } from '../theme/ThemeContext';

export default function Settings() {
  const { isDark, toggleTheme, colors } = useTheme();

  return (
    <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={styles.container}>
      <Text style={[styles.title, { color: colors.text }]} accessibilityRole="header">
        Settings
      </Text>

      {/* The whole card is the tap target */}
      <View style={[styles.cardShell, { borderColor: colors.line }]}>
        <Pressable
          style={[styles.settingRow, { backgroundColor: colors.surface }]}
          onPress={() => toggleTheme(!isDark)}
          android_ripple={{ color: colors.accentSoft }}
          accessibilityRole="switch"
          accessibilityLabel="Dark theme"
          accessibilityState={{ checked: isDark }}
        >
          <View style={styles.settingText}>
            <Text style={[styles.settingTitle, { color: colors.text }]}>Dark theme</Text>
            <Text style={[styles.subtitle, { color: colors.muted }]}>
              Use a dark appearance throughout the app.
            </Text>
          </View>
          <View
            style={[
              styles.track,
              isDark
                ? { backgroundColor: colors.accent, justifyContent: 'flex-end' }
                : { backgroundColor: colors.surface2, borderColor: colors.muted, borderWidth: 2 },
            ]}
          >
            <View
              style={
                isDark
                  ? [styles.thumbOn, { backgroundColor: colors.onAccent }]
                  : [styles.thumbOff, { backgroundColor: colors.muted }]
              }
            />
          </View>
        </Pressable>
      </View>

      <View style={styles.spacer} />
      <DeveloperTools />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    paddingHorizontal: 18,
    paddingTop: 20,
    paddingBottom: 8,
    gap: 14,
  },
  title: {
    fontFamily: FONTS.heading,
    fontSize: 24,
  },
  cardShell: {
    borderRadius: 18,
    borderWidth: 1,
    overflow: 'hidden',
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
  },
  settingText: {
    flex: 1,
    gap: 4,
  },
  settingTitle: {
    fontFamily: FONTS.bodyBold,
    fontSize: 18,
  },
  subtitle: {
    fontFamily: FONTS.body,
    fontSize: 15,
    lineHeight: 20,
  },
  track: {
    width: 56,
    height: 34,
    borderRadius: 17,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  thumbOn: {
    width: 26,
    height: 26,
    borderRadius: 13,
  },
  thumbOff: {
    width: 20,
    height: 20,
    borderRadius: 10,
  },
  // Pushes Developer tools to the bottom when the content is short
  spacer: {
    flexGrow: 1,
  },
});
