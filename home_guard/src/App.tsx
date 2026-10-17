import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { KeyboardProvider } from 'react-native-keyboard-controller';
import { registerRootComponent } from 'expo';
import Navigation from './navigation/Navigation';

export default function App() {
  return (
    <KeyboardProvider>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <Navigation />
      </SafeAreaProvider>
    </KeyboardProvider>
  );
}

registerRootComponent(App);
