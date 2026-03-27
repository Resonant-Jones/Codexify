import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type MockSource = {
  addEventListener: ReturnType<typeof vi.fn>;
  emitError: () => void;
  emitEvent: (type: string, data: unknown, lastEventId?: string) => void;
  close: ReturnType<typeof vi.fn>;
};

const mockState = vi.hoisted(() => ({
  createdSources: [] as MockSource[],
}));

vi.mock("@/lib/guardianEventSource", () => {
  type SourceListener = (event: Event) => void;

  class MockGuardianEventSource {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;

    readonly url: string;
    readonly options: Record<string, unknown>;
    readyState = MockGuardianEventSource.CONNECTING;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    private listeners = new Map<string, Set<SourceListener>>();

    addEventListener = vi.fn((type: string, listener: SourceListener) => {
      const bucket = this.listeners.get(type) ?? new Set<SourceListener>();
      bucket.add(listener);
      this.listeners.set(type, bucket);
    });

    removeEventListener = vi.fn((type: string, listener: SourceListener) => {
      const bucket = this.listeners.get(type);
      if (!bucket) return;
      bucket.delete(listener);
      if (bucket.size === 0) {
        this.listeners.delete(type);
      }
    });

    close = vi.fn(() => {
      this.readyState = MockGuardianEventSource.CLOSED;
    });

    constructor(url: string, options: Record<string, unknown>) {
      this.url = url;
      this.options = options;
      mockState.createdSources.push(this as unknown as MockSource);
    }

    emitError(): void {
      this.readyState = MockGuardianEventSource.CLOSED;
      const event = new Event("error");
      this.onerror?.(event);
      this.emit("error", event);
    }

    emitEvent(type: string, data: unknown, lastEventId?: string): void {
      const event = new MessageEvent(type, {
        data: typeof data === "string" ? data : JSON.stringify(data),
        lastEventId: lastEventId ?? "",
      });
      if (type === "message") {
        this.onmessage?.(event);
      }
      this.emit(type, event);
    }

    private emit(type: string, event: Event): void {
      const bucket = this.listeners.get(type);
      if (!bucket) return;
      [...bucket].forEach((listener) => listener(event));
    }
  }

  return { GuardianEventSource: MockGuardianEventSource };
});

import { useLiveEvents } from "@/hooks/useLiveEvents";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
} from "@/lib/authState";
import {
  __resetLiveEventsHubForTests,
  getLiveEventsHubStatus,
} from "@/lib/liveEventsHub";

describe("live events singleton hub", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockState.createdSources.length = 0;
    __resetAuthStateForTests();
    __resetLiveEventsHubForTests();
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "token-1",
    });
    vi.spyOn(Math, "random").mockReturnValue(0.5);
    vi.spyOn(console, "info").mockImplementation(() => {});
    vi.spyOn(console, "debug").mockImplementation(() => {});
  });

  afterEach(() => {
    __resetLiveEventsHubForTests();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("uses one EventSource instance across multiple hook consumers", async () => {
    const hookA = renderHook(() => useLiveEvents({ passive: true }));
    const hookB = renderHook(() => useLiveEvents({ passive: true }));
    const hookC = renderHook(() => useLiveEvents({ passive: true }));

    await waitFor(() => {
      expect(mockState.createdSources).toHaveLength(1);
    });

    hookA.unmount();
    hookB.unmount();
    hookC.unmount();
  });

  it("reconnects once after an error using backoff scheduling", async () => {
    const hook = renderHook(() => useLiveEvents({ passive: true }));

    await waitFor(() => {
      expect(mockState.createdSources).toHaveLength(1);
    });

    act(() => {
      mockState.createdSources[0].emitError();
    });

    expect(getLiveEventsHubStatus().connectAttempt).toBe(1);
    expect(getLiveEventsHubStatus().retryMs).toBe(1000);

    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(mockState.createdSources).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(1);
    });

    await waitFor(() => {
      expect(mockState.createdSources).toHaveLength(2);
    });

    hook.unmount();
  });

  it("dedupes replayed events by SSE id after reconnect", async () => {
    const { result, unmount } = renderHook(() => useLiveEvents({ passive: true }));

    await waitFor(() => {
      expect(mockState.createdSources).toHaveLength(1);
    });

    const listener = vi.fn();
    const unsubscribe = result.current.subscribe("message.created", listener);

    act(() => {
      mockState.createdSources[0].emitEvent("message.created", { value: 1 }, "evt-1");
    });
    expect(listener).toHaveBeenCalledTimes(1);

    act(() => {
      mockState.createdSources[0].emitError();
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockState.createdSources).toHaveLength(2);
    });

    act(() => {
      mockState.createdSources[1].emitEvent("message.created", { value: 1 }, "evt-1");
    });
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
    unmount();
  });

  it("binds task lifecycle SSE event types needed by the chat store bridge", async () => {
    const { unmount } = renderHook(() => useLiveEvents({ passive: true }));

    await waitFor(() => {
      expect(mockState.createdSources).toHaveLength(1);
    });

    const registeredTypes = mockState.createdSources[0].addEventListener.mock.calls.map(
      ([type]) => type
    );

    expect(registeredTypes).toEqual(
      expect.arrayContaining(["task.created", "task.updated", "task.progress"])
    );

    unmount();
  });

  it("activates pressure fuse under burst load and flushes buffered events", async () => {
    const priorRaf = window.requestAnimationFrame;
    const priorCancelRaf = window.cancelAnimationFrame;
    (window as any).requestAnimationFrame = undefined;
    (window as any).cancelAnimationFrame = undefined;

    const infoSpy = vi.spyOn(console, "info").mockImplementation(() => {});
    const { result, unmount } = renderHook(() => useLiveEvents({ passive: true }));
    await waitFor(() => {
      expect(mockState.createdSources).toHaveLength(1);
    });

    const listener = vi.fn();
    const unsubscribe = result.current.subscribe("message.created", listener);

    act(() => {
      for (let i = 0; i < 120; i += 1) {
        mockState.createdSources[0].emitEvent("message.created", { index: i }, `burst-${i}`);
      }
    });

    expect(listener.mock.calls.length).toBeLessThan(120);
    expect(
      infoSpy.mock.calls.some((call) =>
        String(call[0]).includes("event pressure fuse enabled")
      )
    ).toBe(true);

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(listener).toHaveBeenCalledTimes(120);

    act(() => {
      vi.advanceTimersByTime(2100);
      mockState.createdSources[0].emitEvent("message.created", { index: 121 }, "burst-121");
    });
    expect(
      infoSpy.mock.calls.some((call) =>
        String(call[0]).includes("event pressure fuse disabled")
      )
    ).toBe(true);

    unsubscribe();
    unmount();
    (window as any).requestAnimationFrame = priorRaf;
    (window as any).cancelAnimationFrame = priorCancelRaf;
  });
});
