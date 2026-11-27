import { defineConfig, mergeConfig } from "vitest/config";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import base from "./vitest.config";

// Isolated identity/UI verification with bounded workers and a task-owned cache.
export default mergeConfig(base, defineConfig({
  cacheDir: resolve(tmpdir(), `codexify-presentation-tests-${process.pid}`),
  esbuild: { jsx: "automatic" },
  test: { maxWorkers: 2 },
}));
