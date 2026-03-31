import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat, {
  flattenChatEventPayload,
} from "@/features/chat/GuardianChat";
import {
  CHAT_LANE_MAX_WIDTH,
  CHAT_LANE_MAX_WIDTH_CLASS,
  GUARDIAN_SHELL_MAX_WIDTH_CLASS,
} from "@/features/chat/chatLane";

const chatViewSpy = vi.hoisted(() => vi.fn());
const fetchLatestRagTraceMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  buildLlmCatalogPath: () => "/llm/catalog",
  buildChatCompletePath: () => "/chat/complete",
  clearInFlightCompletionTurnId: vi.fn(),
  fetchLatestRagTrace: fetchLatestRagTraceMock,
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
}));

vi.mock("@/lib/devFlags", () => ({
  isRagTraceUIEnabled: () => true,
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: any) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children, asChild, ...props }: any) => {
    if (asChild) return children;
    return (
      <button type="button" {...props}>
        {children}
      </button>
    );
  },
  DropdownMenuContent: ({ children }: any) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick, ...props }: any) => (
    <button type="button" onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@/features/chat/components", () => ({
  Composer: () => <div data-testid="composer-stub" />,
}));

vi.mock("@/features/chat/ChatView", () => ({
  default: (props: any) => {
    chatViewSpy(props);
    return <div data-testid="chat-view-stub">{String(props.threadId)}</div>;
  },
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children, className, style, "data-testid": dataTestId }: any) => (
    <div className={className} style={style} data-testid={dataTestId}>
      {children}
    </div>
  ),
}));

vi.mock("@/components/ui/sheet", () => ({
  Sheet: ({ children }: any) => <div>{children}</div>,
  SheetContent: ({ children }: any) => <div>{children}</div>,
  SheetHeader: ({ children }: any) => <div>{children}</div>,
  SheetTitle: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/features/chat/useChat", () => ({
  default: () => ({
    messages: [],
    loading: false,
    error: null,
    hasMore: false,
    activateThread: vi.fn(),
    refreshSnapshot: vi.fn().mockResolvedValue([]),
    loadOlderMessages: vi.fn().mockResolvedValue([]),
    completionState: {
      isCompleting: false,
      activeTaskId: null,
      activeThreadId: null,
      startedAt: null,
    },
    startCompletion: vi.fn(),
    endCompletion: vi.fn(),
    updateCompletionTaskId: vi.fn(),
    startCompletionSession: vi.fn(),
    reassociateCompletionSession: vi.fn(() => true),
    updateCompletionSessionTurnId: vi.fn(() => true),
    finalizeCompletionSession: vi.fn(() => true),
    handleIncomingAssistantMessage: vi.fn(() => false),
    isCompletionInFlight: vi.fn(() => false),
    setCompletionInFlight: vi.fn(),
  }),
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    subscribe: () => () => {},
  }),
}));

vi.mock("@/state/contextTrace", () => ({
  setTrace: vi.fn(),
}));

vi.mock("@/features/chat/components/PromptCostIndicator", () => ({
  default: () => null,
}));

const sessionRailSpy = vi.fn();

vi.mock("@/components/SessionRail/SessionRail", () => ({
  default: (props: any) => {
    sessionRailSpy(props);
    return (
      <div data-testid="session-rail-mock" data-has-tabs={props.tabs?.length > 0}>
        {props.tabs?.map((tab: any) => (
          <div
            key={tab.tabId}
            data-tab-id={tab.tabId}
            data-is-active={tab.tabId === props.activeTabId}
            data-testid={`mock-session-tab-${tab.tabId}`}
          >
            <span data-testid={`mock-tab-label-${tab.tabId}`}>{tab.title}</span>
            {tab.tabId === props.activeTabId && (
              <button
                data-testid={`mock-tab-close-${tab.tabId}`}
                onClick={() => props.onCloseTab?.(tab.tabId)}
              />
            )}
          </div>
        ))}
      </div>
    );
  },
}));

vi.mock("@/imprint/api", () => ({
  fetchSystemPromptSummary: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  markRuntimeRouteUnavailableIfNotFound: vi.fn(),
  useRuntimeRouteCapability: () => ({
    ready: true,
    state: "available",
  }),
}));

