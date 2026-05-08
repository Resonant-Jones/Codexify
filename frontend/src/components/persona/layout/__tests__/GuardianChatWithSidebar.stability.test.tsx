import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import GuardianChatWithSidebar from "../GuardianChatWithSidebar";
import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";

const guardianPropsSpy = vi.hoisted(() => vi.fn());
const sidebarPropsSpy = vi.hoisted(() => vi.fn());
const sessionSpineInstances = vi.hoisted(() => [] as any[]);
const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}));
const sessionHooksState = vi.hoisted(() => ({
  railSlice: { tabs: [] as any[], activeTabId: null as string | null },
  activeTab: null as any,
  activeDraft: "",
  activeProviderId: "local" as string | null,
  activeModelId: "default",
  activeInferenceMode: "default",
}));
const providerState = vi.hoisted(() => ({
  data: null as unknown,
  error: null as unknown,
  isLoading: false,
}));
const authState = vi.hoisted(() => ({
  ready: true,
  status: "authenticated" as const,
  token: "test-token",
}));
const runtimeAuthState = vi.hoisted(() => ({
  isTauri: false,
  desktopAuthConfig: null as
    | null
    | {
        apiKeyPresent: boolean;
        apiKey: string | null;
        envPath: string | null;
        runtimeRoot: string | null;
        failureKind: string | null;
      },
}));
const runtimeHealthState = vi.hoisted(() => ({
  status: "healthy" as const,
    diagnostics: null as
    | null
    | {
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
        };
        liveEvents: {
          endpoint: string | null;
          connectionState: string;
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
        failureKind: string | null;
        lastSuccessAt: number | null;
        lastFailedAt: number | null;
        lastCheckedAt: number | null;
        currentComputedStateSource: string;
      },
}));
const routeCapabilityStates = vi.hoisted(
  () =>
    ({
      imprint: "available",
      ui_session: "available",
    }) as Record<string, "available" | "unavailable" | "unknown">
);

vi.mock("@/features/chat/GuardianChat", () => ({
  default: (props: any) => {
    guardianPropsSpy(props);
    return (
      <div data-testid="guardian-chat-mock">
        <div data-testid="active-thread-id">{String(props?.activeThread?.id ?? "none")}</div>
        <div data-testid="active-thread-title">{String(props?.activeThread?.title ?? "")}</div>
        <div data-testid="active-thread-messages">{String(props?.activeThread?.messages?.length ?? 0)}</div>
        {props?.runtimeHealth?.diagnostics ? (
          <div data-testid="runtime-health-diagnostics">
            {[
              `resolvedApiBaseUrl=${String(props.runtimeHealth.diagnostics.resolvedApiBaseUrl ?? "")}`,
              `resolvedApiBaseUrlSource=${String(props.runtimeHealth.diagnostics.resolvedApiBaseUrlSource ?? "")}`,
              `apiKeyPresent=${props.runtimeHealth.diagnostics.apiKeyPresent ? "true" : "false"}`,
              `apiKeySource=${String(props.runtimeHealth.diagnostics.apiKeySource ?? "")}`,
              `hydrationState=${String(props.runtimeHealth.diagnostics.hydrationState ?? "")}`,
              `nativeCommandStatus=${String(props.runtimeHealth.diagnostics.nativeCommandStatus ?? "")}`,
              `authSource=${String(props.runtimeHealth.diagnostics.authSource ?? "")}`,
              `chatEndpoint=${String(props.runtimeHealth.diagnostics.chat.endpoint ?? "")}`,
              `chatStatus=${String(props.runtimeHealth.diagnostics.chat.parsedStatus ?? "")}`,
              `llmEndpoint=${String(props.runtimeHealth.diagnostics.llm.endpoint ?? "")}`,
              `llmStatus=${String(props.runtimeHealth.diagnostics.llm.parsedStatus ?? "")}`,
              `failureKind=${String(props.runtimeHealth.diagnostics.failureKind ?? "")}`,
            ].join(" | ")}
          </div>
        ) : null}
      </div>
    );
  },
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: (props: any) => {
    sidebarPropsSpy(props);
    return (
      <div data-testid="sidebar-root-mock">
        <button data-testid="sidebar-new-chat" onClick={() => props.onNewChat?.()}>
          New Chat
        </button>
        <button data-testid="sidebar-load-more" onClick={() => props.onLoadMoreThreads?.()}>
          Load More
        </button>
        <button data-testid="sidebar-set-project-2" onClick={() => props.onProjectChange?.("2")}>
          Set Project 2
        </button>
        {Array.isArray(props.threads) &&
          props.threads.map((thread: any) => (
            <button
              key={String(thread.id)}
              data-testid={`thread-${String(thread.id)}`}
              onClick={() => props.onSelect?.(String(thread.id))}
            >
              {String(thread.title)}
            </button>
          ))}
      </div>
    );
  },
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    subscribe: () => () => {},
  }),
}));

