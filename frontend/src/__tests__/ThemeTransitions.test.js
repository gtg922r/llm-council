import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('theme transitions', () => {
  it('defines global color transitions for theme switching', () => {
    const css = readFileSync(resolve(process.cwd(), 'src', 'index.css'), 'utf8');

    expect(css).toContain('transition: background-color 0.3s ease');
    expect(css).toContain('color 0.3s ease');
    expect(css).toContain('border-color 0.3s ease');
  });
});
