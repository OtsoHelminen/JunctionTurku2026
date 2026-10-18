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
    activeIcon: 'information',
    inactiveIcon: 'information-outline',
  },
  {
    name: 'Check',
    label: 'Check',
    activeIcon: 'check-circle',
    inactiveIcon: 'check-circle-outline',
  },
  {
    name: 'Settings',
    label: 'Settings',
    activeIcon: 'cog',
    inactiveIcon: 'cog-outline',
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
          height: 80 + insets.bottom,
          paddingBottom: insets.bottom,
          backgroundColor: colors.surface,
          borderTopColor: colors.line,
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
    borderTopWidth: 1,
  },
});
