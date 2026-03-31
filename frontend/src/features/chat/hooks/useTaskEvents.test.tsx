import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  buildAuthenticatedFetchInit: (init: RequestInit) => init,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveApiUrl: (path: string) => path,
}));

import { useTaskEvents } from "./useTaskEvents";

function createResponse(status: number): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    body: null,
  } as Response;
}

async function flushPromises() {
  await Promise.resolve();
  await vi.advanceTimersByTimeAsync(0);
}

describe("useTaskEvents", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(console, "warn").mockImplementation(() => {});
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it.each([401, 403])(
    "stops reconnecting after a terminal auth failure (%i)",
    async (status) => {
      const fetchMock = vi
        .mocked(global.fetch)
        .mockResolvedValue(createResponse(status));

      const { unmount } = renderHook(() =>
        useTaskEvents("task-auth", vi.fn())
      );

      await act(async () => {
        await flushPromises();
      });

      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(console.warn).toHaveBeenCalledWith(
        `[task-events] stream unauthorized (${status}); stopping reconnect`
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(10_000);
      });

      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(vi.getTimerCount()).toBe(0);

      unmount();
    }
  );

  it("retries transient failures with backoff", async () => {
    const fetchMock = vi
      .mocked(global.fetch)
      .mockResolvedValue(createResponse(500));

    const { unmount } = renderHook(() => useTaskEvents("task-retry", vi.fn()));

    await act(async () => {
      await flushPromises();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(console.warn).toHaveBeenCalledWith(
      "[task-events] stream disconnected",
      expect.objectContaining({
        message: "Task event stream failed with status 500",
      })
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(499);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
      await flushPromises();
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);

    unmount();
  });

  it("clears a scheduled retry on cleanup", async () => {
    const fetchMock = vi
      .mocked(global.fetch)
      .mockResolvedValue(createResponse(500));

    const { unmount } = renderHook(() => useTaskEvents("task-cleanup", vi.fn()));

    await act(async () => {
      await flushPromises();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(1);

    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
      await flushPromises();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });
});
