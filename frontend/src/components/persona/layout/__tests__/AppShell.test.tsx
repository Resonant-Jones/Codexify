import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import AppShell from "../AppShell";
import api from "@/lib/api";
import {
  LIVE_EVENT_CONNECTION_STATES,
  RUNTIME_HEALTH_STATUSES,
} from "@/contracts/runtimeTokens";
import {
  DEFAULT_WORKSPACE_PANE_RATIO,
  MAX_WORKSPACE_PANE_RATIO,
  MIN_WORKSPACE_PRIMARY_PANE_WIDTH,
  WORKSPACE_LAYOUT_STORAGE_KEY,
} from "@/features/workspace/state/useWorkspaceLayoutMode";

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

const uploaderState = vi.hoisted(() => ({
  configs: [] as Array<{
    onImages?: (items: Array<Record<string, unknown>>) => void;
  }>,
}));

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
  default: (config: {
    onImages?: (items: Array<Record<string, unknown>>) => void;
  }) => {
    uploaderState.configs.push(config);
    return {
      handleFiles: vi.fn(),
      onDrop: vi.fn(),
      onDragOver: vi.fn(),
      pick: vi.fn(),
      uploading: false,
    };
  },
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
    gallery,
  }: {
    onRequestNewProject: () => void;
    gallery?: Array<{ src: string; prompt: string }>;
  }) => (
    <div data-testid="dashboard-view-mock">
      <button type="button" onClick={onRequestNewProject}>
        New Project
      </button>
      <div data-testid="dashboard-gallery-mock">
        {(gallery ?? []).map((item) => (
          <span key={item.src}>{item.prompt}</span>
        ))}
      </div>
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

function setWorkspaceLayoutState(paneRatio: number) {
  window.localStorage.setItem(
    WORKSPACE_LAYOUT_STORAGE_KEY,
    JSON.stringify({ paneRatio })
  );
}

function readPaneBasis(element: HTMLElement): number {
  return Number.parseFloat(element.getAttribute("data-pane-basis") ?? "0");
}

describe("AppShell logo wordmark color contract", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    routeCapabilityState.ready = true;
    routeCapabilityState.state = "available";
    listCodexEntriesSpy.mockClear();
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

      const lightShell = lightWordmark.closest(
        "div[style*='--text-on-accent:']"
      );
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

      const darkShell = darkWordmark.closest(
        "div[style*='--text-on-accent:']"
      );
      expect(darkShell).not.toBeNull();
      expect(darkShell?.getAttribute("style")).toContain("--text: #ffffff");
      expect(darkShell?.getAttribute("style")).toContain(
        "--text-on-accent: #f9fafb"
      );
    },
    15_000
  );

  it("skips codex bootstrap when the restricted profile marks codex unavailable", () => {
    routeCapabilityState.state = "unavailable";

    render(<AppShell />);

    expect(listCodexEntriesSpy).not.toHaveBeenCalled();
  });
});

