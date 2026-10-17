import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { registerRootComponent } from 'expo';
import Navigation from './navigation/Navigation';

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Navigation />
    </SafeAreaProvider>
  );
}

registerRootComponent(App);
