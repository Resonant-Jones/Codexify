import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import {
  personaStudioApiMock,
  resetPersonaStudioApiMock,
} from "@/features/personaStudio/__tests__/personaStudioApiMock";
import api from "@/lib/api";
import {
  LIVE_EVENT_CONNECTION_STATES,
  RUNTIME_HEALTH_STATUSES,
} from "@/contracts/runtimeTokens";
import {
  MIN_WORKSPACE_PRIMARY_PANE_WIDTH,
  getWorkspaceLayoutStorageKeyForThread,
  getWorkspacePaneRatioForLayoutMode,
  type WorkspaceLayoutMode,
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

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("@/features/personaStudio/__tests__/personaStudioApiMock"))
    .personaStudioApiMock
);

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

let AppShell: typeof import("../AppShell").default;

beforeAll(async () => {
  AppShell = (await import("../AppShell")).default;
});

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

function setRoutePath(pathname: string) {
  window.history.pushState({}, "", pathname);
}

function setRouteThread(threadId: number | null) {
  setRoutePath(threadId == null ? "/" : `/chat/${threadId}`);
}

function notifyRouteChange() {
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function setWorkspaceThreadPosture(
  threadId: number | string | null,
  layoutMode: WorkspaceLayoutMode
) {
  window.localStorage.setItem(
    getWorkspaceLayoutStorageKeyForThread(threadId),
    layoutMode
  );
}

function readPaneBasis(element: HTMLElement): number {
  return Number.parseFloat(element.getAttribute("data-pane-basis") ?? "0");
}

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  window.dispatchEvent(new Event("resize"));
}

beforeEach(() => {
  setViewportWidth(1280);
});

describe("AppShell logo wordmark color contract", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    setRouteThread(null);
  routeCapabilityState.ready = true;
  routeCapabilityState.state = "available";
  resetPersonaStudioApiMock();
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

  it("honors the /persona-studio route on initial render", async () => {
    setRoutePath("/persona-studio");

    render(<AppShell />);

    expect(
      await screen.findByText(/configure runtime persona profiles/i)
    ).toBeInTheDocument();
  });
});

describe("AppShell settings utility trigger", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    setRouteThread(null);
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

  it("moves Settings into the utility rail and opens the existing settings surface", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "dashboard");

    render(<AppShell />);

    expect(screen.getByTestId("app-shell-top-chrome")).toHaveStyle(
      "grid-template-columns: auto minmax(var(--shell-gap), 1fr) auto"
    );
    expect(screen.getByTestId("app-shell-nav-anchor")).toHaveStyle({
      gridColumn: "1",
      justifySelf: "start",
    });
    expect(screen.getByTestId("app-shell-utility-cluster")).toHaveStyle({
      gridColumn: "3",
      justifySelf: "end",
    });
    expect(screen.getByTestId("app-shell-top-nav")).toHaveClass(
      "glass-pill",
      "inline-flex",
      "w-fit",
      "max-w-full"
    );
    expect(screen.queryByTestId("settings-view-mock")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("settings-utility-toggle"));

    expect(await screen.findByTestId("settings-view-mock")).toBeInTheDocument();
  });
});

