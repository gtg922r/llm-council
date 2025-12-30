import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const indexCssPath = resolve(process.cwd(), 'src', 'index.css');
const chatInputCssPath = resolve(process.cwd(), 'src', 'components', 'ChatInput.css');

const indexCss = readFileSync(indexCssPath, 'utf8');
const chatInputCss = readFileSync(chatInputCssPath, 'utf8');

describe('file upload theming', () => {
  it('defines accent and danger variables for light and dark modes', () => {
    expect(indexCss).toContain('--color-accent: #4a90e2');
    expect(indexCss).toContain('--color-accent-strong: #357abd');
    expect(indexCss).toContain('--color-accent-soft: rgba(74, 144, 226, 0.12)');
    expect(indexCss).toContain('--color-danger: #d93025');
    expect(indexCss).toContain('--color-danger-soft: rgba(217, 48, 37, 0.12)');

    expect(indexCss).toContain(':root.dark');
    expect(indexCss).toContain('--color-accent: #6aa8ff');
    expect(indexCss).toContain('--color-accent-strong: #4a90e2');
    expect(indexCss).toContain('--color-accent-soft: rgba(106, 168, 255, 0.2)');
    expect(indexCss).toContain('--color-danger: #ff6b61');
    expect(indexCss).toContain('--color-danger-soft: rgba(255, 107, 97, 0.18)');
  });

  it('uses theme variables for file upload UI accents', () => {
    expect(chatInputCss).toContain('var(--color-accent');
    expect(chatInputCss).toContain('var(--color-accent-soft');
    expect(chatInputCss).toContain('var(--color-danger');
    expect(chatInputCss).toContain('var(--color-elevation-2');
  });
});
