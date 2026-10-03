import { act, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import InferenceStatusBanner from "@/features/chat/components/InferenceStatusBanner";

import {
  describeInferenceRequestState,
  INFERENCE_SLOW_PATH_MS,
  useInferenceRequestState,
} from "@/features/chat/hooks/useInferenceRequestState";

const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

const eventSources = vi.hoisted(() => ({
  instances: [] as MockGuardianEventSource[],
}));

type MockGuardianEventSource = EventTarget & {
  url: string;
  options: Record<string, unknown>;
  readyState: number;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent<string>) => void) | null;
  onerror: ((event: Event) => void) | null;
  close: ReturnType<typeof vi.fn>;
  emit: (type: string, data: Record<string, unknown>) => void;
  emitError: () => void;
};

vi.mock("@/lib/api", () => ({
  default: apiSpies,
  buildAuthenticatedFetchInit: (init: RequestInit = {}) => init,
  getAuthToken: vi.fn(() => null),
  getDevApiKey: vi.fn(() => null),
  readRuntimeApiKey: vi.fn(() => null),
}));

vi.mock("@/lib/guardianEventSource", () => {
  class MockGuardianEventSource extends EventTarget {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;

    readonly url: string;
    readonly options: Record<string, unknown>;
    readyState = MockGuardianEventSource.OPEN;
    onopen: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent<string>) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    close = vi.fn(() => {
      this.readyState = MockGuardianEventSource.CLOSED;
    });

    constructor(url: string, options: Record<string, unknown> = {}) {
      super();
      this.url = url;
      this.options = options;
      eventSources.instances.push(this as unknown as MockGuardianEventSource);
    }

    emit(type: string, data: Record<string, unknown>): void {
      const event = new MessageEvent(type, {
        data: JSON.stringify(data),
      });
      this.dispatchEvent(event);
      if (type === "message") {
        this.onmessage?.(event);
      }
    }

    emitError(): void {
      const event = new Event("error");
      this.onerror?.(event);
    }
  }

  return { GuardianEventSource: MockGuardianEventSource };
});

function emitTaskEvent(
  source: MockGuardianEventSource,
  type: string,
  data: Record<string, unknown>
) {
  act(() => {
    source.emit(type, data);
  });
}

