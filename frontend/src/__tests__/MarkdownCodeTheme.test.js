import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const cssPath = resolve(process.cwd(), 'src', 'index.css');
const css = readFileSync(cssPath, 'utf8');

describe('markdown code theme', () => {
  it('defines code block and inline code variables for light and dark themes', () => {
    expect(css).toContain('--color-code-block-bg:');
    expect(css).toContain('--color-code-block-border:');
    expect(css).toContain('--color-code-inline-bg:');
    expect(css).toContain('--color-code-inline-text:');
    expect(css).toContain('--color-code-inline-border:');

    expect(css).toContain(':root.dark');
    expect(css).toContain('--color-code-block-bg:');
    expect(css).toContain('--color-code-block-border:');
    expect(css).toContain('--color-code-inline-bg:');
    expect(css).toContain('--color-code-inline-text:');
    expect(css).toContain('--color-code-inline-border:');
  });

  it('uses theme variables for markdown code styling', () => {
    expect(css).toContain('background: var(--color-code-block-bg');
    expect(css).toContain('border: 1px solid var(--color-code-block-border');
    expect(css).toContain('background: var(--color-code-inline-bg');
    expect(css).toContain('color: var(--color-code-inline-text');
    expect(css).toContain('border: 1px solid var(--color-code-inline-border');
    expect(css).toContain('.markdown-content pre code');
    expect(css).toContain('border: none');
  });
});
