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
  },
}));

vi.mock('../components/Sidebar', () => ({
  default: ({ onNewConversation }) => (
    <button type="button" onClick={onNewConversation}>
      New Conversation
    </button>
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
});
