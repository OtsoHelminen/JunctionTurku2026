import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export interface ThemeColors {
  /** Screen background */
  bg: string;
  /** Cards, bottom nav, dialog */
  surface: string;
  /** Secondary button, map bg, toggle-off track */
  surface2: string;
  /** 1px borders and dividers */
  line: string;
  text: string;
  /** Secondary text, inactive tabs */
  muted: string;
  /** Primary button fill, focused input border, toggle-on */
  accent: string;
  onAccent: string;
  /** Accent icons and text, active tab */
  accentText: string;
  /** Active tab pill, pressed ripple */
  accentSoft: string;
  /** Top app bar and status bar */
  header: string;
  onHeader: string;
  error: string;
  scrim: string;
}

interface ThemeContextValue {
  isDark: boolean;
  isReady: boolean;
  toggleTheme: (isDark: boolean) => void;
  colors: ThemeColors;
}

const THEME_STORAGE_KEY = 'home-guard-theme';

const LIGHT_COLORS: ThemeColors = {
  bg: '#F4F7F7',
  surface: '#FFFFFF',
  surface2: '#E8EEEF',
  line: '#CBD6D8',
  text: '#0A1517',
  muted: '#43555A',
  accent: '#00726B',
  onAccent: '#FFFFFF',
  accentText: '#00655F',
  accentSoft: 'rgba(0,114,107,0.12)',
  header: '#00302D',
  onHeader: '#FFFFFF',
  error: '#C4281C',
  scrim: 'rgba(0,0,0,0.55)',
};

const DARK_COLORS: ThemeColors = {
  bg: '#060A0D',
  surface: '#0F171B',
  surface2: '#18242A',
  line: '#26363D',
  text: '#F1F6F7',
  muted: '#A9B8BD',
  accent: '#2CEBDD',
  onAccent: '#00211F',
  accentText: '#2CEBDD',
  accentSoft: 'rgba(44,235,221,0.14)',
  header: '#000000',
  onHeader: '#2CEBDD',
  error: '#FF7A6B',
  scrim: 'rgba(0,0,0,0.55)',
};

/** Font family names as registered with useFonts in App.tsx. */
export const FONTS = {
  heading: 'SpaceGrotesk_700Bold',
  body: 'AtkinsonHyperlegible_400Regular',
  bodyBold: 'AtkinsonHyperlegible_700Bold',
} as const;

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: React.PropsWithChildren) {
  const [isDark, setIsDark] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isActive = true;
    const loadTheme = async () => {
      try {
        const savedTheme = await AsyncStorage.getItem(THEME_STORAGE_KEY);
        if (isActive && savedTheme !== null) {
          setIsDark(savedTheme === 'dark');
        }
      } catch (error: unknown) {
        console.error('Failed to load saved theme preference:', error);
      } finally {
        if (isActive) setIsReady(true);
      }
    };

    void loadTheme();
    return () => {
      isActive = false;
    };
  }, []);

  const toggleTheme = useCallback((dark: boolean) => {
    setIsDark(dark);
    void AsyncStorage.setItem(THEME_STORAGE_KEY, dark ? 'dark' : 'light').catch(
      (error: unknown) => {
        console.error('Failed to save theme preference:', error);
      }
    );
  }, []);

  const value = useMemo(
    () => ({
      isDark,
      isReady,
      toggleTheme,
      colors: isDark ? DARK_COLORS : LIGHT_COLORS,
    }),
    [isDark, isReady, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider.');
  }
  return context;
}
