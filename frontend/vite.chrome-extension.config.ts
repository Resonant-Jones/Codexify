import { readFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import react from "@vitejs/plugin-react"
import type { Plugin } from "vite"
import { defineConfig } from "vitest/config"

const frontendRoot = dirname(fileURLToPath(import.meta.url))
const extensionRoot = resolve(frontendRoot, "chrome-extension")
const outputRoot = resolve(frontendRoot, "dist/chrome-extension")
const manifestPath = resolve(extensionRoot, "manifest.json")

function emitChromeManifest(): Plugin {
  return {
    name: "emit-chrome-extension-manifest",
    apply: "build",
    buildStart() {
      this.emitFile({
        type: "asset",
        fileName: "manifest.json",
        source: readFileSync(manifestPath, "utf8"),
      })
    },
  }
}

export default defineConfig({
  root: extensionRoot,
  publicDir: false,
  plugins: [react(), emitChromeManifest()],
  resolve: {
    alias: {
      react: resolve(frontendRoot, "src/node_modules/react"),
      "react-dom": resolve(frontendRoot, "src/node_modules/react-dom"),
      "@testing-library/react": resolve(
        frontendRoot,
        "src/node_modules/@testing-library/react",
      ),
    },
    dedupe: ["react", "react-dom"],
  },
  build: {
    outDir: outputRoot,
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      input: {
        sidepanel: resolve(extensionRoot, "sidepanel.html"),
        "service-worker": resolve(extensionRoot, "service-worker.ts"),
      },
      output: {
        entryFileNames: (chunk) =>
          chunk.name === "service-worker"
            ? "service-worker.js"
            : "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: resolve(frontendRoot, "src/test/setup.ts"),
    css: true,
    include: ["src/__tests__/**/*.{test,spec}.{ts,tsx}"],
  },
})
