import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AppShell from "@/components/persona/layout/AppShell";
import {
  LIVE_EVENT_CONNECTION_STATES,
  LiveEventConnectionState,
  RUNTIME_HEALTH_FAILURE_KINDS,
  RUNTIME_HEALTH_STATUSES,
  RuntimeHealthFailureKindToken,
  RuntimeHealthStatusToken,
} from "@/contracts/runtimeTokens";

type RuntimeHealthMock = {
  status: RuntimeHealthStatusToken;
  failureKind: RuntimeHealthFailureKindToken | "unknown" | null;
  llmDetail: string | null;
  lastSuccessAt: number | null;
  lastFailedAt: number | null;
  backendReachable: boolean | null;
  chatHealthy: boolean | null;
  llmHealthy: boolean | null;
  liveEventsStatus: LiveEventConnectionState;
  lastCheckedAt: number | null;
  stale: boolean;
  diagnostics: {
    resolvedApiBaseUrl: string | null;
    resolvedApiBaseUrlSource: string;
    apiKeyPresent: boolean;
    apiKeySource: string;
    hydrationState: "pending" | "ready" | "failed";
    nativeCommandStatus: string | null;
    authSource: string;
    chat: {
      endpoint: string;
      httpStatus: number | null;
      transportErrorClass: string | null;
      parsedStatus: string | null;
      parsedOk: boolean | null;
    };
    llm: {
      endpoint: string;
      httpStatus: number | null;
      transportErrorClass: string | null;
      parsedStatus: string | null;
      parsedOk: boolean | null;
      detailsStatus?: string | null;
      detailsOk?: boolean | null;
      provider?: string | null;
      model?: string | null;
      providerRuntimeAvailable?: boolean | null;
      endpointResolutionState?: string | null;
      failureReason?: string | null;
    };
    liveEvents: {
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
    failureKind: RuntimeHealthFailureKindToken | "unknown" | null;
    lastSuccessAt: number | null;
    lastFailedAt: number | null;
    lastCheckedAt: number | null;
    currentComputedStateSource: string;
  };
};

const runtimeHealthState: RuntimeHealthMock = {
  status: RUNTIME_HEALTH_STATUSES.HEALTHY,
  failureKind: null,
  llmDetail: null,
  lastSuccessAt: Date.parse("2026-03-20T12:00:00Z"),
  lastFailedAt: null,
  backendReachable: true,
  chatHealthy: true,
  llmHealthy: true,
  liveEventsStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
  lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
  stale: false,
  diagnostics: {
    resolvedApiBaseUrl: "http://127.0.0.1:8888/api",
    resolvedApiBaseUrlSource: "runtime-desktop",
    apiKeyPresent: true,
    apiKeySource: "runtime-desktop",
    hydrationState: "ready",
    nativeCommandStatus: "ready",
    authSource: "runtime-desktop",
    chat: {
      endpoint: "/health/chat",
      httpStatus: 200,
      transportErrorClass: null,
      parsedStatus: "healthy",
      parsedOk: true,
    },
      llm: {
        endpoint: "/api/health/llm",
        httpStatus: 200,
        transportErrorClass: null,
        parsedStatus: "online",
        parsedOk: true,
        detailsStatus: "online",
        detailsOk: true,
        provider: "local",
        model: "library2/ministral-3:8b",
        providerRuntimeAvailable: true,
        endpointResolutionState: "available",
        failureReason: null,
      },
    liveEvents: {
      endpoint: "http://127.0.0.1:8888/api/events",
      connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
      lastEventAt: Date.parse("2026-03-20T11:59:58Z"),
      lastPingAt: Date.parse("2026-03-20T11:59:58Z"),
      statusUpdatedAt: Date.parse("2026-03-20T12:00:00Z"),
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
    },
    failureKind: null,
    lastSuccessAt: Date.parse("2026-03-20T12:00:00Z"),
    lastFailedAt: null,
    lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
    currentComputedStateSource: "live-poll",
  },
};
const routeCapabilityState = {
  ready: true,
  state: "available" as const,
};

vi.mock("@/hooks/useRuntimeHealth", () => ({
  default: () => runtimeHealthState,
  formatRuntimeHealthDiagnostics: (diagnostics: typeof runtimeHealthState.diagnostics) =>
    [
      `resolved api base url=${diagnostics.resolvedApiBaseUrl ?? "<unresolved>"}`,
      `resolved api base url source=${diagnostics.resolvedApiBaseUrlSource}`,
      `apiKeyPresent=${diagnostics.apiKeyPresent ? "true" : "false"}`,
      `api key source=${diagnostics.apiKeySource}`,
      `hydration state=${diagnostics.hydrationState}`,
      `native command status=${diagnostics.nativeCommandStatus ?? "<unknown>"}`,
      `authSource=${diagnostics.authSource}`,
      `chat endpoint called=${diagnostics.chat.endpoint}`,
      `chat HTTP status=${diagnostics.chat.httpStatus ?? "<none>"}`,
      `parsed chat health status=${diagnostics.chat.parsedStatus ?? "<none>"}`,
      `parsed chat health ok=${
        diagnostics.chat.parsedOk == null
          ? "<unknown>"
          : diagnostics.chat.parsedOk
            ? "true"
            : "false"
      }`,
      `llm endpoint called=${diagnostics.llm.endpoint}`,
      `llm HTTP status=${diagnostics.llm.httpStatus ?? "<none>"}`,
      `parsed llm health status=${diagnostics.llm.parsedStatus ?? "<none>"}`,
      `parsed llm health ok=${
        diagnostics.llm.parsedOk == null
          ? "<unknown>"
          : diagnostics.llm.parsedOk
          ? "true"
          : "false"
      }`,
      `parsed llm details status=${diagnostics.llm.detailsStatus ?? "<none>"}`,
      `parsed llm details ok=${
        diagnostics.llm.detailsOk == null
          ? "<unknown>"
          : diagnostics.llm.detailsOk
          ? "true"
          : "false"
      }`,
      `parsed llm provider=${diagnostics.llm.provider ?? "<none>"}`,
      `parsed llm model=${diagnostics.llm.model ?? "<none>"}`,
      `parsed llm provider runtime available=${
        diagnostics.llm.providerRuntimeAvailable == null
          ? "<unknown>"
          : diagnostics.llm.providerRuntimeAvailable
          ? "true"
          : "false"
      }`,
      `parsed llm endpoint resolution state=${
        diagnostics.llm.endpointResolutionState ?? "<none>"
      }`,
      `parsed llm failure reason=${diagnostics.llm.failureReason ?? "<none>"}`,
      `live events endpoint called=${diagnostics.liveEvents.endpoint ?? "<unresolved>"}`,
      `live events connection state=${diagnostics.liveEvents.connectionState}`,
      `live events last event=${diagnostics.liveEvents.lastEventAt ?? "<none>"}`,
      `live events last ping=${diagnostics.liveEvents.lastPingAt ?? "<none>"}`,
      `live events HTTP status=${diagnostics.liveEvents.lastHttpStatus ?? "<none>"}`,
      `live events transport error class=${diagnostics.liveEvents.transportErrorClass ?? "<none>"}`,
      `live events authSource=${diagnostics.liveEvents.authSource}`,
      `live events apiKeyPresent=${diagnostics.liveEvents.apiKeyPresent ? "true" : "false"}`,
      `live events hydration state=${diagnostics.liveEvents.hydrationState}`,
      `live events native command status=${diagnostics.liveEvents.nativeCommandStatus ?? "<unknown>"}`,
      `live events reconnect attempts=${diagnostics.liveEvents.reconnectAttempts}`,
      `live events status updated=${diagnostics.liveEvents.statusUpdatedAt ?? "<none>"}`,
      `failureKind=${diagnostics.failureKind ?? "none"}`,
      `last successful health poll=${diagnostics.lastSuccessAt ?? "<none>"}`,
      `last failed health poll=${diagnostics.lastFailedAt ?? "<none>"}`,
      `current health poll=${diagnostics.lastCheckedAt ?? "<none>"}`,
      `current computed state source=${diagnostics.currentComputedStateSource}`,
    ],
}));

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: () => ({
    ready: routeCapabilityState.ready,
    state: routeCapabilityState.state,
    mounted: [],
    declared: {},
  }),
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    lastEvent: null,
    subscribe: () => () => {},
    connected: true,
    connectionStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
    statusUpdatedAt: Date.now(),
  }),
}));

