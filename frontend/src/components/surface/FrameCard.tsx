/****
 * FrameCard — Canonical Tile Shell (Radius Contract Compliant)
 * ---------------------------------------------------------------------------
 * Purpose
 *  - Provide a single, reusable shell for cards/tiles/panels that guarantees:
 *    • One source-of-truth corner radius (from `--card-radius`, e.g. 20px)
 *    • No phantom square corners at high blur (hard clipping on decorative layers)
 *    • Depth that scales predictably via tokens
 *    • Optional accent ring for selected/active state
 *
 * How it connects to the theme registry
 *  - The registry publishes static geometry. AppShell projects responsive
 *    layout and active material colors; FrameCard reads the resulting variables.
 *
 * Tokens consumed
 *  - Geometry:  --card-radius (→ typically points to --radius-tile: 20px)
 *  - Chrome:    --bezel (px), --frame (px), --rim (px), --card-pad (px)
 *  - Material:  --panel-bg, --panel-border, --panel-bezel, --tile-blur (px)
 *  - Elevation: --depth-scale (multiplier, 0.75–1.25 typical)
 *  - Accents:   --accent-strong (used when data-selected="true")
 *
 * Props
 *  - depth?: number       → local multiplier (0.5–1.75) applied atop --depth-scale
 *  - selected?: boolean   → when true, liquid ring uses --accent-strong
 *  - hoverPop?: boolean   → subtle elevation bump on hover
 *  - className?: string   → extra classes for the root
 *  - style?: CSSProperties→ extra inline styles for the root
 *  - ariaLabel?: string   → accessible label for the card region
 *
 * Usage examples
 *  <FrameCard>…</FrameCard>
 *  <FrameCard selected depth={1.2}>…</FrameCard>
 *  <FrameCard hoverPop={false} depth={0.9}>…</FrameCard>
 *
 * Design rules (important)
 *  1) Do NOT add Tailwind `rounded-*` to the FrameCard shell. Let it own the curve.
 *  2) All decorative layers must use `border-radius: inherit` and be hard-clipped.
 *  3) If you need the content to look inset, adjust *inset/padding*, not radius math.
 *  4) Keep `isolation: isolate` on the root to avoid backdrop bleed in deep stacks.
 *
 * QA checklist (DevTools)
 *  - Computed border-radius on `.fc-root`, `.fc-bezel`, `.fc-liquid`, `.fc-inner`
 *    all match and equal `--card-radius`.
 *  - At 200–300% zoom, hover shadows do not reveal squared corners.
 *  - Toggling `data-selected=true` switches ring to `--accent-strong`.
 */

import React, { PropsWithChildren } from "react";
import clsx from "clsx";

export type FrameCardProps = PropsWithChildren<{
  /** Extra classes on the root wrapper */
  className?: string;
  /** Inline styles on the root wrapper */
  style?: React.CSSProperties;
  /**
   * Additional depth multiplier (1 = default).
   * Multiplies the global `--depth-scale` token for this instance only.
   * Acceptable range: 0.5–1.75 (values are clamped).
   */
  depth?: number;
  /**
   * When true, show the accent liquid ring using `--accent-strong`.
   * Useful for selected/active state.
   */
  selected?: boolean;
  /**
   * When true (default), slightly increases elevation on hover/focus-visible.
   */
  hoverPop?: boolean;
  /** Accessible label for the card region */
  ariaLabel?: string;
  /** Apply fallback glass background for divider-style cards (used to replace FrameCard) */
  refractiveFallback?: boolean;
  /** Optional visual mode for refractive fallback */
  shimmerMode?: "subtle" | "strong" | "ambient";
  /**
   * Whether to show the liquid bezel ring.
   * The accent uses the canonical rim and can be hidden independently.
   */
  liquidBezel?: boolean;
  /**
   * Deprecated compatibility prop. Rim geometry is owned by --rim.
   */
  liquidBezelWidth?: number;
  /**
   * Whether the FrameCard should fill its container.
   * Defaults to true.
   */
  fill?: boolean;
  /** Optional testing hook forwarded to the root element. */
  "data-testid"?: string;
}>;

const clamp = (n: number | undefined, lo: number, hi: number, fb: number) => {
  if (typeof n !== "number" || Number.isNaN(n)) return fb;
  return Math.max(lo, Math.min(hi, n));
};