vi.mock("@/hooks/useRuntimeHealth", () => ({
  __esModule: true,
  default: () => runtimeHealthState,
  formatRuntimeHealthDiagnostics: (diagnostics: any) => [
    `resolved api base url=${diagnostics.resolvedApiBaseUrl ?? "<unresolved>"}`,
    `resolved api base url source=${diagnostics.resolvedApiBaseUrlSource ?? "<unknown>"}`,
    `apiKeyPresent=${diagnostics.apiKeyPresent ? "true" : "false"}`,
    `api key source=${diagnostics.apiKeySource ?? "<unknown>"}`,
    `hydration state=${diagnostics.hydrationState ?? "<unknown>"}`,
    `native command status=${diagnostics.nativeCommandStatus ?? "<unknown>"}`,
    `authSource=${diagnostics.authSource}`,
    `chat endpoint called=${diagnostics.chat.endpoint}`,
    `parsed chat health status=${diagnostics.chat.parsedStatus ?? "<none>"}`,
    `parsed chat health ok=${
      diagnostics.chat.parsedOk == null
        ? "<unknown>"
        : diagnostics.chat.parsedOk
          ? "true"
          : "false"
    }`,
    `llm endpoint called=${diagnostics.llm.endpoint}`,
    `parsed llm health status=${diagnostics.llm.parsedStatus ?? "<none>"}`,
    `parsed llm health ok=${
      diagnostics.llm.parsedOk == null
        ? "<unknown>"
        : diagnostics.llm.parsedOk
          ? "true"
          : "false"
    }`,
    `failureKind=${diagnostics.failureKind ?? "none"}`,
    `last successful health poll=${diagnostics.lastSuccessAt ?? "<none>"}`,
    `last failed health poll=${diagnostics.lastFailedAt ?? "<none>"}`,
    `current health poll=${diagnostics.lastCheckedAt ?? "<none>"}`,
    `current computed state source=${diagnostics.currentComputedStateSource}`,
  ],
}));

vi.mock("@/hooks/useWallpaperUrl", () => ({
  useWallpaperUrl: () => ({ wallpaperUrl: null }),
}));

vi.mock("@/imprint/useImprintZero", () => ({
  default: () => ({
    proposal: null,
    status: null,
    accept: vi.fn(),
    reject: vi.fn(),
  }),
}));

vi.mock("@/imprint/ImprintZeroToast", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/components/PromptCostIndicator", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/hooks/useProviderState", () => ({
  useProviderState: () => providerState,
}));

vi.mock("@/components/ui/RefractiveGlassCard", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/lib/authState", () => ({
  useAuthState: () => authState,
  checkAuthGate: () => true,
  requireAuthReady: () => true,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  isTauriRuntime: () => runtimeAuthState.isTauri,
  getDesktopRuntimeAuthConfig: () => runtimeAuthState.desktopAuthConfig,
}));

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapabilities: (labels: string[]) => {
    const states: Record<string, "available" | "unavailable" | "unknown"> =
      {};
    for (const label of labels) {
      states[label] = routeCapabilityStates[label] ?? "unknown";
    }
    return {
      ready: true,
      states,
      mounted: [],
      declared: {},
    };
  },
}));

