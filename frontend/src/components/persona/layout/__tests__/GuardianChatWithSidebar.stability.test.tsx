import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import GuardianChatWithSidebar from "../GuardianChatWithSidebar";
import api from "@/lib/api";

const guardianPropsSpy = vi.hoisted(() => vi.fn());
const sidebarPropsSpy = vi.hoisted(() => vi.fn());
const sessionSpineInstances = vi.hoisted(() => [] as any[]);
const sessionHooksState = vi.hoisted(() => ({
  railSlice: { tabs: [] as any[], activeTabId: null as string | null },
  activeTab: null as any,
  activeModelId: "default",
}));
const authState = vi.hoisted(() => ({
  ready: true,
  status: "authenticated" as const,
  token: "test-token",
}));

vi.mock("@/features/chat/GuardianChat", () => ({
  default: (props: any) => {
    guardianPropsSpy(props);
    return (
      <div data-testid="guardian-chat-mock">
        <div data-testid="active-thread-id">{String(props?.activeThread?.id ?? "none")}</div>
        <div data-testid="active-thread-title">{String(props?.activeThread?.title ?? "")}</div>
        <div data-testid="active-thread-messages">{String(props?.activeThread?.messages?.length ?? 0)}</div>
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

vi.mock("@/state/session/SessionStateStore", () => ({
  RedisSessionStateStore: class {},
}));

vi.mock("@/state/session/SessionSpine", () => ({
  SessionSpine: class {
    hydrate = vi.fn(async () => null);
    getDraft = vi.fn(() => "");
    tabOpen = vi.fn();
    tabSetThread = vi.fn();
    tabActivate = vi.fn();
    tabClose = vi.fn();
    tabSetModel = vi.fn();
    tabSetDraft = vi.fn();

    constructor() {
      sessionSpineInstances.push(this);
    }
  },
}));

vi.mock("@/state/session/hooks", () => ({
  useSessionRailSlice: () => sessionHooksState.railSlice,
  useSessionActiveTab: () => sessionHooksState.activeTab,
  useSessionActiveModelId: () => sessionHooksState.activeModelId,
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

type ThreadRow = {
  id: number;
  title: string;
  last_message?: string;
  project_id?: number | null;
};

function t(id: number, title?: string, projectId: number | null = null): ThreadRow {
  return {
    id,
    title: title ?? `Thread ${id}`,
    last_message: "",
    project_id: projectId,
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
    sessionHooksState.activeModelId = "default";
    localStorage.clear();
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

  it("keeps selected thread stable when pagination appends", async () => {
    setupThreadApi({
      all: {
        0: { threads: [t(1), t(2)], has_more: true },
        2: { threads: [t(3)], has_more: false },
      },
    });

    const user = userEvent.setup();
    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

    await screen.findByTestId("thread-1");
    await user.click(screen.getByTestId("thread-2"));
    await waitFor(() => {
      expect(screen.getByTestId("active-thread-id").textContent).toBe("2");
    });

    await user.click(screen.getByTestId("sidebar-load-more"));
    await screen.findByTestId("thread-3");

    expect(screen.getByTestId("active-thread-id").textContent).toBe("2");
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
    render(<GuardianChatWithSidebar guardianName="Guardian" userName="User" />);

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
      title: "Thread 1",
      modelId: "default",
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };
    const tabTwo = {
      tabId: "tab-2",
      threadId: "2",
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
});
