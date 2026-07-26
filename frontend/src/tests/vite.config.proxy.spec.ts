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

  it("uses the legacy VITE_GUARDIAN_API_KEY for dev proxy auth", async () => {
    vi.stubEnv("VITE_GUARDIAN_API_KEY", "legacy-local-key");
    vi.stubEnv("VITE_GUARDIAN_DEV_API_KEY", "");
    vi.resetModules();

    const viteConfigModule = await import("../vite.config");
    const config = viteConfigModule.default as any;
    const proxy = config.server?.proxy;

    expect(proxy?.["/api"]?.headers?.["X-API-Key"]).toBe("legacy-local-key");
    expect(proxy?.["/api/events"]?.headers?.["X-API-Key"]).toBe("legacy-local-key");
    expect(proxy?.["^/api/chat(?=/|$)"]?.headers?.["X-API-Key"]).toBe(
      "legacy-local-key"
    );
  });

  it("binds the dev server to 0.0.0.0 and allows the MagicDNS host and Tailscale IP", async () => {
    const viteConfigModule = await import("../vite.config");
    const config = viteConfigModule.default as any;

    expect(config.server?.host).toBe("0.0.0.0");
    expect(config.server?.allowedHosts).toContain("vaultnode");
    expect(config.server?.allowedHosts).toContain("100.100.42.37");
  });

  it("proxies canonical WebSocket and lightweight health paths before general API traffic", async () => {
    vi.stubEnv("VITE_PROXY_TARGET", "http://proxy.test:9999");
    vi.resetModules();

    const viteConfigModule = await import("../vite.config");
    const proxy = (viteConfigModule.default as any).server?.proxy;
    const keys = Object.keys(proxy);

    expect(proxy["^/api/ws(?=/|$)"]).toMatchObject({
      target: "ws://proxy.test:9999",
      ws: true,
    });
    expect(proxy["^/api/collab/ws(?=/|$)"]).toMatchObject({
      target: "ws://proxy.test:9999",
      ws: true,
    });
    expect(proxy["^/api/ws(?=/|$)"].rewrite).toBeUndefined();
    expect(proxy["^/health(?=/|$)"].target).toBe("http://proxy.test:9999");
    expect(keys.indexOf("^/api/ws(?=/|$)")).toBeLessThan(keys.indexOf("/api"));
    expect(keys.indexOf("^/api/collab/ws(?=/|$)")).toBeLessThan(keys.indexOf("/api"));
  });
});