vi.mock("@/state/session/SessionStateStore", () => ({
  InMemorySessionStateStore: class {
    getSessionState = vi.fn(async () => null);
  },
  RedisSessionStateStore: class {
    getSessionState = vi.fn(async (_userId: string, _deviceId: string) => {
      return apiSpies.get("/ui/session", {
        params: {
          user_id: _userId,
          device_id: _deviceId,
        },
      });
    });
  },
}));

vi.mock("@/state/session/SessionSpine", () => ({
  SessionSpine: class {
    __config: any;
    __activeCompletion: any;
    __composerBlocked: boolean;
    __cancelShouldUnblock: boolean;

    hydrate = vi.fn(async () => {
      return (
        (await this.__config?.store?.getSessionState?.(
          this.__config?.userId,
          this.__config?.deviceId
        )) ?? null
      );
    });
    getDraft = vi.fn(() => "");
    getActiveCompletion = vi.fn(() => this.__activeCompletion ?? null);
    isComposerBlocked = vi.fn(() => Boolean(this.__composerBlocked));
    cancelActiveCompletion = vi.fn((options?: any) => {
      const targetThreadId = String(options?.threadId ?? "");
      const activeThreadId = String(this.__activeCompletion?.threadId ?? "");
      if (!targetThreadId || !activeThreadId || targetThreadId !== activeThreadId) {
        return null;
      }
      if (this.__cancelShouldUnblock !== false) {
        this.__composerBlocked = false;
        this.__activeCompletion = {
          ...this.__activeCompletion,
          status: "canceled",
        };
      }
      return this.__activeCompletion;
    });
    tabOpen = vi.fn();
    tabSetThread = vi.fn((tabId: string, threadId?: string, title?: string) => {
      const rail = sessionHooksState.railSlice;
      const tabs = Array.isArray(rail?.tabs) ? rail.tabs : [];
      const index = tabs.findIndex((tab: any) => tab.tabId === tabId);
      if (index === -1) return;
      const baseTab = tabs[index];
      const nextTab = {
        ...baseTab,
        threadId: threadId ?? undefined,
        pendingThread: !threadId,
        title: title ?? baseTab.title,
      };
      const nextTabs = tabs.slice();
      nextTabs[index] = nextTab;
      sessionHooksState.railSlice = {
        ...rail,
        tabs: nextTabs,
      };
      if (rail.activeTabId === tabId) {
        sessionHooksState.activeTab = nextTab;
      }
    });
    tabActivate = vi.fn();
    tabClose = vi.fn();
    tabSetProvider = vi.fn();
    tabSetModel = vi.fn();
    tabSetInferenceMode = vi.fn();
    tabSetDraft = vi.fn();

    constructor(config: any) {
      this.__config = config;
      this.__activeCompletion = null;
      this.__composerBlocked = false;
      this.__cancelShouldUnblock = true;
      sessionSpineInstances.push(this);
    }
  },
}));

vi.mock("@/state/session/hooks", () => ({
  useSessionRailSlice: () => sessionHooksState.railSlice,
  useSessionActiveTab: () => sessionHooksState.activeTab,
  useSessionActiveDraft: () => sessionHooksState.activeDraft,
  useSessionActiveProviderId: () => sessionHooksState.activeProviderId,
  useSessionActiveModelId: () => sessionHooksState.activeModelId,
  useSessionActiveInferenceMode: () => sessionHooksState.activeInferenceMode,
}));

vi.mock("@/lib/api", () => ({
  default: apiSpies,
}));

const mockApi = apiSpies;

type ThreadRow = {
  id: number;
  title: string;
  last_message?: string;
  project_id?: number | null;
  thread_config?: Record<string, unknown> | null;
};

function t(
  id: number,
  title?: string,
  projectId: number | null = null,
  threadConfig: Record<string, unknown> | null = null
): ThreadRow {
  return {
    id,
    title: title ?? `Thread ${id}`,
    last_message: "",
    project_id: projectId,
    thread_config: threadConfig,
  };
}

