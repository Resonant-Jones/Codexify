import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "node:path";

export default defineConfig({
  root: ".",
  publicDir: "public",
  cacheDir: "node_modules/.vite",
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  css: {
    devSourcemap: true,
  },
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "framer-motion",
      "lucide-react",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-dialog",
      "@radix-ui/react-separator",
      "@radix-ui/react-slot",
    ],
  },
  build: {
    sourcemap: true,
    target: "es2020",
    outDir: "dist",
    assetsDir: "assets",
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
          ui: ["framer-motion", "lucide-react"],
          radix: [
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-dialog",
            "@radix-ui/react-separator",
            "@radix-ui/react-slot",
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    open: false,
  },
  preview: {
    port: 5174,
  },
});
