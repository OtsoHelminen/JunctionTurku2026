import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { KeyboardProvider } from 'react-native-keyboard-controller';
import { registerRootComponent } from 'expo';
import { useFonts } from 'expo-font';
import { SpaceGrotesk_700Bold } from '@expo-google-fonts/space-grotesk';
import {
  AtkinsonHyperlegible_400Regular,
  AtkinsonHyperlegible_700Bold,
} from '@expo-google-fonts/atkinson-hyperlegible';
import Navigation from './navigation/Navigation';
import { ThemeProvider, useTheme } from './theme/ThemeContext';
import { View } from 'react-native';

function ThemedApp() {
  const { isReady, colors } = useTheme();

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      {/* The status bar sits on the dark header in both themes */}
      <StatusBar style="light" />
      {isReady ? <Navigation /> : null}
    </View>
  );
}

export default function App() {
  const [fontsLoaded, fontError] = useFonts({
    SpaceGrotesk_700Bold,
    AtkinsonHyperlegible_400Regular,
    AtkinsonHyperlegible_700Bold,
  });

  // Fall back to system fonts if loading fails instead of blocking the app
  if (!fontsLoaded && !fontError) return null;

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