describe("GuardianChat session-tab binding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionRailSpy.mockClear();
    window.history.pushState({}, "", "/chat/1");
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the active tab thread instead of a stale route thread id", async () => {
    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "2", title: "Thread 2", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-2",
            threadId: "2",
            pendingThread: false,
            title: "Thread 2",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-2" as any}
      />
    );

    expect(await screen.findByTestId("chat-view-stub")).toHaveTextContent("2");
    expect(chatViewSpy.mock.calls.at(-1)?.[0]?.threadId).toBe(2);
  });

  it("shows a blank new-thread surface for an unsaved draft tab", async () => {
    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "temp", title: "New Thread", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-draft",
            pendingThread: true,
            title: "New Thread",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-draft" as any}
      />
    );

    expect(screen.queryByTestId("chat-view-stub")).not.toBeInTheDocument();
    expect(
      await screen.findByText("New thread ready. Start typing below.")
    ).toBeInTheDocument();
  });

  it("requests the RAG trace for the active thread and refetches when the active thread changes", async () => {
    fetchLatestRagTraceMock.mockResolvedValue({ documents: [], graph: [] });

    const { rerender } = render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "2", title: "Thread 2", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-2",
            threadId: "2",
            pendingThread: false,
            title: "Thread 2",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-2" as any}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /view rag trace/i }));

    await waitFor(() => {
      expect(fetchLatestRagTraceMock).toHaveBeenCalledWith(2);
    });

    rerender(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "7", title: "Thread 7", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-7",
            threadId: "7",
            pendingThread: false,
            title: "Thread 7",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-7" as any}
      />
    );

    await waitFor(() => {
      expect(fetchLatestRagTraceMock).toHaveBeenLastCalledWith(7);
    });
  });

  it("keeps the composer rail on the shared conversation lane", async () => {
    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "2", title: "Thread 2", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-2",
            threadId: "2",
            pendingThread: false,
            title: "Thread 2",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-2" as any}
      />
    );

    await waitFor(() => {
      const shell = screen.getByTestId("guardian-shell");
      expect(shell.className).toContain(GUARDIAN_SHELL_MAX_WIDTH_CLASS);

      const lane = screen.getByTestId("composer-conversation-lane");
      expect(lane).toHaveStyle({ maxWidth: `${CHAT_LANE_MAX_WIDTH}px` });
      expect(lane.className).toContain(CHAT_LANE_MAX_WIDTH_CLASS);

      const composerShell = screen.getByTestId("composer-shell");
      expect(composerShell).toHaveStyle({
        maxWidth: `${CHAT_LANE_MAX_WIDTH}px`,
      });
      expect(composerShell.className).toContain(CHAT_LANE_MAX_WIDTH_CLASS);
      expect(screen.getByTestId("composer-stub")).toBeInTheDocument();

      const nestedRoundedFaces = Array.from(
        composerShell.querySelectorAll("div")
      ).filter(
        (node) =>
          typeof node.className === "string" &&
          node.className.includes("rounded-[var(--tile-radius)]")
      );
      expect(nestedRoundedFaces).toHaveLength(0);
    });
  });
});

describe("GuardianChat session rail segmented strip behavior", () => {
  it("passes session tabs to the SessionRail component", async () => {
    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "1", title: "Thread 1", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-1",
            threadId: "1",
            pendingThread: false,
            title: "Alpha",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
          {
            tabId: "tab-2",
            threadId: "2",
            pendingThread: false,
            title: "Beta",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    await waitFor(() => {
      expect(sessionRailSpy).toHaveBeenCalled();
      const props = sessionRailSpy.mock.calls[0][0];
      expect(props.tabs).toHaveLength(2);
      expect(props.activeTabId).toBe("tab-1");
    });
  });

  it("close button is only rendered on the active session tab", async () => {
    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "1", title: "Thread 1", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-1",
            threadId: "1",
            pendingThread: false,
            title: "Alpha",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
          {
            tabId: "tab-2",
            threadId: "2",
            pendingThread: false,
            title: "Beta",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    await waitFor(() => {
      const activeTabCloseButton = screen.queryByTestId("mock-tab-close-tab-1");
      const inactiveTabCloseButton = screen.queryByTestId("mock-tab-close-tab-2");

      expect(activeTabCloseButton).toBeInTheDocument();
      expect(inactiveTabCloseButton).not.toBeInTheDocument();
    });
  });

  it("calls onCloseTab when the active tab close button is clicked", async () => {
    const onSessionTabClose = vi.fn();

    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "1", title: "Thread 1", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        onSessionTabClose={onSessionTabClose}
        sessionTabs={[
          {
            tabId: "tab-1",
            threadId: "1",
            pendingThread: false,
            title: "Alpha",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    await waitFor(() => {
      const closeButton = screen.getByTestId("mock-tab-close-tab-1");
      closeButton.click();
    });

    expect(onSessionTabClose).toHaveBeenCalledWith("tab-1");
  });

  it("session rail is rendered with tabs when multiple sessions exist", async () => {
    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "1", title: "Thread 1", messages: [] } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-1",
            threadId: "1",
            pendingThread: false,
            title: "Alpha",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
          {
            tabId: "tab-2",
            threadId: "2",
            pendingThread: false,
            title: "Beta",
            modelId: "default",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "default",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    await waitFor(() => {
      const railMock = screen.getByTestId("session-rail-mock");
      expect(railMock).toHaveAttribute("data-has-tabs", "true");
    });
  });
});

describe("GuardianChat task event payload handling", () => {
  it("keeps the outer task_id while exposing nested turn data", () => {
    const payload = flattenChatEventPayload({
      task_id: "task-outer",
      data: {
        turn_id: "turn-1",
        thread_id: 42,
      },
    });

    expect(payload.task_id).toBe("task-outer");
    expect(payload.turn_id).toBe("turn-1");
    expect(payload.thread_id).toBe(42);
  });
});
