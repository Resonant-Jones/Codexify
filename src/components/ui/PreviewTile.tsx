import * as React from "react";
import LayeredCard from "@/components/ui/LayeredCard";
import { CardContent } from "@/components/ui/card";

// Simple helper to merge classNames without adding a dependency
function mergeClass(a?: string, b?: string) {
  return [a, b].filter(Boolean).join(" ");
}

type PreviewTileProps = React.PropsWithChildren<{
  active?: boolean;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
  tone?: "chat" | "panel" | "neutral";
  /**
   * When true, renders a square media tile.
   * The child will be forced to fill the square (object-cover).
   */
  square?: boolean;
  /**
   * Simplify the inner bezel: in square mode, bezel="simple" drops the inner
   * border and shadow so media can go truly edge-to-edge inside the 3px outer rim.
   */
  bezel?: "default" | "simple";
  /**
   * Compact padding for non-square text tiles (tight vertical rhythm for pinned).
   */
  compact?: boolean;
  /**
   * Render without the LayeredCard two-layer chrome. Keeps a 3px internal rim
   * but drops the occlusion/back-plate. Useful for gallery/doc tiles.
   */
  layer?: "layered" | "flat";
  /**
   * Optional outer drop shadow on the 3px rim.
   */
  elevation?: "none" | "sm" | "md" | "lg";
  /**
   * Optional inner glass bevel overlay (inset highlight/shade).
   * "soft" = subtle highlight/shade, "crisp" = 1px white rim + stronger bottom shade.
   */
  bevel?: "none" | "soft" | "crisp" | "chunky";
  /** Optional simplified ornamental rim on the 3px outer ring. */
  ornate?: boolean;
  /** Custom min height for non-square tiles (default 88; use 60 for Threads). */
  rectH?: number;
}>; 

export default function PreviewTile({
  active,
  className,
  style,
  onClick,
  tone,
  children,
  square = false,
  bezel = "default",
  compact = false,
  layer = "layered",
  elevation = "none",
  bevel = "none",
  ornate = false,
  rectH = 88,
}: PreviewTileProps) {
  // Map semantic tones to LayeredCard tones without changing LayeredCard API
  const layerTone: "base" | "sheet" | "floating" | "merge" | undefined =
    tone === "panel" ? "sheet" : tone === "chat" ? "base" : undefined;

  const ringStyle = active
    ? ({ boxShadow: "inset 0 0 0 2px var(--accent-strong)" } as React.CSSProperties)
    : undefined;

  const elevationClass =
    elevation === "lg" ? "shadow-lg shadow-black/30" :
    elevation === "md" ? "shadow-md shadow-black/25" :
    elevation === "sm" ? "shadow-sm" : "";

  if (layer === "flat") {
    return (
      <div className={mergeClass("rounded-2xl", className)} onClick={onClick} style={ringStyle}>
        <div
          className={mergeClass("p-[3px] rounded-2xl", elevationClass) + " transition-shadow"}
          style={{ background: "var(--chip-bg)", boxShadow: ornate ? "inset 0 1px 0 var(--bezel-highlight), inset 0 -2px 0 var(--bezel-shadow)" : undefined }}
        >
          <div
            className={
              square
                ? bezel === "simple"
                  ? "relative rounded-xl aspect-square overflow-hidden"
                  : "relative rounded-xl border aspect-square overflow-hidden"
                : mergeClass(
                    "rounded-xl border px-3 shadow-sm",
                    compact ? "py-1.5" : "py-2.5"
                  )
            }
            style={{
              background: "var(--chip-bg)",
              borderColor: bezel === "simple" && square ? undefined : "var(--panel-border)",
              color: "var(--text)",
              boxShadow: bezel === "simple" && square ? undefined : "var(--elevation-shadow-front)",
              minHeight: !square ? rectH : undefined,
              ...style,
            }}
          >
            {bevel !== "none" && (
              <div
                aria-hidden
                className="pointer-events-none absolute inset-0 rounded-[inherit] z-[1]"
                style={{
                  boxShadow:
                    bevel === "chunky"
                      ? "inset 0 0 0 3px rgba(255,255,255,0.90), inset 0 -2px 0 rgba(0,0,0,0.28)"
                      : bevel === "crisp"
                      ? "inset 0 0 0 1px rgba(255,255,255,0.90), inset 0 -1px 0 rgba(0,0,0,0.35)"
                      : "inset 0 1px 0 rgba(255,255,255,0.75), inset 0 -1px 0 rgba(0,0,0,0.18)",
                }}
              />
            )}
            {square ? (
              <div className="relative w-full h-full">
                {React.isValidElement(children) ? (
                  React.cloneElement(children as React.ReactElement<any>, {
                    className: mergeClass(
                      (children as any).props?.className,
                      "absolute inset-0 w-full h-full object-cover block"
                    ),
                  })
                ) : (
                  <div className="absolute inset-0 grid place-items-center">{children}</div>
                )}
              </div>
            ) : (
              children
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <LayeredCard
      tone={layerTone}
      className={className}
      // OUTER wrapper contributes intrinsic height even though LayeredCard's inner layers are absolute
      style={{ ...(square ? {} : { minHeight: 96 }), ...ringStyle }}
      onClick={onClick}
    >
      {/* 3px internal rim always */}
      <CardContent className="p-[3px]" style={{ background: "var(--chip-bg)", boxShadow: ornate ? "inset 0 1px 0 var(--bezel-highlight), inset 0 -2px 0 var(--bezel-shadow)" : undefined }}>
        <div
          className={
            square
              ? bezel === "simple"
                ? "relative rounded-xl aspect-square overflow-hidden"
                : "relative rounded-xl border aspect-square overflow-hidden"
              : mergeClass(
                  "rounded-xl border px-3 shadow-sm",
                  compact ? "py-1.5" : "py-2.5"
                )
          }
          style={{
            background: "var(--chip-bg)",
            borderColor: bezel === "simple" && square ? undefined : "var(--panel-border)",
            color: "var(--text)",
            boxShadow: bezel === "simple" && square ? undefined : "var(--elevation-shadow-front)",
            minHeight: !square ? rectH : undefined,
            ...style,
          }}
        >
          {bevel !== "none" && (
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-[inherit] z-[1]"
              style={{
                boxShadow:
                  bevel === "chunky"
                    ? "inset 0 0 0 3px rgba(255,255,255,0.90), inset 0 -2px 0 rgba(0,0,0,0.28)"
                    : bevel === "crisp"
                    ? "inset 0 0 0 1px rgba(255,255,255,0.90), inset 0 -1px 0 rgba(0,0,0,0.35)"
                    : "inset 0 1px 0 rgba(255,255,255,0.75), inset 0 -1px 0 rgba(0,0,0,0.18)",
              }}
            />
          )}
          {square ? (
            <div className="relative w-full h-full">
              {React.isValidElement(children) ? (
                React.cloneElement(children as React.ReactElement<any>, {
                  className: mergeClass(
                    (children as any).props?.className,
                    "absolute inset-0 w-full h-full object-cover block"
                  ),
                })
              ) : (
                <div className="absolute inset-0 grid place-items-center">{children}</div>
              )}
            </div>
          ) : (
            children
          )}
        </div>
      </CardContent>
    </LayeredCard>
  );
}
