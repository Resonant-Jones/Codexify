import { Globe2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type CSSProperties, type PropsWithChildren } from "react";

const DEFAULT_CODEXIFY_RATIO = 0.52;
const MIN_CODEXIFY_WIDTH = 420;
const MIN_BROWSER_WIDTH = 320;
const DIVIDER_WIDTH = 12;

type Props = PropsWithChildren<{
  enabled: boolean;
  shellStyle: CSSProperties;
}>;

function clampRatio(ratio: number, containerWidth: number): number {
  const available = Math.max(1, containerWidth - DIVIDER_WIDTH);
  const lower = MIN_CODEXIFY_WIDTH / available;
  const upper = 1 - MIN_BROWSER_WIDTH / available;
  return Math.min(Math.max(ratio, lower), Math.max(lower, upper));
}

export default function UnifiedDesktopCompositor({ enabled, shellStyle, children }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [codexifyRatio, setCodexifyRatio] = useState(DEFAULT_CODEXIFY_RATIO);
  const [containerWidth, setContainerWidth] = useState(() =>
    typeof window === "undefined" ? 1440 : window.innerWidth
  );
  const ratio = clampRatio(codexifyRatio, containerWidth);

  useEffect(() => {
    if (!enabled || !rootRef.current) return;
    const root = rootRef.current;
    const updateWidth = () => {
      if (root.clientWidth > 0) setContainerWidth(root.clientWidth);
    };
    updateWidth();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateWidth);
      return () => window.removeEventListener("resize", updateWidth);
    }
    const observer = new ResizeObserver(updateWidth);
    observer.observe(root);
    return () => observer.disconnect();
  }, [enabled]);

  const resizeAt = useCallback((clientX: number) => {
    const rect = rootRef.current?.getBoundingClientRect();
    if (!rect) return;
    const available = Math.max(1, rect.width - DIVIDER_WIDTH);
    setCodexifyRatio(clampRatio((clientX - rect.left) / available, rect.width));
  }, []);

  if (!enabled) return <>{children}</>;

  return (
    <div
      ref={rootRef}
      className="unified-desktop"
      data-testid="unified-desktop"
      data-browser-open={browserOpen ? "true" : "false"}
      style={shellStyle}
    >
      <div
        className="unified-desktop__codexify"
        data-testid="unified-desktop-codexify"
        style={{ flexGrow: browserOpen ? ratio : 1 }}
      >
        {children}
      </div>
      {browserOpen ? (
        <>
          <div
            role="separator"
            tabIndex={0}
            aria-label="Resize Codexify and browser"
            aria-orientation="vertical"
            aria-valuemin={Math.round(clampRatio(0, containerWidth) * 100)}
            aria-valuemax={Math.round(clampRatio(1, containerWidth) * 100)}
            aria-valuenow={Math.round(ratio * 100)}
            className="unified-desktop__divider"
            data-testid="unified-desktop-divider"
            onPointerDown={(event) => {
              event.currentTarget.setPointerCapture(event.pointerId);
              resizeAt(event.clientX);
            }}
            onPointerMove={(event) => {
              if (event.currentTarget.hasPointerCapture(event.pointerId)) resizeAt(event.clientX);
            }}
            onKeyDown={(event) => {
              if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
              event.preventDefault();
              setCodexifyRatio((current) =>
                clampRatio(current + (event.key === "ArrowRight" ? 0.05 : -0.05), containerWidth)
              );
            }}
          />
          <section
            className="unified-desktop__browser"
            data-testid="unified-desktop-browser"
            aria-label="Browser preview"
            style={{ flexGrow: 1 - ratio }}
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
                className="unified-desktop__close"
                aria-label="Close browser preview"
                onClick={() => setBrowserOpen(false)}
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
        </>
      ) : (
        <button
          type="button"
          className="unified-desktop__open"
          aria-label="Open browser preview"
          onClick={() => setBrowserOpen(true)}
        >
          <Globe2 size={18} aria-hidden="true" />
          <span>Browser</span>
        </button>
      )}
    </div>
  );
}
