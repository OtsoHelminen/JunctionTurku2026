import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import TabBar, { TabName } from './TabBar';
import Home from '../pages/Home';
import Info from '../pages/Info';
import Check from '../pages/Check';
import Profile from '../pages/Profile';
import Header from '../components/Header';

export default function Navigation() {
  const [activeTab, setActiveTab] = useState<TabName>('Home');

  const renderPage = () => {
    switch (activeTab) {
      case 'Home':
        return <Home />;
      case 'Info':
        return <Info />;
      case 'Check':
        return <Check />;
      case 'Profile':
        return <Profile />;
    }
  };

  return (
    <View style={styles.container}>
      <Header title={activeTab} />
      <View style={styles.content}>{renderPage()}</View>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  content: {
    flex: 1,
  },
});
