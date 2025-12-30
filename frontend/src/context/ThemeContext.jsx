import { createContext, useContext, useMemo, useState } from 'react';

const DEFAULT_THEME = 'system';

export const ThemeContext = createContext(null);

/**
 * Provides theme state and setters for the app.
 */
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(DEFAULT_THEME);
  const resolvedTheme = theme === 'system' ? 'light' : theme;

  const value = useMemo(() => ({ theme, resolvedTheme, setTheme }), [theme, resolvedTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/**
 * Access theme state from the nearest ThemeProvider.
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider.');
  }
  return context;
}
