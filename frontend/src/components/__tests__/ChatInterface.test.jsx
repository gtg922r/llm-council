import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChatInterface from '../ChatInterface';

// Mock the sub-components to focus on ChatInterface logic
vi.mock('../ChatInput', () => ({
  default: ({ onSendMessage }) => (
    <div data-testid="chat-input">
      <button onClick={() => onSendMessage('test message')}>Send Test</button>
    </div>
  )
}));

describe('ChatInterface', () => {
  const mockConversation = {
    id: '1',
    title: 'Test Conversation',
    messages: []
  };

  const mockConversationWithMessages = {
    id: '1',
    title: 'Test Conversation',
    messages: [
      { role: 'user', content: 'hello' },
      { role: 'assistant', content: 'world', stage3: 'world' }
    ]
  };

  beforeAll(() => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it('renders correctly with new conversation', () => {
    render(
      <ChatInterface 
        conversation={mockConversation} 
        onSendMessage={vi.fn()}
        onHeaderAction={vi.fn()}
        onUpdateTitle={vi.fn()}
        isLoading={false}
      />
    );
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
  });

  it('hides input when loading', () => {
    render(
      <ChatInterface 
        conversation={mockConversation} 
        onSendMessage={vi.fn()}
        onHeaderAction={vi.fn()}
        onUpdateTitle={vi.fn()}
        isLoading={true}
      />
    );
    expect(screen.queryByTestId('chat-input')).not.toBeInTheDocument();
  });

  it('hides input after message is sent (waiting for council)', () => {
    const convWithUserLast = {
      id: '1',
      messages: [{ role: 'user', content: 'hello' }]
    };
    render(
      <ChatInterface 
        conversation={convWithUserLast} 
        onSendMessage={vi.fn()}
        onHeaderAction={vi.fn()}
        onUpdateTitle={vi.fn()}
        isLoading={false}
      />
    );
    expect(screen.queryByTestId('chat-input')).not.toBeInTheDocument();
  });

  it('shows follow-up trigger after council response', () => {
    render(
      <ChatInterface 
        conversation={mockConversationWithMessages} 
        onSendMessage={vi.fn()}
        onHeaderAction={vi.fn()}
        onUpdateTitle={vi.fn()}
        isLoading={false}
      />
    );
    expect(screen.getByText(/Send Message to Chairman/i)).toBeInTheDocument();
    expect(screen.queryByTestId('chat-input')).not.toBeInTheDocument();
  });
});
