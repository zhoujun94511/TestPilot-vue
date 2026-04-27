import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const flaskTarget = env.VITE_FLASK_TARGET;

  if (mode !== 'production' && !flaskTarget) {
    throw new Error('Missing VITE_FLASK_TARGET, please generate frontend/.env.development.local first.');
  }

  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src')
      }
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: flaskTarget
        ? {
            '/api': {
              target: flaskTarget,
              changeOrigin: true
            },
            '/static': {
              target: flaskTarget,
              changeOrigin: true
            },
            '/favicon.ico': {
              target: flaskTarget,
              changeOrigin: true
            }
          }
        : undefined
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return;
            if (id.includes('/node_modules/vue/') || id.includes('/node_modules/vue-router/')) {
              return 'framework';
            }
            if (id.includes('/node_modules/markdown-it/') || id.includes('/node_modules/markdown-it-anchor/')) {
              return 'markdown';
            }
            if (id.includes('/node_modules/highlight.js/')) {
              return 'highlight';
            }
            return 'vendor';
          }
        }
      }
    }
  };
});
