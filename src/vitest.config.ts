import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: resolve(__dirname, "test/setup.ts"),
    css: true,
  },
  resolve: {
    alias: {
      "@": resolve(__dirname),
    },
  },
});
