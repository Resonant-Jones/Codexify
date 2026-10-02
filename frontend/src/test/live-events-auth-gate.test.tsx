import { renderHook, waitFor, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import {
  clearRuntimeApiKey,
  default as api,
  getAuthToken,
  setAuthToken,
  setRuntimeApiKey,
} from "@/lib/api";
import {
  getAuthState,
  __resetAuthStateForTests,
  __setAuthStateForTests,
} from "@/lib/authState";
import { __resetLiveEventsHubForTests } from "@/lib/liveEventsHub";
import { useAuth } from "@/components/auth/useAuth";

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
const originalAdapter = api.defaults.adapter;
const runtimeState = vi.hoisted(() => ({
  hydrationState: "ready" as "pending" | "ready" | "failed",
  authMode: "local" as "local" | "remote",
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
          authMode: runtimeState.authMode,
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
    authMode: runtimeState.authMode,
  }),
  resolveApiUrl: (url: string) => url,
  subscribeRuntimeConfigState: () => () => {},
  isTauriRuntime: () => true,
  resolveSseEndpoint: () => "http://127.0.0.1:8888/api/events",
}));

describe("useLiveEvents auth gating", () => {
  beforeEach(() => {
    createdSources.length = 0;
    runtimeState.hydrationState = "ready";
    runtimeState.authMode = "local";
    __resetAuthStateForTests();
    __resetLiveEventsHubForTests();
    clearRuntimeApiKey();
    setAuthToken(null);
    vi.spyOn(console, "debug").mockImplementation(() => {});
    vi.spyOn(console, "info").mockImplementation(() => {});
  });

  afterEach(() => {
    api.defaults.adapter = originalAdapter;
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

  it("keeps the account session after login and skips the operator event stream", async () => {
    runtimeState.authMode = "remote";
    const accountToken = "account-session-token";
    let loginRequests = 0;
    let threadAuthorization: string | undefined;
    api.defaults.adapter = async (config) => {
      if (String(config.url).includes("/auth/login")) {
        loginRequests += 1;
        return {
          config,
          data: { token: accountToken, user_id: "account-a", expires_at: 0 },
          headers: {},
          status: 200,
          statusText: "OK",
        };
      }
      if (String(config.url).includes("/chat/threads")) {
        const headers = config.headers as any;
        threadAuthorization =
          headers?.get?.("Authorization") ??
          headers?.Authorization ??
          headers?.authorization;
        return {
          config,
          data: { threads: [] },
          headers: {},
          status: 200,
          statusText: "OK",
        };
      }
      throw new Error(`Unexpected request route: ${String(config.url)}`);
    };

    const auth = renderHook(() => useAuth());
    await act(async () => {
      await auth.result.current.login({ username: "person", password: "secret" });
    });
    const { result } = renderHook(() => useLiveEvents({ passive: true }));
    const response = await api.get("/chat/threads");

    expect(loginRequests).toBe(1);
    expect(createdSources).toHaveLength(0);
    expect(result.current.connectionStatus).toBe("disconnected");
    expect(threadAuthorization).toBe(`Bearer ${accountToken}`);
    expect(response.status).toBe(200);
    expect(getAuthToken()).toBe(accountToken);
    expect(window.sessionStorage.getItem("guardian.auth.token")).toBe(
      accountToken
    );
    expect(getAuthState().status).toBe("authenticated");
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

  it("keeps auth state and stops reconnecting after an operator stream 401", async () => {
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "account-session-token",
    });
    setAuthToken("account-session-token");
    setRuntimeApiKey("desktop-key");

    const { result } = renderHook(() => useLiveEvents({ passive: true }));
    await waitFor(() => {
      expect(createdSources).toHaveLength(1);
    });

    const unauthorized = createdSources[0].options.onUnauthorized as
      | (() => void)
      | undefined;
    expect(unauthorized).toBeTypeOf("function");
    act(() => unauthorized?.());

    await waitFor(() => {
      expect(result.current.diagnostics.lastHttpStatus).toBe(401);
      expect(result.current.connectionStatus).toBe("disconnected");
    });
    await new Promise((resolve) => setTimeout(resolve, 40));

    expect(createdSources).toHaveLength(1);
    expect(getAuthState().status).toBe("authenticated");
    expect(getAuthToken()).toBe("account-session-token");
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