describe("AppShell dashboard create project flow", () => {
  beforeEach(() => {
    localStorage.clear();
    uploaderState.configs = [];
    installMatchMedia(false);
    document.documentElement.classList.remove("dark");
    setRouteThread(null);
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
    setRouteThread(null);
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
    setRouteThread(null);
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
    setRouteThread(null);
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
    "renders the shared workspace drawer from the shell for %s and keeps open/close behavior intact",
    async (initialView) => {
      localStorage.setItem("cfy.lastView", initialView);

      render(<AppShell />);

      const toggle = screen.getByTestId("workspace-drawer-toggle");
      expect(toggle).toBeInTheDocument();

      fireEvent.click(toggle);

      expect(await screen.findByTestId("workspace-drawer")).toBeInTheDocument();

      fireEvent.click(toggle);
      expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
    }
  );

  it("keeps the mobile workspace summon explicit and opens the drawer as an overlay", async () => {
    const user = userEvent.setup();
    setViewportWidth(390);
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(null);

    render(<AppShell />);

    expect(screen.getByTestId("app-shell-top-nav")).toHaveAttribute(
      "data-shell-nav-mode",
      "scroll_rail"
    );
    expect(
      screen.getByRole("button", { name: "Open Workspace" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open Workspace" }));

    expect(
      await screen.findByRole("button", { name: "Close Workspace" })
    ).toBeInTheDocument();
    expect(screen.getByTestId("workspace-drawer-overlay")).toHaveAttribute(
      "data-overlay-mode",
      "mobile"
    );
    expect(screen.getByTestId("workspace-drawer-pane")).toHaveAttribute(
      "data-overlay",
      "true"
    );
  });

  it("tracks the phone shell height from the visual viewport instead of plain 100vh", () => {
    const originalInnerHeight = Object.getOwnPropertyDescriptor(window, "innerHeight");
    const originalVisualViewport = Object.getOwnPropertyDescriptor(
      window,
      "visualViewport"
    );

    setViewportWidth(390);
    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      writable: true,
      value: 844,
    });
    Object.defineProperty(window, "visualViewport", {
      configurable: true,
      value: {
        height: 544,
        offsetTop: 0,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(null);

    try {
      const { container } = render(<AppShell />);
      const root = container.firstElementChild as HTMLElement;

      expect(root.style.height).toBe("var(--shell-viewport-height, 100vh)");
      expect(root.style.minHeight).toBe("var(--shell-viewport-height, 100vh)");
      expect(root.style.getPropertyValue("--shell-viewport-height")).toBe("544px");
      expect(root.style.getPropertyValue("--shell-keyboard-inset")).toBe("300px");
    } finally {
      if (originalInnerHeight) {
        Object.defineProperty(window, "innerHeight", originalInnerHeight);
      }
      if (originalVisualViewport) {
        Object.defineProperty(window, "visualViewport", originalVisualViewport);
      } else {
        delete (window as any).visualViewport;
      }
    }
  });

  it("resolves supported views to chat_focus while the workspace is closed", () => {
    localStorage.setItem("cfy.lastView", "dashboard");
    setRouteThread(101);
    setWorkspaceThreadPosture(101, "workspace_focus");

    render(<AppShell />);

    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "chat_focus"
    );
    expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
  });

  it("defaults to Chat Focus and cycles the centered posture control through the preset states", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(101);

    render(<AppShell />);

    fireEvent.click(screen.getByTestId("workspace-drawer-toggle"));

    const drawer = await screen.findByTestId("workspace-drawer");
    const posture = screen.getByTestId("workspace-drawer-posture");
    const primaryPane = screen.getByTestId("workspace-primary-pane");
    const drawerPane = screen.getByTestId("workspace-drawer-pane");
    const chatPrimaryBasis = readPaneBasis(primaryPane);
    const chatDrawerBasis = readPaneBasis(drawerPane);

    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "chat_focus"
    );
    expect(drawer).toHaveAttribute("data-layout-mode", "chat_focus");
    expect(drawer).toHaveAttribute("data-layout-label", "Chat Focus");
    expect(posture).toHaveTextContent("Chat Focus");
    expect(primaryPane).toHaveAttribute(
      "data-pane-min-width",
      MIN_WORKSPACE_PRIMARY_PANE_WIDTH
    );

    await user.click(posture);

    expect(posture).toHaveTextContent("Balanced Split");
    expect(drawer).toHaveAttribute("data-layout-mode", "balanced_split");
    expect(drawer).toHaveAttribute("data-layout-label", "Balanced Split");
    expect(drawer).toHaveAttribute(
      "data-pane-ratio",
      getWorkspacePaneRatioForLayoutMode("balanced_split").toFixed(2)
    );
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "balanced_split"
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Balanced Split"
    );

    await user.click(posture);

    expect(posture).toHaveTextContent("Workspace Focus");
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(drawer).toHaveAttribute("data-layout-label", "Workspace Focus");
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-dominant",
      "true"
    );
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-ratio-bucket",
      "workspace_first"
    );
    expect(drawer).toHaveAttribute(
      "data-pane-ratio",
      getWorkspacePaneRatioForLayoutMode("workspace_focus").toFixed(2)
    );
    expect(readPaneBasis(drawerPane)).toBeGreaterThan(chatDrawerBasis);
    expect(readPaneBasis(primaryPane)).toBeLessThan(chatPrimaryBasis);
    expect(primaryPane).toHaveAttribute(
      "data-pane-min-width",
      MIN_WORKSPACE_PRIMARY_PANE_WIDTH
    );

    await user.dblClick(posture);

    expect(posture).toHaveTextContent("Chat Focus");
    expect(drawer).toHaveAttribute("data-layout-mode", "chat_focus");
    expect(drawer).toHaveAttribute("data-layout-label", "Chat Focus");
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "chat_focus"
    );
  });

  it("persists posture per thread and restores the saved posture when switching routes", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(101);

    render(<AppShell />);

    fireEvent.click(screen.getByTestId("workspace-drawer-toggle"));

    const drawer = await screen.findByTestId("workspace-drawer");
    const posture = screen.getByTestId("workspace-drawer-posture");

    await user.click(posture);
    await user.click(posture);

    expect(
      localStorage.getItem(getWorkspaceLayoutStorageKeyForThread(101))
    ).toBe("workspace_focus");

    act(() => {
      setRouteThread(202);
      notifyRouteChange();
    });

    await waitFor(() => {
      expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
        "data-layout-mode",
        "chat_focus"
      );
      expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
        "Chat Focus"
      );
    });

    await user.click(screen.getByTestId("workspace-drawer-posture"));
    expect(
      localStorage.getItem(getWorkspaceLayoutStorageKeyForThread(202))
    ).toBe("balanced_split");

    act(() => {
      setRouteThread(101);
      notifyRouteChange();
    });

    await waitFor(() => {
      expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
        "data-layout-mode",
        "workspace_focus"
      );
      expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
        "Workspace Focus"
      );
    });
  });

  it("does not render the workspace drawer for unsupported views", () => {
    localStorage.setItem("cfy.lastView", "gallery");
    setRouteThread(null);

    render(<AppShell />);

    expect(screen.queryByTestId("workspace-drawer-toggle")).not.toBeInTheDocument();
    expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
  });
});
