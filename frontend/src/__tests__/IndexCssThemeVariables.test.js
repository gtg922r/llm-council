import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const cssPath = resolve(process.cwd(), 'src', 'index.css');

const requiredVariables = [
  '--color-bg',
  '--color-surface',
  '--color-text',
  '--color-muted',
  '--color-border',
  '--color-code-bg',
  '--color-code-text',
  '--color-blockquote-border',
  '--color-blockquote-text',
];

describe('index.css theme variables', () => {
  it('uses CSS variables for core colors', () => {
    const css = readFileSync(cssPath, 'utf8');

    for (const variable of requiredVariables) {
      expect(css).toContain(`var(${variable}`);
    }
  });

  it('defines light mode variable values in :root', () => {
    const css = readFileSync(cssPath, 'utf8');

    expect(css).toContain('--color-bg: #f5f5f5');
    expect(css).toContain('--color-surface: #ffffff');
    expect(css).toContain('--color-text: #333');
    expect(css).toContain('--color-muted: #666');
    expect(css).toContain('--color-border: #e0e0e0');
    expect(css).toContain('--color-code-bg: #f5f5f5');
    expect(css).toContain('--color-code-text: #333');
    expect(css).toContain('--color-blockquote-border: #ddd');
    expect(css).toContain('--color-blockquote-text: #666');
  });
});
