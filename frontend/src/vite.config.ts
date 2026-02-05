import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
const API_KEY = (process.env.VITE_GUARDIAN_API_KEY ?? '').trim();
const API_HEADERS = API_KEY ? { 'X-API-Key': API_KEY } : {};
const PROXY_TARGET =
  process.env.VITE_PROXY_TARGET ||
  process.env.VITE_BACKEND_URL ||
  'http://localhost:8888';

const IS_DEV = process.env.NODE_ENV !== 'production';

export default defineConfig({
  root: resolve(__dirname),

  envDir: resolve(__dirname, '..'),

  envPrefix: ['VITE_'],

  plugins: [
    react(),
    {
      name: 'inject-guardian-key',
      configureServer(server) {
        const UI_KEY = (process.env.VITE_GUARDIAN_API_KEY ?? '').trim();
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
      disable: IS_DEV,
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
        mode: 'development',
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
      // SSE: proxy to backend without rewriting path; backend supports /api/events
      '/api/events': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        proxyTimeout: 0,
        timeout: 0,
        headers: {
          ...API_HEADERS,
          'accept': 'text/event-stream',
          'cache-control': 'no-cache',
          'connection': 'keep-alive',
        },
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            if (API_KEY) {
              try { proxyReq.setHeader('X-API-Key', API_KEY); } catch {}
            }
          });
          proxy.on('error', (err) => {
            console.error('[vite-proxy] /api/events error:', err?.message || err);
          });
        }
      },

      // Compatibility bridges: map some legacy '/api/*' routes to unprefixed backend paths
      // Chat (backend serves /api/chat/*)
      '^/api/chat(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: API_HEADERS,
      },
      // Threads alias (/api/threads -> /threads, /api/thread -> /thread)
      '^/api/threads(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\//, '/'),
      },
      '^/api/thread(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\//, '/'),
      },
      // Projects
      '^/api/projects(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\//, '/'),
      },

      // Some clients build URLs as `${base}/api/...` where base is already `/api`.
      // Collapse `/api/api/*` -> `/api/*` to avoid 404s.
      '^/api/api(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\/api/, '/api'),
      },

      // General API: /api/* -> backend /api/* (do not rewrite; backend serves /api/*)
      '/api': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: {
          ...API_HEADERS,
        },

        // Let Vite serve source files itself instead of proxying them
        bypass: (req) => {
          if (req.url && /\.(ts|tsx|js|jsx)(\?.*)?$/.test(req.url)) {
            return req.url;
          }
        },

        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            if (API_KEY) {
              try {
                proxyReq.setHeader('X-API-Key', API_KEY);
              } catch {}
            }
          });
          proxy.on('error', (err) => {
            console.error('[vite-proxy] /api error:', err?.message || err);
          });
        },
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
