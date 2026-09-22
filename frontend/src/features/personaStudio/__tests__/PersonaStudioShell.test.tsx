import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AppShell from "@/components/persona/layout/AppShell";
import {
  LIVE_EVENT_CONNECTION_STATES,
  RUNTIME_HEALTH_STATUSES,
} from "@/contracts/runtimeTokens";
import {
  personaStudioApiMock,
  resetPersonaStudioApiMock,
} from "./personaStudioApiMock";

vi.mock("@/lib/authState", () => ({
  checkAuthGate: () => true,
  useAuthState: () => ({ user: null, token: null, loading: false }),
}));
vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({ connected: false, lastEvent: null }),
}));
vi.mock("@/hooks/useRuntimeHealth", () => ({
  default: () => ({
    status: RUNTIME_HEALTH_STATUSES.UNAVAILABLE,
    failureKind: null,
    llmDetail: null,
    lastSuccessAt: null,
    backendReachable: null,
    chatHealthy: null,
    llmHealthy: null,
    liveEventsStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
    lastCheckedAt: null,
    lastFailedAt: null,
    stale: false,
    diagnostics: {
      resolvedApiBaseUrl: null, resolvedApiBaseUrlSource: "unknown", apiKeyPresent: false,
      apiKeySource: "unknown", hydrationState: "ready", nativeCommandStatus: null,
      authSource: "unknown", failureKind: null, lastSuccessAt: null, lastFailedAt: null,
      lastCheckedAt: null, currentComputedStateSource: "fallback",
      chat: { endpoint: "/health/chat", httpStatus: null, transportErrorClass: null, parsedStatus: null, parsedOk: null, detailsStatus: null, detailsOk: null, providerRuntimeAvailable: null, endpointResolutionState: null, failureReason: null },
      llm: { endpoint: "/api/health/llm", httpStatus: null, transportErrorClass: null, parsedStatus: null, parsedOk: null, detailsStatus: null, detailsOk: null, providerRuntimeAvailable: null, endpointResolutionState: null, failureReason: null },
      liveEvents: { connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED, connected: true, statusUpdatedAt: null },
    },
  }),
}));
vi.mock("@/hooks/useWallpaperUrl", () => ({ useWallpaperUrl: () => null }));
vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);
vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: () => ({ ready: true, state: "available" }),
  SUPPORTED_PROFILE_ROUTE_LABELS: { CODEX: "codex", IMPRINT: "imprint", CONNECTORS: "connectors" },
}));
vi.mock("@/state/session/SessionSpine", () => ({
  SessionSpine: { getRegisteredSpine: () => null, subscribeActiveSpine: () => () => {} },
}));

beforeEach(() => {
  window.localStorage.clear();
  window.history.pushState({}, "", "/persona-studio");
  resetPersonaStudioApiMock();
});

describe("Persona Studio V2 AppShell integration", () => {
  it("keeps AppShell Dock authority and routes directly to the two-frame workspace", () => {
    render(<AppShell startupLocked={false} startupOverlay={null} />);

    expect(screen.getByTestId("app-shell-top-nav")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-page")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-assistant-frame")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-configuration-frame")).toBeInTheDocument();
    expect(screen.queryByTestId("persona-studio-framecard")).not.toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-page").closest("[data-active-view='personaStudio']")).toHaveAttribute("data-active-view-contract", "assistant-configuration");
  });

  it("retains the local-only Test boundary inside AppShell", async () => {
    const user = userEvent.setup();
    render(<AppShell startupLocked={false} startupOverlay={null} />);

    await user.click(screen.getByRole("tab", { name: /^test$/i }));
    expect(screen.getByTestId("persona-preview-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();
  });
});
