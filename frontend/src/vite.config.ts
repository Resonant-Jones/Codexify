import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
const API_KEY = process.env.VITE_GUARDIAN_API_KEY || 'local-guardian-ui';
const PROXY_TARGET =
  process.env.VITE_PROXY_TARGET ||
  process.env.VITE_BACKEND_URL ||
  'http://localhost:8888';

export default defineConfig({
  root: resolve(__dirname),

  envDir: resolve(__dirname, '..'),

  envPrefix: ['VITE_'],

  plugins: [
    react(),
    {
      name: 'inject-guardian-key',
      configureServer(server) {
        const UI_KEY = process.env.VITE_GUARDIAN_API_KEY;
        server.middlewares.use((req, _res, next) => {
          // Node lowercases header names; add the expected API key header for all /api* routes
          if (req.url && req.url.startsWith('/api')) {
            if (UI_KEY) {
              if (!req.headers['x-api-key']) req.headers['x-api-key'] = UI_KEY;       // primary, matches OpenAPI
              if (!req.headers['x-guardian-key']) req.headers['x-guardian-key'] = UI_KEY; // optional legacy header
            }
          }
          next();
        });
      },
    },
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
      '@': resolve(__dirname),
    },
    dedupe: ['react', 'react-dom'],
  },

  server: {
    port: Number(process.env.VITE_DEV_SERVER_PORT ?? 5173),
    host: true,
    strictPort: false,
    proxy: {
      '/api/events': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        // keep the SSE request alive through the proxy
        proxyTimeout: 0,
        timeout: 0,
        // /api/events -> /events on backend
        rewrite: (path) => path.replace(/^\/api(\/)?/, '/'),
        headers: {
          'X-API-Key': API_KEY,
          'accept': 'text/event-stream',
          'cache-control': 'no-cache',
          'connection': 'keep-alive',
        },
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            try { proxyReq.setHeader('X-API-Key', API_KEY); } catch {}
          });
          proxy.on('error', (err) => {
            console.error('[vite-proxy] /api/events error:', err?.message || err);
          });
        }
      },
      '^/api(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: {
          'X-API-Key': API_KEY,
        },
        // Strip the /api prefix so backend receives routes at root
        rewrite: (path) => path.replace(/^\/api(\/)?/, '/'),
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            try { proxyReq.setHeader('X-API-Key', API_KEY); } catch {}
          });
          proxy.on('error', (err) => {
            console.error('[vite-proxy] /api error:', err?.message || err);
          });
        }
      },

      // Convenience routes so you can open docs directly via Vite dev server
      '/openapi.json': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8888',
        changeOrigin: true,
        secure: false,
      },
      '/docs': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8888',
        changeOrigin: true,
        secure: false,
      },
      '/redoc': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8888',
        changeOrigin: true,
        secure: false,
      },

      '^/api/ws(?=/|$)': {
        target: (process.env.VITE_PROXY_TARGET ?? 'http://localhost:8888').replace(/^http/, 'ws'),
        ws: true,
        changeOrigin: true,
        secure: false,
        // /api/ws -> /ws
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  }
})
