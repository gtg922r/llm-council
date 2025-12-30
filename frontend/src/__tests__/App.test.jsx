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
      {conversations?.[1] && (
        <button type="button" onClick={() => onSelectConversation(conversations[1].id)}>
          Select Conversation 2
        </button>
      )}
      <div data-testid="pending-count">
        {pendingConversationIds ? pendingConversationIds.size : 0}
      </div>
    </>
  ),
}));

vi.mock('../components/ChatInterface', () => ({
  default: ({ conversation, onSendMessage }) => (
    conversation ? (
      <button
        type="button"
        onClick={() => onSendMessage('hello', undefined, fileToSend ? [fileToSend] : [])}
      >
        Send
      </button>
    ) : null
  ),
}));

import App from '../App';
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
});
