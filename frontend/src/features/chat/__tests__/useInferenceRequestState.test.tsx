import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
