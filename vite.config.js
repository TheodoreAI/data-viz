import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  base: command === 'build' ? '/static/dist/' : '/',
  server: {
    port: 8080,
    strictPort: true,
    host: '0.0.0.0',
    cors: true,
  },
  build: {
    manifest: true,
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        bubbles: 'src/entries/bubbles.js',
        home: 'src/entries/home.js',
        graph: 'src/entries/graph.js',
        register: 'src/entries/register.js',
        login: 'src/entries/login.js',
        profile: 'src/entries/profile.js',
        dashboard: 'src/entries/dashboard.js',
        posts: 'src/entries/posts.js',
        'forgot-password': 'src/entries/forgot-password.js',
        'reset-password': 'src/entries/reset-password.js',
      },
    },
  },
}));