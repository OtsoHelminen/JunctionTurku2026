import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import TabBar, { TabName } from './TabBar';
import Properties from '../pages/Properties';
import Info from '../pages/Info';
import Check from '../pages/Check';
import Settings from '../pages/Settings';
import Header from '../components/Header';
import { useTheme } from '../theme/ThemeContext';

export default function Navigation() {
  const [activeTab, setActiveTab] = useState<TabName>('Home');
  const { colors } = useTheme();

  const renderPage = () => {
    switch (activeTab) {
      case 'Home':
        return <Properties />;
      case 'Info':
        return <Info />;
      case 'Check':
        return <Check />;
      case 'Settings':
        return <Settings />;
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.bg }]}>
      <Header title={activeTab} />
      <View style={styles.content}>{renderPage()}</View>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
});
