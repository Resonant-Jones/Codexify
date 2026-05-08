import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  initRuntimeConfig,
  readDesktopStartupRoutingDecision,
  getDesktopRuntimeAuthConfig,
  getRuntimeConfigHydrationState,
  resolveApiUrl,
  resolveBackendUrl,
  resolveSseEndpoint,
} from "@/lib/runtimeConfig";
import {
  buildAuthenticatedFetchInit,
  clearRuntimeApiKey,
  readRuntimeApiKey,
} from "@/lib/api";

const invokeMock = vi.fn();

describe("runtime config", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    invokeMock.mockReset();
    clearRuntimeApiKey();
    const storage = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn((key: string) => storage.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => {
          storage.set(key, value);
        }),
        removeItem: vi.fn((key: string) => {
          storage.delete(key);
        }),
        clear: vi.fn(() => {
          storage.clear();
        }),
      },
      configurable: true,
    });
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

  it("uses the browser origin as the backend base in the webUI compose bundle", async () => {
    vi.stubEnv("VITE_WEBUI_COMPOSE_BUNDLE", "1");

    const config = await initRuntimeConfig({ force: true });

    expect(config.mode).toBe("web");
    expect(config.backendBaseUrl).toBe(window.location.origin);
    expect(resolveBackendUrl("/health", config)).toBe(
      `${window.location.origin}/health`
    );
    expect(resolveApiUrl("/api/share", config)).toBe("/api/share");
    expect(resolveSseEndpoint(config)).toBe("/api/events");
  });

  it("ignores relative packaged API base overrides in tauri mode", async () => {
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    vi.stubEnv("VITE_API_BASE_URL", "/api");
    invokeMock.mockResolvedValue({
      mode: "tauri",
      backendBaseUrl: "http://127.0.0.1:8888",
      apiBaseUrl: "http://127.0.0.1:8888/api",
      sseUrl: "http://127.0.0.1:8888/api/events",
      sharePublicBaseUrl: "http://127.0.0.1:5173",
      authMode: "local",
      apiKeyPresent: true,
      apiKey: "packaged-runtime-key",
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: null,
      runtimeContext: "packaged",
    });

    const config = await initRuntimeConfig({ force: true });

    expect(config.apiBaseUrl).toBe("http://127.0.0.1:8888/api");
    expect(resolveApiUrl("/api/share", config)).toBe(
      "http://127.0.0.1:8888/api/share"
    );
  });

  it("hydrates tauri runtime config via desktop command", async () => {
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    invokeMock.mockResolvedValue({
      mode: "tauri",
      backendBaseUrl: "http://127.0.0.1:8888",
      apiBaseUrl: "http://127.0.0.1:8888/api",
      sseUrl: "http://127.0.0.1:8888/api/events",
      sharePublicBaseUrl: "https://share.example",
      authMode: "local",
      apiKeyPresent: true,
      apiKey: "packaged-runtime-key",
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: null,
      runtimeContext: "packaged",
    });

    const config = await initRuntimeConfig({ force: true });

    expect(config.mode).toBe("tauri");
    expect(config.backendBaseUrl).toBe("http://127.0.0.1:8888");
    expect(config.apiBaseUrl).toBe("http://127.0.0.1:8888/api");
    expect(readRuntimeApiKey()).toBe("packaged-runtime-key");
    expect(getDesktopRuntimeAuthConfig()?.apiKeyPresent).toBe(true);
    expect(getDesktopRuntimeAuthConfig()?.envPath).toBe(
      "/Users/chriscastillo/Codexify/.env"
    );
    expect(getRuntimeConfigHydrationState()).toBe("ready");
    expect(resolveApiUrl("/api/share", config)).toBe(
      "http://127.0.0.1:8888/api/share"
    );
    expect(resolveSseEndpoint(config)).toBe("http://127.0.0.1:8888/api/events");
    const headers = buildAuthenticatedFetchInit().headers as Record<string, string>;
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe(
      "packaged-runtime-key"
    );
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

  it("normalizes desktop setup readiness diagnostics", async () => {
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    invokeMock.mockResolvedValue({
      shouldRunWizard: true,
      setupComplete: true,
      runtimeProfile: "local",
      envPath: "/tmp/.env",
      handoffTarget: null,
      detail: "launcher handoff missing",
      setupReadiness: {
        state: "docker_not_running",
        explanation: "Docker is installed, but the daemon is not running.",
        recommendedAction: "Open Docker Desktop, then retry.",
        details: "docker info failed",
      },
    });

    const decision = await readDesktopStartupRoutingDecision();

    expect(decision?.status).toBe("runtime-unavailable");
    expect(decision?.setupReadiness?.state).toBe("docker_not_running");
    expect(decision?.setupReadiness?.recommendedAction).toBe(
      "Open Docker Desktop, then retry."
    );
  });

  it("captures packaged auth diagnostics without exposing the secret", async () => {
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    invokeMock.mockResolvedValue({
      mode: "tauri",
      backendBaseUrl: "http://127.0.0.1:8888",
      apiBaseUrl: "http://127.0.0.1:8888/api",
      sseUrl: "http://127.0.0.1:8888/api/events",
      sharePublicBaseUrl: "http://127.0.0.1:5173",
      authMode: "local",
      apiKeyPresent: false,
      apiKey: null,
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: "config_incomplete",
      runtimeContext: "packaged",
    });

    await initRuntimeConfig({ force: true });

    const snapshot = getDesktopRuntimeAuthConfig();

    expect(snapshot?.apiKeyPresent).toBe(false);
    expect(snapshot?.failureKind).toBe("config_incomplete");
    expect(JSON.stringify(snapshot)).not.toContain("packaged-runtime-key");
  });

  it("refreshes launcher setup readiness when the first handoff is incomplete", async () => {
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    invokeMock
      .mockResolvedValueOnce({
        shouldRunWizard: true,
        setupComplete: true,
        runtimeProfile: "local",
        envPath: "/tmp/.env",
        handoffTarget: null,
        detail: "launcher handoff missing readiness",
        setupReadiness: null,
      })
      .mockResolvedValueOnce({
        shouldRunWizard: true,
        setupComplete: true,
        runtimeProfile: "local",
        envPath: "/tmp/.env",
        handoffTarget: null,
        detail: "launcher handoff refreshed",
        setupReadiness: {
          state: "backend_not_running",
          explanation: "Backend is not running.",
          recommendedAction: "Start the backend service, then retry.",
          details: "backend service missing",
        },
      });

    const decision = await readDesktopStartupRoutingDecision();

    expect(invokeMock).toHaveBeenCalledTimes(2);
    expect(decision?.setupReadiness?.state).toBe("backend_not_running");
    expect(decision?.detail).toBe("launcher handoff refreshed");
  });
});
