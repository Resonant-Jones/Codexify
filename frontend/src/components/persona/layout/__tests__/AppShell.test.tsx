import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
  act,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import {
  LIVE_EVENT_CONNECTION_STATES,
  RUNTIME_HEALTH_STATUSES,
} from "@/contracts/runtimeTokens";
import { resetPersonaStudioApiMock } from "@/features/personaStudio/__tests__/personaStudioApiMock";
import {
  MIN_WORKSPACE_PRIMARY_PANE_WIDTH,
  getWorkspaceLayoutStorageKeyForThread,
  getWorkspacePaneRatioForLayoutMode,
  type WorkspaceLayoutMode,
} from "@/features/workspace/state/useWorkspaceLayoutMode";
import api from "@/lib/api";

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
  diagnostics: {
    resolvedApiBaseUrl: "http://localhost:8888",
    resolvedApiBaseUrlSource: "vite-dev",
    apiKeyPresent: true,
    apiKeySource: "vite-dev",
    hydrationState: "ready" as const,
    nativeCommandStatus: "ready",
    authSource: "vite-dev",
    chat: {
      endpoint: "/health/chat",
      httpStatus: 200,
      transportErrorClass: null,
      parsedStatus: "ok",
      parsedOk: true,
      detailsStatus: "ok",
      detailsOk: true,
      providerRuntimeAvailable: true,
      endpointResolutionState: "ready",
      failureReason: null,
    },
    llm: {
      endpoint: "/api/health/llm",
      httpStatus: 200,
      transportErrorClass: null,
      parsedStatus: "ok",
      parsedOk: true,
      detailsStatus: "ok",
      detailsOk: true,
      providerRuntimeAvailable: true,
      endpointResolutionState: "ready",
      failureReason: null,
    },
    liveEvents: {
      connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
      statusUpdatedAt: Date.parse("2026-03-20T12:00:00Z"),
      connected: true,
    },
    failureKind: null,
    lastSuccessAt: Date.parse("2026-03-20T12:00:00Z"),
    lastFailedAt: null,
    lastCheckedAt: Date.parse("2026-03-20T12:00:00Z"),
    currentComputedStateSource: "live-poll" as const,
  },
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
  default: ({
    projectId,
    threadId,
  }: {
    projectId?: number | string | null;
    threadId?: number | string | null;
  }) => (
    <div data-testid="documents-view-mock">
      <section
        data-testid="documents-layout"
        data-documents-layout="center_lane"
        data-workspace-anchor="app-shell-right"
      >
        <div data-testid="documents-center-panel">Documents center</div>
        <div data-testid="documents-project-id">
          {projectId ?? "no-project"}
        </div>
        <div data-testid="documents-default-project-id">
          {projectId ?? "no-project"}
        </div>
        <div data-testid="documents-thread-id">
          {threadId ?? "no-thread"}
        </div>
      </section>
    </div>
  ),
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: () => (
    <div data-testid="sidebar-root-mock">
      <div data-testid="sidebar-threads-tab">Threads</div>
      <div data-testid="sidebar-projects-tab">Projects</div>
    </div>
  ),
}));

