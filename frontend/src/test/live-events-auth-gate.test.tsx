import { renderHook, waitFor, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
} from "@/lib/authState";

type MockSource = {
  url: string;
  options: Record<string, unknown>;
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
};

const createdSources: MockSource[] = [];

vi.mock("@/lib/guardianEventSource", () => {
  class MockGuardianEventSource {
    url: string;
    options: Record<string, unknown>;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    addEventListener = vi.fn();
    removeEventListener = vi.fn();
    close = vi.fn();

    constructor(url: string, options: Record<string, unknown>) {
      this.url = url;
      this.options = options;
      createdSources.push(this as unknown as MockSource);
    }
  }

  return { GuardianEventSource: MockGuardianEventSource };
});

describe("useLiveEvents auth gating", () => {
  beforeEach(() => {
    createdSources.length = 0;
    __resetAuthStateForTests();
    vi.spyOn(console, "debug").mockImplementation(() => {});
    vi.spyOn(console, "info").mockImplementation(() => {});
  });

  it("does not connect while auth is unresolved or unauthenticated", () => {
    __setAuthStateForTests({ status: "unknown", ready: false });
    const { unmount } = renderHook(() => useLiveEvents({ passive: true }));
    expect(createdSources).toHaveLength(0);
    unmount();

    __setAuthStateForTests({ status: "unauthenticated", ready: true });
    renderHook(() => useLiveEvents({ passive: true }));
    expect(createdSources).toHaveLength(0);
  });

  it("connects when authenticated and closes on unauthenticated transition", async () => {
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "token-1",
    });
    renderHook(() => useLiveEvents({ passive: true }));

    await waitFor(() => {
      expect(createdSources).toHaveLength(1);
    });

    const source = createdSources[0];
    act(() => {
      __setAuthStateForTests({ status: "unauthenticated", ready: true });
    });

    await waitFor(() => {
      expect(source.close).toHaveBeenCalledTimes(1);
    });
  });
});
