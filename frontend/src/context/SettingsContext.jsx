/**
 * Settings context that syncs user settings with Firestore.
 * Combines theme and model mode settings.
 */
import { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react';
import { doc, getDoc, setDoc, onSnapshot } from 'firebase/firestore';
import { db } from '../firebase';
import { useAuth } from './AuthContext';

const DEFAULT_SETTINGS = {
  theme: 'system',
  modelMode: 'smart'
};

const VALID_THEMES = new Set(['light', 'dark', 'system']);
const VALID_MODES = new Set(['fast', 'smart']);

export const SettingsContext = createContext(null);

/**
 * Provider that syncs settings with Firestore for authenticated users.
 */
export function SettingsProvider({ children }) {
  const { user, isAuthenticated } = useAuth();
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [isLoading, setIsLoading] = useState(true);
  const [systemTheme, setSystemTheme] = useState('light');

  // Track system theme preference
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    setSystemTheme(mediaQuery.matches ? 'dark' : 'light');
    
    const handleChange = (e) => setSystemTheme(e.matches ? 'dark' : 'light');
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Subscribe to settings from Firestore
  useEffect(() => {
    if (!isAuthenticated || !user?.uid) {
      setSettings(DEFAULT_SETTINGS);
      setIsLoading(false);
      return;
    }

    const settingsRef = doc(db, 'users', user.uid);
    
    const unsubscribe = onSnapshot(
      settingsRef,
      (docSnap) => {
        if (docSnap.exists()) {
          const data = docSnap.data();
          setSettings({
            theme: VALID_THEMES.has(data.settings?.theme) ? data.settings.theme : DEFAULT_SETTINGS.theme,
            modelMode: VALID_MODES.has(data.settings?.modelMode) ? data.settings.modelMode : DEFAULT_SETTINGS.modelMode
          });
        } else {
          // Create default settings document
          setDoc(settingsRef, { settings: DEFAULT_SETTINGS }, { merge: true });
          setSettings(DEFAULT_SETTINGS);
        }
        setIsLoading(false);
      },
      (error) => {
        console.error('Error loading settings:', error);
        setSettings(DEFAULT_SETTINGS);
        setIsLoading(false);
      }
    );

    return () => unsubscribe();
  }, [isAuthenticated, user?.uid]);

  // Apply theme to document
  const resolvedTheme = settings.theme === 'system' ? systemTheme : settings.theme;
  
  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.classList.toggle('dark', resolvedTheme === 'dark');
    document.documentElement.dataset.theme = resolvedTheme;
  }, [resolvedTheme]);

  // Update settings in Firestore
  const updateSettings = useCallback(async (updates) => {
    if (!isAuthenticated || !user?.uid) return;
    
    const newSettings = { ...settings, ...updates };
    setSettings(newSettings); // Optimistic update
    
    try {
      const settingsRef = doc(db, 'users', user.uid);
      await setDoc(settingsRef, { settings: newSettings }, { merge: true });
    } catch (error) {
      console.error('Error saving settings:', error);
      // Revert on error
      setSettings(settings);
    }
  }, [isAuthenticated, user?.uid, settings]);

  const setTheme = useCallback((theme) => {
    if (VALID_THEMES.has(theme)) {
      updateSettings({ theme });
    }
  }, [updateSettings]);

  const setModelMode = useCallback((modelMode) => {
    if (VALID_MODES.has(modelMode)) {
      updateSettings({ modelMode });
    }
  }, [updateSettings]);

  const value = useMemo(() => ({
    // Theme
    theme: settings.theme,
    resolvedTheme,
    setTheme,
    // Model mode
    mode: settings.modelMode,
    setMode: setModelMode,
    // Loading state
    isLoading
  }), [settings, resolvedTheme, setTheme, setModelMode, isLoading]);

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

/**
 * Hook to access settings.
 */
export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}

/**
 * Compatibility hook for theme (maps to useSettings).
 */
export function useTheme() {
  const { theme, resolvedTheme, setTheme } = useSettings();
  return { theme, resolvedTheme, setTheme };
}

/**
 * Compatibility hook for model mode (maps to useSettings).
 */
export function useModelMode() {
  const { mode, setMode } = useSettings();
  return { mode, setMode };
}
