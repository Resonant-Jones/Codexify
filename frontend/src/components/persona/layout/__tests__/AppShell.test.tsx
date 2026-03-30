import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import AppShell from "../AppShell";
import api from "@/lib/api";
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

vi.mock("@/hooks/useRuntimeHealth", () => ({
  default: () => runtimeHealthState,
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
  Button: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock("@/components/ui/input", () => ({
  Input: (props: Record<string, unknown>) => <input {...props} />,
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
  default: ({
    onRequestNewProject,
  }: {
    onRequestNewProject: () => void;
  }) => (
    <div data-testid="dashboard-view-mock">
      <button type="button" onClick={onRequestNewProject}>
        New Project
      </button>
    </div>
  ),
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

const mockApi = api as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

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
  return screen.findByRole("button", { name: "Codexify" });
}

describe("AppShell logo wordmark color contract", () => {
  beforeEach(() => {
    localStorage.clear();
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    mockApi.get.mockClear();
    mockApi.post.mockClear();
    mockApi.delete.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
    cleanup();
  });

  it(
    "binds the wordmark to a theme token instead of a raw color literal across light and dark themes",
    async () => {
      const lightWordmark = await renderWordmark("light");
      await waitFor(() => {
        expect(lightWordmark.style.color).toBe("var(--text-on-accent)");
      });
      expect(lightWordmark.getAttribute("style")).not.toMatch(/#|rgb|hsl/i);

      const lightShell = lightWordmark.closest("div[style*='--text:']");
      expect(lightShell).not.toBeNull();
      expect(lightShell?.getAttribute("style")).toContain("--text: #111827");
      expect(lightShell?.getAttribute("style")).toContain(
        "--text-on-accent: #111827"
      );

      cleanup();

      const darkWordmark = await renderWordmark("dark");
      await waitFor(() => {
        expect(darkWordmark.style.color).toBe("var(--text-on-accent)");
      });
      expect(darkWordmark.getAttribute("style")).not.toMatch(/#|rgb|hsl/i);

      const darkShell = darkWordmark.closest("div[style*='--text:']");
      expect(darkShell).not.toBeNull();
      expect(darkShell?.getAttribute("style")).toContain("--text: #ffffff");
      expect(darkShell?.getAttribute("style")).toContain(
        "--text-on-accent: #f9fafb"
      );
    },
    15_000
  );
});

describe("AppShell dashboard create project flow", () => {
  beforeEach(() => {
    localStorage.clear();
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    localStorage.setItem("cfy.lastView", "dashboard");
    mockApi.get.mockClear();
    mockApi.post.mockClear();
    mockApi.delete.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("submits through the runtime API contract and falls back to the mounted projects route on 404", async () => {
    mockApi.post
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValueOnce({ data: { id: 321 } });

    render(<AppShell />);

    fireEvent.click(screen.getByRole("button", { name: "New Project" }));
    fireEvent.change(screen.getByLabelText(/project name/i), {
      target: { value: "Atlas" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create project/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenNthCalledWith(1, "/api/projects", {
        name: "Atlas",
        icon: "📁",
      });
      expect(mockApi.post).toHaveBeenNthCalledWith(2, "/projects", {
        name: "Atlas",
        icon: "📁",
      });
    });

    await waitFor(() => {
      expect(screen.queryByLabelText(/project name/i)).not.toBeInTheDocument();
    });
  });
});
