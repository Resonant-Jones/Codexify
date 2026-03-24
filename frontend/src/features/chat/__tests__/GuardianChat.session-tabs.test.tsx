import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";

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
    completionState: { isCompleting: false, activeThreadId: null },
    startCompletion: vi.fn(),
    endCompletion: vi.fn(),
    updateCompletionTaskId: vi.fn(),
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
});
