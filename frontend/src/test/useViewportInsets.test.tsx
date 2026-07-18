import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useViewportInsets } from "@/hooks/useViewportInsets";

describe("useViewportInsets", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("resyncs after the iOS focus transition finishes without a final viewport event", () => {
    vi.useFakeTimers();

    const originalInnerHeight = Object.getOwnPropertyDescriptor(window, "innerHeight");
    const originalVisualViewport = Object.getOwnPropertyDescriptor(
      window,
      "visualViewport"
    );
    const animationFrames = new Map<number, FrameRequestCallback>();
    let nextAnimationFrameId = 1;
    const visualViewport = {
      height: 844,
      offsetTop: 0,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };

    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      writable: true,
      value: 844,
    });
    Object.defineProperty(window, "visualViewport", {
      configurable: true,
      value: visualViewport,
    });
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      const id = nextAnimationFrameId++;
      animationFrames.set(id, callback);
      return id;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation((id) => {
      animationFrames.delete(id);
    });

    const flushAnimationFrames = () => {
      const pending = Array.from(animationFrames.entries());
      animationFrames.clear();
      pending.forEach(([, callback]) => callback(0));
    };

    try {
      const { result, unmount } = renderHook(() => useViewportInsets());

      act(flushAnimationFrames);
      expect(result.current.visualViewportHeight).toBe(844);

      act(() => {
        window.dispatchEvent(new FocusEvent("focusin"));
      });
      act(flushAnimationFrames);

      visualViewport.height = 544;
      act(() => {
        vi.advanceTimersByTime(350);
      });
      act(flushAnimationFrames);

      expect(result.current.visualViewportHeight).toBe(544);
      expect(result.current.keyboardInset).toBe(300);
      expect(result.current.isKeyboardOpen).toBe(true);

      unmount();
    } finally {
      if (originalInnerHeight) {
        Object.defineProperty(window, "innerHeight", originalInnerHeight);
      }
      if (originalVisualViewport) {
        Object.defineProperty(window, "visualViewport", originalVisualViewport);
      } else {
        delete (window as Window & { visualViewport?: VisualViewport }).visualViewport;
      }
    }
  });
});
