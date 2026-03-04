import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ChatView from "@/features/chat/ChatView";

type Subscriber = (event: { type: string; data: unknown }) => void;

let mockMessages: any[] = [];
const loadMessagesMock = vi.fn().mockResolvedValue(undefined);
const appendMessageMock = vi.fn();
const shouldRefreshMock = vi.fn().mockReturnValue(false);
const markRefreshedMock = vi.fn();
const subscribeMock = vi.fn();
const apiPostMock = vi.fn();
const apiGetMock = vi.fn();
const pollOptionsHistory: any[] = [];
let pollFnRef: (() => Promise<void>) | null = null;

const liveSubscribersByType = new Map<string, Set<Subscriber>>();
let unsubscribeCount = 0;

function resetLiveSubscribers(): void {
  liveSubscribersByType.clear();
  unsubscribeCount = 0;
}

function emitLiveEvent(eventType: string, payload: unknown): void {
  const bucket = liveSubscribersByType.get(eventType);
  if (!bucket) return;
  [...bucket].forEach((listener) => listener({ type: eventType, data: payload }));
}

function activeSubscriberCount(eventType: string): number {
  return liveSubscribersByType.get(eventType)?.size ?? 0;
}

vi.mock("@/features/chat/useChat", () => ({
  useChat: () => ({
    messages: mockMessages,
    loadMessages: loadMessagesMock,
    appendMessage: appendMessageMock,
    loading: false,
    error: null,
    hasMore: false,
    shouldRefresh: shouldRefreshMock,
    markRefreshed: markRefreshedMock,
  }),
  parseMessagesResponse: (data: any) => {
    if (data?.ok && Array.isArray(data.messages)) {
      return [data.messages, data.total ?? data.messages.length];
    }
    if (Array.isArray(data)) {
      return [data, data.length];
    }
    return null;
  },
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    subscribe: subscribeMock,
  }),
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

vi.mock("@/lib/polling/usePollWithBackoff", () => ({
  usePollWithBackoff: (fn: () => Promise<void>, opts: any) => {
    pollFnRef = fn;
    pollOptionsHistory.push(opts);
  },
}));

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/components/ChatBubble", () => ({
  default: ({
    message,
    showPlay,
    onPlay,
    playState,
    playing,
  }: {
    message: { id: string; content: string };
    showPlay?: boolean;
    onPlay?: () => void;
    playState?: "idle" | "playing" | "unavailable" | "disabled";
    playing?: boolean;
  }) => {
    const resolved =
      playState ?? (playing ? "playing" : "idle");
    const label =
      resolved === "playing"
        ? "Playing..."
        : resolved === "unavailable"
          ? "Audio unavailable"
        : resolved === "disabled"
            ? "Voice disabled"
            : "Read Aloud";
    const disabled = resolved === "unavailable" || resolved === "disabled";
    const ariaLabel = label === "Read Aloud" ? "Read message aloud" : label;
    return (
      <div data-testid={`bubble-${message.id}`}>
        <div>{message.content}</div>
        {showPlay ? (
          <button
            type="button"
            onClick={onPlay}
            disabled={disabled}
            aria-label={ariaLabel}
            title={label}
          >
            {label}
          </button>
        ) : null}
      </div>
    );
  },
}));

vi.mock("@/lib/api", () => ({
  default: {
    post: (...args: any[]) => apiPostMock(...args),
    get: (...args: any[]) => apiGetMock(...args),
  },
  getBackendOutageRemainingMs: vi.fn(() => 0),
}));