vi.mock("@/components/persona/layout/GuardianChatWithSidebar", () => ({
  default: (props: {
    onProjectChange?: (projectId: string | null, projectName: string | null) => void;
  }) => (
    <div data-testid="guardian-chat-with-sidebar-mock">
      <button
        type="button"
        data-testid="guardian-set-project-2"
        onClick={() => props.onProjectChange?.("2", "Launch Project")}
      >
        Set Project 2
      </button>
    </div>
  ),
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

  it("refreshes a stale stored general project id before loading media", async () => {
    localStorage.setItem("cfy.generalProjectId", "1");
    localStorage.setItem("cfy.defaultProjectId", "1");

    const documentProjectIds: Array<number | undefined> = [];
    mockApi.get.mockImplementation(async (path: string, options?: any) => {
      if (path === "/api/projects") {
        return {
          data: {
            projects: [
              { id: 7, name: "General" },
              { id: 8, name: "Research" },
            ],
          },
        };
      }

      if (path === "/media/documents") {
        documentProjectIds.push(options?.params?.project_id);
        expect(options?.params?.project_id).not.toBe(1);
        return { data: { documents: [] } };
      }

      return { data: {} };
    });

    render(<AppShell />);

    await waitFor(() => {
      expect(mockApi.get).toHaveBeenCalledWith("/api/projects");
    });

    expect(documentProjectIds).not.toContain(1);

    await waitFor(() => {
      expect(localStorage.getItem("cfy.generalProjectId")).toBe("1");
      expect(localStorage.getItem("cfy.defaultProjectId")).toBe("1");
      expect(localStorage.getItem("cfy.generalProjectIdTrusted")).toBeNull();
    });
  });

  it("honors the /flow-builder route on initial render", async () => {
    localStorage.setItem("cfy.lastView", "dashboard");
    setRoutePath("/flow-builder?mode=expertise");

    render(<AppShell />);

    expect(await screen.findByTestId("flow-builder-page")).toBeInTheDocument();
    expect(screen.getByTestId("flow-builder-page")).toHaveAttribute(
      "data-flow-builder-mode",
      "expertise"
    );
  });

  it("keeps the prior Guardian route reachable from Flow Builder even after the draft fields take focus", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "guardian");
    setRoutePath("/flow-builder?mode=expertise");

    render(<AppShell />);

    await user.click(await screen.findByTestId("flow-builder-mode-expertise"));

    const objective = await screen.findByTestId("flow-builder-draft-objective");
    objective.focus();

    await user.click(screen.getByTestId("flow-builder-return-guardian"));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/chat");
    });
    expect(screen.getByTestId("guardian-chat-with-sidebar-mock")).toBeInTheDocument();
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

  it("hides unfinished beta surfaces from the visible primary nav", async () => {
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
    expect(screen.getByTestId("app-shell-top-nav-rail")).toHaveStyle({
      flex: "0 0 auto",
      width: "fit-content",
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
    const primaryNav = within(screen.getByTestId("app-shell-top-nav"));
    expect(primaryNav.getByRole("button", { name: "Guardian" })).toBeInTheDocument();
    expect(primaryNav.getByRole("button", { name: "Dashboard" })).toBeInTheDocument();
    expect(primaryNav.getByRole("button", { name: "Documents" })).toBeInTheDocument();
    expect(primaryNav.getByRole("button", { name: "Gallery" })).toBeInTheDocument();
    expect(primaryNav.queryByRole("button", { name: "Flow Builder" })).not.toBeInTheDocument();
    expect(primaryNav.queryByRole("button", { name: "Persona Studio" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("settings-view-mock")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("settings-utility-toggle"));

    expect(await screen.findByTestId("settings-view-mock")).toBeInTheDocument();
  });

  it("routes Project Knowledge Base requests to the Documents surface", async () => {
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(123);

    render(<AppShell />);

    expect(screen.getByTestId("guardian-chat-with-sidebar-mock")).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(
        new CustomEvent("cfy:project-kb:open", {
          detail: { projectId: 42, projectName: "Launch Project" },
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("documents-view-mock")).toBeInTheDocument();
    });
    expect(screen.getByTestId("documents-project-id")).toHaveTextContent(
      "42"
    );
    expect(screen.getByTestId("documents-thread-id")).toHaveTextContent("123");
  });

  it("preserves the Guardian project selection when switching to Documents", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(123);

    render(<AppShell />);

    expect(screen.getByTestId("guardian-chat-with-sidebar-mock")).toBeInTheDocument();

    await user.click(screen.getByTestId("guardian-set-project-2"));
    await user.click(screen.getByRole("button", { name: "Documents" }));

    await waitFor(() => {
      expect(screen.getByTestId("documents-view-mock")).toBeInTheDocument();
    });
    expect(screen.getByTestId("documents-default-project-id")).toHaveTextContent(
      "2"
    );
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

  it.each(["guardian", "documents"] as const)(
    "renders the shared workspace drawer from the shell for %s and keeps open/close behavior intact",
    async (initialView) => {
      localStorage.setItem("cfy.lastView", initialView);

      render(<AppShell />);

      const toggle = screen.getByTestId("workspace-drawer-toggle");
      expect(toggle).toBeInTheDocument();

      fireEvent.click(toggle);

      expect(await screen.findByTestId("workspace-drawer")).toBeInTheDocument();

      fireEvent.click(toggle);
      await waitFor(() => {
        expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
      });
    }
  );

  it("does not render workspace controls on dashboard", () => {
    localStorage.setItem("cfy.lastView", "dashboard");

    render(<AppShell />);

    expect(screen.queryByTestId("workspace-drawer-toggle")).not.toBeInTheDocument();
    expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
  });

  it("keeps the documents workspace drawer right-anchored as its posture expands", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "documents");

    render(<AppShell />);

    const toggle = screen.getByTestId("workspace-drawer-toggle");
    fireEvent.click(toggle);

    const drawer = await screen.findByTestId("workspace-drawer");
    const drawerPane = screen.getByTestId("workspace-drawer-pane");
    const primaryPane = screen.getByTestId("workspace-primary-pane");
    const posture = screen.getByTestId("workspace-drawer-posture");

    expect(drawerPane).toHaveStyle({ marginLeft: "auto" });
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "chat_focus"
    );
    expect(readPaneBasis(primaryPane)).toBeGreaterThan(readPaneBasis(drawerPane));

    await user.click(posture);

    expect(drawer).toHaveAttribute("data-layout-mode", "balanced_split");
    expect(drawerPane).toHaveStyle({ marginLeft: "auto" });
    expect(screen.getByTestId("workspace-layout-surface")).toHaveAttribute(
      "data-workspace-layout-mode",
      "balanced_split"
    );

    await user.click(posture);

    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(drawerPane).toHaveStyle({ marginLeft: "auto" });
    expect(readPaneBasis(drawerPane)).toBeGreaterThan(readPaneBasis(primaryPane));
  });

  it("gives Documents the same shared sidebar, center lane, and right workspace shell as Guardian", async () => {
    localStorage.setItem("cfy.lastView", "documents");

    render(<AppShell />);

    expect(screen.getByTestId("documents-shared-shell")).toHaveAttribute(
      "data-documents-shared-shell",
      "sidebar-center"
    );
    expect(screen.getByTestId("documents-shared-sidebar-pane")).toHaveAttribute(
      "data-shared-sidebar",
      "true"
    );
    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-primary-pane")).toHaveAttribute(
      "data-pane-basis",
      "100.00%"
    );
    expect(screen.queryByTestId("documents-scope-rail")).not.toBeInTheDocument();
    expect(screen.queryAllByTestId("documents-shared-sidebar-pane")).toHaveLength(1);
    expect(screen.queryByTestId("workspace-drawer-pane")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("workspace-drawer-toggle"));

    expect(await screen.findByTestId("workspace-drawer-pane")).toHaveAttribute(
      "data-shell-workspace-arrangement",
      "split"
    );
    expect(screen.getByTestId("workspace-drawer-pane")).toHaveStyle({
      marginLeft: "auto",
      padding: "var(--board-edge)",
    });
    expect(screen.queryAllByTestId("workspace-drawer")).toHaveLength(1);
    expect(screen.queryAllByTestId("workspace-drawer-pane")).toHaveLength(1);
    expect(screen.getByTestId("workspace-primary-pane")).not.toHaveAttribute(
      "data-pane-basis",
      "100.00%"
    );
  });

  it("keeps Documents responsive without reintroducing route-local sidebar or workspace copies", async () => {
    const user = userEvent.setup();
    setViewportWidth(390);
    localStorage.setItem("cfy.lastView", "documents");
    setRouteThread(null);

    render(<AppShell />);

    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("documents-shared-sidebar-pane")).not.toBeInTheDocument();
    expect(screen.queryByTestId("documents-scope-rail")).not.toBeInTheDocument();
    expect(screen.queryByTestId("workspace-drawer-overlay")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open Workspace" }));

    expect(screen.getByTestId("workspace-drawer-overlay")).toHaveAttribute(
      "data-overlay-mode",
      "mobile"
    );
    expect(screen.queryAllByTestId("workspace-drawer-overlay")).toHaveLength(1);
    expect(screen.queryAllByTestId("workspace-drawer-pane")).toHaveLength(1);
    expect(screen.queryByTestId("documents-shared-sidebar-pane")).not.toBeInTheDocument();
    expect(screen.queryByTestId("documents-scope-rail")).not.toBeInTheDocument();
  });

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
    expect(screen.getByRole("button", { name: "Guardian" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    expect(
      screen.getByRole("button", { name: "Open Workspace" })
    ).toHaveAttribute("data-workspace-affordance-state", "collapsed");

    await user.click(screen.getByRole("button", { name: "Open Workspace" }));

    expect(
      await screen.findByRole("button", { name: "Close Workspace" })
    ).toHaveAttribute("data-workspace-affordance-state", "open");
    expect(screen.getByTestId("workspace-drawer-overlay")).toHaveAttribute(
      "data-overlay-mode",
      "mobile"
    );
    expect(screen.getByTestId("workspace-drawer-overlay")).toHaveAttribute(
      "data-workspace-motion-state",
      "peek"
    );
    expect(screen.getByTestId("workspace-drawer-overlay")).toHaveAttribute(
      "data-workspace-motion-phase",
      "open"
    );
    expect(screen.getByTestId("workspace-drawer-pane")).toHaveAttribute(
      "data-overlay",
      "true"
    );

    await user.click(screen.getByRole("button", { name: "Close Workspace" }));

    expect(
      screen.getByRole("button", { name: "Close Workspace" })
    ).toHaveAttribute("data-workspace-affordance-state", "open");

    expect(screen.getByTestId("workspace-drawer-overlay")).toHaveAttribute(
      "data-workspace-motion-phase",
      "closing"
    );
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Open Workspace" })
      ).toHaveAttribute("data-workspace-affordance-state", "collapsed");
      expect(screen.queryByTestId("workspace-drawer-overlay")).not.toBeInTheDocument();
    });
  });

  it("keeps the phone nav rail momentum-enabled and the selected pill tactile", async () => {
    const user = userEvent.setup();
    setViewportWidth(390);
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(null);

    render(<AppShell />);

    const rail = screen.getByTestId("app-shell-top-nav-rail");
    const railStyle = rail.getAttribute("style") ?? "";
    expect((rail as HTMLElement).style.touchAction).toBe("pan-x");
    expect(railStyle).toContain("scroll-padding-inline: 12px");
    expect(railStyle).toContain("-webkit-overflow-scrolling: touch");

    const guardian = screen.getByRole("button", { name: "Guardian" });
    const guardianStyle = guardian.getAttribute("style") ?? "";
    expect(guardian).toHaveAttribute("data-state", "active");
    expect(guardianStyle).toContain(
      "background: color-mix(in oklab, var(--accent-strong) 90%, var(--panel-bg) 10%)"
    );
    expect(guardianStyle).toContain("transition-duration: 140ms");
    expect(guardianStyle).toContain(
      "transition-timing-function: cubic-bezier(0.22, 1, 0.36, 1)"
    );
    expect(guardianStyle).toContain(
      "transition-property: color, background, border-color, box-shadow, transform, opacity, filter"
    );
    expect(guardianStyle).not.toContain("transform:");

    fireEvent.pointerDown(guardian, { button: 0, pointerType: "touch" });
    expect(guardian).toHaveAttribute("data-press-feedback", "pressed");

    fireEvent.pointerUp(guardian, { button: 0, pointerType: "touch" });
    expect(guardian).toHaveAttribute("data-press-feedback", "idle");

    await user.click(screen.getByRole("button", { name: "Dashboard" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Dashboard" })).toHaveAttribute(
        "data-state",
        "active"
      );
    });
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
        const windowWithVisualViewport = window as Window & {
          visualViewport?: typeof window.visualViewport;
        };
        delete windowWithVisualViewport.visualViewport;
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

    await screen.findByTestId("workspace-drawer");
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

describe("AppShell documents sidebar posture", () => {
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

  it("renders the shared sidebar on Documents by default on desktop", () => {
    localStorage.setItem("cfy.lastView", "documents");
    setViewportWidth(1280);

    render(<AppShell />);

    expect(screen.getByTestId("documents-shared-sidebar-pane")).toBeInTheDocument();
    expect(screen.getByTestId("documents-shared-sidebar-pane")).toHaveAttribute(
      "data-shared-sidebar",
      "true"
    );
    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
  });

  it("dismisses the Documents sidebar via the toggle button and expands the center lane", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "documents");
    setViewportWidth(1280);

    render(<AppShell />);

    expect(screen.getByTestId("documents-shared-sidebar-pane")).toBeInTheDocument();

    const sidebarToggle = screen.getByTestId("documents-sidebar-toggle");
    expect(sidebarToggle).toHaveAttribute("data-state", "active");

    await user.click(sidebarToggle);

    await waitFor(() => {
      expect(screen.queryByTestId("documents-shared-sidebar-pane")).not.toBeInTheDocument();
    });

    expect(screen.getByTestId("documents-sidebar-edge-affordance")).toBeInTheDocument();
    expect(sidebarToggle).toHaveAttribute("data-state", "inactive");

    const primaryPane = screen.getByTestId("workspace-primary-pane");
    expect(primaryPane).toHaveAttribute("data-pane-basis", "100.00%");
  });

  it("re-invokes the Documents sidebar from the edge affordance after dismissal", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "documents");
    setViewportWidth(1280);

    render(<AppShell />);

    const sidebarToggle = screen.getByTestId("documents-sidebar-toggle");
    await user.click(sidebarToggle);

    await waitFor(() => {
      expect(screen.queryByTestId("documents-shared-sidebar-pane")).not.toBeInTheDocument();
    });

    const edgeAffordance = screen.getByTestId("documents-sidebar-edge-affordance");
    await user.click(edgeAffordance);

    await waitFor(() => {
      expect(screen.getByTestId("documents-shared-sidebar-pane")).toBeInTheDocument();
    });
  });

  it("re-invokes the Documents sidebar from the toggle button after dismissal", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "documents");
    setViewportWidth(1280);

    render(<AppShell />);

    const sidebarToggle = screen.getByTestId("documents-sidebar-toggle");
    await user.click(sidebarToggle);

    await waitFor(() => {
      expect(screen.queryByTestId("documents-shared-sidebar-pane")).not.toBeInTheDocument();
    });

    await user.click(sidebarToggle);

    await waitFor(() => {
      expect(screen.getByTestId("documents-shared-sidebar-pane")).toBeInTheDocument();
    });
    expect(sidebarToggle).toHaveAttribute("data-state", "active");
  });

  it("uses sidebar overlay on mobile instead of permanent sidebar", async () => {
    const user = userEvent.setup();
    setViewportWidth(390);
    localStorage.setItem("cfy.lastView", "documents");
    setRouteThread(null);

    render(<AppShell />);

    expect(screen.queryByTestId("documents-shared-sidebar-pane")).not.toBeInTheDocument();
    expect(screen.queryByTestId("documents-sidebar-overlay")).not.toBeInTheDocument();
    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();

    const sidebarToggle = screen.getByTestId("documents-sidebar-toggle");
    await user.click(sidebarToggle);

    expect(await screen.findByTestId("documents-sidebar-overlay")).toBeInTheDocument();
    expect(screen.getByTestId("documents-sidebar-overlay")).toHaveAttribute(
      "data-overlay-mode",
      "mobile"
    );
    expect(screen.getByTestId("documents-sidebar-overlay-pane")).toHaveAttribute(
      "data-overlay",
      "true"
    );

    const overlayBackdrop = screen.getByTestId("documents-sidebar-overlay").querySelector(
      'button[aria-label="Close sidebar"]'
    );
    expect(overlayBackdrop).toBeInTheDocument();
  });

  it("closes the Documents sidebar overlay on mobile via backdrop click", async () => {
    const user = userEvent.setup();
    setViewportWidth(390);
    localStorage.setItem("cfy.lastView", "documents");
    setRouteThread(null);

    render(<AppShell />);

    await user.click(screen.getByTestId("documents-sidebar-toggle"));
    expect(await screen.findByTestId("documents-sidebar-overlay")).toBeInTheDocument();

    const backdrop = screen.getByTestId("documents-sidebar-overlay").querySelector(
      'button[aria-label="Close sidebar"]'
    );
    fireEvent.click(backdrop!);

    await waitFor(() => {
      expect(screen.queryByTestId("documents-sidebar-overlay")).not.toBeInTheDocument();
    });
  });

  it("does not show duplicate sidebar or workspace drawer on Documents", () => {
    localStorage.setItem("cfy.lastView", "documents");
    setViewportWidth(1280);

    render(<AppShell />);

    expect(screen.queryAllByTestId("documents-shared-sidebar-pane")).toHaveLength(1);
    expect(screen.queryAllByTestId("workspace-drawer-pane")).toHaveLength(0);
    expect(screen.queryByTestId("documents-scope-rail")).not.toBeInTheDocument();
  });

  it("keeps Guardian shell behavior unaffected by Documents sidebar fix", async () => {
    const user = userEvent.setup();
    localStorage.setItem("cfy.lastView", "guardian");
    setRouteThread(101);

    render(<AppShell />);

    expect(screen.queryByTestId("documents-sidebar-toggle")).not.toBeInTheDocument();
    expect(screen.queryByTestId("documents-shared-sidebar-pane")).not.toBeInTheDocument();
    expect(screen.queryByTestId("documents-sidebar-overlay")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("workspace-drawer-toggle"));
    expect(await screen.findByTestId("workspace-drawer")).toBeInTheDocument();
  });

  it("shows no duplicate sidebar on constrained viewport with workspace focus", async () => {
    const user = userEvent.setup();
    setViewportWidth(1024);
    localStorage.setItem("cfy.lastView", "documents");
    setRouteThread(null);

    render(<AppShell />);

    fireEvent.click(screen.getByTestId("workspace-drawer-toggle"));
    await screen.findByTestId("workspace-drawer");

    const posture = screen.getByTestId("workspace-drawer-posture");
    await user.click(posture);
    await user.click(posture);

    await waitFor(() => {
      expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
        "data-layout-mode",
        "workspace_focus"
      );
    });

    expect(screen.queryAllByTestId("documents-shared-sidebar-pane")).toHaveLength(0);
    expect(screen.getByTestId("documents-center-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("documents-scope-rail")).not.toBeInTheDocument();
  });
});
