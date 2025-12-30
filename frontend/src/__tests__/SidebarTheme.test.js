import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const cssPath = resolve(process.cwd(), 'src', 'components', 'Sidebar.css');
const css = readFileSync(cssPath, 'utf8');

describe('sidebar theme accents', () => {
  it('uses theme variables for the active conversation styling', () => {
    expect(css).toContain('.conversation-item.active');
    expect(css).toContain('background: var(--color-accent-soft');
    expect(css).toContain('border: 1px solid var(--color-accent');
  });

  it('uses theme variables for primary and danger actions', () => {
    expect(css).toContain('background: var(--color-accent');
    expect(css).toContain('border: 1px solid var(--color-accent');
    expect(css).toContain('color: var(--color-danger');
  });

  it('evenly spaces the theme toggle inside the settings popover', () => {
    expect(css).toContain('.sidebar-settings-popover .theme-toggle');
    expect(css).toContain('justify-content: space-between');
    expect(css).toContain('width: 100%');
  });
});
