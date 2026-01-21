import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

let fileToSend = null;

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
    markAsRead: vi.fn().mockResolvedValue({}),
    deleteConversation: vi.fn().mockResolvedValue({}),
    duplicateConversation: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../components/Sidebar', () => ({
  default: ({
    onNewConversation,
    onSelectConversation,
    onDeleteConversation,
    onBulkDelete,
    conversations,
    pendingConversationIds,
  }) => (
    <>
      <button type="button" onClick={onNewConversation}>
        New Conversation
      </button>
      {conversations?.[0] && (
        <button type="button" onClick={() => onSelectConversation(conversations[0].id)}>
          Select Conversation
        </button>
      )}
      {conversations?.[0] && (
        <button type="button" onClick={() => onDeleteConversation(conversations[0].id)}>
          Delete Conversation
        </button>
      )}
      {conversations?.[1] && (
        <button type="button" onClick={() => onSelectConversation(conversations[1].id)}>
          Select Conversation 2
        </button>
      )}
      <button type="button" onClick={onBulkDelete}>
        Empty Trash
      </button>
      <div data-testid="pending-count">
        {pendingConversationIds ? pendingConversationIds.size : 0}
      </div>
    </>
  ),
}));

vi.mock('../components/ChatInterface', () => ({
  default: ({ conversation, onSendMessage }) => {
    if (!conversation) return null;
    const lastMsg = conversation.messages[conversation.messages.length - 1];
    return (
      <div data-testid="chat-interface">
        <h2>{conversation.title}</h2>
        <button
          type="button"
          onClick={() => onSendMessage('hello', undefined, fileToSend ? [fileToSend] : [])}
        >
          Send
        </button>
        {lastMsg && (
          <div data-testid="assistant-state">
            <span data-testid="s1-loading">{String(lastMsg.loading?.stage1)}</span>
            <span data-testid="s2-loading">{String(lastMsg.loading?.stage2)}</span>
            <span data-testid="s3-loading">{String(lastMsg.loading?.stage3)}</span>
          </div>
        )}
      </div>
    );
  },
}));

vi.mock('../components/DeleteConfirmationModal', () => ({
  default: ({ isOpen, onConfirm, onClose, title }) => (
    isOpen ? (
      <div data-testid="delete-modal">
        {title && <span>{title}</span>}
        <button onClick={onConfirm}>Confirm Delete</button>
        <button onClick={onClose}>Cancel</button>
      </div>
    ) : null
  ),
}));

import App from '../App';

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
import { api } from '../api';

