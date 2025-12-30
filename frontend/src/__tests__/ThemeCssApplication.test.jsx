import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ThemeProvider, useTheme } from '../context/ThemeContext';

function ThemeSetter() {
  const { setTheme } = useTheme();
  return (
    <button type="button" onClick={() => setTheme('dark')}>
      Set Dark
    </button>
  );
}

function mockMatchMedia(matches) {
  return {
    matches,
    media: '(prefers-color-scheme: dark)',
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };
}

describe('theme CSS application', () => {
  beforeEach(() => {
    delete window.matchMedia;
    document.documentElement.classList.remove('dark');
    document.documentElement.removeAttribute('data-theme');
  });

  it('sets data-theme on the document element when theme changes', () => {
    render(
      <ThemeProvider>
        <ThemeSetter />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Set Dark' }));

    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('sets data-theme based on system preference when using system theme', () => {
    window.matchMedia = vi.fn().mockReturnValue(mockMatchMedia(true));

    render(
      <ThemeProvider>
        <div />
      </ThemeProvider>
    );

    expect(document.documentElement.dataset.theme).toBe('dark');
  });
});