describe("ChatView loop guards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMessages = [];
    loadMessagesMock.mockResolvedValue(undefined);
    appendMessageMock.mockClear();
    shouldRefreshMock.mockReturnValue(false);
    markRefreshedMock.mockClear();
    apiPostMock.mockReset();
    apiGetMock.mockReset();
    pollFnRef = null;
    pollOptionsHistory.length = 0;
    resetLiveSubscribers();

    subscribeMock.mockImplementation((eventType: string, handler: Subscriber) => {
      const bucket = liveSubscribersByType.get(eventType) ?? new Set<Subscriber>();
      bucket.add(handler);
      liveSubscribersByType.set(eventType, bucket);
      return () => {
        const current = liveSubscribersByType.get(eventType);
        if (!current) return;
        current.delete(handler);
        unsubscribeCount += 1;
        if (current.size === 0) {
          liveSubscribersByType.delete(eventType);
        }
      };
    });
  });

  it("keeps one message.created subscription per thread and unsubscribes on thread change", async () => {
    const baseCompletion = {
      isCompleting: false,
      activeTaskId: null,
      activeThreadId: null,
      startedAt: null,
    };
    const endCompletion = vi.fn();

    const { rerender } = render(
      <ChatView threadId={1} completionState={baseCompletion} endCompletion={endCompletion} />
    );

    await waitFor(() => {
      expect(activeSubscriberCount("message.created")).toBe(1);
    });

    rerender(
      <ChatView
        threadId={1}
        reloadVersion={1}
        completionState={baseCompletion}
        endCompletion={endCompletion}
      />
    );
    await waitFor(() => {
      expect(activeSubscriberCount("message.created")).toBe(1);
    });

    rerender(
      <ChatView
        threadId={2}
        reloadVersion={1}
        completionState={baseCompletion}
        endCompletion={endCompletion}
      />
    );
    await waitFor(() => {
      expect(activeSubscriberCount("message.created")).toBe(1);
    });
    expect(unsubscribeCount).toBeGreaterThanOrEqual(1);
  });

  it("ignores stale-thread completion events and finalizes active-thread completion only", async () => {
    vi.useFakeTimers();
    const endCompletion = vi.fn();
    const completionThread2 = {
      isCompleting: true,
      activeTaskId: "task-2",
      activeThreadId: 2,
      startedAt: Date.now(),
    };
    const completionThread3 = {
      isCompleting: true,
      activeTaskId: "task-3",
      activeThreadId: 3,
      startedAt: Date.now(),
    };

    const { rerender } = render(
      <ChatView threadId={2} completionState={completionThread2} endCompletion={endCompletion} />
    );
    await waitFor(() => {
      expect(activeSubscriberCount("message.created")).toBe(1);
    });

    rerender(
      <ChatView threadId={3} completionState={completionThread3} endCompletion={endCompletion} />
    );
    await waitFor(() => {
      expect(activeSubscriberCount("message.created")).toBe(1);
    });

    emitLiveEvent("message.created", { thread_id: 2, role: "assistant", id: 5002 });
    vi.advanceTimersByTime(200);
    expect(endCompletion).toHaveBeenCalledTimes(0);

    emitLiveEvent("message.created", { thread_id: 3, role: "assistant", id: 5003 });
    vi.advanceTimersByTime(200);
    expect(endCompletion).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it("clears completion immediately when task.failed arrives for the active task", async () => {
    const endCompletion = vi.fn();
    const completion = {
      isCompleting: true,
      activeTaskId: "task-11",
      activeThreadId: 11,
      startedAt: Date.now(),
    };

    render(
      <ChatView
        threadId={11}
        completionState={completion}
        endCompletion={endCompletion}
      />
    );

    await waitFor(() => {
      expect(activeSubscriberCount("task.failed")).toBe(1);
    });

    emitLiveEvent("task.failed", {
      thread_id: 11,
      task_id: "task-11",
      error: "boom",
    });

    await waitFor(() => {
      expect(endCompletion).toHaveBeenCalledTimes(1);
    });
  });

  it("ignores stale task.failed and only finalizes for the active thread/task", async () => {
    const endCompletion = vi.fn();
    const completionThread2 = {
      isCompleting: true,
      activeTaskId: "task-2",
      activeThreadId: 2,
      startedAt: Date.now(),
    };
    const completionThread3 = {
      isCompleting: true,
      activeTaskId: "task-3",
      activeThreadId: 3,
      startedAt: Date.now(),
    };

    const { rerender } = render(
      <ChatView
        threadId={2}
        completionState={completionThread2}
        endCompletion={endCompletion}
      />
    );

    await waitFor(() => {
      expect(activeSubscriberCount("task.failed")).toBe(1);
    });

    rerender(
      <ChatView
        threadId={3}
        completionState={completionThread3}
        endCompletion={endCompletion}
      />
    );

    await waitFor(() => {
      expect(activeSubscriberCount("task.failed")).toBe(1);
    });

    act(() => {
      emitLiveEvent("task.failed", {
        thread_id: 2,
        task_id: "task-2",
        error: "stale",
      });
    });
    expect(endCompletion).toHaveBeenCalledTimes(0);

    act(() => {
      emitLiveEvent("task.failed", {
        thread_id: 3,
        task_id: "task-3",
        error: "active",
      });
    });
    await waitFor(() => {
      expect(endCompletion).toHaveBeenCalledTimes(1);
    });
  });

  it("uses poll-key idempotency and restarts when depth/profile context changes", async () => {
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    mockMessages = [
      {
        id: 101,
        thread_id: 1,
        role: "user",
        content: "hello",
        created_at: "2026-03-02T00:00:00.000Z",
      },
    ];

    const completion = {
      isCompleting: true,
      activeTaskId: "task-1",
      activeThreadId: 1,
      startedAt: Date.now(),
    };
    const endCompletion = vi.fn();

    const { rerender } = render(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={endCompletion}
        reloadVersion={0}
        depthMode="normal"
        profileId="profile-a"
      />
    );

    rerender(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={endCompletion}
        reloadVersion={1}
        depthMode="normal"
        profileId="profile-a"
      />
    );
    await waitFor(() => {
      expect(
        debugSpy.mock.calls.some((call) =>
          String(call[0]).includes("key=1:101:normal:profile-a")
        )
      ).toBe(true);
    });

    expect(pollOptionsHistory.length).toBeGreaterThan(0);
    const latestOptions = pollOptionsHistory[pollOptionsHistory.length - 1];
    expect(latestOptions.intervalMs).toBe(1500);
    expect(latestOptions.maxBackoffMs).toBe(5000);

    rerender(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={endCompletion}
        reloadVersion={2}
        depthMode="normal"
        profileId="profile-a"
      />
    );
    await waitFor(() => {
      expect(
        debugSpy.mock.calls.some((call) =>
          String(call[0]).includes("skip duplicate poll session key=1:101:normal:profile-a")
        )
      ).toBe(true);
    });

    rerender(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={endCompletion}
        reloadVersion={3}
        depthMode="deep"
        profileId="profile-a"
      />
    );
    await waitFor(() => {
      expect(
        debugSpy.mock.calls.some((call) =>
          String(call[0]).includes("key=1:101:deep:profile-a")
        )
      ).toBe(true);
    });
  });

  it("does not start polling from reload updates when completion is inactive", async () => {
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    mockMessages = [
      {
        id: 201,
        thread_id: 1,
        role: "user",
        content: "hello",
        created_at: "2026-03-02T00:00:00.000Z",
      },
    ];
    const completion = {
      isCompleting: false,
      activeTaskId: null,
      activeThreadId: null,
      startedAt: null,
    };

    const { rerender } = render(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={vi.fn()}
        reloadVersion={0}
      />
    );

    rerender(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={vi.fn()}
        reloadVersion={1}
      />
    );

    await waitFor(() => {
      expect(loadMessagesMock).toHaveBeenCalled();
    });

    expect(
      debugSpy.mock.calls.some((call) =>
        String(call[0]).includes("[chat:poll] start reason=")
      )
    ).toBe(false);
  });

  it("stops polling when assistant reply arrives after user message", async () => {
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    mockMessages = [
      {
        id: 301,
        thread_id: 1,
        role: "user",
        content: "pending",
        created_at: "2026-03-02T00:00:00.000Z",
      },
    ];
    apiGetMock.mockResolvedValue({
      data: {
        ok: true,
        messages: [
          {
            id: 302,
            thread_id: 1,
            role: "assistant",
            content: "done",
            created_at: "2026-03-02T00:00:01.000Z",
          },
        ],
        total: 2,
      },
    });
    const completion = {
      isCompleting: true,
      activeTaskId: "task-301",
      activeThreadId: 1,
      startedAt: Date.now(),
    };

    render(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={vi.fn()}
        reloadVersion={1}
      />
    );

    await waitFor(() => {
      expect(
        debugSpy.mock.calls.some((call) =>
          String(call[0]).includes("[chat:poll] start reason=user-message")
        )
      ).toBe(true);
    });

    expect(pollFnRef).not.toBeNull();
    await act(async () => {
      await pollFnRef?.();
    });

    expect(apiGetMock).toHaveBeenCalledWith("/chat/1/messages", {
      params: { limit: 100, offset: 0 },
    });
    expect(appendMessageMock).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ id: 302, role: "assistant" })
    );
    expect(
      debugSpy.mock.calls.some((call) =>
        String(call[0]).includes("stop reason=assistant-reply-arrived")
      )
    ).toBe(true);
  });

  it("classifies voice 404s: message-level unavailable and route-level disable", async () => {
    const completion = {
      isCompleting: false,
      activeTaskId: null,
      activeThreadId: null,
      startedAt: null,
    };
    const endCompletion = vi.fn();

    mockMessages = [
      {
        id: 700,
        thread_id: 1,
        role: "assistant",
        content: "assistant message",
        created_at: "2026-03-02T00:00:00.000Z",
      },
    ];

    apiPostMock.mockRejectedValueOnce({
      response: { status: 404, data: { detail: "message_not_found" } },
    });

    const { rerender } = render(
      <ChatView
        threadId={1}
        completionState={completion}
        endCompletion={endCompletion}
        voiceReadAloudEnabled
        voiceCapabilitiesFailed
      />
    );

    const firstPlay = await screen.findByRole("button", {
      name: "Read message aloud",
    });
    fireEvent.click(firstPlay);

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledTimes(1);
    });
    expect(await screen.findByRole("button", { name: "Audio unavailable" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Audio unavailable" }));
    expect(apiPostMock).toHaveBeenCalledTimes(1);

    mockMessages = [
      {
        id: 800,
        thread_id: 2,
        role: "assistant",
        content: "assistant message 2",
        created_at: "2026-03-02T00:01:00.000Z",
      },
    ];
    apiPostMock.mockRejectedValueOnce({
      response: { status: 404, data: { detail: "route_not_found" } },
    });

    rerender(
      <ChatView
        threadId={2}
        completionState={completion}
        endCompletion={endCompletion}
        voiceReadAloudEnabled
        voiceCapabilitiesFailed
      />
    );

    const secondPlay = await screen.findByRole("button", {
      name: "Read message aloud",
    });
    fireEvent.click(secondPlay);

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "Read message aloud" })
      ).not.toBeInTheDocument();
    });
  });
});