vi.mock("@/hooks/useWallpaperUrl", () => ({
  useWallpaperUrl: () => ({ wallpaperUrl: null }),
}));

vi.mock("@/hooks/useUploader", () => ({
  default: () => ({
    uploadFiles: vi.fn(),
    uploading: false,
  }),
}));

vi.mock("@/hooks/useBreakpoint", () => ({
  useBreakpoint: () => "lg",
}));

vi.mock("@/lib/authState", () => ({
  useAuthState: () => ({
    ready: true,
    status: "authenticated",
    token: "test-token",
  }),
  checkAuthGate: () => true,
}));

vi.mock("@/state/session/SessionSpine", () => ({
  SessionSpine: class {
    static getRegisteredSpine() {
      return {
        isComposerBlocked: () => false,
        getActiveCompletion: () => null,
        consumeAcceptedLiveEvent: vi.fn(),
        findTabIdForThread: () => null,
        getActiveTabId: () => null,
        rememberSubmittedDraft: vi.fn(),
        startCompletion: vi.fn(),
      };
    }
    static subscribeActiveSpine() {
      return () => {};
    }
  },
}));

vi.mock("@/api/codex", () => ({
  listCodexEntries: vi.fn(async () => []),
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(async () => ({ data: {} })),
    post: vi.fn(async () => ({ data: {} })),
    delete: vi.fn(async () => ({ data: {} })),
    interceptors: {
      request: { use: vi.fn(() => 1), eject: vi.fn() },
      response: { use: vi.fn(() => 2), eject: vi.fn() },
    },
  },
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({ children }: { children?: ReactNode }) => (
    <button>{children}</button>
  ),
}));

