import { act, render, screen, waitFor } from "@testing-library/react";
import { useEffect, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatView from "@/features/chat/ChatView";
import { useChat } from "@/features/chat/useChat";

const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
}));

const taskEventHandlers = vi.hoisted(
  () => new Map<string, (event: Record<string, unknown>) => void>()
);

type HarnessApi = {
  setThreadId: (threadId: number) => void;
  startCompletion: ReturnType<typeof useChat>["startCompletion"];
  startCompletionSession: ReturnType<typeof useChat>["startCompletionSession"];
  handleIncomingAssistantMessage: ReturnType<
    typeof useChat
  >["handleIncomingAssistantMessage"];
};

let harnessApi: HarnessApi | null = null;

vi.mock("@/lib/api", () => ({
  default: apiSpies,
}));

vi.mock("@/features/chat/hooks/useTaskEvents", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  return {
    useTaskEvents: (
      taskId: string | null,
      onEvent: (event: Record<string, unknown>) => void
    ) => {
      React.useEffect(() => {
        if (!taskId) return;
        taskEventHandlers.set(taskId, onEvent);
        return () => {
          if (taskEventHandlers.get(taskId) === onEvent) {
            taskEventHandlers.delete(taskId);
          }
        };
      }, [onEvent, taskId]);
    },
  };
});

vi.mock("@/features/chat/components/ChatBubble", () => ({
  default: ({
    message,
  }: {
    message: { id: string; content: string };
  }) => <div data-testid={`bubble-${message.id}`}>{message.content}</div>,
}));

vi.mock("@/features/chat/components/InferenceStatusBanner", () => ({
  default: () => null,
}));

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/hooks/useChatAutoScroll", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  return {
    useChatAutoScroll: () => ({
      containerRef: React.useRef<HTMLDivElement | null>(null),
      endRef: React.useRef<HTMLDivElement | null>(null),
    }),
  };
});

function buildMessage(
  id: number,
  role: "user" | "assistant",
  threadId: number,
  content: string
) {
  return {
    id,
    thread_id: threadId,
    role,
    content,
    created_at: `2026-04-02T00:00:${String(id).padStart(2, "0")}.000Z`,
  };
}

function emitTaskEvent(taskId: string, event: Record<string, unknown>) {
  const handler = taskEventHandlers.get(taskId);
  if (!handler) return false;
  act(() => {
    handler({
      ...event,
      task_id: taskId,
    });
  });
  return true;
}

function StreamingChatHarness() {
  const chat = useChat({ completionHardTimeoutMs: 60_000 });
  const [threadId, setThreadId] = useState(7);

  useEffect(() => {
    void chat.activateThread(threadId);
  }, [chat.activateThread, threadId]);

  useEffect(() => {
    harnessApi = {
      setThreadId,
      startCompletion: chat.startCompletion,
      startCompletionSession: chat.startCompletionSession,
      handleIncomingAssistantMessage: chat.handleIncomingAssistantMessage,
    };
    return () => {
      harnessApi = null;
    };
  }, [
    chat.handleIncomingAssistantMessage,
    chat.startCompletion,
    chat.startCompletionSession,
    setThreadId,
  ]);

  return (
    <ChatView
      threadId={threadId}
      guardianName="Guardian"
      messages={chat.messages}
      loading={chat.loading}
      error={chat.error}
      hasMore={chat.hasMore}
      completionState={chat.completionState}
      endCompletion={chat.endCompletion}
      streamingDraft={chat.streamingDraft}
    />
  );
}

