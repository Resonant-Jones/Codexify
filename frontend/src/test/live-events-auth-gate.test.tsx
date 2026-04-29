import { renderHook, waitFor, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import {
  clearRuntimeApiKey,
  setAuthToken,
  setRuntimeApiKey,
} from "@/lib/api";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
} from "@/lib/authState";
import { __resetLiveEventsHubForTests } from "@/lib/liveEventsHub";

type MockSource = {
  url: string;
  options: Record<string, unknown>;
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
};

const createdSources: MockSource[] = [];
const runtimeState = vi.hoisted(() => ({
  hydrationState: "ready" as "pending" | "ready" | "failed",
}));

vi.mock("@/lib/guardianEventSource", () => {
  class MockGuardianEventSource {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;

    url: string;
    options: Record<string, unknown>;
    readyState = MockGuardianEventSource.CONNECTING;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    addEventListener = vi.fn();
    removeEventListener = vi.fn();
    close = vi.fn();

    constructor(url: string, options: Record<string, unknown>) {
      this.url = url;
      this.options = options;
      createdSources.push(this as unknown as MockSource);
    }
  }

  return { GuardianEventSource: MockGuardianEventSource };
});

vi.mock("@/lib/runtimeConfig", () => ({
  getDesktopRuntimeAuthConfig: () =>
    runtimeState.hydrationState === "failed"
      ? null
      : {
          mode: "tauri",
          backendBaseUrl: "http://127.0.0.1:8888",
          apiBaseUrl: "http://127.0.0.1:8888/api",
          sseUrl: "http://127.0.0.1:8888/api/events",
          sharePublicBaseUrl: "http://127.0.0.1:5173",
          authMode: "local",
          apiKeyPresent: true,
          apiKey: "desktop-key",
          envPath: "/Users/chriscastillo/Codexify/.env",
          runtimeRoot: "/Users/chriscastillo/Codexify",
          failureKind: null,
          runtimeContext: "packaged",
        },
  getRuntimeConfigHydrationState: () => runtimeState.hydrationState,
  getRuntimeConfigVersion: () => 0,
  getRuntimeConfigSync: () => ({
    mode: "tauri",
    backendBaseUrl: "http://127.0.0.1:8888",
    apiBaseUrl: "http://127.0.0.1:8888/api",
    sseUrl: "http://127.0.0.1:8888/api/events",
    sharePublicBaseUrl: "http://127.0.0.1:5173",
    authMode: "local",
  }),
  subscribeRuntimeConfigState: () => () => {},
  isTauriRuntime: () => true,
  resolveSseEndpoint: () => "http://127.0.0.1:8888/api/events",
}));

describe("useLiveEvents auth gating", () => {
  beforeEach(() => {
    createdSources.length = 0;
    runtimeState.hydrationState = "ready";
    __resetAuthStateForTests();
    __resetLiveEventsHubForTests();
    clearRuntimeApiKey();
    setAuthToken(null);
    vi.spyOn(console, "debug").mockImplementation(() => {});
    vi.spyOn(console, "info").mockImplementation(() => {});
  });

  it("does not connect while auth is unresolved or unauthenticated", () => {
    __setAuthStateForTests({ status: "unknown", ready: false });
    const { unmount } = renderHook(() => useLiveEvents({ passive: true }));
    expect(createdSources).toHaveLength(0);
    unmount();

    __setAuthStateForTests({ status: "unauthenticated", ready: true });
    renderHook(() => useLiveEvents({ passive: true }));
    expect(createdSources).toHaveLength(0);
  });

  it("connects when authenticated and closes on unauthenticated transition", async () => {
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "token-1",
    });
    renderHook(() => useLiveEvents({ passive: true }));

    await waitFor(() => {
      expect(createdSources).toHaveLength(1);
    });

    const source = createdSources[0];
    act(() => {
      __setAuthStateForTests({ status: "unauthenticated", ready: true });
    });

    await waitFor(() => {
      expect(source.close).toHaveBeenCalledTimes(1);
    });
  });

  it("attaches the packaged runtime API key without letting a stale bearer shadow it", async () => {
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "stale-bearer-token",
    });
    setAuthToken("stale-bearer-token");
    setRuntimeApiKey("desktop-key");

    const { result } = renderHook(() => useLiveEvents({ passive: true }));

    await waitFor(() => {
      expect(createdSources).toHaveLength(1);
    });

    const source = createdSources[0];
    const headers = source.options.headers as Record<string, string>;

    expect(result.current.diagnostics.authSource).toBe("runtime-desktop");
    expect(result.current.diagnostics.apiKeyPresent).toBe(true);
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("desktop-key");
    expect(headers["Authorization"] ?? headers["authorization"]).toBe(
      "Bearer stale-bearer-token"
    );
    expect(JSON.stringify(result.current.diagnostics)).not.toContain(
      "desktop-key"
    );
    expect(JSON.stringify(result.current.diagnostics)).not.toContain(
      "stale-bearer-token"
    );
  });

  it("waits for runtime hydration before connecting live events", async () => {
    runtimeState.hydrationState = "pending";
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "token-1",
    });

    const { result, rerender } = renderHook(() => useLiveEvents({ passive: true }));

    expect(createdSources).toHaveLength(0);
    expect(result.current.diagnostics.hydrationState).toBe("pending");
    await waitFor(() => {
      expect(result.current.connectionStatus).toBe("connecting");
    });

    runtimeState.hydrationState = "ready";
    rerender();

    await waitFor(() => {
      expect(createdSources).toHaveLength(1);
      expect(result.current.diagnostics.hydrationState).toBe("ready");
      expect(result.current.diagnostics.authSource).toBe("runtime-desktop");
      expect(result.current.diagnostics.apiKeyPresent).toBe(true);
    });
  });
});
