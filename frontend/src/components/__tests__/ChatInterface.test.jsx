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

  beforeAll(() => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it('renders correctly with conversation', () => {
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

  it('calls onSendMessage when ChatInput sends a message', () => {
    const onSendMessage = vi.fn();
    render(
      <ChatInterface 
        conversation={mockConversation} 
        onSendMessage={onSendMessage}
        onHeaderAction={vi.fn()}
        onUpdateTitle={vi.fn()}
        isLoading={false}
      />
    );
    
    screen.getByText('Send Test').click();
    expect(onSendMessage).toHaveBeenCalledWith('test message');
  });
});
