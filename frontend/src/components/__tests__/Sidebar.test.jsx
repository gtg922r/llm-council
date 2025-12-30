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

  it('shows a new-message blue dot until the conversation is opened', () => {
    render(
      <ThemeProvider>
        <Sidebar
          {...baseProps}
          currentConversationId="conv-1"
          conversations={[
            {
              id: 'conv-1',
              title: 'Opened',
              is_pinned: false,
              is_archived: false,
              message_count: 1,
              has_new: true,
              is_pending: false,
            },
            {
              id: 'conv-2',
              title: 'Unread',
              is_pinned: false,
              is_archived: false,
              message_count: 2,
              has_new: true,
              is_pending: false,
            },
          ]}
        />
      </ThemeProvider>
    );

    // Active conversations should not show a "new" dot.
    expect(screen.getAllByLabelText(/new messages/i)).toHaveLength(1);
    expect(screen.getByText('Unread')).toBeInTheDocument();
  });

  it('shows a pending indicator while processing (and hides new dot)', () => {
    render(
      <ThemeProvider>
        <Sidebar
          {...baseProps}
          conversations={[
            {
              id: 'conv-3',
              title: 'Running',
              is_pinned: false,
              is_archived: false,
              message_count: 3,
              has_new: true,
              is_pending: true,
            },
          ]}
        />
      </ThemeProvider>
    );

    expect(screen.getByLabelText(/conversation running/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/new messages/i)).toBeNull();
  });
});