function setupThreadApi(
  pages: Record<
    string,
    Record<number, { threads: ThreadRow[]; has_more: boolean }>
  >
) {
  mockApi.get.mockImplementation((url: string, config?: any) => {
    if (url !== "/chat/threads") {
      return Promise.resolve({ data: {} });
    }
    const params = config?.params ?? {};
    const projectKey =
      params.project_id != null ? String(params.project_id) : "all";
    const offset = Number(params.offset ?? 0);
    const page = pages[projectKey]?.[offset] ?? { threads: [], has_more: false };
    return Promise.resolve({
      data: {
        ok: true,
        threads: page.threads,
        has_more: page.has_more,
      },
    });
  });
}

describe("GuardianChatWithSidebar stability contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionSpineInstances.length = 0;
    sessionHooksState.railSlice = { tabs: [], activeTabId: null };
    sessionHooksState.activeTab = null;
    sessionHooksState.activeDraft = "";
    sessionHooksState.activeProviderId = "local";
    sessionHooksState.activeModelId = "default";
    sessionHooksState.activeInferenceMode = "default";
    providerState.data = null;
    providerState.error = null;
    providerState.isLoading = false;
    routeCapabilityStates[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] = "available";
    routeCapabilityStates[SUPPORTED_PROFILE_ROUTE_LABELS.UI_SESSION] =
      "available";
    const storage = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn((key: string) => storage.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => {
          storage.set(key, value);
        }),
        removeItem: vi.fn((key: string) => {
          storage.delete(key);
        }),
        clear: vi.fn(() => {
          storage.clear();
        }),
      },
      configurable: true,
    });
    Object.defineProperty(window, "sessionStorage", {
      value: {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      },
      configurable: true,
    });
    window.history.pushState({}, "", "/chat");
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it("does not probe /ui/session when the restricted profile marks ui_session unavailable", async () => {
    routeCapabilityStates[SUPPORTED_PROFILE_ROUTE_LABELS.UI_SESSION] =
      "unavailable";
    setupThreadApi({
      all: {
        0: { threads: [t(1), t(2)], has_more: false },
      },
    });

    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        runtimeHealth={runtimeHealthState as any}
      />
    );

    await screen.findByTestId("thread-1");

    expect(
      mockApi.get.mock.calls.some(([url]) => url === "/ui/session")
    ).toBe(false);
  });

  it("stays mounted when provider state transitions to an error", () => {
    const { rerender } = render(
      <GuardianChatWithSidebar guardianName="Guardian" userName="User" />
    );

    providerState.error = new Error("Provider state fetch failed");

    rerender(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    expect(screen.getByTestId("guardian-chat-mock")).toBeInTheDocument();
  });

  it("keeps selected thread stable when pagination appends", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(1), t(2)], has_more: true },
        2: { threads: [t(3)], has_more: false },
      },
    });

    const user = userEvent.setup();
    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        runtimeHealth={runtimeHealthState as any}
      />
    );

    await screen.findByTestId("thread-1");
    await user.click(screen.getByTestId("thread-2"));
    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("2");
    });

    await user.click(screen.getByTestId("sidebar-load-more"));
    await screen.findByTestId("thread-3");

    expect(screen.getByTestId("active-thread-id").textContent).toBe("2");
  });

  it("preserves thread_config from backend rows when restoring the active thread", async () => {
    const persistedConfig = {
      providerId: "local",
      modelId: "qwen3.5:14b",
      inferenceMode: "fast",
      retrievalSource: "project",
      personaId: null,
    };

    setupThreadApi({
      all: {
        0: {
          threads: [t(1, "Thread 1"), t(2, "Thread 2", null, persistedConfig)],
          has_more: false,
        },
      },
    });

    const user = userEvent.setup();
    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        runtimeHealth={runtimeHealthState as any}
      />
    );

    await screen.findByTestId("thread-2");
    await user.click(screen.getByTestId("thread-2"));

    await waitFor(() => {
      const activeThread = guardianPropsSpy.mock.calls.at(-1)?.[0]?.activeThread;
      expect(activeThread?.id).toBe("2");
      expect(activeThread?.threadConfig).toEqual(persistedConfig);
    });
  });

  it("keeps click selection consistent after loading more and dedupes by id", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(1), t(2)], has_more: true },
      },
      "2": {
        0: { threads: [t(167, "Imports 167", 2)], has_more: true },
        1: { threads: [t(167, "Imports 167", 2), t(168, "Imports 168", 2)], has_more: false },
      },
    });

    const user = userEvent.setup();
    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        runtimeHealth={runtimeHealthState as any}
      />
    );

    await screen.findByTestId("thread-1");
    await user.click(screen.getByTestId("sidebar-set-project-2"));
    await screen.findByTestId("thread-167", {}, { timeout: 3000 });

    await waitFor(() => {
      expect(
        mockApi.get.mock.calls.some(
          ([url, cfg]) =>
            url === "/chat/threads" && Number((cfg as any)?.params?.project_id) === 2
        )
      ).toBe(true);
    });

    await user.click(screen.getByTestId("thread-167"));
    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("167");
    });

    await user.click(screen.getByTestId("sidebar-load-more"));
    await screen.findByTestId("thread-168");

    expect(screen.getAllByTestId("thread-167")).toHaveLength(1);
    expect(screen.getByTestId("active-thread-id").textContent).toBe("167");
  });

  it("new chat clears prior thread and shows New Thread placeholder", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(11, "Thread 11")], has_more: false },
      },
    });

    const user = userEvent.setup();
    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("thread-11");
    await user.click(screen.getByTestId("thread-11"));
    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("11");
    });
    expect(screen.getByTestId("active-thread-title").textContent).toBe("Thread 11");

    await user.click(screen.getByTestId("sidebar-new-chat"));

    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("temp");
    });
    expect(screen.getByTestId("active-thread-title").textContent).toBe("New Thread");
    expect(screen.getByTestId("active-thread-messages").textContent).toBe("0");
    expect(window.location.pathname).toBe("/chat");
  });

  it("clears stale session tab thread ids that are missing from loaded threads", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(2, "Thread 2")], has_more: false },
      },
    });

    sessionHooksState.railSlice = {
      tabs: [
        {
          tabId: "tab-1",
          threadId: "1",
          pendingThread: false,
          title: "Stale Thread",
          modelId: "default",
          createdAt: "2026-01-01T00:00:00.000Z",
          updatedAt: "2026-01-01T00:00:00.000Z",
        },
      ],
      activeTabId: "tab-1",
    };
    sessionHooksState.activeTab = sessionHooksState.railSlice.tabs[0];
    sessionHooksState.activeModelId = "default";

    window.history.pushState({}, "", "/chat/1");
    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("thread-2");
    await waitFor(() => {
      expect(window.location.pathname).toBe("/chat");
    });
    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("temp");
    });

    const spine = sessionSpineInstances[0];
    expect(spine).toBeDefined();
    expect(
      spine.tabSetThread.mock.calls.some(
        (args: unknown[]) =>
          args[0] === "tab-1" && args[1] === undefined && args[2] === undefined
      )
    ).toBe(true);
  });

  it("does not copy the previous thread into a newly activated session tab", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(1, "Thread 1"), t(2, "Thread 2")], has_more: false },
      },
    });

    const tabOne = {
      tabId: "tab-1",
      threadId: "1",
      pendingThread: false,
      title: "Thread 1",
      modelId: "default",
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };
    const tabTwo = {
      tabId: "tab-2",
      threadId: "2",
      pendingThread: false,
      title: "Thread 2",
      modelId: "default",
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };

    sessionHooksState.railSlice = {
      tabs: [tabOne, tabTwo],
      activeTabId: "tab-1",
    };
    sessionHooksState.activeTab = tabOne;
    sessionHooksState.activeModelId = "default";

    window.history.pushState({}, "", "/chat/1");
    const view = render(
      <GuardianChatWithSidebar guardianName="Guardian" userName="User" />
    );

    await screen.findByTestId("thread-1");
    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("1");
    });

    const spine = sessionSpineInstances[0];
    expect(spine).toBeDefined();
    spine.tabSetThread.mockClear();

    sessionHooksState.railSlice = {
      tabs: [tabOne, tabTwo],
      activeTabId: "tab-2",
    };
    sessionHooksState.activeTab = tabTwo;
    view.rerender(
      <GuardianChatWithSidebar guardianName="Guardian" userName="User" />
    );

    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("2");
    });

    expect(
      spine.tabSetThread.mock.calls.some(
        (args: unknown[]) => args[0] === "tab-2" && args[1] === "1"
      )
    ).toBe(false);
  });

  it("binds sidebar selection to the active tab only", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(1, "Thread 1"), t(2, "Thread 2")], has_more: false },
      },
    });

    const tabOne = {
      tabId: "tab-1",
      threadId: "1",
      pendingThread: false,
      title: "Thread 1",
      modelId: "default",
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };
    const tabTwo = {
      tabId: "tab-2",
      pendingThread: true,
      title: "New Thread",
      modelId: "default",
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };

    sessionHooksState.railSlice = {
      tabs: [tabOne, tabTwo],
      activeTabId: "tab-2",
    };
    sessionHooksState.activeTab = tabTwo;

    const user = userEvent.setup();
    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("thread-1");
    const spine = sessionSpineInstances[0];
    expect(spine).toBeDefined();

    await user.click(screen.getByTestId("thread-1"));

    expect(
      spine.tabSetThread.mock.calls.some(
        (args: unknown[]) =>
          args[0] === "tab-2" && args[1] === "1" && args[2] === "Thread 1"
      )
    ).toBe(true);
    expect(
      spine.tabSetThread.mock.calls.some(
        (args: unknown[]) => args[0] === "tab-1" && args[1] === "1"
      )
    ).toBe(false);
  });

  it("persists a created thread back to its originating tab only", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(1, "Thread 1"), t(2, "Thread 2")], has_more: false },
      },
    });

    const tabOne = {
      tabId: "tab-1",
      pendingThread: true,
      title: "New Thread",
      modelId: "default",
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };
    const tabTwo = {
      tabId: "tab-2",
      threadId: "2",
      pendingThread: false,
      title: "Thread 2",
      modelId: "default",
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };

    sessionHooksState.railSlice = {
      tabs: [tabOne, tabTwo],
      activeTabId: "tab-2",
    };
    sessionHooksState.activeTab = tabTwo;

    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("thread-1");
    const spine = sessionSpineInstances[0];
    expect(spine).toBeDefined();
    const guardianProps = guardianPropsSpy.mock.calls.at(-1)?.[0];
    expect(guardianProps).toBeDefined();

    act(() => {
      guardianProps.onThreadPersisted(77, "Draft Bound", { tabId: "tab-1" });
    });

    expect(
      spine.tabSetThread.mock.calls.some(
        (args: unknown[]) =>
          args[0] === "tab-1" && args[1] === "77" && args[2] === "Draft Bound"
      )
    ).toBe(true);
    expect(
      spine.tabSetThread.mock.calls.some(
        (args: unknown[]) => args[0] === "tab-2" && args[1] === "77"
      )
    ).toBe(false);
    expect(screen.getByTestId("active-thread-id").textContent).toBe("2");
  });

  it("deleting the active thread applies a safe fallback and updates tab binding", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(11, "Thread 11"), t(22, "Thread 22")], has_more: false },
      },
    });

    sessionHooksState.railSlice = {
      tabs: [
        {
          tabId: "tab-1",
          threadId: "11",
          pendingThread: false,
          title: "Thread 11",
          modelId: "default",
          createdAt: "2026-01-01T00:00:00.000Z",
          updatedAt: "2026-01-01T00:00:00.000Z",
        },
      ],
      activeTabId: "tab-1",
    };
    sessionHooksState.activeTab = sessionHooksState.railSlice.tabs[0];

    const user = userEvent.setup();
    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("thread-11");
    await user.click(screen.getByTestId("thread-11"));
    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("11");
    });

    const sidebarProps = sidebarPropsSpy.mock.calls.at(-1)?.[0];
    expect(sidebarProps).toBeDefined();
    await act(async () => {
      await sidebarProps.onDeleteThread?.("11");
    });

    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("22");
    });
    expect(window.location.pathname).toBe("/chat/22");
    expect(screen.queryByTestId("thread-11")).not.toBeInTheDocument();

    const spine = sessionSpineInstances[0];
    expect(
      spine.tabSetThread.mock.calls.some(
        (args: unknown[]) =>
          args[0] === "tab-1" && args[1] === "22" && args[2] === "Thread 22"
      )
    ).toBe(true);
  });

  it("allows deleting a thread after canceling an in-flight completion lock", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(11, "Thread 11")], has_more: false },
      },
    });

    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);
    await screen.findByTestId("thread-11");

    const spine = sessionSpineInstances[0];
    spine.__activeCompletion = {
      completionId: "c-1",
      threadId: "11",
      status: "streaming",
    };
    spine.__composerBlocked = true;
    spine.__cancelShouldUnblock = true;

    const sidebarProps = sidebarPropsSpy.mock.calls.at(-1)?.[0];
    expect(sidebarProps).toBeDefined();
    const guardMessage = await sidebarProps.onBeforeDeleteThread?.("11");

    expect(guardMessage).toBeNull();
    expect(
      spine.cancelActiveCompletion.mock.calls.some(
        (args: unknown[]) =>
          (args?.[0] as any)?.threadId === "11" &&
          (args?.[0] as any)?.restoreDraft === false
      )
    ).toBe(true);
    expect(spine.isComposerBlocked()).toBe(false);
  });

  it("blocks deletion with a clear message when in-flight completion cannot be unwound", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(11, "Thread 11")], has_more: false },
      },
    });

    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);
    await screen.findByTestId("thread-11");

    const spine = sessionSpineInstances[0];
    spine.__activeCompletion = {
      completionId: "c-2",
      threadId: "11",
      status: "streaming",
    };
    spine.__composerBlocked = true;
    spine.__cancelShouldUnblock = false;

    const sidebarProps = sidebarPropsSpy.mock.calls.at(-1)?.[0];
    expect(sidebarProps).toBeDefined();
    const guardMessage = await sidebarProps.onBeforeDeleteThread?.("11");

    expect(guardMessage).toBe(
      "Finish or cancel the current assistant reply before deleting this thread."
    );
    expect(
      spine.cancelActiveCompletion.mock.calls.some(
        (args: unknown[]) => (args?.[0] as any)?.threadId === "11"
      )
    ).toBe(true);
    expect(spine.isComposerBlocked()).toBe(true);
  });
});

  it("stays mounted when optional system prompt summary returns 403", async () => {
    routeCapabilityStates[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] = "available";
    routeCapabilityStates[SUPPORTED_PROFILE_ROUTE_LABELS.UI_SESSION] = "available";
    setupThreadApi({
      all: {
        0: { threads: [t(1)], has_more: false },
      },
    });

    mockApi.get.mockImplementation((url: string) => {
      if (url === "/api/system_prompt/summary") {
        const err = new Error("Forbidden") as any;
        err.response = { status: 403 };
        return Promise.reject(err);
      }
      if (url === "/chat/threads") {
        return Promise.resolve({
          data: { ok: true, threads: [{ id: 1, title: "Thread 1", last_message: "" }], has_more: false },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("guardian-chat-mock");
    expect(screen.getByTestId("guardian-chat-mock")).toBeInTheDocument();
  });

  it("stays mounted when optional embed route returns 404", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(1)], has_more: false },
      },
    });

    const originalFetch = global.fetch;
    global.fetch = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = String(url);
      if (urlStr.includes("/embed")) {
        return new Response("Not Found", { status: 404 });
      }
      return originalFetch(url, init);
    });

    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("guardian-chat-mock");
    expect(screen.getByTestId("guardian-chat-mock")).toBeInTheDocument();

    global.fetch = originalFetch;
  });