vi.mock("@/components/ui/input", () => ({
  Input: () => <input data-testid="input-mock" />,
}));

vi.mock("@/components/ui/RefractiveGlassCard", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/features/chat/GuardianChat", () => ({
  default: () => <div data-testid="guardian-chat-mock" />,
}));

vi.mock("@/features/workspace/WorkspacePane", () => ({
  default: () => <div data-testid="workspace-pane-mock" />,
}));

vi.mock("@/components/dashboard/DashboardView", () => ({
  default: () => <div data-testid="dashboard-view-mock" />,
}));

vi.mock("@/features/settings/SettingsView", () => ({
  default: () => <div data-testid="settings-view-mock" />,
}));

vi.mock("@/components/ErrorBoundary", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/components/documents/DocumentsView", () => ({
  default: () => <div data-testid="documents-view-mock" />,
}));

vi.mock("@/components/persona/layout/GuardianChatWithSidebar", () => ({
  default: () => <div data-testid="guardian-chat-with-sidebar-mock" />,
}));

vi.mock("@/components/ui/ToastPortal", () => ({
  default: () => null,
}));

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/components/modals/ImageGenModal", () => ({
  ImageGenModal: () => null,
}));

vi.mock("@/components/ShareButton", () => ({
  ShareButton: () => <button type="button">Share</button>,
}));

vi.mock("@/theme", () => ({
  injectCssVars: vi.fn(),
  applySurfaceWarmth: vi.fn((base: string) => base),
  normalizeSurfaceWarmth: vi.fn((value: number) => value),
}));

