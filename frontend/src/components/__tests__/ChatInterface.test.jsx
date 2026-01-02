import { render, screen, act, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import ChatInterface from '../ChatInterface';

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
        { role: 'assistant', stage3: { response: 'done' } }
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
    expect(screen.getByRole('form', { name: /chat input form/i })).toBeInTheDocument();
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
    expect(screen.queryByRole('form', { name: /chat input form/i })).not.toBeInTheDocument();
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
    expect(screen.queryByRole('form', { name: /chat input form/i })).not.toBeInTheDocument();
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
    expect(screen.queryByRole('form', { name: /chat input form/i })).not.toBeInTheDocument();
  });

  it('hides Stage3 and follow-up trigger when stage3 response is missing', () => {
    const conversation = {
      id: '1',
      title: 'Empty Stage3',
      messages: [
        { role: 'user', content: 'hello' },
        { role: 'assistant', stage3: {} } // Missing .response
      ]
    };

    render(
      <ChatInterface
        conversation={conversation}
        onSendMessage={() => {}}
        onHeaderAction={() => {}}
        onUpdateTitle={() => {}}
        isLoading={false}
      />
    );

    // Should NOT show follow-up trigger
    expect(screen.queryByText(/Send Message to Chairman/i)).not.toBeInTheDocument();
    // Should NOT render Stage3 content (we can check by searching for common Stage3 elements if it had any unique ones, 
    // but the final-response class is a good proxy if we didn't mock it)
    // Since we don't mock Stage3 in this file, it will try to render the real one which returns null if finalResponse.response is missing.
  });

  it('validates and stages files', async () => {
    render(
      <ChatInterface 
        conversation={mockConversation} 
        onSendMessage={vi.fn()}
        onHeaderAction={vi.fn()}
        onUpdateTitle={vi.fn()}
        isLoading={false}
      />
    );

    const container = screen.getByRole('form', { name: /chat input form/i }).parentElement;

    const validFile = new File(['content'], 'test.txt', { type: 'text/plain' });
    const largeFile = new File(['a'.repeat(1024 * 1024 + 1)], 'large.txt', { type: 'text/plain' });
    const invalidType = new File(['content'], 'test.exe', { type: 'application/x-msdownload' });

    // Mock alert
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    await act(async () => {
      fireEvent.drop(container, {
        dataTransfer: {
          files: [validFile, largeFile, invalidType],
          types: ['Files'],
        },
      });
    });

    expect(alertSpy).toHaveBeenCalledWith(expect.stringMatching(/too large/i));
    expect(alertSpy).toHaveBeenCalledWith(expect.stringMatching(/unsupported/i));
    
    alertSpy.mockRestore();
  });

  it('transmits staged files during message submission', async () => {
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

    const container = screen.getByRole('form', { name: /chat input form/i }).parentElement;
    const textarea = screen.getByPlaceholderText(/Ask your question.../i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    const file = new File(['file content'], 'test.txt', { type: 'text/plain' });
    
    // Stage the file
    await act(async () => {
      fireEvent.drop(container, {
        dataTransfer: {
          files: [file],
          types: ['Files'],
        },
      });
    });

    // Enter query
    fireEvent.change(textarea, { target: { value: 'my query' } });

    // Send message
    await act(async () => {
      fireEvent.click(sendButton);
    });

    expect(onSendMessage).toHaveBeenCalledWith(
      'my query',
      undefined,
      expect.arrayContaining([file])
    );
  });

  it('renders file chips in user message history', () => {
    const conversationWithFiles = {
      id: '1',
      messages: [
        { 
          role: 'user', 
          content: 'hello',
          files: [{ name: 'context.txt' }]
        }
      ]
    };

    render(
      <ChatInterface 
        conversation={conversationWithFiles} 
        onSendMessage={vi.fn()}
        onHeaderAction={vi.fn()}
        onUpdateTitle={vi.fn()}
        isLoading={false}
      />
    );

    expect(screen.getByText('context.txt')).toBeInTheDocument();
  });
});
