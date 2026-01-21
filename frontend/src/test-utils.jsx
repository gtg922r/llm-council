/**
 * Test utilities for rendering components with required providers.
 */
import { render } from '@testing-library/react';
import { AuthContext, AuthState } from './context/AuthContext';
import { SettingsContext } from './context/SettingsContext';

/**
 * Default mock auth context value for tests.
 */
export const mockAuthContext = {
  user: { uid: 'test-user-123', email: 'test@example.com', displayName: 'Test User' },
  authState: AuthState.AUTHENTICATED,
  error: null,
  signInWithGoogle: async () => {},
  signOut: async () => {},
  getIdToken: async () => 'mock-token',
  isAuthenticated: true,
  isLoading: false
};

/**
 * Default mock settings context value for tests.
 */
export const mockSettingsContext = {
  theme: 'system',
  resolvedTheme: 'light',
  setTheme: () => {},
  mode: 'smart',
  setMode: () => {},
  isLoading: false
};

/**
 * Test wrapper that provides all required contexts.
 */
export function TestProviders({ 
  children, 
  authValue = mockAuthContext,
  settingsValue = mockSettingsContext 
}) {
  return (
    <AuthContext.Provider value={authValue}>
      <SettingsContext.Provider value={settingsValue}>
        {children}
      </SettingsContext.Provider>
    </AuthContext.Provider>
  );
}

/**
 * Custom render that wraps components with test providers.
 */
export function renderWithProviders(
  ui,
  {
    authValue = mockAuthContext,
    settingsValue = mockSettingsContext,
    ...renderOptions
  } = {}
) {
  function Wrapper({ children }) {
    return (
      <TestProviders authValue={authValue} settingsValue={settingsValue}>
        {children}
      </TestProviders>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

// Re-export everything from testing-library
export * from '@testing-library/react';
