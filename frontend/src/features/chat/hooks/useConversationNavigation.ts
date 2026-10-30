/**
 * useConversationNavigation - owns the transcript geometry projection used by
 * the conversation minimap.
 *
 * Responsibilities:
 * - track the active reading section from real message geometry
 * - commit jumps inside the existing transcript scroll container
 * - retain a single return anchor so repeated jumps do not overwrite it
 * - keep the work bounded (binary search + rAF, never a full transcript scan
 *   on every raw scroll event)
 */
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { RefObject } from "react";

import {
  buildConversationNavigationEntries,
  deriveConversationSections,
  type ConversationNavigationEntry,
  type ConversationSection,
} from "@/features/chat/conversationNavigation";
import type { ChatMessage } from "@/features/chat/useChat";

/** Minimum vertical spacing, in pixels, between two independent rail marks. */
export const CONVERSATION_RAIL_MIN_MARK_SPACING = 12;
/** Lower bound for the number of independent rail marks. */
export const CONVERSATION_RAIL_MIN_MARKS = 4;
/** Upper bound for the number of independent rail marks. */
export const CONVERSATION_RAIL_MAX_MARKS = 64;
/** Minimum transcript width, in pixels, that can host the rail and preview. */
export const CONVERSATION_MINIMAP_MIN_CONTAINER_WIDTH = 640;
/** Distance, in pixels, kept above a jumped-to message. */
export const CONVERSATION_JUMP_INSET = 8;

export type ConversationReturnAnchor = {
  sectionId: string;
  /** Offset of the anchor element relative to the scroll container viewport. */
  offset: number;
};

export type UseConversationNavigationArgs = {
  containerRef: RefObject<HTMLDivElement | null>;
  contentRef?: RefObject<HTMLDivElement | null>;
  messages: ChatMessage[];
  threadId: number;
  /** Called before a committed jump so the caller can leave latest-follow. */
  onNavigateAwayFromLatest?: () => void;
};

