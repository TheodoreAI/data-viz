import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  base: command === 'build' ? '/static/dist/' : '/',
  server: {
    port: 8080,
    strictPort: true,
    host: '0.0.0.0',
  },
  build: {
    manifest: true,
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        bubbles: 'src/entries/bubbles.js',
        home: 'src/entries/home.js',
      },
    },
  },
}));