describe("GuardianChatWithSidebar auth banner", () => {
  beforeEach(() => {
    authState.ready = true;
    authState.status = "authenticated";
    authState.token = "test-token";
    runtimeAuthState.isTauri = false;
    runtimeAuthState.desktopAuthConfig = null;
    runtimeHealthState.status = "healthy";
    runtimeHealthState.diagnostics = null;
    const storage = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn((key: string) => storage.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => {
          storage.set(key, value);
        }),
        removeItem: vi.fn((key: string) => {
          storage.delete(key);
        }),
        clear: vi.fn(() => {
          storage.clear();
        }),
      },
      configurable: true,
    });
    Object.defineProperty(window, "sessionStorage", {
      value: {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      },
      configurable: true,
    });
  });

  it("does not render the auth banner when the runtime auth key is already unified into auth state", () => {
    authState.ready = true;
    authState.status = "authenticated";
    authState.token = undefined;
    runtimeAuthState.isTauri = true;
    runtimeAuthState.desktopAuthConfig = {
      apiKeyPresent: true,
      apiKey: "desktop-secret-key",
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: null,
    };

    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    expect(screen.queryByText("Authentication required.")).toBeNull();
  });

  it("renders sanitized desktop diagnostics without exposing the raw key", () => {
    authState.ready = true;
    authState.status = "unauthenticated";
    authState.token = undefined;
    runtimeAuthState.isTauri = true;
    runtimeAuthState.desktopAuthConfig = {
      apiKeyPresent: true,
      apiKey: "desktop-secret-key",
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: "config_incomplete",
    };

    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    expect(screen.getByText("Authentication required.")).toBeInTheDocument();
    expect(screen.getByText("apiKeyPresent=true")).toBeInTheDocument();
    expect(screen.getByText("envPath=/Users/chriscastillo/Codexify/.env")).toBeInTheDocument();
    expect(screen.getByText("runtimeRoot=/Users/chriscastillo/Codexify")).toBeInTheDocument();
    expect(screen.getByText("failureKind=config_incomplete")).toBeInTheDocument();
    expect(screen.queryByText("desktop-secret-key")).toBeNull();
    expect(screen.queryByText("Sign in or provide a dev key in local development.")).toBeNull();
  });

  it("forwards sanitized runtime-health diagnostics to the provider banner path", () => {
    runtimeHealthState.status = "degraded";
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
      },
      liveEvents: {
        endpoint: "http://127.0.0.1:8888/api/events",
        connectionState: "connected",
        lastEventAt: Date.parse("2026-03-20T11:59:58.000Z"),
        lastPingAt: Date.parse("2026-03-20T11:59:58.000Z"),
        statusUpdatedAt: Date.parse("2026-03-20T12:00:00.000Z"),
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
      failureKind: "chat_unhealthy",
      lastSuccessAt: Date.parse("2026-03-20T12:00:00.000Z"),
      lastFailedAt: Date.parse("2026-03-20T11:59:00.000Z"),
      lastCheckedAt: Date.parse("2026-03-20T12:00:00.000Z"),
      currentComputedStateSource: "live-poll",
    };
    runtimeAuthState.isTauri = true;
    runtimeAuthState.desktopAuthConfig = {
      apiKeyPresent: true,
      apiKey: "desktop-secret-key",
      envPath: "/Users/chriscastillo/Codexify/.env",
      runtimeRoot: "/Users/chriscastillo/Codexify",
      failureKind: null,
    };

    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        runtimeHealth={runtimeHealthState as any}
      />
    );

    expect(screen.getByTestId("runtime-health-diagnostics")).toHaveTextContent(
      "resolvedApiBaseUrl=http://127.0.0.1:8888/api"
    );
    expect(screen.getByTestId("runtime-health-diagnostics")).toHaveTextContent(
      "apiKeyPresent=true"
    );
    expect(screen.getByTestId("runtime-health-diagnostics")).toHaveTextContent(
      "authSource=runtime-desktop"
    );
    expect(screen.getByTestId("runtime-health-diagnostics")).toHaveTextContent(
      "chatEndpoint=/health/chat"
    );
    expect(screen.getByTestId("runtime-health-diagnostics")).toHaveTextContent(
      "llmEndpoint=/api/health/llm"
    );
    expect(screen.getByTestId("runtime-health-diagnostics")).toHaveTextContent(
      "failureKind=chat_unhealthy"
    );
    expect(screen.queryByText("desktop-secret-key")).toBeNull();
  });
});
