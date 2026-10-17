import React, { createContext, useContext, useMemo, useState } from 'react';

export interface ThemeColors {
  background: string;
  surface: string;
  subtleSurface: string;
  text: string;
  secondaryText: string;
  mutedText: string;
  border: string;
  inputBorder: string;
  selectedSurface: string;
}

interface ThemeContextValue {
  isDark: boolean;
  toggleTheme: (isDark: boolean) => void;
  colors: ThemeColors;
}

const LIGHT_COLORS: ThemeColors = {
  background: '#f8fafc',
  surface: '#ffffff',
  subtleSurface: '#f1f5f9',
  text: '#0f172a',
  secondaryText: '#475569',
  mutedText: '#64748b',
  border: '#e2e8f0',
  inputBorder: '#cbd5e1',
  selectedSurface: '#eff6ff',
};

const DARK_COLORS: ThemeColors = {
  background: '#0f172a',
  surface: '#1e293b',
  subtleSurface: '#334155',
  text: '#f8fafc',
  secondaryText: '#cbd5e1',
  mutedText: '#94a3b8',
  border: '#334155',
  inputBorder: '#475569',
  selectedSurface: '#1e3a8a',
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: React.PropsWithChildren) {
  const [isDark, setIsDark] = useState(false);

  const value = useMemo(
    () => ({
      isDark,
      toggleTheme: setIsDark,
      colors: isDark ? DARK_COLORS : LIGHT_COLORS,
    }),
    [isDark]
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
