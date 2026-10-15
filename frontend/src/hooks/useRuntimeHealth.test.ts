import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useRuntimeHealth } from "@/hooks/useRuntimeHealth";
import {
  LIVE_EVENT_CONNECTION_STATES,
  LiveEventConnectionState,
  RUNTIME_HEALTH_FAILURE_KINDS,
  RUNTIME_HEALTH_STATUSES,
} from "@/contracts/runtimeTokens";

type LiveEventsStatus = {
  connected: boolean;
  connectionStatus: LiveEventConnectionState;
  statusUpdatedAt: number | null;
  diagnostics: {
    endpoint: string | null;
    connectionState: LiveEventConnectionState;
    lastEventAt: number | null;
    lastPingAt: number | null;
    statusUpdatedAt: number | null;
    lastHttpStatus: number | null;
    transportErrorClass: string | null;
    authSource: string;
    apiKeyPresent: boolean;
    hydrationState: "pending" | "ready" | "failed";
    nativeCommandStatus: string | null;
    reconnectAttempts: number;
    retryMs: number;
    subscribers: number;
    readyState: 0 | 1 | 2;
    lastErrorAt: number | null;
    lastEventId: string | null;
  };
};

function makeLiveEventsDiagnostics(overrides: Partial<LiveEventsStatus["diagnostics"]> = {}): LiveEventsStatus["diagnostics"] {
  return {
    endpoint: "http://127.0.0.1:8888/api/events",
    connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
    lastEventAt: Date.parse("2026-03-20T11:59:58.000Z"),
    lastPingAt: Date.parse("2026-03-20T11:59:58.000Z"),
    statusUpdatedAt: Date.parse("2026-03-20T12:00:00.000Z"),
    lastHttpStatus: 200,
    transportErrorClass: null,
    authSource: "runtime-desktop",
    apiKeyPresent: true,
    hydrationState: "ready",
    nativeCommandStatus: "ready",
    reconnectAttempts: 0,
    retryMs: 1000,
    subscribers: 1,
    readyState: 1,
    lastErrorAt: null,
    lastEventId: "evt-1",
    ...overrides,
  };
}

const apiGet = vi.fn();
const runtimeState = vi.hoisted(() => ({
  isTauri: true,
  apiBaseUrl: "http://127.0.0.1:8888/api",
  hydrationState: "ready" as "pending" | "ready" | "failed",
  desktopAuthConfig: {
    apiKeyPresent: true,
    apiKey: "packaged-runtime-key",
    envPath: "/Users/chriscastillo/Codexify/.env",
    runtimeRoot: "/Users/chriscastillo/Codexify",
    failureKind: null,
    runtimeContext: "packaged",
  } as
    | null
    | {
        apiKeyPresent: boolean;
        apiKey: string | null;
        envPath: string | null;
        runtimeRoot: string | null;
        failureKind: string | null;
        runtimeContext: string | null;
      },
  runtimeApiKey: "packaged-runtime-key" as string | null,
  authToken: null as string | null,
  devApiKey: "" as string,
}));
let liveEventsStatus: LiveEventsStatus = {
  connected: true,
  connectionStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
  statusUpdatedAt: Date.now(),
  diagnostics: makeLiveEventsDiagnostics(),
};

vi.mock("@/lib/api", () => ({
  default: {
    get: (...args: unknown[]) => apiGet(...args),
  },
  getAuthToken: () => runtimeState.authToken,
  getDevApiKey: () => runtimeState.devApiKey,
  readRuntimeApiKey: () => runtimeState.runtimeApiKey,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  getDesktopRuntimeAuthConfig: () => runtimeState.desktopAuthConfig,
  getRuntimeConfigHydrationState: () => runtimeState.hydrationState,
  getRuntimeConfigVersion: () => 0,
  getRuntimeConfigSync: () => ({
    mode: runtimeState.isTauri ? "tauri" : "web",
    backendBaseUrl: "http://127.0.0.1:8888",
    apiBaseUrl: runtimeState.apiBaseUrl,
    sseUrl: "http://127.0.0.1:8888/api/events",
    sharePublicBaseUrl: "http://127.0.0.1:5173",
    authMode: "local",
  }),
  isTauriRuntime: () => runtimeState.isTauri,
  subscribeRuntimeConfigState: () => () => {},
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => liveEventsStatus,
}));

