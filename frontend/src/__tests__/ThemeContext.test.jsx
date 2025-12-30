import { useContext } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ThemeContext, ThemeProvider } from '../context/ThemeContext';

function ContextProbe() {
  const { theme, resolvedTheme, setTheme } = useContext(ThemeContext);
  return (
    <div>
      <div data-testid="theme">{theme}</div>
      <div data-testid="resolved-theme">{resolvedTheme}</div>
      <button type="button" onClick={() => setTheme('dark')}>
        Set Dark
      </button>
    </div>
  );
}

describe('ThemeContext', () => {
  it('defaults to system theme', () => {
    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('system');
    expect(screen.getByTestId('resolved-theme')).toHaveTextContent('light');
  });

  it('updates the theme state', () => {
    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Set Dark' }));

    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    expect(screen.getByTestId('resolved-theme')).toHaveTextContent('dark');
  });
});
