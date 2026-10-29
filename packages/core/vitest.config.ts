import path from 'node:path';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@flowgate/ml': path.resolve(__dirname, '../ml/src/index.ts'),
    },
  },
  test: {
    environment: 'node',
  },
});
