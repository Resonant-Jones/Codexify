import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
const IS_DEV = process.env.NODE_ENV !== 'production';
const IS_TAURI_BUILD =
  Boolean(process.env.TAURI_ENV_PLATFORM) ||
  Boolean(process.env.TAURI_ENV_ARCH) ||
  Boolean(process.env.TAURI_ENV_TARGET_TRIPLE);
const DEV_API_KEY = IS_DEV
  ? (process.env.VITE_GUARDIAN_DEV_API_KEY ?? '').trim()
  : '';
const DEV_API_HEADERS = DEV_API_KEY ? { 'X-API-Key': DEV_API_KEY } : {};
const PROXY_TARGET =
  process.env.VITE_PROXY_TARGET ||
  process.env.VITE_BACKEND_URL ||
  'http://localhost:8888';

const ADDITIONAL_ALLOWED_HOSTS = (
  process.env.__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS ?? ''
)
  .split(',')
  .map((host) => host.trim())
  .filter(Boolean);
const DEV_ALLOWED_HOSTS = Array.from(
  new Set([
    'axisnode',
    ...ADDITIONAL_ALLOWED_HOSTS,
  ])
);

export default defineConfig({
  root: resolve(__dirname),

  envDir: resolve(__dirname, '..'),

  envPrefix: ['VITE_'],

  plugins: [
    react(),
    {
      name: 'inject-guardian-key',
      configureServer(server) {
        if (!IS_DEV || !DEV_API_KEY) return;
        server.middlewares.use((req, _res, next) => {
          // Node lowercases header names; add the expected API key header for all /api* routes
          if (req.url && req.url.startsWith('/api')) {
            if (!req.headers['x-api-key']) req.headers['x-api-key'] = DEV_API_KEY;       // primary, matches OpenAPI
            if (!req.headers['x-guardian-key']) req.headers['x-guardian-key'] = DEV_API_KEY; // optional legacy header
          }
          next();
        });
      },
    },
    VitePWA({
      disable: IS_DEV || IS_TAURI_BUILD,
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
    allowedHosts: DEV_ALLOWED_HOSTS,
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
          ...DEV_API_HEADERS,
          'accept': 'text/event-stream',
          'cache-control': 'no-cache',
          'connection': 'keep-alive',
        },
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            if (DEV_API_KEY) {
              try { proxyReq.setHeader('X-API-Key', DEV_API_KEY); } catch {}
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
        headers: DEV_API_HEADERS,
      },
      // Threads alias (/api/threads -> /threads, /api/thread -> /thread)
      '^/api/threads(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: DEV_API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\//, '/'),
      },
      '^/api/thread(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: DEV_API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\//, '/'),
      },
      // Projects
      '^/api/projects(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: DEV_API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\//, '/'),
      },

      // Some clients build URLs as `${base}/api/...` where base is already `/api`.
      // Collapse `/api/api/*` -> `/api/*` to avoid 404s.
      '^/api/api(?=/|$)': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: DEV_API_HEADERS,
        rewrite: (p) => p.replace(/^\/api\/api/, '/api'),
      },

      // General API: /api/* -> backend /api/* (do not rewrite; backend serves /api/*)
      '/api': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        headers: {
          ...DEV_API_HEADERS,
        },

        // Let Vite serve source files itself instead of proxying them
        bypass: (req) => {
          if (req.url && /\.(ts|tsx|js|jsx)(\?.*)?$/.test(req.url)) {
            return req.url;
          }
        },

        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            if (DEV_API_KEY) {
              try {
                proxyReq.setHeader('X-API-Key', DEV_API_KEY);
              } catch {}
            }
          });
          proxy.on('error', (err) => {
            console.error('[vite-proxy] /api error:', err?.message || err);
          });
        },
      },

      // Signed media assets are served from the backend at /media/*.
      // Keep the path and query string intact so signature validation continues to work.
      '/media': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: false,
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