describe("AppShell dashboard create project flow", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    localStorage.setItem("cfy.lastView", "dashboard");
    routeCapabilityState.ready = true;
    routeCapabilityState.state = "available";
    listCodexEntriesSpy.mockClear();
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

describe("AppShell shared gallery persistence truth", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    routeCapabilityState.ready = true;
    routeCapabilityState.state = "available";
    listCodexEntriesSpy.mockClear();
    mockApi.get.mockClear();
    mockApi.post.mockClear();
    mockApi.delete.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders only persisted gallery items on the dashboard when transient failed uploads are cached", async () => {
    localStorage.setItem("cfy.lastView", "dashboard");
    localStorage.setItem(
      "cfy.gallery",
      JSON.stringify([
        { src: "/media/images/persisted-image.png", prompt: "Persisted image" },
        {
          src: "data:image/png;base64,ZmFrZQ==",
          prompt: "Failed upload",
          mock: true,
        },
      ])
    );

    render(<AppShell />);

    expect(await screen.findByText("Persisted image")).toBeInTheDocument();
    expect(screen.queryByText("Failed upload")).not.toBeInTheDocument();

    await waitFor(() => {
      const persistedGallery = JSON.parse(
        localStorage.getItem("cfy.gallery") ?? "[]"
      ) as Array<{ prompt: string }>;
      expect(persistedGallery).toHaveLength(1);
      expect(persistedGallery[0]?.prompt).toBe("Persisted image");
    });
  });

  it("ignores failed gallery upload previews and keeps persisted uploads visible", async () => {
    localStorage.setItem("cfy.lastView", "gallery");
    localStorage.setItem("cfy.gallery", JSON.stringify([]));

    render(<AppShell />);

    const galleryUploaderConfig = uploaderState.configs.at(-1);
    expect(galleryUploaderConfig?.onImages).toBeTypeOf("function");

    act(() => {
      galleryUploaderConfig?.onImages?.([
        {
          src: "data:image/png;base64,ZmFrZQ==",
          prompt: "Failed upload",
          mock: true,
        },
      ]);
    });

    expect(
      screen.queryByRole("img", { name: "Failed upload" })
    ).not.toBeInTheDocument();

    await waitFor(() => {
      const persistedGallery = JSON.parse(
        localStorage.getItem("cfy.gallery") ?? "[]"
      ) as Array<{ prompt: string }>;
      expect(persistedGallery).toHaveLength(0);
    });

    act(() => {
      galleryUploaderConfig?.onImages?.([
        {
          src: "/media/images/persisted-upload.png",
          prompt: "Persisted upload",
        },
      ]);
    });

    expect(
      await screen.findByRole("img", { name: "Persisted upload" })
    ).toBeInTheDocument();

    await waitFor(() => {
      const persistedGallery = JSON.parse(
        localStorage.getItem("cfy.gallery") ?? "[]"
      ) as Array<{ prompt: string }>;
      expect(persistedGallery).toHaveLength(1);
      expect(persistedGallery[0]?.prompt).toBe("Persisted upload");
    });
  });
});

