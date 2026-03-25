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
};

const apiGet = vi.fn();
let liveEventsStatus: LiveEventsStatus = {
  connected: true,
  connectionStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
  statusUpdatedAt: Date.now(),
};

vi.mock("@/lib/api", () => ({
  default: {
    get: (...args: unknown[]) => apiGet(...args),
  },
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => liveEventsStatus,
}));

const flushPromises = async () => {
  await Promise.resolve();
  await vi.advanceTimersByTimeAsync(0);
};

function mockHealthResponses(overrides: {
  embedder?: "ok" | "fail" | "missing" | "unreachable";
  llm?: "ok" | "fail" | "missing" | "unreachable";
} = {}) {
  const embedder = overrides.embedder ?? "ok";
  const llm = overrides.llm ?? "ok";

  apiGet.mockImplementation((path: string) => {
    if (path === "/api/health/llm") {
      if (llm === "ok") {
        return Promise.resolve({ data: { ok: true, status: "online" } });
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
    if (path === "/api/health/embedder") {
      if (embedder === "ok") {
        return Promise.resolve({ data: { status: "ok" } });
      }
      if (embedder === "missing") {
        const error = new Error("not found") as Error & {
          response?: { status?: number };
        };
        error.response = { status: 404 };
        return Promise.reject(error);
      }
      if (embedder === "unreachable") {
        return Promise.reject(new Error("embedder unreachable"));
      }
      return Promise.resolve({ data: { status: "error" } });
    }
    return Promise.reject(new Error("unknown endpoint"));
  });
}

describe("useRuntimeHealth", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-20T12:00:00.000Z"));
    apiGet.mockReset();
    liveEventsStatus = {
      connected: true,
      connectionStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
      statusUpdatedAt: Date.now(),
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
    });
  });

  it("flags backend unreachable", async () => {
    mockHealthResponses({ llm: "unreachable", embedder: "unreachable" });
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

  it("treats /api/health/embedder 404 as missing endpoint, not backend unreachable", async () => {
    mockHealthResponses({ embedder: "missing" });
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

  it("flags chat unhealthy", async () => {
    mockHealthResponses({ embedder: "fail" });
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

  it("polls only contract-valid health endpoints", async () => {
    mockHealthResponses();
    renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });

    const calledPaths = apiGet.mock.calls.map(([path]) => String(path));
    expect(calledPaths).toContain("/api/health/llm");
    expect(calledPaths).toContain("/api/health/embedder");
    expect(calledPaths).not.toContain("/health");
    expect(calledPaths).not.toContain("/health/chat");
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

  it("flags live events disconnected after the threshold", async () => {
    mockHealthResponses();
    liveEventsStatus = {
      connected: false,
      connectionStatus: LIVE_EVENT_CONNECTION_STATES.DISCONNECTED,
      statusUpdatedAt: Date.now() - 46_000,
    };
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe(
        RUNTIME_HEALTH_FAILURE_KINDS.LIVE_EVENTS_DISCONNECTED
      );
      expect(result.current.status).toBe(RUNTIME_HEALTH_STATUSES.DEGRADED);
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
