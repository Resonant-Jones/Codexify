// @vitest-environment node

import { afterEach, describe, expect, it, vi } from "vitest";

describe("vite /media proxy", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("defines a /media proxy with the same target as /api", async () => {
    vi.stubEnv("VITE_PROXY_TARGET", "http://proxy.test:9999");
    vi.resetModules();

    const viteConfigModule = await import("../vite.config");
    const config = viteConfigModule.default as any;
    const proxy = config.server?.proxy;

    expect(proxy?.["/media"]).toBeDefined();
    expect(proxy?.["/api"]).toBeDefined();
    expect(proxy["/media"].target).toBe(proxy["/api"].target);
    expect(proxy["/media"].target).toBe("http://proxy.test:9999");
  });
});
