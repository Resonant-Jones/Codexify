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
