import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const stageFiles = [
  { path: 'src/components/Stage1.css', vars: ['--color-elevation-1'] },
  { path: 'src/components/Stage2.css', vars: ['--color-elevation-1', '--color-elevation-2'] },
  { path: 'src/components/Stage3.css', vars: ['--color-elevation-1', '--color-elevation-2'] },
];

describe('elevation shading styles', () => {
  it('uses elevation variables in stage components', () => {
    for (const entry of stageFiles) {
      const css = readFileSync(resolve(process.cwd(), entry.path), 'utf8');
      for (const variable of entry.vars) {
        expect(css).toContain(`var(${variable}`);
      }
    }
  });
});
