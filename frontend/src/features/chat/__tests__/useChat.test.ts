import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";

import { parseMessagesResponse, useChat } from "../useChat";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../hooks/useTaskEvents", () => ({
  useTaskEvents: vi.fn(),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function buildMessage(
  id: number,
  role: "user" | "assistant",
  overrides: Record<string, unknown> = {}
) {
  return {
    id,
    thread_id: Number(overrides.thread_id ?? 7),
    role,
    content: String(overrides.content ?? `${role}-${id}`),
    created_at: String(
      overrides.created_at ??
        `2026-03-13T00:00:${String(id).padStart(2, "0")}.000Z`
    ),
    ...overrides,
  };
}

function buildEnvelope(messages: any[], total = messages.length) {
  return {
    data: {
      ok: true,
      total,
      messages,
    },
  };
}

describe("parseMessagesResponse", () => {
  it("parses envelope and raw array shapes", () => {
    const messages = [buildMessage(1, "user"), buildMessage(2, "assistant")];
    expect(parseMessagesResponse({ ok: true, total: 5, messages })).toEqual([
      messages,
      5,
    ]);
    expect(parseMessagesResponse(messages)).toEqual([messages, 2]);
  });

  it("returns null for unsupported payloads", () => {
    expect(parseMessagesResponse({ ok: false, messages: [] })).toBeNull();
    expect(parseMessagesResponse({ foo: "bar" })).toBeNull();
    expect(parseMessagesResponse(null)).toBeNull();
  });
});

