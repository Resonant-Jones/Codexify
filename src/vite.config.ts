import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  // Use the current directory (src) as the Vite root so imports like ./main.tsx resolve
  root: resolve(__dirname),

  // Read .env files from the repository root (one level up from src)
  envDir: resolve(__dirname, '..'),

  // Allow non-VITE prefixes to be visible in import.meta.env if needed
  envPrefix: ['VITE_', 'GUARDIAN_', 'GC_', 'GROQ_'],

  plugins: [react()],

  resolve: {
    alias: {
      // Keep @ pointing at the src directory
      '@': resolve(__dirname)
    },
    // Prevent duplicate React copies (can cause hooks errors/blank UI)
    dedupe: ['react', 'react-dom']
  },

  optimizeDeps: {
    exclude: ['@tauri-apps/api', '@tauri-apps/api/tauri']
  },

  server: {
    port: 5173,
    strictPort: true
  }
})
