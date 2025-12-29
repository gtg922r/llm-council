import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';
import { api } from '../api';

// Mock the api module
vi.mock('../api', () => ({
  api: {
    listConversations: vi.fn().mockResolvedValue([]),
    createConversation: vi.fn(),
    getConversation: vi.fn(),
    sendMessage: vi.fn(),
    sendMessageStream: vi.fn(),
  },
}));

describe('App - File Transmission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock scrollIntoView which is not available in jsdom
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it('sends structured files when a message is sent with attachments', async () => {
    // 1. Setup mock conversation
    const mockConv = { id: 'conv-123', title: 'Test', messages: [] };
    api.createConversation.mockResolvedValue(mockConv);
    api.getConversation.mockResolvedValue(mockConv);
    api.sendMessageStream.mockResolvedValue();

    render(<App />);

    // 2. Create new conversation
    const newConvBtn = screen.getByRole('button', { name: /new conversation/i });
    fireEvent.click(newConvBtn);
    
    await waitFor(() => expect(api.createConversation).toHaveBeenCalled());

    // 3. Find ChatInput components and simulate file drop/selection
    // Since App doesn't expose internal state easily, we have to interact through DOM
    const textarea = screen.getByPlaceholderText(/Ask your question.../i);
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    // Simulate adding files to ChatInput - this is tricky because we'd need to mock FileReader
    // or use real Files and wait for handleSendMessage to process them.
    
    // Let's mock FileReader globally if needed, or just rely on the implementation 
    // using the real one since it works in jsdom usually if used correctly.
    
    const file = new File(['hello world'], 'hello.txt', { type: 'text/plain' });
    
    // We need to trigger the file selection in ChatInput
    const fileInput = document.querySelector('input[type="file"]');
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    // Verify file chip appears
    expect(await screen.findByText('hello.txt')).toBeInTheDocument();

    // 4. Send message
    fireEvent.change(textarea, { target: { value: 'What is this?' } });
    fireEvent.click(sendButton);

    // 5. Verify api.sendMessageStream was called with structured data
    await waitFor(() => {
      expect(api.sendMessageStream).toHaveBeenCalledWith(
        'conv-123',
        'What is this?',
        expect.any(Function),
        null, // targetModel
        expect.arrayContaining([
          expect.objectContaining({
            name: 'hello.txt',
            content: 'hello world'
          })
        ])
      );
    });
  });
});
