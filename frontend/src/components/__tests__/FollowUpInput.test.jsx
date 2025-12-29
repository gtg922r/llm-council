import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FollowUpInput from '../FollowUpInput';

// Mock ChatInput to focus on FollowUpInput logic
vi.mock('../ChatInput', () => ({
  default: ({ onSendMessage, onCancel, placeholder }) => (
    <div data-testid="chat-input">
      <span>{placeholder}</span>
      <button onClick={() => onSendMessage('follow up message')}>Send</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  )
}));

describe('FollowUpInput', () => {
  it('renders trigger button initially', () => {
    render(<FollowUpInput onSendFollowUp={vi.fn()} isLoading={false} />);
    expect(screen.getByRole('button', { name: /Send Message to Chairman/i })).toBeInTheDocument();
    expect(screen.queryByTestId('chat-input')).not.toBeInTheDocument();
  });

  it('shows ChatInput when trigger button is clicked', () => {
    render(<FollowUpInput onSendFollowUp={vi.fn()} isLoading={false} />);
    fireEvent.click(screen.getByRole('button', { name: /Send Message to Chairman/i }));
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    expect(screen.getByText('Follow up with the Chairman...')).toBeInTheDocument();
  });

  it('calls onSendFollowUp and hides input when Send is clicked', () => {
    const onSendFollowUp = vi.fn();
    render(<FollowUpInput onSendFollowUp={onSendFollowUp} isLoading={false} />);
    
    fireEvent.click(screen.getByRole('button', { name: /Send Message to Chairman/i }));
    fireEvent.click(screen.getByText('Send'));
    
    expect(onSendFollowUp).toHaveBeenCalledWith('follow up message');
    expect(screen.queryByTestId('chat-input')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send Message to Chairman/i })).toBeInTheDocument();
  });

  it('hides input when Cancel is clicked', () => {
    render(<FollowUpInput onSendFollowUp={vi.fn()} isLoading={false} />);
    
    fireEvent.click(screen.getByRole('button', { name: /Send Message to Chairman/i }));
    fireEvent.click(screen.getByText('Cancel'));
    
    expect(screen.queryByTestId('chat-input')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send Message to Chairman/i })).toBeInTheDocument();
  });
});