export default function FrameCard({
  children,
  className,
  style,
  depth = 1,
  selected = false,
  hoverPop = true,
  ariaLabel,
  refractiveFallback = false,
  shimmerMode = "subtle",
  liquidBezel = true,
  fill = true,
  ["data-testid"]: dataTestId,
}: FrameCardProps) {
  const d = clamp(depth, 0.5, 1.75, 1);

  const rootStyle: React.CSSProperties = {
    ...(style || {}),
    boxSizing: "border-box",
    ...(refractiveFallback
      ? {
          background:
            "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)), rgba(255,255,255,0.06)",
          backdropFilter: "blur(12px) saturate(120%)",
          WebkitBackdropFilter: "blur(12px) saturate(120%)",
          borderColor: "rgba(255,255,255,0.18)",
          boxShadow:
            shimmerMode === "ambient"
              ? "inset 0 1px rgba(255,255,255,0.2), inset 0 -1px rgba(0,0,0,0.25), 0 30px 70px rgba(0,0,0,0.28), 0 12px 36px rgba(0,0,0,0.22)"
              : shimmerMode === "strong"
              ? "inset 0 1px rgba(255,255,255,0.22), inset 0 -1px rgba(0,0,0,0.28), 0 22px 48px rgba(0,0,0,0.25), 0 8px 24px rgba(0,0,0,0.20)"
              : "inset 0 1px rgba(255,255,255,0.2), inset 0 -1px rgba(0,0,0,0.22), 0 14px 28px rgba(0,0,0,0.18), 0 6px 18px rgba(0,0,0,0.16)",
        }
      : {}),
    // Local depth multiplier for this instance only (multiplies --depth-scale)
    ["--fc-depth" as any]: String(d),
    // The frame layer owns thickness even when older callers pass a root border.
    borderTopWidth: 0,
    borderRightWidth: 0,
    borderBottomWidth: 0,
    borderLeftWidth: 0,
    // Conditionally set height and width to avoid double-layer glass when nested inside another FrameCard
    height: fill ? "100%" : "auto",
    width: fill ? "100%" : "auto",
  };

  return (
    <div
      className={clsx("fc-root relative rounded-[var(--card-radius)] bg-[var(--panel-bg)] shadow-sm", className)}
      style={rootStyle}
      role="group"
      aria-label={ariaLabel}
      data-testid={dataTestId}
      data-selected={selected ? "true" : undefined}
      data-hoverpop={hoverPop ? "true" : undefined}
    >
      {/* Outer glass/bezel layer */}
      <div className="fc-bezel" aria-hidden />

      {/* Accent liquid ring (neutral by default; accent in selected state) */}
      {liquidBezel && (
        <div
          className={clsx("fc-liquid", shimmerMode && `shimmer-${shimmerMode}`)}
          aria-hidden
          style={{
            WebkitMask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
            WebkitMaskComposite: "xor",
            maskComposite: "exclude",
          }}
        />
      )}

      {/* Inner content face (scroll-safe wrapper) */}
      <div className="fc-frame">
        <div className="fc-rim">
          <div className="fc-inner-clip">
            <div className="fc-inner relative">{children}</div>
          </div>
        </div>
      </div>

      {/* Strict CSS (scoped) */}
      <style>{`
        .fc-inner-clip {
          position: relative;
          flex: 1 1 auto;
          min-height: 0;
          border-radius: inherit;
          overflow: visible;
          display: flex;
          flex-direction: column;
        }
        .fc-root {
          border-radius: var(--card-radius);
          padding: var(--bezel);
          isolation: isolate; /* prevent backdrop bleed */
          display: flex;
          flex-direction: column;
          height: 100%;
          width: 100%;
          box-sizing: border-box;
          overflow: hidden; /* clip content to rounded corners */
          min-height: 0;
        }
        .fc-inner {
          position: relative;
          display: flex;
          flex-direction: column;
          flex: 1 1 auto;
          min-height: 0;
          box-sizing: border-box;
          padding: var(--card-pad);
        }
        .fc-bezel,
        .fc-frame,
        .fc-rim,
        .fc-liquid,
        .fc-inner {
          border-radius: inherit; /* exact match: no phantom corners */
        }

        /* Hard-clip decorative layers to the exact curve */
        .fc-bezel,
        .fc-liquid {
          position: absolute;
          inset: 0;
          overflow: clip;
          -webkit-clip-path: inset(0 round var(--card-radius));
          clip-path: inset(0 round var(--card-radius));
          pointer-events: none;
        }

        /* Bezel: translucent ring + depth shadow that scales by depth vars */
        .fc-bezel {
          border: var(--bezel) solid var(--panel-bezel, rgba(255,255,255,0.16));
          backdrop-filter: saturate(140%) blur(var(--tile-blur, 8px));
          -webkit-backdrop-filter: saturate(140%) blur(var(--tile-blur, 8px));
          box-shadow:
            inset 0 var(--lip-w, 4px) rgba(255,255,255,0.20),
            inset 0 calc(-1 * var(--lip-w, 4px)) rgba(0,0,0,0.20),
            /* outer depth scales by --depth-scale and --fc-depth */
            0 calc(14px * var(--depth-scale, 1) * var(--fc-depth)) calc(34px * var(--depth-scale, 1) * var(--fc-depth)) rgba(0,0,0,0.20),
            0 calc(4px * var(--depth-scale, 1) * var(--fc-depth))  calc(12px * var(--depth-scale, 1) * var(--fc-depth)) rgba(0,0,0,0.14);
          transition: box-shadow 160ms ease;
        }

        .fc-frame,
        .fc-rim {
          display: flex;
          flex: 1 1 auto;
          flex-direction: column;
          min-height: 0;
        }
        .fc-frame {
          padding: var(--frame);
          background: transparent;
        }
        .fc-rim {
          /* Frame and rim share one edge footprint instead of adding widths. */
          margin: calc(-1 * var(--frame));
          padding: var(--rim);
          background: transparent;
        }

        /* Liquid accent follows the canonical rim without adding an inset. */
        .fc-liquid {
          inset: var(--bezel);
          border: var(--rim) solid transparent;
          background:
            linear-gradient(var(--fc-accent, rgba(255,255,255,0.06)), var(--fc-accent, rgba(255,255,255,0.06))) padding-box,
            linear-gradient(rgba(255,255,255,0.06), rgba(255,255,255,0.06)) border-box;
          background-clip: padding-box, border-box;
        }
        .fc-root[data-selected="true"] .fc-liquid { --fc-accent: var(--accent-strong); }

        /* Inner content face: scroll-safe, compositor-safe */
        .fc-inner {
          position: relative;
          background: var(--panel-bg, rgba(17,24,39,0.86));
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.06),
            inset 0 -10px 24px rgba(0,0,0,0.18);
          overflow: visible; /* allow scroll containers and absolute children */
          flex: 1;
          min-height: 0;
          display: flex;
          flex-direction: column;
        }

        /* Hover energy (optional) */
        .fc-root[data-hoverpop="true"]:where(:hover, :focus-visible) .fc-bezel {
          box-shadow:
            inset 0 var(--lip-w, 4px) rgba(255,255,255,0.20),
            inset 0 calc(-1 * var(--lip-w, 4px)) rgba(0,0,0,0.20),
            0 calc(16px * var(--depth-scale, 1) * var(--fc-depth)) calc(40px * var(--depth-scale, 1) * var(--fc-depth)) rgba(0,0,0,0.22),
            0 calc(6px * var(--depth-scale, 1) * var(--fc-depth))  calc(16px * var(--depth-scale, 1) * var(--fc-depth)) rgba(0,0,0,0.18);
        }

        @keyframes shimmerRipple {
          0% {
            box-shadow: 0 0 0px rgba(255,255,255,0.04);
          }
          50% {
            box-shadow: 0 0 10px rgba(255,255,255,0.12);
          }
          100% {
            box-shadow: 0 0 0px rgba(255,255,255,0.04);
          }
        }
        .fc-liquid.shimmer-subtle {
          animation: shimmerRipple 18s ease-in-out infinite;
        }
        .fc-liquid.shimmer-strong {
          animation: shimmerRipple 10s ease-in-out infinite;
        }
        .fc-liquid.shimmer-ambient {
          animation: shimmerRipple 6s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
