import { renderHook, act, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import api from "@/lib/api";

import { parseMessagesResponse, useChat } from "../useChat";

describe("parseMessagesResponse", () => {
  it("parses envelope format with ok: true and messages array", () => {
    const response = {
      ok: true,
      total: 2,
      messages: [
        {
          id: 1,
          thread_id: 100,
          role: "user",
          content: "Hello",
          created_at: "2024-01-01T00:00:00Z",
        },
        {
          id: 2,
          thread_id: 100,
          role: "assistant",
          content: "Hi there",
          created_at: "2024-01-01T00:00:01Z",
        },
      ],
    };

    const result = parseMessagesResponse(response);
    expect(result).not.toBeNull();
    expect(result?.[0]).toEqual(response.messages);
    expect(result?.[1]).toBe(2);
  });

  it("falls back to raw array format", () => {
    const response = [
      {
        id: 1,
        thread_id: 100,
        role: "user",
        content: "Hello",
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    const result = parseMessagesResponse(response);
    expect(result).not.toBeNull();
    expect(result?.[0]).toEqual(response);
    expect(result?.[1]).toBe(1);
  });

  it("uses total from envelope when available", () => {
    const response = {
      ok: true,
      total: 100,
      messages: [
        {
          id: 1,
          thread_id: 100,
          role: "user",
          content: "Hello",
          created_at: "2024-01-01T00:00:00Z",
        },
      ],
    };

    const result = parseMessagesResponse(response);
    expect(result?.[1]).toBe(100);
  });

  it("returns null for invalid envelope (ok: false)", () => {
    const response = {
      ok: false,
      messages: [],
    };

    const result = parseMessagesResponse(response);
    expect(result).toBeNull();
  });

  it("returns null for missing messages array in envelope", () => {
    const response = {
      ok: true,
      total: 0,
    };

    const result = parseMessagesResponse(response);
    expect(result).toBeNull();
  });

  it("returns null for invalid response (neither envelope nor array)", () => {
    const result = parseMessagesResponse({ foo: "bar" });
    expect(result).toBeNull();
  });

  it("returns null for null/undefined response", () => {
    expect(parseMessagesResponse(null)).toBeNull();
    expect(parseMessagesResponse(undefined)).toBeNull();
  });

  it("handles empty messages array in envelope", () => {
    const response = {
      ok: true,
      total: 0,
      messages: [],
    };

    const result = parseMessagesResponse(response);
    expect(result).not.toBeNull();
    expect(result?.[0]).toEqual([]);
    expect(result?.[1]).toBe(0);
  });

  it("uses message count as total fallback when total is missing", () => {
    const messages = [
      {
        id: 1,
        thread_id: 100,
        role: "user",
        content: "Hello",
        created_at: "2024-01-01T00:00:00Z",
      },
      {
        id: 2,
        thread_id: 100,
        role: "assistant",
        content: "Hi",
        created_at: "2024-01-01T00:00:01Z",
      },
    ];

    const response = {
      ok: true,
      messages,
    };

    const result = parseMessagesResponse(response);
    expect(result?.[1]).toBe(2);
  });

  it("renders both user and assistant messages without filtering by kind", () => {
    const response = {
      ok: true,
      total: 3,
      messages: [
        {
          id: 1,
          thread_id: 100,
          role: "user",
          kind: "chat",
          content: "Question",
          created_at: "2024-01-01T00:00:00Z",
        },
        {
          id: 2,
          thread_id: 100,
          role: "assistant",
          kind: "chat",
          content: "Answer",
          created_at: "2024-01-01T00:00:01Z",
        },
        {
          id: 3,
          thread_id: 100,
          role: "assistant",
          kind: "fact_evidence",
          content: "Evidence",
          created_at: "2024-01-01T00:00:02Z",
        },
      ],
    };

    const result = parseMessagesResponse(response);
    expect(result).not.toBeNull();
    // All messages are returned from parsing - filtering happens later via normalizeMessage
    expect(result?.[0]?.length).toBe(3);
    expect(result?.[1]).toBe(3);
  });
});

describe("useChat - completion state management", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("should start completion tracking with taskId and threadId", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.startCompletion(123, "task-abc-123");
    });

    expect(result.current.completionState.isCompleting).toBe(true);
    expect(result.current.completionState.activeTaskId).toBe("task-abc-123");
    expect(result.current.completionState.activeThreadId).toBe(123);
    expect(result.current.completionState.startedAt).toBeDefined();
  });

  it("should end completion tracking and clear all state", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.startCompletion(123, "task-abc-123");
    });

    expect(result.current.completionState.isCompleting).toBe(true);

    act(() => {
      result.current.endCompletion();
    });

    expect(result.current.completionState.isCompleting).toBe(false);
    expect(result.current.completionState.activeTaskId).toBeNull();
    expect(result.current.completionState.activeThreadId).toBeNull();
    expect(result.current.completionState.startedAt).toBeNull();
  });

  it("keeps completion active after slow-path hint and clears on hard timeout", async () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.startCompletion(123, "task-abc-123");
    });

    expect(result.current.completionState.isCompleting).toBe(true);

    // Fast-forward slow-path hint window — should still be completing
    act(() => {
      jest.advanceTimersByTime(15_000);
    });

    expect(result.current.completionState.isCompleting).toBe(true);

    // Fast-forward to hard timeout (30s total)
    act(() => {
      jest.advanceTimersByTime(15_000);
    });

    await waitFor(() => {
      expect(result.current.completionState.isCompleting).toBe(false);
    });

    expect(result.current.completionState.activeTaskId).toBeNull();
  });

  it("should guard against spam refresh", () => {
    const { result } = renderHook(() => useChat());

    // First refresh for thread 1 - should allow
    expect(result.current.shouldRefresh(1, 5)).toBe(true);

    act(() => {
      result.current.markRefreshed(1, 5);
    });

    // Same state within 500ms - should deny
    expect(result.current.shouldRefresh(1, 5)).toBe(false);

    // Different message count - should allow
    expect(result.current.shouldRefresh(1, 6)).toBe(true);

    // Different thread - should allow
    expect(result.current.shouldRefresh(2, 5)).toBe(true);
  });

  it("should allow refresh after 500ms debounce expires", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.markRefreshed(1, 5);
    });

    // Deny refresh within 500ms
    expect(result.current.shouldRefresh(1, 5)).toBe(false);

    // Fast-forward 500ms
    act(() => {
      jest.advanceTimersByTime(500);
    });

    // Allow refresh after debounce expires
    expect(result.current.shouldRefresh(1, 5)).toBe(true);
  });

  it("should clear timeout when endCompletion is called before hard timeout", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.startCompletion(123, "task-abc-123");
    });

    // Fast-forward 10 seconds (still within 30s)
    act(() => {
      jest.advanceTimersByTime(10000);
    });

    // End completion manually
    act(() => {
      result.current.endCompletion();
    });

    expect(result.current.completionState.isCompleting).toBe(false);

    // Fast-forward another 25 seconds (would be 35s total, past hard timeout)
    act(() => {
      jest.advanceTimersByTime(25000);
    });

    // State should remain cleared (timeout didn't fire again)
    expect(result.current.completionState.isCompleting).toBe(false);
  });

  it("should replace previous completion tracking when starting a new one", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.startCompletion(123, "task-first");
    });

    expect(result.current.completionState.activeTaskId).toBe("task-first");
    expect(result.current.completionState.activeThreadId).toBe(123);

    // Start a new completion
    act(() => {
      result.current.startCompletion(456, "task-second");
    });

    expect(result.current.completionState.activeTaskId).toBe("task-second");
    expect(result.current.completionState.activeThreadId).toBe(456);
  });
});

describe("useChat - loadMessages error hygiene", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("suppresses internal request guard metadata from UI error state", async () => {
    vi.spyOn(api, "get").mockRejectedValueOnce(
      Object.assign(new Error("request guard active (1200ms)"), {
        code: "ERR_CLIENT_RATE_GUARD",
        waitMs: 1200,
      })
    );

    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.loadMessages(32);
    });

    expect(result.current.error).toBeNull();
  });

  it("maps transport/internal exception text to a stable user-facing message", async () => {
    vi.spyOn(api, "get").mockRejectedValueOnce(
      new Error("HTTPConnectionPool(host='100.109.4.57', port=11434): Read timed out")
    );

    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.loadMessages(32);
    });

    expect(result.current.error).toBe("Unable to refresh messages right now.");
  });
});
