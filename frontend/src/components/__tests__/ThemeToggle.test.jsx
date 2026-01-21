import { screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ThemeToggle from '../ThemeToggle';
import { renderWithProviders, mockSettingsContext } from '../../test-utils';

describe('ThemeToggle', () => {
  it('renders light, dark, and system controls', () => {
    renderWithProviders(<ThemeToggle />);

    expect(screen.getByRole('button', { name: /light mode/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /dark mode/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /system mode/i })).toBeInTheDocument();
  });

  it('defaults to system and toggles to dark', () => {
    const mockSetTheme = vi.fn();
    const settingsValue = { 
      ...mockSettingsContext, 
      theme: 'system',
      setTheme: mockSetTheme 
    };
    
    renderWithProviders(<ThemeToggle />, { settingsValue });

    const systemButton = screen.getByRole('button', { name: /system mode/i });
    const darkButton = screen.getByRole('button', { name: /dark mode/i });

    expect(systemButton).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(darkButton);

    expect(mockSetTheme).toHaveBeenCalledWith('dark');
  });
});
