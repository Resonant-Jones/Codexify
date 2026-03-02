import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  initRuntimeConfig,
  resolveApiUrl,
  resolveSseEndpoint,
} from "@/lib/runtimeConfig";

const invokeMock = vi.fn();

describe("runtime config", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    invokeMock.mockReset();
    localStorage.clear();
    delete (window as any).__TAURI_IPC__;
    delete (window as any).__TAURI_INTERNALS__;
    delete (window as any).__CFY_TAURI_CORE__;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses web defaults when not in tauri runtime", async () => {
    const config = await initRuntimeConfig({ force: true });

    expect(config.mode).toBe("web");
    expect(config.apiBaseUrl).toBe("/api");
    expect(resolveApiUrl("/api/share", config)).toBe("/api/share");
    expect(resolveSseEndpoint(config)).toBe("/api/events");
  });

  it("hydrates tauri runtime config via desktop command", async () => {
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    invokeMock.mockResolvedValue({
      mode: "tauri",
      backendBaseUrl: "http://127.0.0.1:9999",
      apiBaseUrl: "http://127.0.0.1:9999/api",
      sseUrl: "http://127.0.0.1:9999/api/events",
      sharePublicBaseUrl: "https://share.example",
      authMode: "local",
    });

    const config = await initRuntimeConfig({ force: true });

    expect(config.mode).toBe("tauri");
    expect(config.backendBaseUrl).toBe("http://127.0.0.1:9999");
    expect(config.apiBaseUrl).toBe("http://127.0.0.1:9999/api");
    expect(resolveApiUrl("/api/share", config)).toBe(
      "http://127.0.0.1:9999/api/share"
    );
    expect(resolveSseEndpoint(config)).toBe("http://127.0.0.1:9999/api/events");
  });

  it("prioritizes persisted desktop connection overrides", async () => {
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    localStorage.setItem("cfy.desktop.backendBaseUrl", "http://127.0.0.1:7777");
    localStorage.setItem("cfy.desktop.sharePublicBaseUrl", "https://public.example");
    invokeMock.mockResolvedValue({
      mode: "tauri",
      backendBaseUrl: "http://127.0.0.1:9999",
      apiBaseUrl: "http://127.0.0.1:9999/api",
      sseUrl: "http://127.0.0.1:9999/api/events",
      sharePublicBaseUrl: "https://fallback.example",
      authMode: "local",
    });

    const config = await initRuntimeConfig({ force: true });

    expect(config.backendBaseUrl).toBe("http://127.0.0.1:7777");
    expect(config.apiBaseUrl).toBe("http://127.0.0.1:7777/api");
    expect(config.sseUrl).toBe("http://127.0.0.1:7777/api/events");
    expect(config.sharePublicBaseUrl).toBe("https://public.example");
  });
});
