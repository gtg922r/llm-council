import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ThemeToggle from '../ThemeToggle';
import { ThemeProvider, useTheme } from '../../context/ThemeContext';

function ThemeProbe() {
  const { theme } = useTheme();
  return <div data-testid="theme">{theme}</div>;
}

describe('ThemeToggle', () => {
  it('defaults to system and toggles to dark', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
        <ThemeProbe />
      </ThemeProvider>
    );

    const systemButton = screen.getByRole('button', { name: /system mode/i });
    const darkButton = screen.getByRole('button', { name: /dark mode/i });

    expect(systemButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('theme')).toHaveTextContent('system');

    fireEvent.click(darkButton);

    expect(darkButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
  });
});
