import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChatInput from '../ChatInput';

describe('ChatInput', () => {
  it('renders correctly', () => {
    render(<ChatInput onSendMessage={vi.fn()} />);
    expect(screen.getByPlaceholderText(/Ask your question.../i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('updates input value on change', () => {
    render(<ChatInput onSendMessage={vi.fn()} />);
    const textarea = screen.getByPlaceholderText(/Ask your question.../i);
    fireEvent.change(textarea, { target: { value: 'Hello Council' } });
    expect(textarea.value).toBe('Hello Council');
  });

  it('calls onSendMessage when send button is clicked', () => {
    const onSendMessage = vi.fn();
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByPlaceholderText(/Ask your question.../i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(textarea, { target: { value: 'Hello Council' } });
    fireEvent.click(sendButton);

    expect(onSendMessage).toHaveBeenCalledWith('Hello Council');
    expect(textarea.value).toBe('');
  });

  it('calls onSendMessage when Enter is pressed (without shift)', () => {
    const onSendMessage = vi.fn();
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByPlaceholderText(/Ask your question.../i);

    fireEvent.change(textarea, { target: { value: 'Hello Council' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(onSendMessage).toHaveBeenCalledWith('Hello Council');
    expect(textarea.value).toBe('');
  });

  it('does not call onSendMessage when Shift+Enter is pressed', () => {
    const onSendMessage = vi.fn();
    render(<ChatInput onSendMessage={onSendMessage} />);
    const textarea = screen.getByPlaceholderText(/Ask your question.../i);

    fireEvent.change(textarea, { target: { value: 'Hello Council' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it('toggles expansion when expand button is clicked', () => {
    render(<ChatInput onSendMessage={vi.fn()} />);
    const expandButton = screen.getByRole('button', { name: /expand|collapse/i });
    
    // Initial state (assuming not expanded)
    expect(expandButton).toHaveAttribute('title', 'Expand');
    
    fireEvent.click(expandButton);
    expect(expandButton).toHaveAttribute('title', 'Collapse');
    
    fireEvent.click(expandButton);
    expect(expandButton).toHaveAttribute('title', 'Expand');
  });

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn();
    render(<ChatInput onSendMessage={vi.fn()} onCancel={onCancel} />);
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    
    fireEvent.click(cancelButton);
    expect(onCancel).toHaveBeenCalled();
  });

  it('highlights border on drag over', () => {
    render(<ChatInput onSendMessage={vi.fn()} />);
    const container = screen.getByRole('form').parentElement;
    
    fireEvent.dragOver(container);
    expect(container).toHaveClass('dragging');
    
    fireEvent.dragLeave(container);
    expect(container).not.toHaveClass('dragging');
  });

  it('calls onFilesDropped when files are dropped', () => {
    const onFilesDropped = vi.fn();
    render(<ChatInput onSendMessage={vi.fn()} onFilesDropped={onFilesDropped} />);
    const container = screen.getByRole('form').parentElement;
    
    const file = new File(['hello'], 'hello.txt', { type: 'text/plain' });
    const dragEvent = {
      dataTransfer: {
        files: [file],
        types: ['Files'],
      },
    };
    
    fireEvent.drop(container, dragEvent);
    expect(onFilesDropped).toHaveBeenCalledWith([file]);
    expect(container).not.toHaveClass('dragging');
  });
});
