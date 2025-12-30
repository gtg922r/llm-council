import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import Sidebar from '../Sidebar';
import { ThemeProvider } from '../../context/ThemeContext';

const baseProps = {
  conversations: [],
  currentConversationId: null,
  loadingConversationId: null,
  onSelectConversation: vi.fn(),
  onNewConversation: vi.fn(),
  onTogglePin: vi.fn(),
  onToggleArchive: vi.fn(),
  onDeleteConversation: vi.fn(),
  onBulkDelete: vi.fn(),
};

describe('Sidebar', () => {
  it('renders the settings button and reveals the theme toggle', async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <Sidebar {...baseProps} />
      </ThemeProvider>
    );

    expect(screen.getByRole('button', { name: /open settings/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /system mode/i })).toBeNull();

    await user.click(screen.getByRole('button', { name: /open settings/i }));

    expect(screen.getByRole('button', { name: /system mode/i })).toBeInTheDocument();
  });

  it('shows pending indicator for loading conversation', () => {
    const conversations = [
      { id: '1', title: 'Test Conv', is_pinned: false, is_archived: false, has_unread: false, message_count: 2 },
    ];
    render(
      <ThemeProvider>
        <Sidebar {...baseProps} conversations={conversations} loadingConversationId="1" />
      </ThemeProvider>
    );

    const pendingIndicator = document.querySelector('.indicator-pending');
    expect(pendingIndicator).toBeInTheDocument();
    expect(pendingIndicator).toHaveAttribute('title', 'Processing...');
  });

  it('shows unread indicator for conversation with unread messages', () => {
    const conversations = [
      { id: '1', title: 'Test Conv', is_pinned: false, is_archived: false, has_unread: true, message_count: 2 },
    ];
    render(
      <ThemeProvider>
        <Sidebar {...baseProps} conversations={conversations} currentConversationId="2" />
      </ThemeProvider>
    );

    const unreadIndicator = document.querySelector('.indicator-unread');
    expect(unreadIndicator).toBeInTheDocument();
    expect(unreadIndicator).toHaveAttribute('title', 'New message');
  });

  it('does not show unread indicator for current conversation', () => {
    const conversations = [
      { id: '1', title: 'Test Conv', is_pinned: false, is_archived: false, has_unread: true, message_count: 2 },
    ];
    render(
      <ThemeProvider>
        <Sidebar {...baseProps} conversations={conversations} currentConversationId="1" />
      </ThemeProvider>
    );

    const unreadIndicator = document.querySelector('.indicator-unread');
    expect(unreadIndicator).not.toBeInTheDocument();
  });

  it('shows pending indicator instead of unread when loading', () => {
    const conversations = [
      { id: '1', title: 'Test Conv', is_pinned: false, is_archived: false, has_unread: true, message_count: 2 },
    ];
    render(
      <ThemeProvider>
        <Sidebar {...baseProps} conversations={conversations} loadingConversationId="1" />
      </ThemeProvider>
    );

    expect(document.querySelector('.indicator-pending')).toBeInTheDocument();
    expect(document.querySelector('.indicator-unread')).not.toBeInTheDocument();
  });
});
