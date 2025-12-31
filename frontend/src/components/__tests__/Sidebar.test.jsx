import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import Sidebar from '../Sidebar';
import { ThemeProvider } from '../../context/ThemeContext';

const baseProps = {
  conversations: [],
  currentConversationId: null,
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

  it('shows unread indicator for background conversations', () => {
    const conversations = [
      {
        id: 'conv-active',
        title: 'Active',
        created_at: '2024-01-01',
        is_pinned: false,
        is_archived: false,
        message_count: 2,
        has_unread: true,
      },
      {
        id: 'conv-unread',
        title: 'Unread',
        created_at: '2024-01-02',
        is_pinned: false,
        is_archived: false,
        message_count: 1,
        has_unread: true,
      },
    ];

    render(
      <ThemeProvider>
        <Sidebar
          {...baseProps}
          conversations={conversations}
          currentConversationId="conv-active"
        />
      </ThemeProvider>
    );

    expect(screen.queryByLabelText('Unread conversation')).toBeInTheDocument();
    expect(screen.getAllByLabelText('Unread conversation')).toHaveLength(1);
  });

  it('shows pending indicator and suppresses unread', () => {
    const conversations = [
      {
        id: 'conv-pending',
        title: 'Pending',
        created_at: '2024-01-03',
        is_pinned: false,
        is_archived: false,
        message_count: 1,
        has_unread: true,
      },
    ];

    render(
      <ThemeProvider>
        <Sidebar
          {...baseProps}
          conversations={conversations}
          pendingConversationIds={new Set(['conv-pending'])}
        />
      </ThemeProvider>
    );

    expect(screen.getByLabelText('Pending conversation')).toBeInTheDocument();
    expect(screen.queryByLabelText('Unread conversation')).toBeNull();
  });
});
