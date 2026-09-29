import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev mode (`npm run dev`) API + WebSocket calls are proxied to the
// Django backend on :8000. In production Django serves the built files
// itself, so everything is same-origin and no proxy is needed.
export default defineConfig({
  plugins: [react()],
  // Relative base so the build works both when Django serves it from "/"
  // and when GitHub Pages serves it from "/<repo-name>/".
  base: './',
  server: {
    host: true,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: { outDir: 'dist' },
});
