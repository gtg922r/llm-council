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

  it('styles unread and pending indicators with theme colors and animation', () => {
    expect(css).toContain('.conversation-unread-dot');
    expect(css).toContain('background: var(--color-accent');
    expect(css).toContain('.conversation-pending-dot');
    expect(css).toContain('background: var(--color-muted');
    expect(css).toContain('animation: pendingPulse');
  });

  it('adds mobile-friendly sizing for indicators and actions', () => {
    expect(css).toContain('@media (max-width: 720px)');
    expect(css).toContain('.conversation-unread-dot');
    expect(css).toContain('width: 12px');
    expect(css).toContain('.action-btn');
    expect(css).toContain('padding: 6px');
  });
});
