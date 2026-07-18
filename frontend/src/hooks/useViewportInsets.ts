import { useEffect, useState } from "react";

export type ViewportInsets = {
  layoutViewportHeight: number;
  visualViewportHeight: number;
  visualViewportOffsetTop: number;
  keyboardInset: number;
  isKeyboardOpen: boolean;
};

const DEFAULT_VIEWPORT_INSETS: ViewportInsets = {
  layoutViewportHeight: 0,
  visualViewportHeight: 0,
  visualViewportOffsetTop: 0,
  keyboardInset: 0,
  isKeyboardOpen: false,
};

const FOCUS_VIEWPORT_SETTLE_DELAY_MS = 350;

function readViewportInsets(): ViewportInsets {
  if (typeof window === "undefined") {
    return DEFAULT_VIEWPORT_INSETS;
  }

  const layoutViewportHeight = Math.max(0, Math.round(window.innerHeight || 0));
  const visualViewport = window.visualViewport;
  const visualViewportHeight = Math.max(
    0,
    Math.round(visualViewport?.height ?? layoutViewportHeight)
  );
  const visualViewportOffsetTop = Math.max(
    0,
    Math.round(visualViewport?.offsetTop ?? 0)
  );
  const keyboardInset = Math.max(
    0,
    layoutViewportHeight - visualViewportHeight - visualViewportOffsetTop
  );

  return {
    layoutViewportHeight,
    visualViewportHeight,
    visualViewportOffsetTop,
    keyboardInset,
    isKeyboardOpen: keyboardInset > 24,
  };
}

export function useViewportInsets(enabled = true): ViewportInsets {
  const [viewportInsets, setViewportInsets] = useState<ViewportInsets>(() =>
    readViewportInsets()
  );

  useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      return;
    }

    const visualViewport = window.visualViewport;
    let frameId: number | null = null;
    let focusSettleTimerId: number | null = null;

    const syncViewportInsets = () => {
      if (frameId != null) {
        return;
      }

      frameId = window.requestAnimationFrame(() => {
        frameId = null;
        const next = readViewportInsets();
        setViewportInsets((previous) =>
          previous.layoutViewportHeight === next.layoutViewportHeight &&
          previous.visualViewportHeight === next.visualViewportHeight &&
          previous.visualViewportOffsetTop === next.visualViewportOffsetTop &&
          previous.keyboardInset === next.keyboardInset &&
          previous.isKeyboardOpen === next.isKeyboardOpen
            ? previous
            : next
        );
      });
    };

    const settleViewportAfterFocusChange = () => {
      syncViewportInsets();

      if (focusSettleTimerId != null) {
        window.clearTimeout(focusSettleTimerId);
      }
      focusSettleTimerId = window.setTimeout(() => {
        focusSettleTimerId = null;
        syncViewportInsets();
      }, FOCUS_VIEWPORT_SETTLE_DELAY_MS);
    };

    syncViewportInsets();

    window.addEventListener("resize", syncViewportInsets, { passive: true });
    window.addEventListener("orientationchange", syncViewportInsets);
    window.addEventListener("focusin", settleViewportAfterFocusChange);
    window.addEventListener("focusout", settleViewportAfterFocusChange);
    visualViewport?.addEventListener("resize", syncViewportInsets, { passive: true });
    visualViewport?.addEventListener("scroll", syncViewportInsets, { passive: true });

    return () => {
      if (frameId != null) {
        window.cancelAnimationFrame(frameId);
      }
      if (focusSettleTimerId != null) {
        window.clearTimeout(focusSettleTimerId);
      }
      window.removeEventListener("resize", syncViewportInsets);
      window.removeEventListener("orientationchange", syncViewportInsets);
      window.removeEventListener("focusin", settleViewportAfterFocusChange);
      window.removeEventListener("focusout", settleViewportAfterFocusChange);
      visualViewport?.removeEventListener("resize", syncViewportInsets);
      visualViewport?.removeEventListener("scroll", syncViewportInsets);
    };
  }, [enabled]);

  return viewportInsets;
}
