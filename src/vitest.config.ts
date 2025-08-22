import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [path.resolve(__dirname, "test/setup.ts")],
    css: false,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname),
    },
  },
});
