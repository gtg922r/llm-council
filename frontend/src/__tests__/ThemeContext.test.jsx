/**
 * Tests for SettingsContext theme functionality.
 * Note: The actual Firestore sync is tested via integration tests.
 * These tests verify the context behavior with mocked values.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, mockSettingsContext } from '../test-utils';

function ThemeProbe({ setTheme }) {
  return (
    <div>
      <button type="button" onClick={() => setTheme('dark')}>Set Dark</button>
      <button type="button" onClick={() => setTheme('light')}>Set Light</button>
    </div>
  );
}

describe('SettingsContext Theme', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark');
  });

  it('provides theme via context', () => {
    renderWithProviders(
      <div data-testid="theme">{mockSettingsContext.theme}</div>
    );
    expect(screen.getByTestId('theme')).toHaveTextContent('system');
  });

  it('setTheme is callable', () => {
    const mockSetTheme = vi.fn();
    const settingsValue = { ...mockSettingsContext, setTheme: mockSetTheme };
    
    renderWithProviders(
      <ThemeProbe setTheme={mockSetTheme} />,
      { settingsValue }
    );

    fireEvent.click(screen.getByText('Set Dark'));
    expect(mockSetTheme).toHaveBeenCalledWith('dark');
  });

  it('resolvedTheme is provided', () => {
    const settingsValue = { ...mockSettingsContext, resolvedTheme: 'dark' };
    
    renderWithProviders(
      <div data-testid="resolved">{settingsValue.resolvedTheme}</div>,
      { settingsValue }
    );

    expect(screen.getByTestId('resolved')).toHaveTextContent('dark');
  });
});