describe("useChat refresh ownership", () => {
  const apiMock = api as unknown as {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("ignores stale snapshot results when a newer refresh supersedes them", async () => {
    const first = deferred<any>();
    const second = deferred<any>();
    apiMock.get
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);

    const { result } = renderHook(() => useChat());

    act(() => {
      void result.current.activateThread(7);
    });
    act(() => {
      void result.current.refreshSnapshot(7, "manual");
    });

    await act(async () => {
      first.resolve(buildEnvelope([buildMessage(1, "assistant")]));
      await Promise.resolve();
    });

    expect(result.current.messages).toEqual([]);

    await act(async () => {
      second.resolve(buildEnvelope([buildMessage(2, "assistant")]));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.messages.map((message) => message.id)).toEqual([2]);
    });
  });

  it("keeps pagination in flight when snapshot refreshes the same thread", async () => {
    const pagination = deferred<any>();
    let paginationSignal: AbortSignal | null = null;

    apiMock.get
      .mockResolvedValueOnce(
        buildEnvelope(
          [buildMessage(2, "user"), buildMessage(3, "assistant")],
          3
        )
      )
      .mockImplementationOnce((_url: string, config?: { signal?: AbortSignal }) => {
        paginationSignal = config?.signal ?? null;
        return pagination.promise;
      })
      .mockResolvedValueOnce(
        buildEnvelope(
          [buildMessage(2, "user"), buildMessage(3, "assistant")],
          3
        )
      );

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.activateThread(7);
    });

    act(() => {
      void result.current.loadOlderMessages(7, 100);
    });
    act(() => {
      void result.current.refreshSnapshot(7, "manual");
    });

    expect(paginationSignal?.aborted).toBe(false);

    await act(async () => {
      pagination.resolve(buildEnvelope([buildMessage(1, "assistant")], 3));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.messages.map((message) => message.id)).toEqual([
        1, 2, 3,
      ]);
    });
    expect(result.current.hasMore).toBe(false);
  });

  it("reassociates provisional task ids and invalidates old aliases after session replacement", async () => {
    apiMock.get
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user")], 1))
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user")], 1))
      .mockResolvedValueOnce(
        buildEnvelope(
          [
            buildMessage(1, "user"),
            buildMessage(2, "assistant", {
              content: "reply",
              audio_status: "ready",
            }),
          ],
          2
        )
      )
      .mockResolvedValueOnce(
        buildEnvelope(
          [buildMessage(10, "user", { thread_id: 7, content: "next" })],
          1
        )
      );

    const { result } = renderHook(() =>
      useChat({ completionHardTimeoutMs: 60_000 })
    );

    await act(async () => {
      await result.current.activateThread(7);
    });

    act(() => {
      result.current.startCompletion(7, "pending-1");
      result.current.startCompletionSession({
        threadId: 7,
        taskId: "pending-1",
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(2);
    });

    expect(
      result.current.reassociateCompletionSession({
        threadId: 7,
        provisionalTaskId: "pending-1",
        realTaskId: "task-1",
        reloadVersion: 1,
      })
    ).toBe(true);

    act(() => {
      result.current.handleIncomingAssistantMessage({
        id: 2,
        thread_id: 7,
        role: "assistant",
        content: "reply",
        created_at: "2026-03-13T00:00:02.000Z",
        task_id: "task-1",
        audio_status: "ready",
      });
    });

    await waitFor(() => {
      expect(result.current.completionState.isCompleting).toBe(false);
    });

    act(() => {
      expect(
        result.current.finalizeCompletionSession({
          taskId: "task-1",
          terminalState: "completed",
        })
      ).toBe(true);
      expect(
        result.current.finalizeCompletionSession({
          taskId: "pending-1",
          terminalState: "completed",
        })
      ).toBe(true);
    });
    act(() => {
      vi.advanceTimersByTime(250);
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(3);
    });

    act(() => {
      result.current.startCompletion(7, "pending-2");
      result.current.startCompletionSession({
        threadId: 7,
        taskId: "pending-2",
        reloadVersion: 2,
      });
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(4);
    });

    expect(
      result.current.finalizeCompletionSession({
        taskId: "task-1",
        terminalState: "completed",
      })
    ).toBe(false);
  });

  it("keeps the latest assistant row when a completion refresh races with a live assistant event", async () => {
    const threadId = 7;
    const turnId = "33333333-3333-4333-8333-333333333333";

    apiMock.get
      .mockResolvedValueOnce(
        buildEnvelope([buildMessage(1, "user", { thread_id: threadId })], 1)
      )
      .mockResolvedValueOnce(
        buildEnvelope([buildMessage(1, "user", { thread_id: threadId })], 1)
      )
      .mockResolvedValueOnce(
        buildEnvelope(
          [
            buildMessage(1, "user", { thread_id: threadId }),
            buildMessage(2, "assistant", {
              thread_id: threadId,
              turn_id: turnId,
              content: "Working...",
              created_at: "2026-03-13T00:00:02.000Z",
              task_id: "task-1",
            }),
            buildMessage(3, "assistant", {
              thread_id: threadId,
              turn_id: turnId,
              content: "Final answer",
              created_at: "2026-03-13T00:00:03.000Z",
              task_id: "task-1",
            }),
          ],
          3
        )
      )
      .mockResolvedValueOnce(
        buildEnvelope(
          [
            buildMessage(1, "user", { thread_id: threadId }),
            buildMessage(2, "assistant", {
              thread_id: threadId,
              turn_id: turnId,
              content: "Working...",
              created_at: "2026-03-13T00:00:02.000Z",
              task_id: "task-1",
            }),
            buildMessage(3, "assistant", {
              thread_id: threadId,
              turn_id: turnId,
              content: "Final answer",
              created_at: "2026-03-13T00:00:03.000Z",
              task_id: "task-1",
            }),
          ],
          3
        )
      );

    const { result } = renderHook(() =>
      useChat({ completionHardTimeoutMs: 60_000 })
    );

    await act(async () => {
      await result.current.activateThread(threadId);
    });

    act(() => {
      result.current.startCompletion(threadId, "task-1");
      result.current.startCompletionSession({
        threadId,
        taskId: "task-1",
        turnId,
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(2);
    });

    act(() => {
      result.current.handleIncomingAssistantMessage({
        id: 2,
        thread_id: threadId,
        role: "assistant",
        content: "Working...",
        created_at: "2026-03-13T00:00:02.000Z",
        task_id: "task-1",
        turn_id: turnId,
      });
    });

    act(() => {
      expect(
        result.current.finalizeCompletionSession({
          taskId: "task-1",
          terminalState: "completed",
        })
      ).toBe(true);
    });

    await act(async () => {
      vi.advanceTimersByTime(250);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(3);
      expect(result.current.messages.map((message) => message.id)).toEqual([
        1,
        3,
      ]);
      expect(
        result.current.messages.filter((message) =>
          String(message.role).trim().toLowerCase() === "assistant"
        )
      ).toHaveLength(1);
      expect(
        result.current.messages.find(
          (message) => String(message.role).trim().toLowerCase() === "assistant"
        )?.content
      ).toBe("Final answer");
    });

    await act(async () => {
      await result.current.refreshSnapshot(threadId, "manual");
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(4);
      expect(result.current.messages.map((message) => message.id)).toEqual([
        1,
        3,
      ]);
      expect(
        result.current.messages.filter((message) =>
          String(message.role).trim().toLowerCase() === "assistant"
        )
      ).toHaveLength(1);
    });
  });

  it("does not attach an assistant row from a background thread to the active thread", async () => {
    apiMock.get
      .mockResolvedValueOnce(
        buildEnvelope([buildMessage(1, "user", { thread_id: 7 })], 1)
      )
      .mockResolvedValueOnce(
        buildEnvelope([buildMessage(9, "user", { thread_id: 8 })], 1)
      );

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.activateThread(7);
    });

    await act(async () => {
      await result.current.activateThread(8);
    });

    act(() => {
      result.current.handleIncomingAssistantMessage({
        id: 2,
        thread_id: 7,
        role: "assistant",
        content: "wrong thread",
        created_at: "2026-03-13T00:00:02.000Z",
        task_id: "task-7",
        turn_id: "44444444-4444-4444-8444-444444444444",
      });
    });

    expect(result.current.messages.map((message) => message.thread_id)).toEqual([
      8,
    ]);
    expect(
      result.current.messages.some((message) => message.thread_id === 7)
    ).toBe(false);
  });

  it("does not end an active completion for an unrelated assistant message", async () => {
    apiMock.get
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user")], 1))
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user")], 1));

    const { result } = renderHook(() =>
      useChat({ completionHardTimeoutMs: 60_000 })
    );
    const activeTurnId = "11111111-1111-4111-8111-111111111111";

    await act(async () => {
      await result.current.activateThread(7);
    });

    act(() => {
      result.current.startCompletion(7, "task-1");
      result.current.startCompletionSession({
        threadId: 7,
        taskId: "task-1",
        turnId: activeTurnId,
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(2);
    });

    expect(
      result.current.handleIncomingAssistantMessage({
        id: 99,
        thread_id: 7,
        role: "assistant",
        content: "other reply",
        created_at: "2026-03-13T00:00:09.000Z",
        task_id: "task-2",
        turn_id: "22222222-2222-4222-8222-222222222222",
      })
    ).toBe(false);
    expect(result.current.completionState.isCompleting).toBe(true);
  });

  it("rejects task aliases after the owning thread session is replaced", async () => {
    apiMock.get
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user", { thread_id: 7 })], 1))
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user", { thread_id: 7 })], 1))
      .mockResolvedValueOnce(buildEnvelope([buildMessage(11, "user", { thread_id: 8 })], 1));

    const { result } = renderHook(() =>
      useChat({ completionHardTimeoutMs: 60_000 })
    );

    await act(async () => {
      await result.current.activateThread(7);
    });

    act(() => {
      result.current.startCompletion(7, "pending-7");
      result.current.startCompletionSession({
        threadId: 7,
        taskId: "pending-7",
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(2);
    });

    expect(
      result.current.reassociateCompletionSession({
        threadId: 7,
        provisionalTaskId: "pending-7",
        realTaskId: "task-7",
        reloadVersion: 1,
      })
    ).toBe(true);

    await act(async () => {
      await result.current.activateThread(8);
    });

    expect(
      result.current.finalizeCompletionSession({
        taskId: "task-7",
        terminalState: "completed",
      })
    ).toBe(false);
  });

  it("marks final snapshot failure as terminal and does not retry on duplicate finalize calls", async () => {
    apiMock.get
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user")], 1))
      .mockResolvedValueOnce(buildEnvelope([buildMessage(1, "user")], 1))
      .mockRejectedValueOnce(new Error("boom"));

    const { result } = renderHook(() =>
      useChat({ completionHardTimeoutMs: 60_000 })
    );

    await act(async () => {
      await result.current.activateThread(7);
    });

    act(() => {
      result.current.startCompletion(7, "pending-1");
      result.current.startCompletionSession({
        threadId: 7,
        taskId: "pending-1",
        reloadVersion: 1,
      });
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(2);
    });

    expect(
      result.current.reassociateCompletionSession({
        threadId: 7,
        provisionalTaskId: "pending-1",
        realTaskId: "task-1",
        reloadVersion: 1,
      })
    ).toBe(true);

    act(() => {
      expect(
        result.current.finalizeCompletionSession({
          taskId: "task-1",
          terminalState: "failed",
        })
      ).toBe(true);
    });
    act(() => {
      vi.advanceTimersByTime(250);
    });

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledTimes(3);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(
      result.current.finalizeCompletionSession({
        taskId: "pending-1",
        terminalState: "failed",
      })
    ).toBe(false);
    expect(apiMock.get).toHaveBeenCalledTimes(3);
  });
});
