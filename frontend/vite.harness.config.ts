/**
 * Proof-only vite config for the generative UI runtime harness.
 * Not part of the shipped application build.
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  root: resolve(__dirname, "src"),
  plugins: [react()],
  define: {
    "import.meta.env.VITE_GENERATIVE_UI": JSON.stringify("true"),
  },
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
  build: {
    outDir: resolve(__dirname, ".harness-dist"),
    emptyOutDir: true,
    minify: false,
    rollupOptions: {
      input: resolve(__dirname, "src/generative-ui-harness.html"),
    },
  },
});