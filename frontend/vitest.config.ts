import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { configDefaults, defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  define: {
    __VITE_API_BASE_URL__: JSON.stringify('http://localhost:8000'),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    exclude: [...configDefaults.exclude, 'e2e/**'],
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    clearMocks: true,
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: [
        'src/features/**/*.{ts,tsx}',
        'src/App.tsx',
        'src/main.tsx',
        'src/app/{AppErrorFallback,ErrorBoundary}.tsx',
        'src/lib/utils.ts',
      ],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/features/heatmap/types/**', 'src/test/**'],
      thresholds: {
        lines: 80,
        statements: 80,
        functions: 80,
        branches: 75,
      },
    },
  },
});