describe("AppShell gallery demo content", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    routeCapabilityState.ready = true;
    routeCapabilityState.state = "available";
    listCodexEntriesSpy.mockClear();
    mockApi.get.mockClear();
    mockApi.post.mockClear();
    mockApi.delete.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders gallery demo items when no real gallery items exist", async () => {
    localStorage.setItem("cfy.lastView", "gallery");
    localStorage.setItem(
      "cfy.gallery",
      JSON.stringify([
        {
          src: "https://example.test/demo-gallery.png",
          prompt: "Demo gallery item",
          mock: true,
        },
      ])
    );

    render(<AppShell />);

    expect(
      await screen.findByRole("img", { name: "Demo gallery item" })
    ).toBeInTheDocument();
    expect(screen.queryByText("Hide Mock Items")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("auto-hides gallery demo items once real gallery items exist", async () => {
    localStorage.setItem("cfy.lastView", "gallery");
    localStorage.setItem(
      "cfy.gallery",
      JSON.stringify([
        {
          src: "/media/images/real-gallery-item.png",
          prompt: "Real gallery item",
        },
        {
          src: "https://example.test/demo-gallery.png",
          prompt: "Demo gallery item",
          mock: true,
        },
      ])
    );

    render(<AppShell />);

    expect(
      await screen.findByRole("img", { name: "Real gallery item" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: "Demo gallery item" })
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Hide Mock Items")).not.toBeInTheDocument();
  });
});

describe("AppShell workspace drawer shell", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    routeCapabilityState.ready = true;
    routeCapabilityState.state = "available";
    listCodexEntriesSpy.mockClear();
    mockApi.get.mockClear();
    mockApi.post.mockClear();
    mockApi.delete.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it.each(["dashboard", "guardian", "documents"] as const)(
    "renders the shared workspace drawer from the shell for %s",
    async (initialView) => {
      localStorage.setItem("cfy.lastView", initialView);

      render(<AppShell />);

      const toggle = screen.getByTestId("workspace-drawer-toggle");
      expect(toggle).toBeInTheDocument();

      fireEvent.click(toggle);

      expect(await screen.findByTestId("workspace-drawer")).toBeInTheDocument();
    }
  );

  it("resolves supported views to chat_focus while the workspace is closed", () => {
    localStorage.setItem("cfy.lastView", "dashboard");
    setWorkspaceLayoutState(MAX_WORKSPACE_PANE_RATIO);

    render(<AppShell />);

    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "chat_focus"
    );
    expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
  });

  it("uses balanced_split for open workspace layouts at the default ratio", async () => {
    localStorage.setItem("cfy.lastView", "guardian");
    setWorkspaceLayoutState(DEFAULT_WORKSPACE_PANE_RATIO);

    render(<AppShell />);

    fireEvent.click(screen.getByTestId("workspace-drawer-toggle"));

    const drawer = await screen.findByTestId("workspace-drawer");
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "balanced_split"
    );
    expect(drawer).toHaveAttribute("data-layout-mode", "balanced_split");
    expect(drawer).toHaveAttribute(
      "data-pane-ratio",
      DEFAULT_WORKSPACE_PANE_RATIO.toFixed(2)
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Balanced split"
    );
  });

  it("makes workspace_focus visibly more dominant than balanced_split", async () => {
    localStorage.setItem("cfy.lastView", "guardian");
    setWorkspaceLayoutState(DEFAULT_WORKSPACE_PANE_RATIO);

    const { unmount } = render(<AppShell />);

    fireEvent.click(screen.getByTestId("workspace-drawer-toggle"));

    const balancedPrimaryPane = await screen.findByTestId(
      "workspace-primary-pane"
    );
    const balancedDrawerPane = screen.getByTestId("workspace-drawer-pane");
    const balancedPrimaryBasis = readPaneBasis(balancedPrimaryPane);
    const balancedDrawerBasis = readPaneBasis(balancedDrawerPane);

    unmount();

    localStorage.setItem("cfy.lastView", "documents");
    localStorage.setItem(
      "cfy.workspace.ui",
      JSON.stringify({ isOpen: true, activeTab: "inspector" })
    );
    setWorkspaceLayoutState(0.95);

    render(<AppShell />);

    const focusPrimaryPane = screen.getByTestId("workspace-primary-pane");
    const focusDrawerPane = screen.getByTestId("workspace-drawer-pane");
    const drawer = screen.getByTestId("workspace-drawer");
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "workspace_focus"
    );
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-dominant",
      "true"
    );
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-ratio-bucket",
      "workspace_first"
    );
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(drawer).toHaveAttribute(
      "data-pane-ratio",
      MAX_WORKSPACE_PANE_RATIO.toFixed(2)
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace focus"
    );
    expect(readPaneBasis(focusDrawerPane)).toBeGreaterThan(balancedDrawerBasis);
    expect(readPaneBasis(focusPrimaryPane)).toBeLessThan(balancedPrimaryBasis);
  });

  it("keeps the chat lane at a readable minimum width in workspace_focus", () => {
    localStorage.setItem("cfy.lastView", "guardian");
    localStorage.setItem(
      "cfy.workspace.ui",
      JSON.stringify({ isOpen: true, activeTab: "scratchpad" })
    );
    setWorkspaceLayoutState(MAX_WORKSPACE_PANE_RATIO);

    render(<AppShell />);

    expect(screen.getByTestId("workspace-primary-pane")).toHaveAttribute(
      "data-pane-min-width",
      MIN_WORKSPACE_PRIMARY_PANE_WIDTH
    );
  });

  it("does not render the workspace drawer for unsupported views", () => {
    localStorage.setItem("cfy.lastView", "gallery");
    localStorage.setItem(
      "cfy.workspace.ui",
      JSON.stringify({ isOpen: true, activeTab: "inspector" })
    );

    render(<AppShell />);

    expect(screen.queryByTestId("workspace-drawer-toggle")).not.toBeInTheDocument();
    expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
  });
});
