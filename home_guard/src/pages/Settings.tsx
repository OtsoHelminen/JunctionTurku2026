import React from 'react';
import { StyleSheet, Switch, Text, View } from 'react-native';
import { useTheme } from '../theme/ThemeContext';

export default function Settings() {
  const { isDark, toggleTheme, colors } = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text }]}>Settings</Text>
      <View
        style={[styles.settingRow, { backgroundColor: colors.surface, borderColor: colors.border }]}
      >
        <View style={styles.settingText}>
          <Text style={[styles.settingTitle, { color: colors.text }]}>Dark theme</Text>
          <Text style={[styles.subtitle, { color: colors.mutedText }]}>
            Use a dark appearance throughout the app.
          </Text>
        </View>
        <Switch
          value={isDark}
          onValueChange={toggleTheme}
          trackColor={{ false: colors.inputBorder, true: '#2563eb' }}
          thumbColor="#ffffff"
          accessibilityLabel="Dark theme"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 16,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    padding: 16,
    borderRadius: 14,
    borderWidth: 1,
  },
  settingText: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 14,
    marginTop: 4,
  },
});