const flushPromises = async () => {
  await Promise.resolve();
  await vi.advanceTimersByTimeAsync(0);
};

function mockHealthResponses(overrides: {
  chat?: "ok" | "fail" | "missing" | "unreachable";
  llm?: "ok" | "fail" | "missing" | "unreachable" | "nested-ok" | "nested-fail";
} = {}) {
  const chat = overrides.chat ?? "ok";
  const llm = overrides.llm ?? "ok";

  apiGet.mockImplementation((path: string) => {
    if (path === "/api/health/llm") {
      if (llm === "ok") {
        return Promise.resolve({ data: { ok: true, status: "online" } });
      }
      if (llm === "nested-ok") {
        return Promise.resolve({
          data: {
            status: "ok",
            ok: true,
            provider: "local",
            model: "library2/ministral-3:8b",
            details: {
              status: "online",
              ok: true,
              provider_runtime: { available: true },
              endpoint_resolution: { state: "available" },
            },
          },
        });
      }
      if (llm === "nested-fail") {
        return Promise.resolve({
          data: {
            status: "ok",
            ok: true,
            provider: "local",
            model: "library2/ministral-3:8b",
            details: {
              status: "offline",
              ok: false,
              provider_runtime: { available: false },
              endpoint_resolution: { state: "unavailable" },
            },
          },
        });
      }
      if (llm === "missing") {
        const error = new Error("not found") as Error & {
          response?: { status?: number };
        };
        error.response = { status: 404 };
        return Promise.reject(error);
      }
      if (llm === "unreachable") {
        return Promise.reject(new Error("llm unreachable"));
      }
      return Promise.resolve({ data: { ok: false, status: "offline" } });
    }
    if (path === "/health/chat") {
      if (chat === "ok") {
        return Promise.resolve({
          data: {
            ok: true,
            status: "healthy",
            completion_service: {
              ok: true,
              status_reason: "ok",
              redis_reachable: true,
            },
          },
        });
      }
      if (chat === "missing") {
        const error = new Error("not found") as Error & {
          response?: { status?: number };
        };
        error.response = { status: 404 };
        return Promise.reject(error);
      }
      if (chat === "unreachable") {
        return Promise.reject(new Error("chat unreachable"));
      }
      return Promise.resolve({
        data: {
          ok: false,
          status: "degraded",
          completion_service: {
            ok: false,
            status_reason: "worker_heartbeat_stale",
          },
        },
      });
    }
    return Promise.reject(new Error("unknown endpoint"));
  });
}

