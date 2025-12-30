import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const files = [
  { path: 'src/components/Sidebar.css', selectors: ['.conversation-item:hover', '.archive-header:hover'] },
  { path: 'src/components/ChatInput.css', selectors: ['.chat-input-tool-button:hover', '.chat-input-cancel-button:hover'] },
  { path: 'src/components/ChatInterface.css', selectors: ['.header-menu button:hover', '.menu-toggle:hover'] },
  { path: 'src/components/CollapsibleSection.css', selectors: ['.collapsible-header:hover'] },
  { path: 'src/components/FollowUpInput.css', selectors: ['.follow-up-button:hover'] },
  { path: 'src/components/Stage1.css', selectors: ['.tab:hover'] },
  { path: 'src/components/Stage2.css', selectors: ['.stage2 .tab:hover'] },
  { path: 'src/components/CopyButton.css', selectors: ['.copy-button:hover'] },
];

describe('hover lightness styling', () => {
  it('uses elevation-2 backgrounds for hover states', () => {
    for (const entry of files) {
      const css = readFileSync(resolve(process.cwd(), entry.path), 'utf8');
      for (const selector of entry.selectors) {
        expect(css).toContain(selector);
      }
      expect(css).toContain('var(--color-elevation-2');
    }
  });
});
