import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// Root Vite config for the repository. We point the project root at `src/`
// so running `vite` (or `npm run dev`) from the repo root works as expected.
export default defineConfig({
  // Serve everything relative to /src
  root: 'src',

  // Load .env* from the repo root (not src/)
  envDir: '.',

  // Expose both Vite-style keys and (optionally) GUARDIAN_/GC_ keys to import.meta.env
  // so accidental non-VITE prefixes don't silently become undefined.
  envPrefix: ['VITE_', 'GUARDIAN_', 'GC_'],

  plugins: [react()],

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
    // Prevent duplicate React copies (which can cause blank/white screen bugs)
    dedupe: ['react', 'react-dom'],
  },

  server: {
    port: 5173,
    strictPort: true,
    // If you later choose to proxy API calls instead of using VITE_GUARDIAN_API_BASE,
    // point this to your FastAPI server (e.g., http://127.0.0.1:8000) and fetch('/api/...').
    // For now it's disabled to avoid masking network errors.
    // proxy: {
    //   '/api': {
    //     target: 'http://127.0.0.1:8000',
    //     changeOrigin: true
    //   }
    // }
  },

  build: {
    // Keep build output under src/ to match current structure
    outDir: 'dist',
    emptyOutDir: true,
    // Modern enough to play nicely with TSX/React defaults
    target: 'es2018',
  },

  css: {
    postcss: {}
  }
})
