import { act, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import InferenceStatusBanner from "@/features/chat/components/InferenceStatusBanner";
import { useInferenceRequestState } from "@/features/chat/hooks/useInferenceRequestState";
import { createIdleInferenceRequestState } from "@/types/inference";

const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

const taskEventSources = vi.hoisted(() => ({
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
      taskEventSources.instances.push(
        this as unknown as MockGuardianEventSource
      );
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

function LifecycleLatencyHarness({
  activeThreadId,
  requestThreadId,
  taskId,
}: {
  activeThreadId: number;
  requestThreadId: number;
  taskId: string;
}) {
  const { state, startRequest, attachTask } = useInferenceRequestState();

  useEffect(() => {
    startRequest({
      threadId: requestThreadId,
      providerId: "local",
      modelId: "local-model",
      mode: "think",
    });
    attachTask(taskId);
  }, [attachTask, requestThreadId, startRequest, taskId]);

  const visibleState =
    state.threadId === activeThreadId
      ? state
      : createIdleInferenceRequestState();

  return <InferenceStatusBanner state={visibleState} />;
}

describe("GuardianChat lifecycle latency", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    taskEventSources.instances.length = 0;
  });

  afterEach(() => {
    taskEventSources.instances.length = 0;
  });

  it("renders latency chips as timings arrive and completes with total time", async () => {
    render(
      <LifecycleLatencyHarness
        activeThreadId={1}
        requestThreadId={1}
        taskId="task-1"
      />
    );

    await waitFor(() => {
      expect(taskEventSources.instances).toHaveLength(1);
    });

    const source = taskEventSources.instances[0];

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "QUEUED",
      queued_at: "2026-04-02T00:00:00.000Z",
    });
    expect(screen.getByText("Queued…")).toBeInTheDocument();
    expect(screen.queryByTestId("inference-latency-readout")).not.toBeInTheDocument();

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_MODEL",
      awaiting_model_at: "2026-04-02T00:00:01.000Z",
    });
    await screen.findByText("Queued: 1.0s");

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_FIRST_TOKEN",
      awaiting_first_token_at: "2026-04-02T00:00:03.000Z",
    });
    await screen.findByText("Warmup: 2.0s");

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "STREAMING",
      first_token_at: "2026-04-02T00:00:04.500Z",
      first_output_at: "2026-04-02T00:00:04.500Z",
    });
    await screen.findByText("First token: 1.5s");

    emitTaskEvent(source, "task.completed", {
      thread_id: 1,
      task_id: "task-1",
      trace: {
        completed_at: "2026-04-02T00:00:06.000Z",
      },
    });

    await screen.findByText("Completed");
    expect(screen.getByText("Queued: 1.0s")).toBeInTheDocument();
    expect(screen.getByText("Warmup: 2.0s")).toBeInTheDocument();
    expect(screen.getByText("First token: 1.5s")).toBeInTheDocument();
    expect(screen.getByText("Total: 6.0s")).toBeInTheDocument();
  });

  it("shows first output rather than first token when only the terminal body knows the timing", async () => {
    render(
      <LifecycleLatencyHarness
        activeThreadId={1}
        requestThreadId={1}
        taskId="task-1"
      />
    );

    await waitFor(() => {
      expect(taskEventSources.instances).toHaveLength(1);
    });

    const source = taskEventSources.instances[0];

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "QUEUED",
      queued_at: "2026-04-02T00:00:00.000Z",
    });
    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_MODEL",
      awaiting_model_at: "2026-04-02T00:00:01.000Z",
    });
    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_FIRST_TOKEN",
      awaiting_first_token_at: "2026-04-02T00:00:02.000Z",
    });

    emitTaskEvent(source, "task.completed", {
      thread_id: 1,
      task_id: "task-1",
      trace: {
        first_output_at: "2026-04-02T00:00:04.000Z",
        completed_at: "2026-04-02T00:00:05.000Z",
      },
    });

    await screen.findByText("First output: 2.0s");
    expect(screen.queryByText("First token: 2.0s")).not.toBeInTheDocument();
    expect(screen.getByText("Total: 5.0s")).toBeInTheDocument();
  });

  it("does not show stale latency when the active thread changes or a new task starts", async () => {
    const { rerender } = render(
      <LifecycleLatencyHarness
        activeThreadId={1}
        requestThreadId={1}
        taskId="task-1"
      />
    );

    await waitFor(() => {
      expect(taskEventSources.instances).toHaveLength(1);
    });

    const firstSource = taskEventSources.instances[0];

    emitTaskEvent(firstSource, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "QUEUED",
      queued_at: "2026-04-02T00:00:00.000Z",
    });
    emitTaskEvent(firstSource, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_MODEL",
      awaiting_model_at: "2026-04-02T00:00:01.000Z",
    });
    await screen.findByText("Queued: 1.0s");

    rerender(
      <LifecycleLatencyHarness
        activeThreadId={2}
        requestThreadId={1}
        taskId="task-1"
      />
    );
    expect(screen.queryByTestId("inference-latency-readout")).not.toBeInTheDocument();

    rerender(
      <LifecycleLatencyHarness
        activeThreadId={1}
        requestThreadId={1}
        taskId="task-2"
      />
    );

    await waitFor(() => {
      expect(taskEventSources.instances).toHaveLength(2);
    });

    const secondSource = taskEventSources.instances[1];
    expect(screen.queryByTestId("inference-latency-readout")).not.toBeInTheDocument();

    emitTaskEvent(firstSource, "task.completed", {
      thread_id: 1,
      task_id: "task-1",
      trace: {
        completed_at: "2026-04-02T00:00:03.000Z",
      },
    });
    expect(screen.queryByText("Total: 3.0s")).not.toBeInTheDocument();

    emitTaskEvent(secondSource, "task.state", {
      thread_id: 1,
      task_id: "task-2",
      state: "QUEUED",
      queued_at: "2026-04-02T00:01:00.000Z",
    });
    emitTaskEvent(secondSource, "task.state", {
      thread_id: 1,
      task_id: "task-2",
      state: "AWAITING_MODEL",
      awaiting_model_at: "2026-04-02T00:01:01.000Z",
    });
    await screen.findByText("Queued: 1.0s");
  });

  it("keeps the lifecycle banner free of latency when no timing data has been stamped", async () => {
    render(
      <LifecycleLatencyHarness
        activeThreadId={1}
        requestThreadId={1}
        taskId="task-1"
      />
    );

    await waitFor(() => {
      expect(taskEventSources.instances).toHaveLength(1);
    });

    expect(screen.getByText("Queued…")).toBeInTheDocument();
    expect(screen.queryByTestId("inference-latency-readout")).not.toBeInTheDocument();
  });
});
