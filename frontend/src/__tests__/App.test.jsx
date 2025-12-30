import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
    deleteConversation: vi.fn().mockResolvedValue({}),
    duplicateConversation: vi.fn().mockResolvedValue({}),
    markAsRead: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../components/Sidebar', () => ({
  default: ({ onNewConversation, onSelectConversation, onTogglePin, conversations = [] }) => (
    <div>
      <button type="button" onClick={onNewConversation}>
        New Conversation
      </button>
      {conversations.map(c => (
        <div key={c.id}>
          <button onClick={() => onSelectConversation(c.id)}>
            Select {c.title}
          </button>
          <button onClick={() => onTogglePin(c.id, !c.is_pinned)}>
            Pin {c.title}
          </button>
        </div>
      ))}
    </div>
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

  it('marks conversation as read when selected', async () => {
    api.listConversations.mockResolvedValue([
      { id: 'unread-1', title: 'Unread', has_unread: true }
    ]);
    
    render(<App />);
    
    await waitFor(() => {
      expect(screen.getByText('Select Unread')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Select Unread'));
    
    await waitFor(() => {
      expect(api.markAsRead).toHaveBeenCalledWith('unread-1');
    });
  });

  it('marks active conversation as read if it becomes unread in background', async () => {
    // 1. Initial state: Read
    api.listConversations.mockResolvedValue([
      { id: 'conv-1', title: 'Conversation', has_unread: false }
    ]);
    
    render(<App />);
    
    // 2. Select it
    await waitFor(() => {
      expect(screen.getByText('Select Conversation')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Select Conversation'));
    
    // 3. Update mock to return Unread (simulating background update)
    api.listConversations.mockResolvedValue([
      { id: 'conv-1', title: 'Conversation', has_unread: true }
    ]);
    
    // Clear previous calls
    api.markAsRead.mockClear();
    
    // 4. Trigger reload (via Pin)
    fireEvent.click(screen.getByText('Pin Conversation'));
    
    // 5. Expect markAsRead to be called
    await waitFor(() => {
      expect(api.markAsRead).toHaveBeenCalledWith('conv-1');
    });
  });
});
