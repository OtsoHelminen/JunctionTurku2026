import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { KeyboardProvider } from 'react-native-keyboard-controller';
import { registerRootComponent } from 'expo';
import Navigation from './navigation/Navigation';
import { ThemeProvider, useTheme } from './theme/ThemeContext';
import { View } from 'react-native';

function ThemedApp() {
  const { isDark, isReady, colors } = useTheme();

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      {isReady ? <Navigation /> : null}
    </View>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <KeyboardProvider>
        <SafeAreaProvider>
          <ThemedApp />
        </SafeAreaProvider>
      </KeyboardProvider>
    </ThemeProvider>
  );
}

registerRootComponent(App);
