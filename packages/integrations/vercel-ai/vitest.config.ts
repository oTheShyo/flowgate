import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const rootDir = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      '@flowgate/core': resolve(rootDir, '../../core/src/index.ts'),
      '@flowgate/ml': resolve(rootDir, '../../ml/src/index.ts'),
    },
  },
});
