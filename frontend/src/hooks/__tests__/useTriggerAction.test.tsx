import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useTriggerAction } from "@/hooks/useTriggerAction";

const toolsSpies = vi.hoisted(() => ({
  execute: vi.fn(),
  job: vi.fn(),
}));

vi.mock("@/dcw-services/gc", () => ({
  Tools: toolsSpies,
}));

describe("useTriggerAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("resolves immediately when the command bus response is already terminal", async () => {
    toolsSpies.execute.mockResolvedValue({
      jobId: "run-1",
      state: "completed",
      result: { ok: true },
    });

    const { result } = renderHook(() => useTriggerAction());

    await expect(
      result.current.trigger("sample.command", { topic: "alpha" })
    ).resolves.toEqual({
      state: "completed",
      result: { ok: true },
    });
    expect(toolsSpies.job).not.toHaveBeenCalled();
  });

  it("keeps polling until a cached trigger job reaches a terminal state", async () => {
    vi.useFakeTimers();
    toolsSpies.execute.mockResolvedValue({
      jobId: "run-2",
      state: "running",
    });
    toolsSpies.job
      .mockResolvedValueOnce({ state: "running", result: null })
      .mockResolvedValueOnce({ state: "completed", result: { ok: true } });

    const { result } = renderHook(() => useTriggerAction());
    const promise = result.current.trigger("sample.command", {
      topic: "beta",
    });

    await act(async () => {
      vi.advanceTimersByTime(1500);
      await Promise.resolve();
    });

    await expect(promise).resolves.toEqual({
      state: "completed",
      result: { ok: true },
    });
    expect(toolsSpies.job).toHaveBeenCalledTimes(2);
  });
});