describe("useInferenceRequestState", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-05T00:00:00.000Z"));
    vi.clearAllMocks();
    eventSources.instances.length = 0;
  });

  afterEach(() => {
    vi.useRealTimers();
    eventSources.instances.length = 0;
  });

  const terminalEvents = [
    "task.completed",
    "task.cancelled",
    "task.failed",
    "completion.error",
  ];
  const streamEvents = ["task.progress", "task.state", ...terminalEvents];
  const request = {
    threadId: 1,
    providerId: "local",
    modelId: "local-model",
    mode: "default" as const,
  };

  it.each(terminalEvents.flatMap((type) => [[type, "thread"], [type, "task"]]))(
    "ignores current-stream terminal %s with foreign %s identity",
    (type, foreignIdentity) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const source = eventSources.instances[0];
      const before = result.current.state;

      emitTaskEvent(source, type, {
        thread_id: foreignIdentity === "thread" ? 2 : 1,
        task_id: foreignIdentity === "task" ? "foreign-task" : "current-task",
        error: "Unrelated failure",
      });

      expect(result.current.state).toEqual(before);
      expect(source.close).not.toHaveBeenCalled();
    }
  );

  it.each(streamEvents.flatMap((type) => [[type, true], [type, false]]))(
    "ignores retired stream %s with explicit identity %s after replacement",
    (type, explicitIdentity) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("old-task");
      });
      const oldSource = eventSources.instances[0];
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const source = eventSources.instances[1];
      const before = result.current.state;

      emitTaskEvent(oldSource, String(type), {
        ...(explicitIdentity ? { thread_id: 1, task_id: "old-task" } : {}),
        state: "COMPLETED",
        error: "Retired task failed",
        token: "Late output",
      });

      expect(oldSource.close).toHaveBeenCalledOnce();
      expect(result.current.state).toEqual(before);
      expect(source.close).not.toHaveBeenCalled();
    }
  );

  it("invalidates stream ownership before closing can dispatch a terminal", () => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    const source = eventSources.instances[0];
    source.close.mockImplementationOnce(() => {
      source.emit("task.completed", { thread_id: 1, task_id: "current-task" });
    });
    act(() => result.current.reset());
    expect(source.close).toHaveBeenCalledOnce();
    expect(result.current.state.phase).toBe("idle");
    expect(result.current.state.taskId).toBeNull();
  });

  it("ignores a retired stream transport error after replacement", () => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("old-task");
    });
    const oldSource = eventSources.instances[0];
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    const before = result.current.state;
    act(() => oldSource.emitError());
    expect(result.current.state).toEqual(before);
    expect(eventSources.instances[1].close).not.toHaveBeenCalled();
  });

  it("rejects the retired connection when the same task ID is reattached", () => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("same-task");
    });
    const oldSource = eventSources.instances[0];
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("same-task");
    });
    const before = result.current.state;
    emitTaskEvent(oldSource, "task.completed", { thread_id: 1, task_id: "same-task" });
    expect(result.current.state).toEqual(before);
    expect(eventSources.instances[1].close).not.toHaveBeenCalled();
  });

  it.each(["task.progress", "task.state"])(
    "does not resurrect completed inference on late %s",
    (type) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const source = eventSources.instances[0];
      emitTaskEvent(source, "task.completed", { thread_id: 1, task_id: "current-task" });
      const completed = result.current.state;
      emitTaskEvent(source, type, { state: "STREAMING", token: "Late output" });
      expect(result.current.state).toEqual(completed);
      expect(result.current.state.phase).toBe("completed");
      expect(source.close).toHaveBeenCalledOnce();
    }
  );

  it.each(terminalEvents.flatMap((type) => [[type, true], [type, false]]))(
    "accepts current stream terminal %s with explicit identity %s",
    (type, explicitIdentity) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const source = eventSources.instances[0];
      emitTaskEvent(source, String(type), {
        ...(explicitIdentity ? { thread_id: 1, task_id: "current-task" } : {}),
        error: "Current task failed",
      });
      const expectedPhase =
        type === "task.completed" ? "completed" : type === "task.cancelled" ? "cancelled" : "failed";
      expect(result.current.state.phase).toBe(expectedPhase);
      expect(result.current.state.taskId).toBeNull();
      expect(source.close).toHaveBeenCalledOnce();
    }
  );

  it.each(["invalid-json", "[]", "null", "42", ""])("ignores malformed terminal data %s instead of inventing completion", (data) => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    const source = eventSources.instances[0];
    const before = result.current.state;
    act(() => source.dispatchEvent(new MessageEvent("task.completed", { data })));
    expect(result.current.state).toEqual(before);
    expect(source.close).not.toHaveBeenCalled();
  });

  it.each(["task.cancelled", "task.state"])("reports owned cancellation identity from %s before clearing it", (type) => {
    const onTaskCancelled = vi.fn();
    const { result } = renderHook(() => useInferenceRequestState({ onTaskCancelled }));
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    emitTaskEvent(eventSources.instances[0], type, { thread_id: 1, task_id: "current-task", state: "CANCELLED" });
    expect(onTaskCancelled).toHaveBeenCalledExactlyOnceWith(1, "current-task");
    expect(result.current.state.phase).toBe("cancelled");
    emitTaskEvent(eventSources.instances[0], type, { thread_id: 1, task_id: "current-task", state: "CANCELLED" });
    expect(onTaskCancelled).toHaveBeenCalledOnce();
  });

  it("does not report cancellation from a retired stream or foreign identity", () => {
    const onTaskCancelled = vi.fn();
    const { result } = renderHook(() => useInferenceRequestState({ onTaskCancelled }));
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("old-task");
    });
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    emitTaskEvent(eventSources.instances[0], "task.cancelled", {});
    emitTaskEvent(eventSources.instances[1], "task.cancelled", { task_id: "old-task" });
    expect(onTaskCancelled).not.toHaveBeenCalled();
  });

  it.each(["task.failed", "completion.error", "task.state"])(
    "projects owned deadline %s as request failure despite terminal timing",
    (type) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const source = eventSources.instances[0];
      vi.setSystemTime(new Date("2026-04-05T00:12:01.000Z"));
      emitTaskEvent(source, type, {
        thread_id: 1, task_id: "current-task", state: "FAILED",
        failure_code: "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED",
        toolTurnState: "failed", loopStopReason: "tool_command_failed",
        error: "Accepted chat task work deadline exceeded.",
        failed_after_state: "QUEUED", provider_request_started: false,
        first_output_observed: false, completed_at: "2026-04-05T00:12:01.000Z",
      });
      expect(result.current.state.phase).toBe("failed");
      expect(result.current.state.failureCode).toBe("CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED");
      expect(result.current.state.toolLoopStopReason).toBeNull();
      expect(result.current.state.statusText).toMatch(/request.*time limit/i);
      expect(describeInferenceRequestState(result.current.state).canonicalState).toBe("failed_retryable");
      expect(describeInferenceRequestState(result.current.state).isDelayed).toBe(false);
      expect(source.close).toHaveBeenCalledOnce();
      render(<InferenceStatusBanner state={result.current.state} />);
      expect(screen.getByText("Reply failed")).toBeInTheDocument();
      expect(screen.getByText(/request.*time limit/i)).toBeInTheDocument();
      expect(screen.queryByText(/provider error|provider.*timed out|completed/i)).not.toBeInTheDocument();
      act(() => result.current.startRequest(request));
      expect(result.current.state.failureCode).toBeNull();
      expect(result.current.state.phase).toBe("sending");
    }
  );

  it.each(["task.failed", "task.cancelled"])("does not mistake %s terminal timing for success", (type) => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    emitTaskEvent(eventSources.instances[0], type, {
      thread_id: 1, task_id: "current-task", error: "Provider rejected the request",
      completed_at: "2026-04-05T00:00:01.000Z",
    });
    expect(result.current.state.phase).toBe(type === "task.failed" ? "failed" : "cancelled");
    expect(describeInferenceRequestState(result.current.state).canonicalState).toBe(
      type === "task.failed" ? "provider_error" : "cancelled"
    );
  });

  function deferCancelPost() {
    let resolve!: (value: unknown) => void;
    let reject!: (reason: Error) => void;
    const promise = new Promise((resolvePromise, rejectPromise) => {
      resolve = resolvePromise;
      reject = rejectPromise;
    });
    apiSpies.post.mockReturnValueOnce(promise);
    return { resolve, reject };
  }

  it.each(["task.failed", "completion.error", "task.state"].flatMap((type) =>
    ["tool_command_failed", "tool_command_blocked"].map((reason) => [type, reason])
  ))("preserves owned command failure from %s: %s", (type, reason) => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    const source = eventSources.instances[0];
    emitTaskEvent(source, type, {
      thread_id: 1, task_id: "current-task", state: "FAILED",
      toolTurnState: "failed", loopStopReason: reason,
      error: reason, completed_at: "2026-04-05T00:00:01.000Z",
    });
    expect(result.current.state.phase).toBe("failed");
    expect(result.current.state.toolLoopStopReason).toBe(reason);
    expect(result.current.state.statusText).toMatch(/action/i);
    expect(describeInferenceRequestState(result.current.state).canonicalState).toBe("failed");
    expect(describeInferenceRequestState(result.current.state).isDelayed).toBe(false);
    expect(source.close).toHaveBeenCalledOnce();
    act(() => {
      source.emitError();
      vi.advanceTimersByTime(60_000);
    });
    expect(result.current.state.statusText).not.toMatch(/provider|degraded/i);
    render(<InferenceStatusBanner state={result.current.state} />);
    expect(screen.getByText("Reply failed")).toBeInTheDocument();
    expect(screen.getByText(reason === "tool_command_failed"
      ? /requested action failed/i : /requested action was not authorized/i)).toBeInTheDocument();
    expect(screen.queryByText(/provider error|completed/i)).not.toBeInTheDocument();
    act(() => result.current.startRequest(request));
    expect(result.current.state.toolLoopStopReason).toBeNull();
  });

  it("rejects retired and foreign command failure events", () => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("old-task");
    });
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    const failure = { toolTurnState: "failed", loopStopReason: "tool_command_failed" };
    emitTaskEvent(eventSources.instances[0], "task.failed", failure);
    emitTaskEvent(eventSources.instances[1], "task.failed", { ...failure, task_id: "old-task" });
    emitTaskEvent(eventSources.instances[1], "task.failed", { ...failure, task_id: "current-task", thread_id: 2 });
    expect(result.current.state.taskId).toBe("current-task");
    expect(result.current.state.toolLoopStopReason).toBeNull();
    expect(result.current.state.phase).not.toBe("failed");
    expect(eventSources.instances[1].close).not.toHaveBeenCalled();
  });

  it.each(["default", "think"] as const)(
    "keeps the %s task observable when its stop POST fails",
    async (mode) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest({ ...request, mode });
        result.current.attachTask("current-task");
      });
      const source = eventSources.instances[0];
      const before = result.current.state;
      apiSpies.post.mockRejectedValueOnce(new Error("Stop request unavailable"));
      await act(async () => {
        expect(await result.current.requestCancel()).toBe(false);
      });
      expect(result.current.state.phase).toBe(before.phase);
      expect(result.current.state.taskId).toBe("current-task");
      expect(result.current.state.statusText).toBe(before.statusText);
      expect(result.current.state.errorText).toBeNull();
      expect(result.current.state.isPendingCancel).toBe(false);
      expect(result.current.state.canCancel).toBe(true);
      expect(result.current.state.detailText).toContain("stop request");
      expect(result.current.state.detailText).toContain("observ");
      expect(describeInferenceRequestState(result.current.state).canonicalState).not.toBe("provider_error");
      expect(source.close).not.toHaveBeenCalled();
      emitTaskEvent(source, "task.progress", { task_id: "current-task", token: "Still producing" });
      expect(result.current.state.phase).toBe("streaming");
      emitTaskEvent(source, "task.completed", { task_id: "current-task", thread_id: 1 });
      expect(result.current.state.phase).toBe("completed");
      expect(source.close).toHaveBeenCalledOnce();
    }
  );

  it.each(["task.completed", "task.cancelled", "task.failed"])(
    "waits for %s after the stop POST is accepted",
    async (type) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const source = eventSources.instances[0];
      apiSpies.post.mockResolvedValueOnce({ data: { ok: true, cancel_requested: true } });
      await act(async () => {
        expect(await result.current.requestCancel()).toBe(true);
      });
      expect(result.current.state.taskId).toBe("current-task");
      expect(result.current.state.phase).toBe("sending");
      expect(source.close).not.toHaveBeenCalled();
      emitTaskEvent(source, type, { thread_id: 1, task_id: "current-task", error: "Actual worker failure" });
      expect(result.current.state.phase).toBe(
        type === "task.completed" ? "completed" : type === "task.cancelled" ? "cancelled" : "failed"
      );
      expect(source.close).toHaveBeenCalledOnce();
    }
  );

  it.each(["task.completed", "task.cancelled", "task.failed"])(
    "preserves authoritative %s when the stop POST rejects later",
    async (type) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const post = deferCancelPost();
      let cancel!: Promise<boolean>;
      act(() => { cancel = result.current.requestCancel(); });
      emitTaskEvent(eventSources.instances[0], type, {
        thread_id: 1, task_id: "current-task", error: "Actual worker failure",
      });
      const terminal = result.current.state;
      await act(async () => {
        post.reject(new Error("Late stop error"));
        expect(await cancel).toBe(false);
      });
      expect(result.current.state).toEqual(terminal);
      expect(eventSources.instances[0].close).toHaveBeenCalledOnce();
    }
  );

  it.each(["current-task", "new-task"])(
    "ignores an old stop rejection after attaching replacement stream %s",
    async (replacementTaskId) => {
      const { result } = renderHook(() => useInferenceRequestState());
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask("current-task");
      });
      const post = deferCancelPost();
      let cancel!: Promise<boolean>;
      act(() => { cancel = result.current.requestCancel(); });
      act(() => {
        result.current.startRequest(request);
        result.current.attachTask(replacementTaskId);
      });
      const current = result.current.state;
      await act(async () => {
        post.reject(new Error("Retired stop error"));
        expect(await cancel).toBe(false);
      });
      expect(result.current.state).toEqual(current);
      expect(eventSources.instances[1].close).not.toHaveBeenCalled();
    }
  );

  it("ignores a stop rejection after resetting observation", async () => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    const post = deferCancelPost();
    let cancel!: Promise<boolean>;
    act(() => { cancel = result.current.requestCancel(); });
    act(() => result.current.reset());
    const idle = result.current.state;
    await act(async () => {
      post.reject(new Error("Late stop error"));
      expect(await cancel).toBe(false);
    });
    expect(result.current.state).toEqual(idle);
  });

  it("does not let an older stop failure clear a newer pending stop", async () => {
    const { result } = renderHook(() => useInferenceRequestState());
    act(() => {
      result.current.startRequest(request);
      result.current.attachTask("current-task");
    });
    const first = deferCancelPost();
    let firstCancel!: Promise<boolean>;
    act(() => { firstCancel = result.current.requestCancel(); });
    const second = deferCancelPost();
    let secondCancel!: Promise<boolean>;
    act(() => { secondCancel = result.current.requestCancel(); });
    const pending = result.current.state;
    await act(async () => {
      first.reject(new Error("Older stop error"));
      expect(await firstCancel).toBe(false);
    });
    expect(result.current.state).toEqual(pending);
    expect(result.current.state.isPendingCancel).toBe(true);
    await act(async () => {
      second.reject(new Error("Latest stop error"));
      expect(await secondCancel).toBe(false);
    });
    expect(result.current.state.phase).toBe("sending");
    expect(result.current.state.isPendingCancel).toBe(false);
    expect(eventSources.instances[0].close).not.toHaveBeenCalled();
  });

  it("attributes a delayed request with no lifecycle evidence as queued", async () => {
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    const { result } = renderHook(() => useInferenceRequestState());

    act(() => {
      result.current.startRequest({
        threadId: 1,
        providerId: "local",
        modelId: "local-model",
        mode: "default",
      });
    });

    expect(result.current.state.statusText).toBe("Queued…");

    await act(async () => {
      vi.advanceTimersByTime(INFERENCE_SLOW_PATH_MS + 1);
      await Promise.resolve();
    });

    expect(result.current.state.detailText).toContain(
      "No lifecycle evidence yet"
    );
    expect(debugSpy).toHaveBeenCalledWith(
      "[useInferenceRequestState] lifecycle attribution",
      expect.objectContaining({
        reason: "slow-threshold",
        canonicalState: "queued",
        isDelayed: true,
        delayDetailText: expect.stringContaining("No lifecycle evidence yet"),
        thresholdMs: INFERENCE_SLOW_PATH_MS,
        threadId: 1,
        taskId: null,
        providerId: "local",
        modelId: "local-model",
        mode: "default",
      })
    );
  });

  it("attributes lifecycle-started requests as awaiting_model before the first token", async () => {
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    const { result } = renderHook(() => useInferenceRequestState());

    act(() => {
      result.current.startRequest({
        threadId: 1,
        providerId: "local",
        modelId: "local-model",
        mode: "think",
      });
      result.current.attachTask("task-1");
    });

    expect(result.current.state.taskId).toBe("task-1");
    expect(result.current.state.phase).toBe("thinking");

    const source = eventSources.instances[0];
    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_MODEL",
      awaiting_model_at: "2026-04-05T00:00:01.000Z",
    });

    await act(async () => {
      vi.advanceTimersByTime(INFERENCE_SLOW_PATH_MS + 1);
      await Promise.resolve();
    });

    expect(result.current.state.statusText).toBe("Warming model…");
    expect(result.current.state.detailText).toContain("warming up");
    expect(
      describeInferenceRequestState(result.current.state).canonicalState
    ).toBe("awaiting_model");
    expect(debugSpy).toHaveBeenCalledWith(
      "[useInferenceRequestState] lifecycle attribution",
      expect.objectContaining({
        reason: "slow-threshold",
        canonicalState: "awaiting_model",
        isDelayed: true,
        delayDetailText: expect.stringContaining("warming up"),
        threadId: 1,
        taskId: "task-1",
      })
    );
  });

  it("keeps a delayed streaming request in progress instead of failing it", async () => {
    const { result } = renderHook(() => useInferenceRequestState());

    act(() => {
      result.current.startRequest({
        threadId: 1,
        providerId: "local",
        modelId: "local-model",
        mode: "think",
      });
      result.current.attachTask("task-1");
    });

    const source = eventSources.instances[0];

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_FIRST_TOKEN",
      awaiting_first_token_at: "2026-04-05T00:00:02.000Z",
    });

    await act(async () => {
      vi.advanceTimersByTime(INFERENCE_SLOW_PATH_MS + 1);
      await Promise.resolve();
    });

    expect(result.current.state.statusText).toBe("Waiting for first token…");
    expect(result.current.state.detailText).toContain("first token");

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "STREAMING",
      first_token_at: "2026-04-05T00:00:03.000Z",
      first_output_at: "2026-04-05T00:00:03.000Z",
    });

    await act(async () => {
      vi.advanceTimersByTime(1);
      await Promise.resolve();
    });

    expect(result.current.state.phase).toBe("streaming");
    expect(result.current.state.errorText).toBeNull();
    expect(result.current.state.detailText).toContain("streaming");
    expect(
      describeInferenceRequestState(result.current.state).canonicalState
    ).toBe("streaming");
  });

  it("preserves synthesized lifecycle timestamps across repeated events", async () => {
    const { result } = renderHook(() => useInferenceRequestState());

    act(() => {
      result.current.startRequest({
        threadId: 1,
        providerId: "local",
        modelId: "local-model",
        mode: "think",
      });
      result.current.attachTask("task-1");
    });

    const source = eventSources.instances[0];
    const lifecycleFields = [
      ["QUEUED", "queuedAt"],
      ["AWAITING_MODEL", "awaitingModelAt"],
      ["AWAITING_FIRST_TOKEN", "awaitingFirstTokenAt"],
      ["STREAMING", "firstOutputAt"],
    ] as const;

    for (const [state, field] of lifecycleFields) {
      emitTaskEvent(source, "task.state", {
        thread_id: 1,
        task_id: "task-1",
        state,
      });
      const firstTimestamp = result.current.state[field];
      expect(firstTimestamp).toEqual(expect.any(String));

      await act(async () => {
        vi.advanceTimersByTime(1_000);
        await Promise.resolve();
      });

      emitTaskEvent(source, "task.state", {
        thread_id: 1,
        task_id: "task-1",
        state,
      });
      expect(result.current.state[field]).toBe(firstTimestamp);
    }
  });

  it("marks transport errors as degraded instead of frozen", async () => {
    const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    const { result } = renderHook(() => useInferenceRequestState());

    act(() => {
      result.current.startRequest({
        threadId: 1,
        providerId: "local",
        modelId: "local-model",
        mode: "default",
      });
      result.current.attachTask("task-1");
    });

    const source = eventSources.instances[0];
    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_MODEL",
    });

    act(() => {
      source.emitError();
    });

    expect(result.current.state.phase).toBe("sending");
    expect(result.current.state.errorText).toBeNull();
    expect(result.current.state.statusText).toBe("Provider degraded…");
    expect(result.current.state.detailText).toContain("degraded");
    expect(debugSpy).toHaveBeenCalledWith(
      "[useInferenceRequestState] lifecycle attribution",
      expect.objectContaining({
        reason: "stream.onerror",
        canonicalState: "awaiting_model",
        threadId: 1,
        taskId: "task-1",
      })
    );
  });
});