describe('App', () => {
  beforeEach(() => {
    fileToSend = new File(['file content'], 'test.txt', { type: 'text/plain' });
    class MockFileReader {
      readAsText() {
        this.onload({ target: { result: 'file content' } });
      }
    }
    vi.stubGlobal('FileReader', MockFileReader);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('opens bulk delete confirmation modal and deletes all archived', async () => {
    api.listConversations.mockResolvedValueOnce([
      {
        id: 'conv-1',
        created_at: 'now',
        title: 'Archived 1',
        is_pinned: false,
        is_archived: true,
        message_count: 0,
        has_unread: false,
      },
      {
        id: 'conv-2',
        created_at: 'later',
        title: 'Archived 2',
        is_pinned: false,
        is_archived: true,
        message_count: 0,
        has_unread: false,
      },
    ]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Empty Trash')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Empty Trash'));

    // Check if modal is open with correct title
    expect(screen.getByTestId('delete-modal')).toBeInTheDocument();
    expect(screen.getByText('Delete All Archived')).toBeInTheDocument();

    // Confirm deletion
    fireEvent.click(screen.getByText('Confirm Delete'));

    await waitFor(() => {
      expect(api.deleteConversation).toHaveBeenCalledWith('conv-1');
      expect(api.deleteConversation).toHaveBeenCalledWith('conv-2');
    });

    // Check if modal is closed
    expect(screen.queryByTestId('delete-modal')).not.toBeInTheDocument();
  });

  it('opens delete confirmation modal and deletes conversation', async () => {
    api.listConversations.mockResolvedValueOnce([
      {
        id: 'conv-1',
        created_at: 'now',
        title: 'Delete Me',
        is_pinned: false,
        is_archived: false,
        message_count: 0,
        has_unread: false,
      },
    ]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Delete Conversation')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Delete Conversation'));

    // Check if modal is open
    expect(screen.getByTestId('delete-modal')).toBeInTheDocument();

    // Confirm deletion
    fireEvent.click(screen.getByText('Confirm Delete'));

    await waitFor(() => {
      expect(api.deleteConversation).toHaveBeenCalledWith('conv-1');
    });

    // Check if modal is closed
    expect(screen.queryByTestId('delete-modal')).not.toBeInTheDocument();
  });

  it('passes file contents to the API when sending messages', async () => {
    render(<App />);

    fireEvent.click(screen.getByText('New Conversation'));

    await waitFor(() => {
      expect(screen.getByText('Send')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(api.sendMessageStream).toHaveBeenCalled();
    });

    const [conversationId, content, files] = api.sendMessageStream.mock.calls[0];
    expect(conversationId).toBe('conv-1');
    expect(content).toBe('hello');
    expect(files).toEqual([
      { name: 'test.txt', content: 'file content', size: fileToSend.size },
    ]);
  });

  it('marks a conversation as read when selected', async () => {
    api.listConversations.mockResolvedValueOnce([
      {
        id: 'conv-1',
        created_at: 'now',
        title: 'Unread',
        is_pinned: false,
        is_archived: false,
        message_count: 1,
        has_unread: true,
      },
    ]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Select Conversation')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Select Conversation'));

    await waitFor(() => {
      expect(api.markAsRead).toHaveBeenCalledWith('conv-1');
    });
  });

  it('clears unread when the active conversation finishes a response', async () => {
    api.sendMessageStream.mockImplementationOnce(async (_id, _content, _files, onEvent) => {
      onEvent('complete', { type: 'complete' });
    });

    render(<App />);

    fireEvent.click(screen.getByText('New Conversation'));

    await waitFor(() => {
      expect(screen.getByText('Send')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(api.markAsRead).toHaveBeenCalledWith('conv-1');
    });
  });

  it('tracks pending conversations during streaming', async () => {
    let triggerComplete;
    api.sendMessageStream.mockImplementationOnce(async (_id, _content, _files, onEvent) => {
      triggerComplete = () => onEvent('complete', { type: 'complete' });
    });

    render(<App />);

    fireEvent.click(screen.getByText('New Conversation'));

    await waitFor(() => {
      expect(screen.getByText('Send')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByTestId('pending-count').textContent).toBe('1');
    });

    await act(async () => {
      triggerComplete();
    });

    await waitFor(() => {
      expect(screen.getByTestId('pending-count').textContent).toBe('0');
    });
  });

  it('does not clear unread if the user switches conversations before completion', async () => {
    api.listConversations.mockResolvedValue([
      {
        id: 'conv-1',
        created_at: 'now',
        title: 'First',
        is_pinned: false,
        is_archived: false,
        message_count: 1,
        has_unread: false,
      },
      {
        id: 'conv-2',
        created_at: 'later',
        title: 'Second',
        is_pinned: false,
        is_archived: false,
        message_count: 1,
        has_unread: false,
      },
    ]);

    let triggerComplete;
    api.sendMessageStream.mockImplementationOnce(async (_id, _content, _files, onEvent) => {
      triggerComplete = () => onEvent('complete', { type: 'complete' });
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Select Conversation')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Select Conversation'));

    await waitFor(() => {
      expect(screen.getByText('Send')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(api.sendMessageStream).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText('Select Conversation 2'));
    const callsBeforeComplete = api.markAsRead.mock.calls.length;

    await act(async () => {
      triggerComplete();
    });

    const markAsReadCalls = api.markAsRead.mock.calls.map(([id]) => id);
    expect(markAsReadCalls).toContain('conv-2');
    expect(api.markAsRead).toHaveBeenCalledTimes(callsBeforeComplete);
  });

  it('correctly handles the full sequence of stage events', async () => {
    let triggerEvent;
    api.sendMessageStream.mockImplementationOnce(async (_id, _content, _files, onEvent) => {
      triggerEvent = (type, data) => onEvent(type, data);
    });

    render(<App />);

    fireEvent.click(screen.getByText('New Conversation'));
    await waitFor(() => expect(screen.getByText('Send')).toBeInTheDocument());
    
    // We need to trigger the send to initialize the mock implementation
    await act(async () => {
      fireEvent.click(screen.getByText('Send'));
    });

    // 1. Stage 1 Start
    await act(async () => {
      triggerEvent('stage_start', { type: 'stage_start', stage: 1, total: 3 });
    });
    expect(screen.getByTestId('s1-loading').textContent).toBe('true');

    // 2. Stage 1 Complete
    await act(async () => {
      triggerEvent('stage_complete', { type: 'stage_complete', stage: 1, data: [] });
    });
    expect(screen.getByTestId('s1-loading').textContent).toBe('false');

    // 3. Stage 2 Start
    await act(async () => {
      triggerEvent('stage_start', { type: 'stage_start', stage: 2, total: 3 });
    });
    expect(screen.getByTestId('s2-loading').textContent).toBe('true');

    // 4. Stage 3 Start (skipping stage 2 complete to test resilience)
    await act(async () => {
      triggerEvent('stage_start', { type: 'stage_start', stage: 3 });
    });
    expect(screen.getByTestId('s2-loading').textContent).toBe('false');
    expect(screen.getByTestId('s3-loading').textContent).toBe('true');

    // 5. Stage 3 Complete
    await act(async () => {
      triggerEvent('stage_complete', { type: 'stage_complete', stage: 3, data: { response: 'done' } });
    });
    expect(screen.getByTestId('s3-loading').textContent).toBe('false');

    // 6. Final Complete
    await act(async () => {
      triggerEvent('complete', { type: 'complete' });
    });
  });

  it('re-detects the correct loading stage when re-selecting a pending conversation', async () => {
    // 1. Setup mock list with 2 items BEFORE render
    api.listConversations.mockResolvedValue([
      { id: 'conv-1', title: 'Pending' },
      { id: 'conv-2', title: 'Other' }
    ]);

    // 2. Setup getConversation mock
    api.getConversation.mockImplementation(async (id) => {
      if (id === 'conv-1') {
        return {
          id: 'conv-1',
          title: 'Pending Conv',
          messages: [
            { role: 'user', content: 'hello' },
            { 
              role: 'assistant', 
              stage1: [{ model: 'm1', response: 'r1', status: 'success' }],
              stage2: [],
              stage3: {}
            }
          ],
        };
      }
      return { id: 'conv-2', title: 'Other', messages: [] };
    });

    render(<App />);

    // 3. Select conv-1 and make it pending
    await waitFor(() => expect(screen.getByText('Select Conversation')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Select Conversation'));
    
    await waitFor(() => expect(screen.getByText('Send')).toBeInTheDocument());
    
    // Trigger send to make it pending locally
    await act(async () => {
      fireEvent.click(screen.getByText('Send'));
    });
    expect(screen.getByTestId('pending-count').textContent).toBe('1');

    // 4. Switch away to conv-2
    await act(async () => {
      fireEvent.click(screen.getByText('Select Conversation 2'));
    });
    // Wait for the Other conversation to appear
    await waitFor(() => expect(screen.getByText('Other')).toBeInTheDocument());
    
    // 5. Switch back to conv-1
    await act(async () => {
      fireEvent.click(screen.getByText('Select Conversation'));
    });

    // 6. Verify loading state: Stage 1 should be FALSE (done), Stage 2 should be TRUE (loading)
    await waitFor(() => {
      const s1 = screen.getByTestId('s1-loading');
      const s2 = screen.getByTestId('s2-loading');
      expect(s1.textContent).toBe('false');
      expect(s2.textContent).toBe('true');
    }, { timeout: 2000 });
  });
});