describe("AppShell system status indicator", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
        key: vi.fn(() => null),
        length: 0,
      },
      configurable: true,
    });
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.HEALTHY;
    runtimeHealthState.failureKind = null;
    runtimeHealthState.llmDetail = null;
    runtimeHealthState.backendReachable = true;
    runtimeHealthState.chatHealthy = true;
    runtimeHealthState.llmHealthy = true;
    runtimeHealthState.liveEventsStatus = LIVE_EVENT_CONNECTION_STATES.CONNECTED;
    runtimeHealthState.stale = false;
    runtimeHealthState.lastSuccessAt = Date.parse("2026-03-20T12:00:00Z");
    runtimeHealthState.lastFailedAt = null;
    routeCapabilityState.ready = true;
    routeCapabilityState.state = "available";
    runtimeHealthState.diagnostics = {
      resolvedApiBaseUrl: "http://127.0.0.1:8888/api",
      resolvedApiBaseUrlSource: "runtime-desktop",
      apiKeyPresent: true,
      apiKeySource: "runtime-desktop",
      hydrationState: "ready",
      nativeCommandStatus: "ready",
      authSource: "runtime-desktop",
      chat: {
        endpoint: "/health/chat",
        httpStatus: 200,
        transportErrorClass: null,
        parsedStatus: "healthy",
        parsedOk: true,
      },
    llm: {
      endpoint: "/api/health/llm",
      httpStatus: 200,
      transportErrorClass: null,
      parsedStatus: "online",
      parsedOk: true,
      detailsStatus: "online",
      detailsOk: true,
      provider: "local",
      model: "library2/ministral-3:8b",
      providerRuntimeAvailable: true,
      endpointResolutionState: "available",
      failureReason: null,
    },
      liveEvents: {
        endpoint: "http://127.0.0.1:8888/api/events",
        connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
        lastEventAt: Date.parse("2026-03-20T11:59:58Z"),
        lastPingAt: Date.parse("2026-03-20T11:59:58Z"),
        statusUpdatedAt: Date.parse("2026-03-20T12:00:00Z"),
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
      },
      failureKind: null,
      lastSuccessAt: Date.parse("2026-03-20T12:00:00Z"),
      lastFailedAt: null,
      lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
      currentComputedStateSource: "live-poll",
    };
    if (!window.matchMedia) {
      window.matchMedia = ((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as unknown as typeof window.matchMedia;
    }
  });

  it("keeps healthy runtime detail behind the green status indicator", () => {
    render(<AppShell />);

    const toggle = screen.getByTestId("system-status-toggle");
    expect(toggle).toHaveAttribute("aria-label", "System status: Healthy");
    expect(screen.queryByTestId("system-status-panel")).toBeNull();

    fireEvent.click(toggle);
    expect(
      screen.getByText(/Everything is working normally/i)
    ).toBeInTheDocument();
  });

  it.each([
    { hydration: "ready", backend: true, llm: null },
    { hydration: "failed", backend: null, llm: null },
    { hydration: "ready", backend: null, llm: true },
  ] as const)("keeps Providers checking without health observations: %j", ({ hydration, backend, llm }) => {
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.HEALTHY;
    runtimeHealthState.diagnostics.hydrationState = hydration;
    runtimeHealthState.backendReachable = backend;
    runtimeHealthState.llmHealthy = llm;
    render(<AppShell />);
    fireEvent.click(screen.getByTestId("system-status-toggle"));
    const providerRow = screen.getByText("Providers").parentElement!;
    expect(within(providerRow).getByText("Checking")).toBeInTheDocument();
    expect(within(providerRow).queryByText("Healthy")).toBeNull();
  });

  it("surfaces an unreachable Guardian as a critical status without a persistent banner", () => {
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.DEGRADED;
    runtimeHealthState.failureKind =
      RUNTIME_HEALTH_FAILURE_KINDS.BACKEND_UNREACHABLE;
    runtimeHealthState.backendReachable = false;
    runtimeHealthState.lastSuccessAt = Date.parse("2026-03-20T11:55:00Z");
    runtimeHealthState.lastFailedAt = Date.parse("2026-03-20T11:54:30Z");
    runtimeHealthState.diagnostics = {
      resolvedApiBaseUrl: "http://127.0.0.1:8888/api",
      resolvedApiBaseUrlSource: "runtime-desktop",
      apiKeyPresent: true,
      apiKeySource: "runtime-desktop",
      hydrationState: "ready",
      nativeCommandStatus: "ready",
      authSource: "runtime-desktop",
      chat: {
        endpoint: "/health/chat",
        httpStatus: 503,
        transportErrorClass: null,
        parsedStatus: "degraded",
        parsedOk: false,
      },
      llm: {
        endpoint: "/api/health/llm",
        httpStatus: 200,
        transportErrorClass: null,
        parsedStatus: "online",
        parsedOk: true,
        detailsStatus: "online",
        detailsOk: true,
        provider: "local",
        model: "library2/ministral-3:8b",
        providerRuntimeAvailable: true,
        endpointResolutionState: "available",
        failureReason: null,
      },
      liveEvents: {
        endpoint: "http://127.0.0.1:8888/api/events",
        connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
        lastEventAt: Date.parse("2026-03-20T11:59:58Z"),
        lastPingAt: Date.parse("2026-03-20T11:59:58Z"),
        statusUpdatedAt: Date.parse("2026-03-20T12:00:00Z"),
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
      },
      failureKind: RUNTIME_HEALTH_FAILURE_KINDS.BACKEND_UNREACHABLE,
      lastSuccessAt: Date.parse("2026-03-20T11:55:00Z"),
      lastFailedAt: Date.parse("2026-03-20T11:54:30Z"),
      lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
      currentComputedStateSource: "live-poll",
    };

    render(<AppShell />);

    const toggle = screen.getByTestId("system-status-toggle");
    expect(toggle).toHaveAttribute("aria-label", "System status: Action required");
    expect(screen.queryByText(/Provider offline/i)).toBeNull();

    fireEvent.click(toggle);
    expect(screen.getByText(/Provider offline/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Guardian cannot be reached/i)
    ).toBeInTheDocument();
  });

  it("does not elevate the intentionally ignored missing health endpoint state", () => {
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.DEGRADED;
    runtimeHealthState.failureKind =
      RUNTIME_HEALTH_FAILURE_KINDS.HEALTH_ENDPOINT_MISSING;
    runtimeHealthState.lastSuccessAt = Date.parse("2026-03-20T11:55:00Z");
    runtimeHealthState.diagnostics.failureKind =
      RUNTIME_HEALTH_FAILURE_KINDS.HEALTH_ENDPOINT_MISSING;

    render(<AppShell />);

    expect(screen.getByTestId("system-status-toggle")).toHaveAttribute(
      "aria-label",
      "System status: Healthy"
    );
    expect(screen.queryByTestId("system-status-panel")).toBeNull();
  });

  it("surfaces llm_unhealthy degradation through the status panel", () => {
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.DEGRADED;
    runtimeHealthState.failureKind =
      RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY;
    runtimeHealthState.llmHealthy = false;
    runtimeHealthState.llmDetail =
      "MiniMax live discovery unavailable using documented model list";
    runtimeHealthState.lastSuccessAt = Date.parse("2026-03-20T11:55:00Z");
    runtimeHealthState.diagnostics.failureKind =
      RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY;
    runtimeHealthState.diagnostics.llm = {
      endpoint: "/api/health/llm",
      httpStatus: 200,
      transportErrorClass: null,
      parsedStatus: "offline",
      parsedOk: false,
      detailsStatus: "offline",
      detailsOk: false,
      provider: "local",
      model: "library2/ministral-3:8b",
      providerRuntimeAvailable: false,
      endpointResolutionState: "unavailable",
      failureReason: "provider_runtime.available=false",
    };
    runtimeHealthState.diagnostics.liveEvents = {
      endpoint: "http://127.0.0.1:8888/api/events",
      connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
      lastEventAt: Date.parse("2026-03-20T11:59:58Z"),
      lastPingAt: Date.parse("2026-03-20T11:59:58Z"),
      statusUpdatedAt: Date.parse("2026-03-20T12:00:00Z"),
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
    };

    render(<AppShell />);

    const toggle = screen.getByTestId("system-status-toggle");
    expect(toggle).toHaveAttribute("aria-label", "System status: Needs attention");
    expect(screen.queryByText(/Provider degraded/i)).toBeNull();
    fireEvent.click(toggle);

    expect(screen.getByText(/Provider degraded/i)).toBeInTheDocument();
    expect(
      screen.getByText(/MiniMax live discovery unavailable/i)
    ).toBeInTheDocument();
  });

  it("keeps a live updates warning behind the amber status indicator", () => {
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.HEALTHY;
    runtimeHealthState.failureKind = null;
    runtimeHealthState.liveEventsStatus = LIVE_EVENT_CONNECTION_STATES.DISCONNECTED;
    runtimeHealthState.diagnostics.failureKind = null;
    runtimeHealthState.diagnostics.liveEvents = {
      endpoint: "http://127.0.0.1:8888/api/events",
      connectionState: LIVE_EVENT_CONNECTION_STATES.DISCONNECTED,
      lastEventAt: Date.parse("2026-03-20T11:45:00Z"),
      lastPingAt: Date.parse("2026-03-20T11:45:00Z"),
      statusUpdatedAt: Date.parse("2026-03-20T11:45:00Z"),
      lastHttpStatus: 200,
      transportErrorClass: null,
      authSource: "runtime-desktop",
      apiKeyPresent: true,
      hydrationState: "ready",
      nativeCommandStatus: "ready",
      reconnectAttempts: 3,
      retryMs: 5000,
      subscribers: 1,
      readyState: 2,
      lastErrorAt: Date.parse("2026-03-20T11:46:00Z"),
      lastEventId: "evt-2",
    };

    render(<AppShell />);

    const toggle = screen.getByTestId("system-status-toggle");
    expect(toggle).toHaveAttribute("aria-label", "System status: Needs attention");
    expect(screen.queryByText(/Live updates unavailable/i)).toBeNull();
    expect(screen.queryByText(/Provider degraded/i)).toBeNull();
    fireEvent.click(toggle);

    expect(screen.getByText(/Live updates unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/Nothing you need to fix/i)).toBeInTheDocument();
    expect(
      screen.getByText(/live events connection state=disconnected/i)
    ).toBeInTheDocument();
  });

  it("renders sanitized technical details when llm health is degraded", () => {
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.DEGRADED;
    runtimeHealthState.failureKind = RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY;
    runtimeHealthState.llmHealthy = false;
    runtimeHealthState.llmDetail =
      "MiniMax live discovery unavailable using documented model list";
    runtimeHealthState.lastFailedAt = Date.parse("2026-03-20T11:54:30Z");
    runtimeHealthState.diagnostics = {
      resolvedApiBaseUrl: "http://127.0.0.1:8888/api",
      resolvedApiBaseUrlSource: "runtime-desktop",
      apiKeyPresent: true,
      apiKeySource: "runtime-desktop",
      hydrationState: "ready",
      nativeCommandStatus: "ready",
      authSource: "runtime-desktop",
      chat: {
        endpoint: "/health/chat",
        httpStatus: 200,
        transportErrorClass: null,
        parsedStatus: "healthy",
        parsedOk: true,
      },
      llm: {
        endpoint: "/api/health/llm",
        httpStatus: 200,
        transportErrorClass: null,
        parsedStatus: "offline",
        parsedOk: false,
        detailsStatus: "offline",
        detailsOk: false,
        provider: "local",
        model: "library2/ministral-3:8b",
        providerRuntimeAvailable: false,
        endpointResolutionState: "unavailable",
        failureReason: "provider_runtime.available=false",
      },
      liveEvents: {
        endpoint: "http://127.0.0.1:8888/api/events",
        connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
        lastEventAt: Date.parse("2026-03-20T11:59:58Z"),
        lastPingAt: Date.parse("2026-03-20T11:59:58Z"),
        statusUpdatedAt: Date.parse("2026-03-20T12:00:00Z"),
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
      },
      failureKind: RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY,
      lastSuccessAt: Date.parse("2026-03-20T11:55:00Z"),
      lastFailedAt: Date.parse("2026-03-20T11:54:30Z"),
      lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
      currentComputedStateSource: "live-poll",
    };

    render(<AppShell />);

    expect(screen.queryByText(/Technical details/i)).toBeNull();
    fireEvent.click(screen.getByTestId("system-status-toggle"));

    expect(screen.getByText(/Technical details/i)).toBeInTheDocument();
    expect(
      screen.getByText(/resolved api base url=http:\/\/127\.0\.0\.1:8888\/api/i)
    ).toBeInTheDocument();
    expect(screen.getAllByText(/^apiKeyPresent=true$/i)[0]).toBeInTheDocument();
    expect(
      screen.getAllByText(/^authSource=runtime-desktop$/i)[0]
    ).toBeInTheDocument();
    expect(screen.getByText(/chat endpoint called=\/health\/chat/i)).toBeInTheDocument();
    expect(screen.getByText(/llm endpoint called=\/api\/health\/llm/i)).toBeInTheDocument();
    expect(screen.getByText(/parsed llm details status=offline/i)).toBeInTheDocument();
    expect(screen.getByText(/parsed llm provider=local/i)).toBeInTheDocument();
    expect(
      screen.getByText(/parsed llm model=library2\/ministral-3:8b/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/parsed llm provider runtime available=false/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/parsed llm endpoint resolution state=unavailable/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/failureKind=llm_unhealthy/i)).toBeInTheDocument();
    expect(screen.queryByText("desktop-secret-key")).toBeNull();
  });

  it("reports chat_unhealthy as a Guardian issue without blaming the provider", () => {
    runtimeHealthState.status = RUNTIME_HEALTH_STATUSES.DEGRADED;
    runtimeHealthState.failureKind =
      RUNTIME_HEALTH_FAILURE_KINDS.CHAT_UNHEALTHY;
    runtimeHealthState.chatHealthy = false;
    runtimeHealthState.diagnostics = {
      resolvedApiBaseUrl: "http://127.0.0.1:8888/api",
      resolvedApiBaseUrlSource: "runtime-desktop",
      apiKeyPresent: true,
      apiKeySource: "runtime-desktop",
      hydrationState: "ready",
      nativeCommandStatus: "ready",
      authSource: "runtime-desktop",
      chat: {
        endpoint: "/health/chat",
        httpStatus: 503,
        transportErrorClass: null,
        parsedStatus: "degraded",
        parsedOk: false,
      },
      llm: {
        endpoint: "/api/health/llm",
        httpStatus: 200,
        transportErrorClass: null,
        parsedStatus: "online",
        parsedOk: true,
        detailsStatus: "online",
        detailsOk: true,
        provider: "local",
        model: "library2/ministral-3:8b",
        providerRuntimeAvailable: true,
        endpointResolutionState: "available",
        failureReason: null,
      },
      liveEvents: {
        endpoint: "http://127.0.0.1:8888/api/events",
        connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
        lastEventAt: Date.parse("2026-03-20T11:59:58Z"),
        lastPingAt: Date.parse("2026-03-20T11:59:58Z"),
        statusUpdatedAt: Date.parse("2026-03-20T12:00:00Z"),
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
      },
      failureKind: RUNTIME_HEALTH_FAILURE_KINDS.CHAT_UNHEALTHY,
      lastSuccessAt: Date.parse("2026-03-20T11:55:00Z"),
      lastFailedAt: Date.parse("2026-03-20T11:54:30Z"),
      lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
      currentComputedStateSource: "live-poll",
    };

    render(<AppShell />);

    const toggle = screen.getByTestId("system-status-toggle");
    expect(toggle).toHaveAttribute("aria-label", "System status: Needs attention");
    expect(screen.queryByText(/Provider degraded/i)).toBeNull();
    fireEvent.click(toggle);

    expect(screen.getByText(/Guardian health degraded/i)).toBeInTheDocument();
    expect(screen.queryByText(/Provider degraded/i)).toBeNull();
    expect(screen.getByText(/failureKind=chat_unhealthy/i)).toBeInTheDocument();
  });
});
