import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useRuntimeHealth } from "@/hooks/useRuntimeHealth";

type LiveEventsStatus = {
  connected: boolean;
  connectionStatus: "connecting" | "connected" | "reconnecting" | "disconnected";
  statusUpdatedAt: number | null;
};

const apiGet = vi.fn();
let liveEventsStatus: LiveEventsStatus = {
  connected: true,
  connectionStatus: "connected",
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
  backend?: "ok" | "fail" | "missing";
  chat?: "ok" | "fail" | "missing";
  llm?: "ok" | "fail" | "missing";
} = {}) {
  const backend = overrides.backend ?? "ok";
  const chat = overrides.chat ?? "ok";
  const llm = overrides.llm ?? "ok";

  apiGet.mockImplementation((path: string) => {
    if (path === "/health") {
      if (backend === "ok") {
        return Promise.resolve({ data: { status: "ok" } });
      }
      if (backend === "missing") {
        const error = new Error("not found") as Error & {
          response?: { status?: number };
        };
        error.response = { status: 404 };
        return Promise.reject(error);
      }
      return Promise.reject(new Error("backend down"));
    }
    if (path === "/health/chat") {
      if (chat === "ok") {
        return Promise.resolve({ data: { ok: true } });
      }
      if (chat === "missing") {
        const error = new Error("not found") as Error & {
          response?: { status?: number };
        };
        error.response = { status: 404 };
        return Promise.reject(error);
      }
      return Promise.resolve({ data: { ok: false } });
    }
    if (path === "/health/llm") {
      if (llm === "ok") {
        return Promise.resolve({ data: { ok: true } });
      }
      if (llm === "missing") {
        const error = new Error("not found") as Error & {
          response?: { status?: number };
        };
        error.response = { status: 404 };
        return Promise.reject(error);
      }
      return Promise.resolve({ data: { ok: false } });
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
      connectionStatus: "connected",
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
      expect(result.current.status).toBe("healthy");
    });
  });

  it("flags backend unreachable", async () => {
    mockHealthResponses({ backend: "fail" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe("backend_unreachable");
      expect(result.current.status).toBe("degraded");
    });
  });

  it("treats /health 404 as missing endpoint, not backend unreachable", async () => {
    mockHealthResponses({ backend: "missing" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.backendReachable).toBe(true);
      expect(result.current.failureKind).toBe("health_endpoint_missing");
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
      expect(result.current.failureKind).toBe("health_endpoint_missing");
    });
  });

  it("flags chat unhealthy", async () => {
    mockHealthResponses({ chat: "fail" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe("chat_unhealthy");
    });
  });

  it("flags llm unhealthy", async () => {
    mockHealthResponses({ llm: "fail" });
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe("llm_unhealthy");
    });
  });

  it("flags stale when no successful check within the window", async () => {
    mockHealthResponses();
    const { result, rerender } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.status).toBe("healthy");
    });

    act(() => {
      vi.setSystemTime(new Date("2026-03-20T12:01:00.000Z"));
    });
    rerender();
    expect(result.current.failureKind).toBe("stale");
    expect(result.current.status).toBe("degraded");
  });

  it("flags live events disconnected after the threshold", async () => {
    mockHealthResponses();
    liveEventsStatus = {
      connected: false,
      connectionStatus: "disconnected",
      statusUpdatedAt: Date.now() - 46_000,
    };
    const { result } = renderHook(() => useRuntimeHealth());
    await act(async () => {
      await flushPromises();
    });
    await waitFor(() => {
      expect(result.current.failureKind).toBe("live_events_disconnected");
      expect(result.current.status).toBe("degraded");
    });
  });
});