describe("useRuntimeHealth", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-20T12:00:00.000Z"));
    apiGet.mockReset();
    runtimeState.isTauri = true;
    runtimeState.apiBaseUrl = "http://127.0.0.1:8888/api";
    runtimeState.hydrationState = "ready";
    runtimeState.desktopAuthConfig = {
      apiKeyPresent: true,
      apiKey: "packaged-runtime-key",
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: null,
      runtimeContext: "packaged",
    };
    runtimeState.runtimeApiKey = "packaged-runtime-key";
    runtimeState.authToken = null;
    runtimeState.devApiKey = "";
    liveEventsStatus = {
      connected: true,
      connectionStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
      statusUpdatedAt: Date.now(),
      diagnostics: makeLiveEventsDiagnostics(),
    };
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("reports healthy when all surfaces are healthy and live events are connected", async () => {
    mockHealthResponses();
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.HEALTHY);
      expect(result.current.failureKind).toBeNull();
      expect(result.current.chatHealthy).toBe(true);
      expect(result.current.llmHealthy).toBe(true);
      expect(result.current.lastCheckedAt).toBe(Date.parse("2026-03-20T12:00:00.000Z"));
      expect(result.current.lastSuccessAt).toBe(Date.parse("2026-03-20T12:00:00.000Z"));
      expect(result.current.lastFailedAt).toBeNull();
      expect(result.current.diagnostics.resolvedApiBaseUrl).toBe(
        "http://127.0.0.1:8888/api"
      );
      expect(result.current.diagnostics.resolvedApiBaseUrlSource).toBe(
        "runtime-desktop"
      );
      expect(result.current.diagnostics.apiKeyPresent).toBe(true);
      expect(result.current.diagnostics.apiKeySource).toBe("runtime-desktop");
      expect(result.current.diagnostics.hydrationState).toBe("ready");
      expect(result.current.diagnostics.nativeCommandStatus).toBe("ready");
      expect(result.current.diagnostics.authSource).toBe("runtime-desktop");
      expect(result.current.diagnostics.chat.endpoint).toBe("/health/chat");
      expect(result.current.diagnostics.chat.httpStatus).toBe(200);
      expect(result.current.diagnostics.chat.parsedStatus).toBe("healthy");
      expect(result.current.diagnostics.chat.parsedOk).toBe(true);
      expect(result.current.diagnostics.llm.endpoint).toBe("/api/health/llm");
      expect(result.current.diagnostics.llm.httpStatus).toBe(200);
      expect(result.current.diagnostics.llm.parsedStatus).toBe("online");
      expect(result.current.diagnostics.llm.parsedOk).toBe(true);
      expect(result.current.diagnostics.llm.detailsStatus).toBeNull();
      expect(result.current.diagnostics.llm.detailsOk).toBeNull();
      expect(result.current.diagnostics.llm.providerRuntimeAvailable).toBeNull();
      expect(result.current.diagnostics.llm.endpointResolutionState).toBeNull();
      expect(result.current.diagnostics.failureKind).toBeNull();
      expect(result.current.diagnostics.currentComputedStateSource).toBe(
        "live-poll"
      );
    });
  });

  it("treats the nested model-health payload as healthy when the local path is available", async () => {
    mockHealthResponses({ llm: "nested-ok" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.HEALTHY);
      expect(result.current.llmHealthy).toBe(true);
      expect(result.current.diagnostics.llm.parsedStatus).toBe("ok");
      expect(result.current.diagnostics.llm.parsedOk).toBe(true);
      expect(result.current.diagnostics.llm.detailsStatus).toBe("online");
      expect(result.current.diagnostics.llm.detailsOk).toBe(true);
      expect(result.current.diagnostics.llm.providerRuntimeAvailable).toBe(true);
      expect(result.current.diagnostics.llm.endpointResolutionState).toBe(
        "available"
      );
      expect(result.current.diagnostics.llm.provider).toBe("local");
      expect(result.current.diagnostics.llm.model).toBe(
        "library2/ministral-3:8b"
      );
      expect(result.current.diagnostics.failureKind).toBeNull();
    });
  });

  it("flags backend unreachable", async () => {
    mockHealthResponses({ llm: "unreachable", chat: "unreachable" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.BACKEND_UNREACHABLE
      );
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.DEGRADED);
    });
  });

  it("treats /api/health/llm 404 as missing endpoint, not backend unreachable", async () => {
    mockHealthResponses({ llm: "missing" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.backendReachable).toBe(true);
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.HEALTH_ENDPOINT_MISSING
      );
    });
  });

  it("treats /health/chat 404 as missing endpoint, not backend unreachable", async () => {
    mockHealthResponses({ chat: "missing" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.backendReachable).toBe(true);
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.HEALTH_ENDPOINT_MISSING
      );
    });
  });

  it("clears chat_unhealthy when /health/chat becomes healthy", async () => {
    mockHealthResponses({ chat: "fail" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.CHAT_UNHEALTHY
      );
      expect(result.current.diagnostics.chat.parsedStatus).toBe("degraded");
      expect(result.current.diagnostics.chat.parsedOk).toBe(false);
      expect(result.current.diagnostics.currentComputedStateSource).toBe(
        "live-poll"
      );
    });

    expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.DEGRADED);

    mockHealthResponses({ chat: "ok" });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
      await flushPromises();
    });

    await waitFor(() => {
      expect(result.current.failureKind).toBeNull();
      expect(result.current.chatHealthy).toBe(true);
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.HEALTHY);
      expect(result.current.diagnostics.chat.parsedStatus).toBe("healthy");
      expect(result.current.diagnostics.chat.parsedOk).toBe(true);
      expect(result.current.diagnostics.lastSuccessAt).toBe(
        Date.parse("2026-03-20T12:00:15.000Z")
      );
      expect(result.current.diagnostics.lastFailedAt).toBe(
        Date.parse("2026-03-20T12:00:00.000Z")
      );
    });
  });

  it("flags chat unhealthy", async () => {
    mockHealthResponses({ chat: "fail" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.CHAT_UNHEALTHY
      );
    });
  });

  it("records endpoint and auth diagnostics for a degraded health poll", async () => {
    runtimeState.desktopAuthConfig = {
      apiKeyPresent: true,
      apiKey: "packaged-runtime-key",
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: null,
      runtimeContext: "packaged",
    };
    runtimeState.runtimeApiKey = "packaged-runtime-key";
    mockHealthResponses({ llm: "fail", chat: "ok" });

    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });

    await waitFor(() => {
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.DEGRADED);
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY
      );
      expect(result.current.diagnostics.apiKeyPresent).toBe(true);
      expect(result.current.diagnostics.apiKeySource).toBe("runtime-desktop");
      expect(result.current.diagnostics.hydrationState).toBe("ready");
      expect(result.current.diagnostics.authSource).toBe("runtime-desktop");
      expect(result.current.diagnostics.llm.endpoint).toBe("/api/health/llm");
      expect(result.current.diagnostics.llm.httpStatus).toBe(200);
      expect(result.current.diagnostics.llm.parsedStatus).toBe("offline");
      expect(result.current.diagnostics.llm.parsedOk).toBe(false);
      expect(result.current.diagnostics.chat.endpoint).toBe("/health/chat");
      expect(result.current.diagnostics.chat.httpStatus).toBe(200);
      expect(result.current.diagnostics.chat.parsedStatus).toBe("healthy");
      expect(result.current.diagnostics.chat.parsedOk).toBe(true);
      expect(result.current.diagnostics.lastCheckedAt).toBe(
        Date.parse("2026-03-20T12:00:00.000Z")
      );
      expect(result.current.diagnostics.currentComputedStateSource).toBe(
        "live-poll"
      );
    });
  });

  it("polls only contract-valid health endpoints", async () => {
    mockHealthResponses();
    renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });

    const calledPaths = apiGet.mock.calls.map(([path]) => String(path));
    expect(calledPaths).toContain("/api/health/llm");
    expect(calledPaths).toContain("/health/chat");
    expect(calledPaths).not.toContain("/health");
    expect(calledPaths).not.toContain("/api/health");
    expect(calledPaths).not.toContain("/api/health/chat");
  });

  it("flags llm unhealthy", async () => {
    mockHealthResponses({ llm: "fail" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY
      );
    });
  });

  it("keeps llm unhealthy when the nested local model path is still unavailable", async () => {
    mockHealthResponses({ llm: "nested-fail" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.DEGRADED);
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY
      );
      expect(result.current.llmHealthy).toBe(false);
      expect(result.current.diagnostics.llm.parsedStatus).toBe("ok");
      expect(result.current.diagnostics.llm.parsedOk).toBe(true);
      expect(result.current.diagnostics.llm.detailsStatus).toBe("offline");
      expect(result.current.diagnostics.llm.detailsOk).toBe(false);
      expect(result.current.diagnostics.llm.providerRuntimeAvailable).toBe(
        false
      );
      expect(result.current.diagnostics.llm.endpointResolutionState).toBe(
        "unavailable"
      );
      expect(result.current.diagnostics.llm.failureReason).toBe(
        "details.ok=false"
      );
    });
  });

  it("flags stale when no successful check within the window", async () => {
    mockHealthResponses();
    const { result, rerender } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.HEALTHY);
    });

    act(() => {
      vi.setSystemTime(new Date("2026-03-20T12:01:00.000Z"));
    });
    rerender();
    expect(result.current.failureKind).toBe(RUNTIME_HEALTH_FAILURE_KINDS.STALE);
    expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.DEGRADED);
  });

  it("exposes live events disconnect diagnostics without degrading provider health", async () => {
    mockHealthResponses();
    liveEventsStatus = {
      connected: false,
      connectionStatus: LIVE_EVENT_CONNECTION_STATES.DISCONNECTED,
      statusUpdatedAt: Date.now() - 46_000,
      diagnostics: makeLiveEventsDiagnostics({
        connectionState: LIVE_EVENT_CONNECTION_STATES.DISCONNECTED,
        statusUpdatedAt: Date.now() - 46_000,
        lastHttpStatus: 200,
        lastErrorAt: Date.now() - 46_000,
        reconnectAttempts: 3,
        retryMs: 5000,
      }),
    };
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBeNull();
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.HEALTHY);
      expect(result.current.diagnostics.liveEvents.connectionState).toBe(
        LIVE_EVENT_CONNECTION_STATES.DISCONNECTED
      );
      expect(result.current.diagnostics.liveEvents.lastHttpStatus).toBe(200);
      expect(result.current.diagnostics.liveEvents.transportErrorClass).toBeNull();
      expect(result.current.diagnostics.liveEvents.apiKeyPresent).toBe(true);
      expect(result.current.diagnostics.liveEvents.hydrationState).toBe("ready");
      expect(result.current.diagnostics.liveEvents.statusUpdatedAt).toBe(
        Date.now() - 46_000
      );
    });
  });

  it("waits for desktop runtime hydration before polling health", async () => {
    runtimeState.hydrationState = "pending";
    mockHealthResponses();
    const { result, rerender } = renderHook(() => useRuntimeHealth());

    await act(async () => {
      await flushPromises();
    });

    expect(apiGet).not.toHaveBeenCalled();
    expect(result.current.diagnostics.hydrationState).toBe("pending");
    expect(result.current.diagnostics.nativeCommandStatus).toBe("pending");

    runtimeState.hydrationState = "ready";
    rerender();

    await act(async () => {
      await flushPromises();
    });

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/health/llm");
      expect(apiGet).toHaveBeenCalledWith("/health/chat");
      expect(result.current.diagnostics.hydrationState).toBe("ready");
      expect(result.current.diagnostics.authSource).toBe("runtime-desktop");
      expect(result.current.diagnostics.apiKeyPresent).toBe(true);
    });
  });

  it("exposes canonical live event connection tokens", () => {
    expect(LIVE_EVENT_CONNECTION_STATES.CONNECTING).toBe("connecting");
    expect(LIVE_EVENT_CONNECTION_STATES.CONNECTED).toBe("connected");
    expect(LIVE_EVENT_CONNECTION_STATES.RECONNECTING).toBe("reconnecting");
    expect(LIVE_EVENT_CONNECTION_STATES.DISCONNECTED).toBe("disconnected");
  });

  it("exposes canonical runtime health tokens", () => {
    expect(RUNTIME_HEALTH_STATUSES.HEALTHY).toBe("healthy");
    expect(RUNTIME_HEALTH_STATUSES.DEGRADED).toBe("degraded");
    expect(RUNTIME_HEALTH_FAILURE_KINDS.BACKEND_UNREACHABLE).toBe(
      "backend_unreachable"
    );
    expect(RUNTIME_HEALTH_FAILURE_KINDS.HEALTH_ENDPOINT_MISSING).toBe(
      "health_endpoint_missing"
    );
    expect(RUNTIME_HEALTH_FAILURE_KINDS.CHAT_UNHEALTHY).toBe("chat_unhealthy");
    expect(RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY).toBe("llm_unhealthy");
    expect(RUNTIME_HEALTH_FAILURE_KINDS.LIVE_EVENTS_DISCONNECTED).toBe(
      "live_events_disconnected"
    );
    expect(RUNTIME_HEALTH_FAILURE_KINDS.STALE).toBe("stale");
  });
});
