import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname)
    }
  },
  optimizeDeps: {
    exclude: ['@tauri-apps/api', '@tauri-apps/api/tauri']
  },
  server: {
    port: 5173,
    strictPort: true
  },
  css: {
    postcss: {}
  }
})
