import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat, {
  flattenChatEventPayload,
} from "@/features/chat/GuardianChat";
import {
  CHAT_LANE_MAX_WIDTH,
  CHAT_LANE_MAX_WIDTH_CLASS,
} from "@/features/chat/chatLane";

const chatViewSpy = vi.hoisted(() => vi.fn());

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
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
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
  default: ({ children }: any) => <div>{children}</div>,
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
    refreshSnapshot: vi.fn(),
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

vi.mock("@/components/SessionRail/SessionRail", () => ({
  default: () => null,
}));

vi.mock("@/imprint/api", () => ({
  fetchSystemPromptSummary: vi.fn().mockResolvedValue(null),
}));

describe("GuardianChat session-tab binding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/chat/1");
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

    const lane = screen.getByTestId("composer-conversation-lane");
    expect(lane).toHaveStyle({ maxWidth: `${CHAT_LANE_MAX_WIDTH}px` });
    expect(lane.className).toContain(CHAT_LANE_MAX_WIDTH_CLASS);
    expect(screen.getByTestId("composer-shell")).toHaveStyle({
      maxWidth: `${CHAT_LANE_MAX_WIDTH}px`,
    });
    expect(screen.getByTestId("composer-shell").className).toContain(
      CHAT_LANE_MAX_WIDTH_CLASS
    );
    expect(screen.getByTestId("composer-stub")).toBeInTheDocument();
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
