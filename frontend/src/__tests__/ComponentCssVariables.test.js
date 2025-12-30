import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const filesToCheck = [
  { path: 'src/App.css', vars: ['--color-surface', '--color-text'] },
  { path: 'src/components/Sidebar.css', vars: ['--color-surface', '--color-border', '--color-text', '--color-muted'] },
  { path: 'src/components/ChatInterface.css', vars: ['--color-surface', '--color-border', '--color-text', '--color-muted'] },
  { path: 'src/components/Stage1.css', vars: ['--color-surface', '--color-text', '--color-border'] },
  { path: 'src/components/Stage2.css', vars: ['--color-surface', '--color-text', '--color-border', '--color-muted'] },
  { path: 'src/components/Stage3.css', vars: ['--color-surface', '--color-text', '--color-border'] },
  { path: 'src/components/ChatInput.css', vars: ['--color-surface', '--color-text', '--color-border', '--color-muted'] },
  { path: 'src/components/EditableTitle.css', vars: ['--color-text', '--color-border'] },
  { path: 'src/components/CollapsibleSection.css', vars: ['--color-surface', '--color-border', '--color-muted'] },
  { path: 'src/components/CopyButton.css', vars: ['--color-surface', '--color-border', '--color-text'] },
  { path: 'src/components/FollowUpInput.css', vars: ['--color-surface', '--color-border', '--color-text'] },
];

describe('component CSS uses theme variables', () => {
  it('references theme variables in component styles', () => {
    for (const entry of filesToCheck) {
      const css = readFileSync(resolve(process.cwd(), entry.path), 'utf8');
      for (const variable of entry.vars) {
        expect(css).toContain(`var(${variable}`);
      }
    }
  });
});
