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
});
