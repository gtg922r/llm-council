import { render, screen } from '@testing-library/react';
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
  it('renders the theme toggle controls', () => {
    render(
      <ThemeProvider>
        <Sidebar {...baseProps} />
      </ThemeProvider>
    );

    expect(screen.getByRole('button', { name: /system mode/i })).toBeInTheDocument();
  });
});
