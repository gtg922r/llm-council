import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';

// Mock Firebase
vi.mock('../firebase', () => ({
  auth: { currentUser: { getIdToken: async () => 'mock-token' } },
  db: {},
  googleProvider: {}
}));

// Mock AuthContext to always return authenticated
vi.mock('../context/AuthContext', () => ({
  AuthProvider: ({ children }) => children,
  useAuth: () => ({
    user: { uid: 'test-user', email: 'test@test.com', displayName: 'Test' },
    authState: 'authenticated',
    isAuthenticated: true,
    isLoading: false,
    error: null,
    signInWithGoogle: vi.fn(),
    signOut: vi.fn(),
    getIdToken: async () => 'mock-token'
  }),
  AuthState: { AUTHENTICATED: 'authenticated', LOADING: 'loading', UNAUTHENTICATED: 'unauthenticated' },
  AuthContext: { Provider: ({ children }) => children }
}));

// Mock SettingsContext
vi.mock('../context/SettingsContext', () => ({
  SettingsProvider: ({ children }) => children,
  useSettings: () => ({
    theme: 'system',
    resolvedTheme: 'light',
    setTheme: vi.fn(),
    mode: 'smart',
    setMode: vi.fn(),
    isLoading: false
  }),
  useTheme: () => ({ theme: 'system', resolvedTheme: 'light', setTheme: vi.fn() }),
  useModelMode: () => ({ mode: 'smart', setMode: vi.fn() }),
  SettingsContext: { Provider: ({ children }) => children }
}));

import App from '../App';

vi.mock('../api', () => ({
  api: {
    listConversations: vi.fn().mockResolvedValue([]),
    createConversation: vi.fn().mockResolvedValue({
      id: 'conv-1',
      created_at: 'now',
      title: 'New Conversation',
      is_pinned: false,
      is_archived: false,
      messages: [],
    }),
    getConversation: vi.fn().mockResolvedValue({
      id: 'conv-1',
      title: 'New Conversation',
      messages: [],
    }),
    sendMessageStream: vi.fn().mockResolvedValue(undefined),
    sendMessage: vi.fn().mockResolvedValue({ stage1: [], stage2: [], stage3: {}, metadata: {} }),
    updateConversation: vi.fn().mockResolvedValue({}),
    deleteConversation: vi.fn().mockResolvedValue({}),
    duplicateConversation: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../components/ChatInterface', () => ({
  default: () => <div>Chat</div>,
}));

describe('App theme provider', () => {
  it('renders the theme toggle without provider errors', async () => {
    const user = userEvent.setup();
    render(<App />);

    const settingsButton = await screen.findByRole('button', { name: /open settings/i });
    await user.click(settingsButton);

    expect(await screen.findByRole('button', { name: /system mode/i })).toBeInTheDocument();
  });
});
