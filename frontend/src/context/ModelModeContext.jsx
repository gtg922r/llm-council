import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const DEFAULT_MODE = 'smart';
const MODE_STORAGE_KEY = 'llm-council-model-mode';
const VALID_MODES = new Set(['fast', 'smart']);

export const ModelModeContext = createContext(null);

/**
 * Provides model mode state (fast vs smart) for the app.
 * - fast: Uses cheap, fast models (gemini flash lite, haiku, etc.)
 * - smart: Uses capable, top-tier models (gpt-5, claude opus, etc.)
 */
export function ModelModeProvider({ children }) {
  const getStoredMode = () => {
    if (typeof window === 'undefined' || !window.localStorage) {
      return DEFAULT_MODE;
    }
    const stored = window.localStorage.getItem(MODE_STORAGE_KEY);
    return VALID_MODES.has(stored) ? stored : DEFAULT_MODE;
  };

  const [mode, setMode] = useState(getStoredMode);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.localStorage) {
      return;
    }
    window.localStorage.setItem(MODE_STORAGE_KEY, mode);
  }, [mode]);

  const value = useMemo(() => ({ mode, setMode }), [mode]);

  return (
    <ModelModeContext.Provider value={value}>
      {children}
    </ModelModeContext.Provider>
  );
}

/**
 * Access model mode state from the nearest ModelModeProvider.
 */
export function useModelMode() {
  const context = useContext(ModelModeContext);
  if (!context) {
    throw new Error('useModelMode must be used within a ModelModeProvider.');
  }
  return context;
}
