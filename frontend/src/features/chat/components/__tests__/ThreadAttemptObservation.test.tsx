import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";

import { ThreadAttemptObservation } from "../ThreadAttemptObservation";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));
const get = vi.mocked(api.get);
const refresh = vi.fn().mockResolvedValue(undefined);
const props = {
  threadId: 11,
  enabled: true,
  identityEpoch: "account-session-a",
  currentTaskId: null,
  onTerminalObserved: refresh,
};

function receipt(
  state: "unknown" | "nonterminal" | "terminal" = "unknown",
  event_type: string | null = null,
) {
  return {
    task_id: "task-a",
    request_id: "request-a",
    thread_id: 11,
    turn_id: "turn-a",
    completed_message_id: event_type === "task.completed" ? 73 : null,
    accepted_at: null,
    state,
    event_type,
  };
}

function page(rows: unknown[], has_more = false) {
  return { data: { ok: true, thread_id: 11, tasks: rows, has_more } };
}

const settle = async () => {
  await act(async () => {
    await Promise.resolve();
  });
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

describe("thread attempt observation", () => {
  it("retains unknown outcome without replay or invented execution phase", async () => {
    get.mockResolvedValue(page([receipt("unknown")]));
    render(<ThreadAttemptObservation {...props} />);
    await settle();

    expect(screen.getByText("Response outcome unconfirmed")).toBeInTheDocument();
    expect(screen.getByRole("status").textContent).not.toMatch(
      /generating|working|failed|stopped/i,
    );
    expect(api.post).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
    expect(get.mock.calls[0][0]).toBe("/chat/threads/11/tasks");
  });

  it("refreshes canonical messages when a durable completion is observed", async () => {
    get.mockResolvedValue(page([receipt("terminal", "task.completed")]));
    const { container } = render(<ThreadAttemptObservation {...props} />);
    await settle();

    expect(refresh).toHaveBeenCalledOnce();
    expect(refresh).toHaveBeenCalledWith(11, "attempt-observation-terminal");
    expect(container).toBeEmptyDOMElement();
    expect(api.post).not.toHaveBeenCalled();
  });

  it.each([
    ["task.failed", "response task failed"],
    ["task.cancelled", "response task stopped"],
  ])("shows the recorded %s outcome", async (eventType, label) => {
    get.mockResolvedValue(page([receipt("terminal", eventType)]));
    render(<ThreadAttemptObservation {...props} />);
    await settle();

    expect(screen.getByText(new RegExp(label))).toBeInTheDocument();
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("does not supersede the locally tracked task", async () => {
    get.mockResolvedValue(page([receipt("nonterminal")]));
    const { container } = render(
      <ThreadAttemptObservation {...props} currentTaskId="task-a" />,
    );
    await settle();

    expect(container).toBeEmptyDOMElement();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("does not read or retain state after authorization ends", async () => {
    get.mockResolvedValue(page([receipt("nonterminal")]));
    const { rerender, container } = render(
      <ThreadAttemptObservation {...props} />,
    );
    await settle();
    rerender(<ThreadAttemptObservation {...props} enabled={false} />);
    await settle();

    expect(container).toBeEmptyDOMElement();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000);
    });
    expect(get).toHaveBeenCalledOnce();
    expect(get.mock.calls[0][1]?.signal?.aborted).toBe(true);
  });

  it("discards a late read after thread or credential changes", async () => {
    let resolve: (value: unknown) => void = () => {};
    get.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    get.mockResolvedValueOnce({
      data: { ok: true, thread_id: 12, tasks: [], has_more: false },
    });
    const { rerender } = render(<ThreadAttemptObservation {...props} />);
    rerender(
      <ThreadAttemptObservation
        {...props}
        threadId={12}
        identityEpoch="account-session-b"
      />,
    );
    await settle();
    await act(async () => {
      resolve(page([receipt("terminal", "task.completed")]) as never);
    });

    expect(screen.queryByText("Response outcome unconfirmed")).not.toBeInTheDocument();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("reports read failure as observation failure and keeps checking", async () => {
    get.mockRejectedValueOnce(new Error("transport missing"));
    render(<ThreadAttemptObservation {...props} />);
    await settle();

    expect(screen.getByText(/Response observation is unavailable/)).toBeInTheDocument();
    expect(screen.getByRole("status").textContent).not.toMatch(/failed|stopped/i);
    expect(api.post).not.toHaveBeenCalled();
  });

  it("makes the bounded history window explicit", async () => {
    get.mockResolvedValue(page([], true));
    render(<ThreadAttemptObservation {...props} />);
    await settle();
    expect(screen.getByText(/newest 100 attempts/)).toBeInTheDocument();
  });
});

const orphanReceipt = () => ({ ...receipt("terminal", "task.failed"),
  reason: "durable_terminal_outcome_recorded", failure_code: "CHAT_ACCEPTED_TASK_ORPHANED" });

describe("durable current attempt recovery", () => {
  it("keeps polling the active task and projects its durable orphan without resending", async () => {
    get.mockResolvedValueOnce(page([receipt("unknown")])).mockResolvedValueOnce(page([orphanReceipt()]));
    const project = vi.fn().mockResolvedValue(true);
    render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    expect(project).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(get).toHaveBeenCalledTimes(2);
    expect(refresh).toHaveBeenCalledWith(11, "attempt-observation-current-terminal");
    expect(project).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
      task_id: "task-a", request_id: "request-a", turn_id: "turn-a", thread_id: 11,
      failure_code: "CHAT_ACCEPTED_TASK_ORPHANED", completed_message_id: null,
    }));
    expect(api.post).not.toHaveBeenCalled();
  });

  it("keeps a missing current task within bounded-page observation", async () => {
    get.mockResolvedValue(page([], true));
    render(<ThreadAttemptObservation {...props} currentTaskId="outside-page" />);
    await settle();
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(get).toHaveBeenCalledTimes(4);
    expect(get.mock.calls.map((call) => call[1]?.params?.offset)).toEqual([0, 100, 0, 100]);
    expect(api.post).not.toHaveBeenCalled();
  });

  it("never substitutes a Redis-only terminal event for durable current truth", async () => {
    get.mockResolvedValue(page([{ ...orphanReceipt(), reason: "terminal_event_observed" }]));
    const project = vi.fn();
    render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(project).not.toHaveBeenCalled();
    expect(get).toHaveBeenCalledTimes(2);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("labels a historical durable orphan separately from provider failure", async () => {
    get.mockResolvedValue(page([orphanReceipt()]));
    render(<ThreadAttemptObservation {...props} />);
    await settle();
    expect(screen.getByRole("status").textContent).toMatch(/closed.*recovery deadline/);
    expect(screen.getByRole("status").textContent).not.toMatch(/provider|task failed|died|executed|generating/);
  });

  it("lets a durable assistant link win over stale orphan detail", async () => {
    get.mockResolvedValue(page([{ ...orphanReceipt(), completed_message_id: 74 }]));
    const project = vi.fn().mockResolvedValue(true);
    render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    expect(project).toHaveBeenCalledWith(expect.objectContaining({
      event_type: "task.completed", failure_code: null, completed_message_id: 74,
    }));
  });

  it("does not project after authorization changes during canonical refresh", async () => {
    let finish = () => {};
    refresh.mockImplementationOnce(() => new Promise<void>((done) => { finish = done; }));
    get.mockResolvedValue(page([orphanReceipt()]));
    const project = vi.fn();
    const { rerender } = render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    rerender(<ThreadAttemptObservation {...props} enabled={false} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await act(async () => { finish(); });
    expect(project).not.toHaveBeenCalled();
  });

  it("discards a stale current receipt when a new task starts during canonical refresh", async () => {
    let finish = () => {};
    refresh.mockImplementationOnce(() => new Promise<void>((done) => { finish = done; }));
    get.mockResolvedValueOnce(page([orphanReceipt()])).mockResolvedValue(page([]));
    const project = vi.fn();
    const { rerender } = render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    rerender(<ThreadAttemptObservation {...props} currentTaskId="task-b" onCurrentTerminalObserved={project} />);
    await act(async () => { finish(); });
    expect(project).not.toHaveBeenCalled();
    expect(api.post).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(get).toHaveBeenCalledTimes(3);
    expect(project).not.toHaveBeenCalled();
  });

  it("retains observation uncertainty after canonical refresh fails", async () => {
    get.mockResolvedValue(page([orphanReceipt()]));
    refresh.mockRejectedValueOnce(new Error("canonical read unavailable"));
    const project = vi.fn();
    render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    expect(project).not.toHaveBeenCalled();
    expect(screen.getByText(/observation is unavailable/)).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });
});


describe("active task history pagination", () => {
  const newerPage = (offset = 0) => page(Array.from({ length: 100 }, (_, index) => ({
    ...receipt("terminal", "task.completed"), task_id: `newer-${offset + index}`,
  })), true);

  it("projects a durable active task beyond the newest receipt page", async () => {
    get.mockResolvedValueOnce(newerPage()).mockResolvedValueOnce(page([orphanReceipt()]));
    const project = vi.fn().mockResolvedValue(true);
    render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    expect(get.mock.calls.map((call) => call[1]?.params?.offset)).toEqual([0, 100]);
    expect(project).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ task_id: "task-a" }));
    expect(api.post).not.toHaveBeenCalled();
  });

  it("advances a finite history sweep across polls instead of restarting at the first page", async () => {
    get.mockImplementation(async (_url, options) => {
      const offset = Number(options?.params?.offset ?? 0);
      return offset === 500 ? page([orphanReceipt()]) : newerPage(offset);
    });
    const project = vi.fn().mockResolvedValue(true);
    render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    expect(get.mock.calls.map((call) => call[1]?.params?.offset)).toEqual([0, 100, 200, 300]);
    expect(project).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(get.mock.calls.map((call) => call[1]?.params?.offset)).toEqual([0, 100, 200, 300, 0, 400, 500]);
    expect(project).toHaveBeenCalledOnce();
    expect(api.post).not.toHaveBeenCalled();
  });

  it("discards an older-page response after authorization ends", async () => {
    let finish: (value: unknown) => void = () => {};
    get.mockResolvedValueOnce(newerPage()).mockImplementationOnce(() => new Promise((done) => { finish = done; }));
    const project = vi.fn();
    const { rerender } = render(<ThreadAttemptObservation {...props} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await settle();
    rerender(<ThreadAttemptObservation {...props} enabled={false} currentTaskId="task-a" onCurrentTerminalObserved={project} />);
    await act(async () => { finish(page([orphanReceipt()])); });
    expect(project).not.toHaveBeenCalled();
    expect(get.mock.calls[1][1]?.signal?.aborted).toBe(true);
  });
});
