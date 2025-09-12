import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { VitePWA } from 'vite-plugin-pwa';

// https://vite.dev/config/
export default defineConfig({
  // Use the current directory (src) as the Vite root so imports like ./main.tsx resolve
  root: resolve(__dirname),

  // Read .env files from the repository root (one level up from src)
  envDir: resolve(__dirname, '..'),

  // Allow non-VITE prefixes to be visible in import.meta.env if needed
  envPrefix: ['VITE_', 'GUARDIAN_', 'GC_', 'GROQ_'],

  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Codexify',
        short_name: 'Codexify',
        description: 'Your AI-powered chat & docs workspace',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' }
        ],
        theme_color: '#00FF00',
        background_color: '#000000',
        display: 'standalone',
        start_url: '/'
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/,
            handler: 'CacheFirst',
            options: { cacheName: 'google-fonts' }
          },
          {
            urlPattern: /\.(?:js|css|html|png|svg|jpg|jpeg)$/,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'assets' }
          }
        ]
      }
    })
  ],

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
