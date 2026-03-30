import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import AppShell from "../AppShell";
import {
  LIVE_EVENT_CONNECTION_STATES,
  RUNTIME_HEALTH_STATUSES,
} from "@/contracts/runtimeTokens";

const runtimeHealthState = {
  status: RUNTIME_HEALTH_STATUSES.HEALTHY,
  failureKind: null,
  llmDetail: null,
  lastSuccessAt: Date.parse("2026-03-20T12:00:00Z"),
  backendReachable: true,
  chatHealthy: true,
  llmHealthy: true,
  liveEventsStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
  lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
  stale: false,
};
const routeCapabilityState = {
  ready: true,
  state: "available" as const,
};
const listCodexEntriesSpy = vi.hoisted(() => vi.fn(async () => []));

vi.mock("@/hooks/useRuntimeHealth", () => ({
  default: () => runtimeHealthState,
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
        attachCompletionIdentity: vi.fn(),
        failActiveCompletion: vi.fn(),
        cancelActiveCompletion: vi.fn(),
      };
    }
    static subscribeActiveSpine() {
      return () => {};
    }
  },
}));

vi.mock("@/api/codex", () => ({
  listCodexEntries: listCodexEntriesSpy,
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
  Button: ({ children }: { children?: ReactNode }) => <button>{children}</button>,
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
}));

function installMatchMedia(prefersDark = false) {
  window.matchMedia = ((query: string) => ({
    matches: query === "(prefers-color-scheme: dark)" ? prefersDark : false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

function renderWordmark(themeMode: "light" | "dark") {
  window.localStorage.setItem("cfy.themeMode", themeMode);
  render(<AppShell />);
  return screen.getByRole("button", { name: "Codexify" });
}

describe("AppShell logo wordmark color contract", () => {
  beforeEach(() => {
    localStorage.clear();
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    routeCapabilityState.ready = true;
    routeCapabilityState.state = "available";
    listCodexEntriesSpy.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("binds the wordmark to the text token instead of a raw color literal across light and dark themes", () => {
    const lightWordmark = renderWordmark("light");
    expect(lightWordmark.style.color).toBe("var(--text-on-accent)");
    expect(lightWordmark.getAttribute("style")).not.toMatch(/#|rgb|hsl/i);

    const lightShell = lightWordmark.closest("div[style*='--text-on-accent:']");
    expect(lightShell).not.toBeNull();
    expect(lightShell?.getAttribute("style")).toContain(
      "--text-on-accent: #111827"
    );

    cleanup();

    const darkWordmark = renderWordmark("dark");
    expect(darkWordmark.style.color).toBe("var(--text-on-accent)");
    expect(darkWordmark.getAttribute("style")).not.toMatch(/#|rgb|hsl/i);

    const darkShell = darkWordmark.closest("div[style*='--text-on-accent:']");
    expect(darkShell).not.toBeNull();
    expect(darkShell?.getAttribute("style")).toContain(
      "--text-on-accent: #f9fafb"
    );
  });

  it("skips codex bootstrap when the restricted profile marks codex unavailable", () => {
    routeCapabilityState.state = "unavailable";

    render(<AppShell />);

    expect(listCodexEntriesSpy).not.toHaveBeenCalled();
  });
});
