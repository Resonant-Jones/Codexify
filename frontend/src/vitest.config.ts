import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: resolve(__dirname, "test/setup.ts"),
    css: true,
    include: [
      "components/**/*.test.{ts,tsx}",
      "src/components/**/*.{test,spec}.{ts,tsx}",
      "contracts/**/*.test.{ts,tsx}",
      "features/**/*.test.{ts,tsx}",
      "lib/**/*.test.{ts,tsx}",
      "persona/**/*.test.{ts,tsx}",
      "tests/**/*.{test,spec}.{ts,tsx}",
      "test/**/*.test.{ts,tsx}",
      "src/test/**/*.{test,spec}.{ts,tsx}",
      "src/tests/**/*.{test,spec}.{ts,tsx}",
      "tests/**/*.{test,spec}.{ts,tsx}",
    ],
    exclude: [
      "node_modules/**",
      "components/persona/__tests__/appshell-*.test.tsx",
      "components/persona/__tests__/theme-toggle-and-storage.test.tsx",
      "components/persona/__tests__/wallpaper-demo-to-glass.test.tsx",
      "src/components/persona/__tests__/appshell-*.test.tsx",
      "src/components/persona/__tests__/theme-toggle-and-storage.test.tsx",
      "src/components/persona/__tests__/wallpaper-demo-to-glass.test.tsx",
    ],
  },
  resolve: {
    alias: {
      "@": resolve(__dirname),
    },
    dedupe: ["react", "react-dom"],
  },
});
