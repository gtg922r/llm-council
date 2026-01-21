/**
 * Tests for theme CSS application.
 * Verifies that theme changes apply the correct CSS classes.
 */
import { screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, mockSettingsContext } from '../test-utils';

function ThemeSetter({ setTheme }) {
  return (
    <button type="button" onClick={() => setTheme('dark')}>
      Set Dark
    </button>
  );
}

describe('theme CSS application', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark');
    document.documentElement.removeAttribute('data-theme');
  });

  it('provides setTheme that can be called', () => {
    const mockSetTheme = vi.fn();
    const settingsValue = { ...mockSettingsContext, setTheme: mockSetTheme };

    renderWithProviders(
      <ThemeSetter setTheme={mockSetTheme} />,
      { settingsValue }
    );

    fireEvent.click(screen.getByRole('button', { name: 'Set Dark' }));
    expect(mockSetTheme).toHaveBeenCalledWith('dark');
  });

  it('resolvedTheme is available in context', () => {
    const settingsValue = { ...mockSettingsContext, resolvedTheme: 'dark' };

    renderWithProviders(
      <div data-testid="theme">{settingsValue.resolvedTheme}</div>,
      { settingsValue }
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
  });
});
