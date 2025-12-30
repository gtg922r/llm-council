import { useContext } from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ThemeContext, ThemeProvider, useTheme } from '../context/ThemeContext';

function ContextProbe() {
  const { theme, resolvedTheme, setTheme } = useContext(ThemeContext);
  return (
    <div>
      <div data-testid="theme">{theme}</div>
      <div data-testid="resolved-theme">{resolvedTheme}</div>
      <button type="button" onClick={() => setTheme('dark')}>
        Set Dark
      </button>
      <button type="button" onClick={() => setTheme('system')}>
        Set System
      </button>
    </div>
  );
}

function HookProbe() {
  const { theme } = useTheme();
  return <div data-testid="hook-theme">{theme}</div>;
}

function mockMatchMedia(matches) {
  let listener = null;
  const mql = {
    matches,
    media: '(prefers-color-scheme: dark)',
    addEventListener: vi.fn((_event, cb) => {
      listener = cb;
    }),
    removeEventListener: vi.fn(),
    addListener: vi.fn((cb) => {
      listener = cb;
    }),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };

  return {
    mql,
    setMatches(nextMatches) {
      mql.matches = nextMatches;
      if (listener) {
        listener({ matches: nextMatches });
      }
    },
  };
}

describe('ThemeContext', () => {
  beforeEach(() => {
    delete window.matchMedia;
    document.documentElement.classList.remove('dark');
    window.localStorage.clear();
  });
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

  it('applies the dark class when the theme is set to dark', () => {
    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Set Dark' }));

    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('exposes theme state via useTheme', () => {
    render(
      <ThemeProvider>
        <HookProbe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('hook-theme')).toHaveTextContent('system');
  });

  it('throws when useTheme is used outside the provider', () => {
    expect(() => render(<HookProbe />)).toThrow(
      'useTheme must be used within a ThemeProvider.'
    );
  });

  it('uses system preference when theme is set to system', () => {
    const { mql } = mockMatchMedia(true);
    window.matchMedia = vi.fn().mockReturnValue(mql);

    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('resolved-theme')).toHaveTextContent('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('reacts to system preference changes', () => {
    const controller = mockMatchMedia(false);
    window.matchMedia = vi.fn().mockReturnValue(controller.mql);

    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('resolved-theme')).toHaveTextContent('light');

    act(() => {
      controller.setMatches(true);
    });

    expect(screen.getByTestId('resolved-theme')).toHaveTextContent('dark');
  });

  it('loads theme preference from localStorage', () => {
    window.localStorage.setItem('llm-council-theme', 'dark');

    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    expect(screen.getByTestId('resolved-theme')).toHaveTextContent('dark');
  });

  it('persists theme changes to localStorage', () => {
    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Set Dark' }));

    expect(window.localStorage.getItem('llm-council-theme')).toBe('dark');
  });

  it('resolves system theme when localStorage is set to system', () => {
    const { mql } = mockMatchMedia(true);
    window.matchMedia = vi.fn().mockReturnValue(mql);
    window.localStorage.setItem('llm-council-theme', 'system');

    render(
      <ThemeProvider>
        <ContextProbe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('system');
    expect(screen.getByTestId('resolved-theme')).toHaveTextContent('dark');
  });
});