export type ConversationNavigationState = {
  sections: ConversationSection[];
  entries: ConversationNavigationEntry[];
  activeSectionId: string | null;
  containerWidth: number;
  containerHeight: number;
  /** True when the transcript content is taller than the scroll viewport. */
  hasOverflow: boolean;
  canGoBack: boolean;
  jumpToSection: (sectionId: string) => boolean;
  backToPreviousPosition: () => boolean;
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

function escapeAttributeValue(value: string): string {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(value);
  }
  return value.replace(/["\\]/g, "\\$&");
}

function scrollContainerTo(
  container: HTMLElement,
  top: number,
  behavior: ScrollBehavior
): void {
  const clamped = Math.max(0, top);
  container.scrollTop = clamped;
  if (behavior === "auto") return;
  if (typeof container.scrollTo !== "function") return;
  try {
    container.scrollTo({ top: clamped, behavior });
  } catch {
    // Some environments expose scrollTo without supporting the options form.
  }
}

export function useConversationNavigation({
  containerRef,
  contentRef,
  messages,
  threadId,
  onNavigateAwayFromLatest,
}: UseConversationNavigationArgs): ConversationNavigationState {
  const sections = useMemo(() => deriveConversationSections(messages), [messages]);
  const sectionsRef = useRef(sections);
  sectionsRef.current = sections;

  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const activeSectionIdRef = useRef<string | null>(null);
  const [containerMetrics, setContainerMetrics] = useState({
    width: 0,
    height: 0,
    scrollHeight: 0,
  });
  const [canGoBack, setCanGoBack] = useState(false);

  const positionsRef = useRef<Array<{ id: string; top: number }>>([]);
  const returnAnchorRef = useRef<ConversationReturnAnchor | null>(null);
  const scrollFrameRef = useRef<number | null>(null);
  const measureFrameRef = useRef<number | null>(null);

  const setActiveSection = useCallback((sectionId: string | null) => {
    if (activeSectionIdRef.current === sectionId) return;
    activeSectionIdRef.current = sectionId;
    setActiveSectionId(sectionId);
  }, []);

  /**
   * Re-read the geometry of the registered section anchors. This runs on
   * layout changes only, never on a raw scroll event.
   */
  const measureAnchors = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();
    const nodes = container.querySelectorAll<HTMLElement>(
      "[data-conversation-anchor]"
    );
    const next: Array<{ id: string; top: number }> = [];
    nodes.forEach((node) => {
      const identity = node.getAttribute("data-conversation-anchor");
      if (!identity) return;
      const rect = node.getBoundingClientRect();
      next.push({
        id: identity,
        top: rect.top - containerRect.top + container.scrollTop,
      });
    });
    positionsRef.current = next;

    setContainerMetrics((previous) => {
      const width = container.clientWidth;
      const height = container.clientHeight;
      const scrollHeight = container.scrollHeight;
      if (
        previous.width === width &&
        previous.height === height &&
        previous.scrollHeight === scrollHeight
      ) {
        // Returning the same reference keeps React from re-rendering on a
        // measurement that did not change.
        return previous;
      }
      return { width, height, scrollHeight };
    });
  }, [containerRef]);

  /**
   * Resolve the active reading section from measured geometry. Uses a binary
   * search over the cached anchor positions so the cost stays bounded.
   */
  const updateActiveSection = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const positions = positionsRef.current;
    if (positions.length === 0) {
      setActiveSection(null);
      return;
    }

    const readingLine = container.scrollTop + 1;
    let low = 0;
    let high = positions.length - 1;
    let resolved: string | null = null;

    while (low <= high) {
      const middle = (low + high) >> 1;
      if (positions[middle].top <= readingLine) {
        resolved = positions[middle].id;
        low = middle + 1;
      } else {
        high = middle - 1;
      }
    }

    // Above the first anchor there is no passed section yet, so the first
    // loaded section is the one being read.
    setActiveSection(resolved ?? positions[0].id);
  }, [containerRef, setActiveSection]);

  const scheduleActiveUpdate = useCallback(() => {
    if (scrollFrameRef.current !== null) return;
    if (typeof requestAnimationFrame !== "function") {
      updateActiveSection();
      return;
    }
    scrollFrameRef.current = requestAnimationFrame(() => {
      scrollFrameRef.current = null;
      updateActiveSection();
    });
  }, [updateActiveSection]);

  const scheduleMeasure = useCallback(() => {
    if (measureFrameRef.current !== null) return;
    if (typeof requestAnimationFrame !== "function") {
      measureAnchors();
      return;
    }
    measureFrameRef.current = requestAnimationFrame(() => {
      measureFrameRef.current = null;
      measureAnchors();
      updateActiveSection();
    });
  }, [measureAnchors, updateActiveSection]);

  // Track ordinary scrolling without scanning the transcript on every event.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      scheduleActiveUpdate();
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      container.removeEventListener("scroll", handleScroll);
    };
  }, [containerRef, scheduleActiveUpdate]);

  // Observe the transcript container and the message lane so growing content
  // (images, streaming content, prepended history) refreshes the projection.
  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver(() => {
      scheduleMeasure();
    });
    observer.observe(container);
    const content = contentRef?.current;
    if (content) observer.observe(content);
    return () => observer.disconnect();
  }, [containerRef, contentRef, scheduleMeasure]);

  // Measure on layout so the projection is never a frame stale, and re-measure
  // through the observer when content grows after layout. The dependency is a
  // stable signature so an unchanged transcript is not re-measured on every
  // render.
  const sectionSignature = useMemo(
    () => sections.map((section) => section.id).join("|"),
    [sections]
  );

  useLayoutEffect(() => {
    measureAnchors();
    updateActiveSection();
  }, [measureAnchors, sectionSignature, updateActiveSection]);

  // A thread switch must never leave the previous thread's position, preview
  // target, or observers behind.
  useEffect(() => {
    returnAnchorRef.current = null;
    setCanGoBack(false);
    setActiveSection(null);
    positionsRef.current = [];
    scheduleMeasure();
  }, [scheduleMeasure, setActiveSection, threadId]);

  useEffect(() => {
    return () => {
      if (scrollFrameRef.current !== null) {
        cancelAnimationFrame(scrollFrameRef.current);
        scrollFrameRef.current = null;
      }
      if (measureFrameRef.current !== null) {
        cancelAnimationFrame(measureFrameRef.current);
        measureFrameRef.current = null;
      }
    };
  }, []);

  const captureReturnAnchor = useCallback(
    (container: HTMLElement) => {
      // Repeated jumps must not replace the original return point.
      if (returnAnchorRef.current) return;

      const activeId = activeSectionIdRef.current;
      if (!activeId) return;

      const node = container.querySelector<HTMLElement>(
        `[data-conversation-anchor="${escapeAttributeValue(activeId)}"]`
      );
      if (!node) return;

      const containerRect = container.getBoundingClientRect();
      const nodeRect = node.getBoundingClientRect();
      returnAnchorRef.current = {
        sectionId: activeId,
        offset: nodeRect.top - containerRect.top,
      };
      setCanGoBack(true);
    },
    []
  );

  const jumpToSection = useCallback(
    (sectionId: string): boolean => {
      const container = containerRef.current;
      if (!container || !sectionId) return false;

      const node = container.querySelector<HTMLElement>(
        `[data-conversation-anchor="${escapeAttributeValue(sectionId)}"]`
      );
      // A missing or removed destination must fail safely rather than land on
      // an unrelated message.
      if (!node) return false;

      captureReturnAnchor(container);

      const containerRect = container.getBoundingClientRect();
      const nodeRect = node.getBoundingClientRect();
      const offsetFromViewport = nodeRect.top - containerRect.top;
      const target = container.scrollTop + offsetFromViewport - CONVERSATION_JUMP_INSET;

      onNavigateAwayFromLatest?.();
      scrollContainerTo(
        container,
        target,
        prefersReducedMotion() ? "auto" : "smooth"
      );
      scheduleMeasure();
      return true;
    },
    [
      captureReturnAnchor,
      containerRef,
      onNavigateAwayFromLatest,
      scheduleMeasure,
    ]
  );

  const backToPreviousPosition = useCallback((): boolean => {
    const container = containerRef.current;
    const anchor = returnAnchorRef.current;
    if (!container || !anchor) return false;

    const node = container.querySelector<HTMLElement>(
      `[data-conversation-anchor="${escapeAttributeValue(anchor.sectionId)}"]`
    );
    if (!node) return false;

    const containerRect = container.getBoundingClientRect();
    const nodeRect = node.getBoundingClientRect();
    // The anchor identity is stable across prepends, so the content offset is
    // re-read from the live DOM instead of from a cached pixel value.
    const contentTop = nodeRect.top - containerRect.top + container.scrollTop;
    const target = contentTop - anchor.offset;

    onNavigateAwayFromLatest?.();
    scrollContainerTo(
      container,
      target,
      prefersReducedMotion() ? "auto" : "smooth"
    );
    returnAnchorRef.current = null;
    setCanGoBack(false);
    scheduleMeasure();
    return true;
  }, [containerRef, onNavigateAwayFromLatest, scheduleMeasure]);

  const hasOverflow = containerMetrics.scrollHeight > containerMetrics.height + 1;

  const maxMarks = Math.min(
    CONVERSATION_RAIL_MAX_MARKS,
    Math.max(
      CONVERSATION_RAIL_MIN_MARKS,
      Math.floor(containerMetrics.height / CONVERSATION_RAIL_MIN_MARK_SPACING) || 1
    )
  );

  const entries = useMemo(
    () => buildConversationNavigationEntries(sections, maxMarks),
    [maxMarks, sections]
  );

  return {
    sections,
    entries,
    activeSectionId,
    containerWidth: containerMetrics.width,
    containerHeight: containerMetrics.height,
    hasOverflow,
    canGoBack,
    jumpToSection,
    backToPreviousPosition,
  };
}
