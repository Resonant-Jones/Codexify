import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchAgentRuns,
  type AgentRunResponse,
} from "@/features/chat/api/actionCenter";
import {
  __resetAgentRunsStoreForTests,
  applyAgentRunEvent,
  useAgentRuns,
} from "@/features/chat/hooks/useAgentRuns";

vi.mock("@/features/chat/api/actionCenter", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/chat/api/actionCenter")
  >("@/features/chat/api/actionCenter");
  return {
    ...actual,
    fetchAgentRuns: vi.fn(),
  };
});

const fetchAgentRunsMock = vi.mocked(fetchAgentRuns);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useAgentRuns", () => {
  beforeEach(() => {
    __resetAgentRunsStoreForTests();
    vi.clearAllMocks();
    fetchAgentRunsMock.mockResolvedValue([]);
  });

  it("skips fallback fetch when live events already hydrated the thread store", async () => {
    act(() => {
      applyAgentRunEvent("701", {
        thread_id: 701,
        run_id: "run_live_1",
        runtime_target: "terminal",
        status: "running",
      });
    });

    const { result } = renderHook(() => useAgentRuns(701));

    await waitFor(() => {
      expect(result.current.data).toHaveLength(1);
    });

    expect(fetchAgentRunsMock).not.toHaveBeenCalled();
  });

  it("merges agent task events and ignores non-agent task traffic", async () => {
    const { result } = renderHook(() => useAgentRuns(702));

    await waitFor(() => {
      expect(fetchAgentRunsMock).toHaveBeenCalledWith(702);
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    act(() => {
      applyAgentRunEvent("702", {
        event_type: "task.created",
        run_id: "run_live_2",
        runtime_target: "container",
        thread_id: 702,
      });
    });

    await waitFor(() => {
      expect(result.current.data).toHaveLength(1);
    });

    expect(result.current.data[0]).toMatchObject({
      run_id: "run_live_2",
      runtime_target: "container",
      status: "running",
      thread_id: 702,
    });

    act(() => {
      applyAgentRunEvent("702", {
        event_type: "task.completed",
        run_id: "f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0",
        thread_id: 702,
      });
    });

    expect(result.current.data).toHaveLength(1);

    act(() => {
      applyAgentRunEvent("702", {
        event_type: "task.completed",
        run_id: "run_live_2",
        thread_id: 702,
      });
    });

    await waitFor(() => {
      expect(result.current.data[0]?.status).toBe("completed");
    });
  });

  it("preserves live event updates when the fallback fetch resolves later", async () => {
    const pending = deferred<AgentRunResponse[]>();
    fetchAgentRunsMock.mockReturnValueOnce(pending.promise);

    const { result } = renderHook(() => useAgentRuns(703));

    await waitFor(() => {
      expect(result.current.loading).toBe(true);
    });

    act(() => {
      applyAgentRunEvent("703", {
        event_type: "task.created",
        run_id: "run_live_3",
        runtime_target: "terminal",
        thread_id: 703,
      });
    });

    await waitFor(() => {
      expect(result.current.data[0]?.run_id).toBe("run_live_3");
    });

    await act(async () => {
      pending.resolve([]);
      await Promise.resolve();
    });

    expect(result.current.data[0]).toMatchObject({
      run_id: "run_live_3",
      status: "running",
      thread_id: 703,
    });
  });
});
