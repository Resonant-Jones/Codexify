import * as React from "react";
import { cn } from "@/lib/utils";

export type Props = React.HTMLAttributes<HTMLDivElement> & {
  /** Visual tone: base (default), sheet (brighter), floating (darker), merge (front matches panel bg) */
  tone?: "base" | "sheet" | "floating" | "merge";
  /** Optional: className for the FRONT card (content layer) */
  innerClassName?: string;
  /** Optional: style for the FRONT card (content layer) */
  innerStyle?: React.CSSProperties;
};

/**
 * LayeredCard — seam‑free two‑layer chrome
 *
 * • Back plate (lighter): real border + soft inner highlight and dual drop shadows
 * • Front card (darker): inset by 3px, real border + inner highlight and dual drop shadows
 * • No pseudo‑element masks, no blur — eliminates rounded‑corner hairlines
 */
export default function LayeredCard({
  className,
  style,
  innerClassName,
  innerStyle,
  tone = "base",
  children,
  ...rest
}: Props) {
  const palettes: Record<NonNullable<Props["tone"]>, { front: string; back: string }> = {
    // Neutral working surface (Guardian chat, Dashboard content)
    base: {
      front: "color-mix(in oklab, var(--panel-bg) 90%, black 10%)",   // slightly darker than bg
      back:  "color-mix(in oklab, var(--panel-bg) 88%, white 12%)",  // slightly lighter than bg
    },
    // Brighter “sheet” for forms/settings (reads as one layer up)
    sheet: {
      front: "color-mix(in oklab, var(--panel-bg) 70%, white 30%)",  // bright paper
      back:  "color-mix(in oklab, var(--panel-bg) 64%, white 36%)",  // a touch brighter behind
    },
    // Darker floating tiles/overlays (subtle pop in light mode)
    floating: {
      front: "color-mix(in oklab, var(--panel-bg) 92%, black 8%)",
      back:  "color-mix(in oklab, var(--panel-bg) 88%, black 12%)",
    },
    // MERGE: front matches the panel background for slab-like continuity; back gives a soft occlusion ring
    merge: {
      front: "var(--panel-bg)",
      back:  "color-mix(in oklab, var(--panel-bg) 88%, black 12%)",
    },
  };

  // Defensive: accept any incoming tone value and fall back to base
  const palette = (palettes as any)[tone] ?? palettes.base;
  const { front: frontColor, back: backColor } = palette;

  return (
    <div data-tone={tone} className={cn("relative min-h-0 rounded-2xl", className)} style={style} {...rest}>
      {/* BACK PLATE (lighter) */}
      <div
        className="absolute inset-0 rounded-2xl border overflow-hidden pointer-events-none"
        style={{
          // 10% lighter than panel bg
          background: backColor,
          borderColor: "var(--panel-bezel)",
          borderWidth: "var(--bezel-thickness, 3px)",
          borderRadius: "var(--card-radius, 16px)",
          // vertical-only lip: soft inner highlight + dual drop shadows
          boxShadow:
            "inset 0 var(--lip-w, 2px) var(--bezel-highlight, rgba(255,255,255,0.22)), inset 0 calc(var(--lip-w, 2px) * -1) var(--bezel-shadow, rgba(0,0,0,0.18)), var(--elevation-shadow-back, 0 14px 34px rgba(0,0,0,0.20), 0 4px 12px rgba(0,0,0,0.14))",
          backgroundClip: "padding-box",
        }}
        aria-hidden
      />

      {/* FRONT CARD (darker, inset by 3px) */}
      <div className="absolute rounded-2xl overflow-hidden" style={{ inset: "var(--inset-3, 3px)", borderRadius: "calc(var(--card-radius, 16px) - var(--inset-3, 3px))" }}>
        <div
          className={cn(
            "h-full min-h-0 rounded-2xl border",
            innerClassName,
          )}
          style={{
            // 10% darker than panel bg
            background: frontColor,
            borderColor: "var(--panel-bezel)",
            borderWidth: "var(--bezel-thickness, 3px)",
            borderRadius: "calc(var(--card-radius, 16px) - var(--inset-3, 3px))",
            // vertical-only inner highlight + dual drop for depth
            boxShadow:
              "inset 0 var(--lip-w, 2px) var(--bezel-highlight, rgba(255,255,255,0.22)), inset 0 calc(var(--lip-w, 2px) * -1) var(--bezel-shadow, rgba(0,0,0,0.22)), var(--elevation-shadow-front, 0 8px 24px rgba(0,0,0,0.22), 0 2px 6px rgba(0,0,0,0.18))",
            backgroundClip: "padding-box",
            ...innerStyle,
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
