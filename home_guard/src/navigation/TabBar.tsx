import React from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import TabItem, { IconName } from './TabItem';
import { useTheme } from '../theme/ThemeContext';

export type TabName = 'Home' | 'Info' | 'Check' | 'Settings';

interface TabBarProps {
  activeTab: TabName;
  onTabChange: (tab: TabName) => void;
}

interface TabConfig {
  name: TabName;
  label: string;
  activeIcon: IconName;
  inactiveIcon: IconName;
}

const TABS: TabConfig[] = [
  {
    name: 'Home',
    label: 'Home',
    activeIcon: 'home',
    inactiveIcon: 'home-outline',
  },
  {
    name: 'Info',
    label: 'Info',
    activeIcon: 'information-circle',
    inactiveIcon: 'information-circle-outline',
  },
  {
    name: 'Check',
    label: 'Check',
    activeIcon: 'checkmark-circle',
    inactiveIcon: 'checkmark-circle-outline',
  },
  {
    name: 'Settings',
    label: 'Settings',
    activeIcon: 'settings',
    inactiveIcon: 'settings-outline',
  },
];

export default function TabBar({ activeTab, onTabChange }: TabBarProps) {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();

  return (
    <View
      style={[
        styles.tabBar,
        {
          paddingBottom: Math.max(insets.bottom, 12),
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
        },
      ]}
    >
      {TABS.map((tab) => (
        <TabItem
          key={tab.name}
          label={tab.label}
          activeIcon={tab.activeIcon}
          inactiveIcon={tab.inactiveIcon}
          isActive={activeTab === tab.name}
          onPress={() => onTabChange(tab.name)}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    paddingTop: 8,
  },
});
