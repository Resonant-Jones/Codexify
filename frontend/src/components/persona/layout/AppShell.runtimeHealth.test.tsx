import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import AppShell from "@/components/persona/layout/AppShell";

type RuntimeHealthMock = {
  status: "healthy" | "degraded";
  failureKind: string | null;
  lastSuccessAt: number | null;
  backendReachable: boolean | null;
  chatHealthy: boolean | null;
  llmHealthy: boolean | null;
  liveEventsStatus: "connecting" | "connected" | "reconnecting" | "disconnected";
  lastCheckedAt: number | null;
  stale: boolean;
};

const runtimeHealthState: RuntimeHealthMock = {
  status: "healthy",
  failureKind: null,
  lastSuccessAt: Date.parse("2026-03-20T12:00:00Z"),
  backendReachable: true,
  chatHealthy: true,
  llmHealthy: true,
  liveEventsStatus: "connected",
  lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
  stale: false,
};

vi.mock("@/hooks/useRuntimeHealth", () => ({
  default: () => runtimeHealthState,
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    lastEvent: null,
    subscribe: () => () => {},
    connected: true,
    connectionStatus: "connected",
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
}));

describe("AppShell runtime health banner", () => {
  beforeEach(() => {
    runtimeHealthState.status = "healthy";
    runtimeHealthState.failureKind = null;
    runtimeHealthState.lastSuccessAt = Date.parse("2026-03-20T12:00:00Z");
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

  it("does not render banner when runtime is healthy", () => {
    render(<AppShell />);
    expect(screen.queryByText(/Runtime degraded/i)).toBeNull();
  });

  it("renders banner when runtime is degraded with failure kind and last healthy", () => {
    runtimeHealthState.status = "degraded";
    runtimeHealthState.failureKind = "backend_unreachable";
    runtimeHealthState.lastSuccessAt = Date.parse("2026-03-20T11:55:00Z");

    render(<AppShell />);

    expect(screen.getByText(/Runtime degraded/i)).toBeInTheDocument();
    expect(
      screen.getByText(/failure:\s*backend_unreachable/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/last healthy:/i)).toBeInTheDocument();
  });
});
