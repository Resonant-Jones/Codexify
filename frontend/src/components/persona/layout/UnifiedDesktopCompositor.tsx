import { ArrowDownLeft, Globe2, Maximize2, Pin, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type CSSProperties, type PropsWithChildren, type RefObject } from "react";

export type BrowserPresentation = "closed" | "docked" | "focused";

const DEFAULT_DOCKED_RATIO = 0.52;
const DIVIDER_WIDTH = 12;
const CLOSE_BROWSER_WIDTH = 140;
const FOCUS_CODEXIFY_WIDTH = 760;
const MIN_USABLE_CODEXIFY_WIDTH = 650;

function focusThreshold(width: number) {
  return Math.max(MIN_USABLE_CODEXIFY_WIDTH, Math.min(FOCUS_CODEXIFY_WIDTH, width * 0.42));
}

type Props = PropsWithChildren<{
  enabled: boolean;
  shellStyle: CSSProperties;
  presentation: BrowserPresentation;
  onPresentationChange: (state: BrowserPresentation) => void;
  focusedSidebarOpen: boolean;
  focusedSidebarPinned: boolean;
  onFocusedSidebarReveal: () => void;
  focusedSidebarRevealRef?: RefObject<HTMLButtonElement | null>;
  onCodexifyPaneWidthChange?: (width: number) => void;
}>;

