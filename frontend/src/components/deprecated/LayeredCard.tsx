// Archived LayeredCard implementation retained for reference only.
import * as React from "react";
import { cn } from "@/lib/utils";
import FrameCard from "@/components/surface/FrameCard";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";

export type BorderBevel = "none" | "small" | "chunky";

export type Props = React.HTMLAttributes<HTMLDivElement> & {
  tone?: "base" | "sheet" | "floating" | "merge";
  innerClassName?: string;
  innerStyle?: React.CSSProperties;
  bevel?: BorderBevel;
  depth?: number;
  glass?: boolean;
  liquidBezel?: boolean;
  liquidBezelWidth?: number;
};

export default function LayeredCard({
  className,
  style,
  innerClassName,
  innerStyle,
  tone = "base",
  bevel = "chunky",
  depth = 1,
  glass = true,
  liquidBezel = true,
  liquidBezelWidth = 3,
  children,
  ...rest
}: Props) {
  const palettes: Record<NonNullable<Props["tone"]>, { front: string; back: string }> = {
    base: {
      front: "color-mix(in oklab, var(--panel-bg) 90%, black 10%)",
      back: "color-mix(in oklab, var(--panel-bg) 88%, white 12%)",
    },
    sheet: {
      front: "color-mix(in oklab, var(--panel-bg) 70%, white 30%)",
      back: "color-mix(in oklab, var(--panel-bg) 64%, white 36%)",
    },
    floating: {
      front: "color-mix(in oklab, var(--panel-bg) 92%, black 8%)",
      back: "color-mix(in oklab, var(--panel-bg) 88%, black 12%)",
    },
    merge: {
      front: "var(--panel-bg)",
      back: "color-mix(in oklab, var(--panel-bg) 88%, black 12%)",
    },
  };

  const palette = (palettes as any)[tone] ?? palettes.base;
  const { front: frontColor, back: backColor } = palette;

  const bevelConfig = {
    none: { inset: 0, bezel: 0, lip: 0, radius: "12px" },
    small: { inset: 3, bezel: 3, lip: 2, radius: "16px" },
    chunky: { inset: 6, bezel: 6, lip: 4, radius: "18px" },
  } as const;

  const chosen = bevelConfig[bevel];
  const depthScale = Math.max(0.5, Number(depth) || 1);

  const cssVars: React.CSSProperties = {
    ["--inset-3" as any]: `${chosen.inset}px`,
    ["--bezel-thickness" as any]: `${chosen.bezel}px`,
    ["--lip-w" as any]: `${chosen.lip}px`,
    ["--card-radius" as any]: `${chosen.radius}`,
    ["--depth-scale" as any]: String(depthScale),
    ["--liquid-bezel-w" as any]: `${liquidBezelWidth}px`,
  };

  const glassStyle: React.CSSProperties = glass
    ? {
        WebkitBackdropFilter: "saturate(140%) blur(8px)",
        backdropFilter: "saturate(140%) blur(8px)",
      }
    : {};

  const backBoxShadow =
    "inset 0 var(--lip-w, 2px) var(--bezel-highlight, rgba(255,255,255,0.22)), inset 0 calc(var(--lip-w, 2px) * -1) var(--bezel-shadow, rgba(0,0,0,0.18)), 0 14px 34px rgba(0,0,0,0.20), 0 4px 12px rgba(0,0,0,0.14)";

  const frontBoxShadow =
    "inset 0 var(--lip-w, 2px) var(--bezel-highlight, rgba(255,255,255,0.22)), inset 0 calc(var(--lip-w, 2px) * -1) var(--bezel-shadow, rgba(0,0,0,0.22)), 0 8px 24px rgba(0,0,0,0.22), 0 2px 6px rgba(0,0,0,0.18)";

  return (
    <div data-tone={tone} className={cn("relative min-h-0 rounded-2xl", className)} style={{ ...cssVars, ...style }} {...rest}>
      <div
        className="absolute inset-0 rounded-2xl border overflow-hidden pointer-events-none"
        style={{
          background: backColor,
          borderColor: "var(--panel-bezel)",
          borderWidth: "var(--bezel-thickness, 3px)",
          borderRadius: "var(--card-radius, 16px)",
          boxShadow: backBoxShadow,
          backgroundClip: "padding-box",
          ...glassStyle,
        }}
        aria-hidden
      />
      {liquidBezel && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-2xl"
          style={{
            borderRadius: "var(--card-radius, 16px)",
            border: "var(--liquid-bezel-w, 3px) solid transparent",
            background:
              "linear-gradient(var(--panel-bg), var(--panel-bg)) padding-box, " +
              "linear-gradient(180deg, rgba(255,255,255,0.50) 0%, rgba(255,255,255,0.12) 55%, rgba(255,255,255,0.28) 100%) border-box",
            backgroundClip: "padding-box, border-box",
            WebkitBackdropFilter: glass ? "saturate(140%) blur(8px)" : undefined,
            backdropFilter: glass ? "saturate(140%) blur(8px)" : undefined,
            boxShadow: "0 0 0 1px rgba(255,255,255,0.06), 0 2px 10px rgba(0,0,0,0.25)",
            zIndex: 0,
          }}
        />
      )}

      <div className="absolute rounded-2xl overflow-hidden" style={{ inset: "var(--inset-3, 3px)", borderRadius: "calc(var(--card-radius, 16px) - var(--inset-3, 3px))", zIndex: 1 }}>
        <div
          className={cn("h-full min-h-0 rounded-2xl border", innerClassName)}
          style={{
            background: frontColor,
            borderColor: "var(--panel-bezel)",
            borderWidth: "var(--bezel-thickness, 3px)",
            borderRadius: "calc(var(--card-radius, 16px) - var(--inset-3, 3px))",
            boxShadow: frontBoxShadow,
            backgroundClip: "padding-box",
            ...glassStyle,
            ...innerStyle,
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

export function LayeredRefractiveCard({
  className,
  style,
  innerClassName,
  innerStyle,
  children,
  ...rest
}: Props & { wallpaperUrl?: string }) {
  const { wallpaperUrl } = useWallpaperUrl();
  return (
    <FrameCard liquidBezel shimmer tone="base"wallpaperUrl={wallpaperUrl} className={cn("rounded-2xl", className)} style={style}>
      <div className="p-[3px] rounded-2xl">
        <div className={cn("rounded-2xl", innerClassName)} style={innerStyle} {...rest}>
          {children}
        </div>
      </div>
    </surface/FrameCard>
  );
}
