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
});