describe("GuardianChat streaming drafts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    taskEventHandlers.clear();
    harnessApi = null;
    apiSpies.get.mockImplementation((url: string) => {
      const match = String(url).match(/\/chat\/(\d+)\/messages/);
      const threadId = match ? Number(match[1]) : 7;
      const messages = [buildMessage(1, "user", threadId, `thread-${threadId}-user`)];
      return Promise.resolve({
        data: {
          ok: true,
          total: messages.length,
          messages,
        },
      });
    });
  });

  afterEach(() => {
    taskEventHandlers.clear();
    harnessApi = null;
  });

  it("renders streamed chunks before the final assistant message lands", async () => {
    render(<StreamingChatHarness />);

    await waitFor(() => {
      expect(screen.getByText("thread-7-user")).toBeInTheDocument();
    });

    act(() => {
      harnessApi?.startCompletion(7, "task-1");
      harnessApi?.startCompletionSession({
        threadId: 7,
        taskId: "task-1",
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(taskEventHandlers.has("task-1")).toBe(true);
    });

    emitTaskEvent("task-1", {
      type: "task.chunk",
      thread_id: 7,
      delta: "Hel",
    });

    await waitFor(() => {
      expect(screen.getByTestId("chat-streaming-draft")).toHaveTextContent("Hel");
    });

    emitTaskEvent("task-1", {
      type: "task.chunk",
      thread_id: 7,
      delta: "lo",
    });

    await waitFor(() => {
      expect(screen.getByTestId("chat-streaming-draft")).toHaveTextContent("Hello");
    });

    act(() => {
      harnessApi?.handleIncomingAssistantMessage({
        id: 42,
        thread_id: 7,
        role: "assistant",
        content: "Hello world",
        created_at: "2026-04-02T00:00:42.000Z",
        task_id: "task-1",
      });
    });

    await waitFor(() => {
      expect(screen.queryByTestId("chat-streaming-draft")).not.toBeInTheDocument();
      expect(screen.getByText("Hello world")).toBeInTheDocument();
    });
  });

  it("clears stale streamed text on thread switch and ignores old chunks", async () => {
    render(<StreamingChatHarness />);

    await waitFor(() => {
      expect(screen.getByText("thread-7-user")).toBeInTheDocument();
    });

    act(() => {
      harnessApi?.startCompletion(7, "task-1");
      harnessApi?.startCompletionSession({
        threadId: 7,
        taskId: "task-1",
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(taskEventHandlers.has("task-1")).toBe(true);
    });

    emitTaskEvent("task-1", {
      type: "task.chunk",
      thread_id: 7,
      delta: "draft",
    });

    await waitFor(() => {
      expect(screen.getByTestId("chat-streaming-draft")).toHaveTextContent("draft");
    });

    act(() => {
      harnessApi?.setThreadId(8);
    });

    await waitFor(() => {
      expect(screen.getByText("thread-8-user")).toBeInTheDocument();
      expect(screen.queryByTestId("chat-streaming-draft")).not.toBeInTheDocument();
    });

    emitTaskEvent("task-1", {
      type: "task.chunk",
      thread_id: 7,
      delta: "stale",
    });

    expect(screen.queryByTestId("chat-streaming-draft")).not.toBeInTheDocument();
  });

  it("renders the final assistant message even when no chunks were emitted", async () => {
    render(<StreamingChatHarness />);

    await waitFor(() => {
      expect(screen.getByText("thread-7-user")).toBeInTheDocument();
    });

    act(() => {
      harnessApi?.startCompletion(7, "task-1");
      harnessApi?.startCompletionSession({
        threadId: 7,
        taskId: "task-1",
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(taskEventHandlers.has("task-1")).toBe(true);
    });

    expect(screen.queryByTestId("chat-streaming-draft")).not.toBeInTheDocument();

    act(() => {
      harnessApi?.handleIncomingAssistantMessage({
        id: 42,
        thread_id: 7,
        role: "assistant",
        content: "Final answer",
        created_at: "2026-04-02T00:00:42.000Z",
        task_id: "task-1",
      });
    });

    await waitFor(() => {
      expect(screen.getByText("Final answer")).toBeInTheDocument();
      expect(screen.queryByTestId("chat-streaming-draft")).not.toBeInTheDocument();
    });
  });
});
