import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const VITE_CONFIG_PATH = resolve(__dirname, "..", "vite.config.ts");

function readViteConfig(): string {
  return readFileSync(VITE_CONFIG_PATH, "utf8");
}

describe("vite.config proxy preserves canonical /api/* routes", () => {
  it("forwards /api/health/llm through the general /api proxy rule", () => {
    const source = readViteConfig();
    // The general /api proxy rule is what serves canonical LLM health;
    // no rewrite must strip the /api prefix for catalog or health.
    expect(source).toMatch(/['"]\/api['"]\s*:\s*\{/);
    expect(source).not.toMatch(
      /rewrite\s*:\s*\(p\)\s*=>\s*p\.replace\(\s*\/\\\/api\\\/catalog/i
    );
    // The proxy target must remain configurable via VITE_PROXY_TARGET or
    // VITE_BACKEND_URL so the docker-compose override can pin it to the
    // backend service DNS name in the tester netns.
    expect(source).toMatch(/VITE_PROXY_TARGET|VITE_BACKEND_URL/);
  });

  it("forwards /health explicitly so it survives a custom baseURL", () => {
    const source = readViteConfig();
    expect(source).toMatch(/\/health\(\?=\/\|\$\)/);
    // changeOrigin must be enabled so Host: matches the backend in the tester
    // netns.
    expect(source).toMatch(/changeOrigin\s*:\s*true/);
  });

  it("forwards /llm/catalog through the general /api rule (no path rewrite)", () => {
    const source = readViteConfig();
    expect(source).not.toMatch(
      /rewrite\s*:\s*\(p\)\s*=>\s*p\.replace\(\s*\/\\\/api\\\/catalog/i
    );
  });

  it("keeps /health same-origin for browser-side preflight", () => {
    const source = readViteConfig();
    expect(source).toMatch(/\/health\(\?=\/\|\$\)/);
    expect(source).toMatch(/changeOrigin\s*:\s*true/);
  });
});