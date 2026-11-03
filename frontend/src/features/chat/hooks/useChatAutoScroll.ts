import { useCallback, useEffect, useRef } from "react";
import type { RefObject } from "react";

export type ChatAutoScrollOptions = {
  /**
   * When present, the hook consults this ref before scheduling an
   * auto-scroll. A consumer that intentionally navigated away from the latest
   * turn sets it to `false` so incoming messages and streaming updates do not
   * pull the reader back down.
   */
  followLatestRef?: RefObject<boolean | null>;
};

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

export function useChatAutoScroll(
  messagesLength: number,
  threshold = 120,
  options?: ChatAutoScrollOptions
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nearBottomRef = useRef(true);
  const pendingFrameRef = useRef<number | null>(null);
  const followLatestRef = options?.followLatestRef ?? null;

  const cancelPendingAutoScroll = useCallback(() => {
    if (pendingFrameRef.current !== null) {
      cancelAnimationFrame(pendingFrameRef.current);
      pendingFrameRef.current = null;
    }
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const updateNearBottom = () => {
      const distance = el.scrollHeight - el.clientHeight - el.scrollTop;
      nearBottomRef.current = distance <= threshold;
    };

    updateNearBottom();
    el.addEventListener("scroll", updateNearBottom, { passive: true });
    return () => {
      el.removeEventListener("scroll", updateNearBottom);
    };
  }, [threshold]);

  useEffect(() => {
    if (followLatestRef?.current === false) return;
    if (!nearBottomRef.current) return;

    cancelPendingAutoScroll();
    pendingFrameRef.current = requestAnimationFrame(() => {
      pendingFrameRef.current = null;
      // Re-check the reader's intent before pulling the transcript back down.
      // `nearBottomRef` only changes on a real scroll event, so it survives
      // the transcript growing underneath the reader. Recomputing the
      // distance from the current geometry here would mistake a tall
      // appended reply for the reader having moved away.
      if (!nearBottomRef.current) return;
      if (followLatestRef?.current === false) return;
      endRef.current?.scrollIntoView({
        behavior: prefersReducedMotion() ? "auto" : "smooth",
        block: "end",
      });
    });

    return () => {
      cancelPendingAutoScroll();
    };
  }, [cancelPendingAutoScroll, followLatestRef, messagesLength, threshold]);

  return { containerRef, endRef, cancelPendingAutoScroll };
}