export default function UnifiedDesktopCompositor({
  enabled,
  shellStyle,
  presentation,
  onPresentationChange,
  focusedSidebarOpen,
  focusedSidebarPinned,
  onFocusedSidebarReveal,
  focusedSidebarRevealRef,
  onCodexifyPaneWidthChange,
  children,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const lastCodexifyFocusRef = useRef<HTMLElement | null>(null);
  const restoreCodexifyFocusRef = useRef(false);
  const [dockedRatio, setDockedRatio] = useState(DEFAULT_DOCKED_RATIO);
  const [containerWidth, setContainerWidth] = useState(() =>
    typeof window === "undefined" ? 1440 : window.innerWidth
  );
  const availableWidth = Math.max(1, containerWidth - DIVIDER_WIDTH);

  useEffect(() => {
    if (presentation !== "closed" || !restoreCodexifyFocusRef.current) return;
    restoreCodexifyFocusRef.current = false;
    queueMicrotask(() => {
      const pane = rootRef.current?.querySelector<HTMLElement>(".unified-desktop__codexify");
      if (!pane) return;
      const previous = lastCodexifyFocusRef.current;
      const target = previous?.isConnected && pane.contains(previous)
        ? previous
        : pane.querySelector<HTMLElement>("[data-testid='app-shell-nav-anchor'] button, button:not([disabled])") ?? pane;
      target.focus();
    });
  }, [presentation]);

  const changePresentation = useCallback((next: BrowserPresentation) => {
    if (next === "closed" && presentation !== "closed") restoreCodexifyFocusRef.current = true;
    onPresentationChange(next);
  }, [onPresentationChange, presentation]);

  useEffect(() => {
    const measuredWidth = rootRef.current?.clientWidth || containerWidth;
    const measuredAvailableWidth = Math.max(1, measuredWidth - DIVIDER_WIDTH);
    if (enabled && presentation === "docked" && measuredAvailableWidth * dockedRatio <= focusThreshold(measuredAvailableWidth)) {
      changePresentation("focused");
    }
  }, [changePresentation, containerWidth, dockedRatio, enabled, presentation]);

  useEffect(() => {
    if (!enabled || !rootRef.current) return;
    const root = rootRef.current;
    const updateWidth = () => {
      if (root.clientWidth > 0) setContainerWidth(root.clientWidth);
      const paneWidth = root.querySelector<HTMLElement>(".unified-desktop__codexify")?.clientWidth;
      if (paneWidth && paneWidth > 0) onCodexifyPaneWidthChange?.(paneWidth);
    };
    updateWidth();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateWidth);
      return () => window.removeEventListener("resize", updateWidth);
    }
    const observer = new ResizeObserver(updateWidth);
    observer.observe(root);
    const pane = root.querySelector<HTMLElement>(".unified-desktop__codexify");
    if (pane) observer.observe(pane);
    return () => observer.disconnect();
  }, [enabled, onCodexifyPaneWidthChange]);

  const resizeTo = useCallback((clientX: number) => {
    const rect = rootRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= DIVIDER_WIDTH) return;
    const width = rect.width - DIVIDER_WIDTH;
    const codexifyWidth = clientX - rect.left;
    if (codexifyWidth <= focusThreshold(width)) {
      changePresentation("focused");
      return;
    }
    if (width - codexifyWidth <= CLOSE_BROWSER_WIDTH) {
      changePresentation("closed");
      return;
    }
    setDockedRatio(Math.max(0, Math.min(1, codexifyWidth / width)));
  }, [changePresentation]);

  if (!enabled) return <>{children}</>;

  return (
    <div
      ref={rootRef}
      className="unified-desktop"
      data-testid="unified-desktop"
      data-browser-state={presentation}
      data-focused-sidebar-pinned={focusedSidebarPinned ? "true" : "false"}
      style={shellStyle}
    >
      <div
        className="unified-desktop__codexify"
        data-testid="unified-desktop-codexify"
        inert={presentation === "focused"}
        tabIndex={-1}
        onFocusCapture={(event) => { lastCodexifyFocusRef.current = event.target as HTMLElement; }}
        style={{ flexGrow: presentation === "docked" ? dockedRatio : 1 }}
      >
        {children}
      </div>
      {presentation === "docked" && (
        <div
          role="separator"
          tabIndex={0}
          aria-label="Resize Codexify and browser"
          aria-orientation="vertical"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(dockedRatio * 100)}
          className="unified-desktop__divider"
          data-testid="unified-desktop-divider"
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId);
            resizeTo(event.clientX);
          }}
          onPointerMove={(event) => {
            if (event.currentTarget.hasPointerCapture(event.pointerId)) resizeTo(event.clientX);
          }}
          onKeyDown={(event) => {
            if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
            event.preventDefault();
            const step = event.key === "ArrowRight" ? 0.05 : -0.05;
            resizeTo((rootRef.current?.getBoundingClientRect().left ?? 0) +
              availableWidth * (dockedRatio + step));
          }}
        />
      )}
      {presentation !== "closed" && (
        <section
          className="unified-desktop__browser"
          data-testid="unified-desktop-browser"
          aria-label="Browser preview"
          style={{ flexGrow: presentation === "docked" ? 1 - dockedRatio : 1 }}
        >
          <header className="unified-desktop__browser-chrome">
            <Globe2 size={18} aria-hidden="true" />
            <input
              className="unified-desktop__location"
              aria-label="Browser location"
              value="Preview only · no page loaded"
              readOnly
            />
            <button
              type="button"
              className="unified-desktop__chrome-action"
              aria-label={presentation === "focused" ? "Restore docked browser" : "Focus browser"}
              title={presentation === "focused" ? "Restore docked browser" : "Focus browser"}
              onClick={() => changePresentation(presentation === "focused" ? "docked" : "focused")}
            >
              {presentation === "focused" ? <ArrowDownLeft size={18} aria-hidden="true" /> : <Maximize2 size={18} aria-hidden="true" />}
            </button>
            <button
              type="button"
              className="unified-desktop__chrome-action"
              aria-label="Close browser preview"
              title="Close browser preview"
              onClick={() => changePresentation("closed")}
            >
              <X size={18} aria-hidden="true" />
            </button>
          </header>
          <div className="unified-desktop__browser-content">
            <Globe2 size={40} aria-hidden="true" />
            <h2>Browser surface</h2>
            <p>This is a spatial preview. Page navigation is not connected yet.</p>
          </div>
        </section>
      )}
      {presentation === "closed" && (
        <div className="unified-desktop__edge-summon" data-testid="browser-edge-summon">
          <button
            type="button"
            aria-label="Open browser preview"
            title="Open browser preview"
            onClick={() => changePresentation("docked")}
          >
            <Globe2 size={18} aria-hidden="true" />
          </button>
        </div>
      )}
      {presentation === "focused" && !focusedSidebarOpen && !focusedSidebarPinned && (
        <div
          className="unified-desktop__sidebar-edge"
          data-testid="focused-sidebar-edge"
          onPointerEnter={onFocusedSidebarReveal}
        >
          <button ref={focusedSidebarRevealRef} type="button" aria-label="Reveal Codexify sidebar" onClick={onFocusedSidebarReveal}>
            <Pin size={16} aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  );
}
