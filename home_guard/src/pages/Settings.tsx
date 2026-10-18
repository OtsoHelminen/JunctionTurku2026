import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import DeveloperTools from '../components/properties/DeveloperTools';
import { FONTS, useTheme } from '../theme/ThemeContext';

function Toggle({ value }: { value: boolean }) {
  const { colors } = useTheme();

  return (
    <View
      style={[
        styles.track,
        value
          ? { backgroundColor: colors.accent, justifyContent: 'flex-end' }
          : { backgroundColor: colors.surface2, borderColor: colors.muted, borderWidth: 2 },
      ]}
    >
      <View
        style={
          value
            ? [styles.thumbOn, { backgroundColor: colors.onAccent }]
            : [styles.thumbOff, { backgroundColor: colors.muted }]
        }
      />
    </View>
  );
}

function SectionHeader({ title }: { title: string }) {
  const { colors } = useTheme();

  return (
    <Text style={[styles.sectionHeader, { color: colors.muted }]} accessibilityRole="header">
      {title}
    </Text>
  );
}

interface ToggleRowProps {
  title: string;
  description: string;
  value: boolean;
  onChange: (value: boolean) => void;
}

// The whole row is the tap target
function ToggleRow({ title, description, value, onChange }: ToggleRowProps) {
  const { colors } = useTheme();

  return (
    <Pressable
      style={styles.settingRow}
      onPress={() => onChange(!value)}
      android_ripple={{ color: colors.accentSoft }}
      accessibilityRole="switch"
      accessibilityLabel={title}
      accessibilityState={{ checked: value }}
    >
      <View style={styles.settingText}>
        <Text style={[styles.settingTitle, { color: colors.text }]}>{title}</Text>
        <Text style={[styles.subtitle, { color: colors.muted }]}>{description}</Text>
      </View>
      <Toggle value={value} />
    </Pressable>
  );
}

export default function Settings() {
  const { isDark, toggleTheme, colors } = useTheme();
  // Mockup only: these switches are not wired to anything yet
  const [criticalAlerts, setCriticalAlerts] = useState(true);
  const [weatherWarnings, setWeatherWarnings] = useState(true);

  const cardStyle = [styles.card, { backgroundColor: colors.surface, borderColor: colors.line }];
  const divider = <View style={[styles.divider, { backgroundColor: colors.line }]} />;

  return (
    <ScrollView style={{ backgroundColor: colors.bg }} contentContainerStyle={styles.container}>
      <SectionHeader title="Appearance" />
      <View style={cardStyle}>
        <ToggleRow
          title="Dark theme"
          description="Use a dark appearance throughout the app."
          value={isDark}
          onChange={toggleTheme}
        />
      </View>

      <SectionHeader title="Alerts" />
      <View style={cardStyle}>
        <ToggleRow
          title="Critical alerts"
          description="Sound and vibrate, even in Do Not Disturb"
          value={criticalAlerts}
          onChange={setCriticalAlerts}
        />
        {divider}
        <ToggleRow
          title="Weather warnings"
          description="Storm, frost and heavy rain"
          value={weatherWarnings}
          onChange={setWeatherWarnings}
        />
      </View>

      <SectionHeader title="General" />
      <View style={cardStyle}>
        {/* Mockup only: not linked to a screen yet */}
        <Pressable
          style={styles.linkRow}
          android_ripple={{ color: colors.accentSoft }}
          accessibilityRole="button"
          accessibilityLabel="Properties"
        >
          <MaterialIcons name="holiday-village" size={26} color={colors.text} />
          <Text style={[styles.linkTitle, { color: colors.text }]}>Properties</Text>
          <MaterialIcons name="chevron-right" size={24} color={colors.muted} />
        </Pressable>
        {divider}
        <DeveloperTools />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 18,
    paddingBottom: 24,
  },
  sectionHeader: {
    fontFamily: FONTS.heading,
    fontSize: 14,
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginTop: 22,
    marginBottom: 10,
    marginLeft: 2,
  },
  card: {
    borderRadius: 18,
    borderWidth: 1,
    overflow: 'hidden',
  },
  divider: {
    height: 1,
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
  linkRow: {
    minHeight: 64,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingHorizontal: 16,
  },
  linkTitle: {
    flex: 1,
    fontFamily: FONTS.body,
    fontSize: 17,
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
});
