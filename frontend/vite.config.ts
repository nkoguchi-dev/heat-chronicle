import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

import { resolveViteApiConfig } from './vite-api-config.ts';

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), ['VITE_API_URL', 'HEAT_CHRONICLE_API_PROXY_TARGET']);
  const { apiBaseUrl, proxyTarget } = resolveViteApiConfig(
    command,
    env.VITE_API_URL,
    env.HEAT_CHRONICLE_API_PROXY_TARGET,
  );

  return {
    build: {
      outDir: 'dist',
    },
    define: {
      __VITE_API_BASE_URL__: JSON.stringify(apiBaseUrl),
    },
    plugins: [react()],
    preview: {
      host: 'localhost',
      port: 4173,
      proxy: { '/api': { target: proxyTarget, changeOrigin: true } },
      strictPort: true,
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: 'localhost',
      port: 3000,
      proxy: { '/api': { target: proxyTarget, changeOrigin: true } },
      strictPort: true,
    },
  };
});
