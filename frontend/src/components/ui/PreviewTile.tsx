import React from "react";
import FrameCard from "@/components/surface/FrameCard";

type PreviewTileProps = {
  title?: React.ReactNode;
  snippet?: React.ReactNode;
  children?: React.ReactNode; // [title, snippet] fallback
  onClick?: () => void;
  className?: string;
  style?: React.CSSProperties;
  minHeight?: number | string; // list tiles default height
  strongRim?: boolean; // brighter outer glass ring (for image tiles)
  /** Explicit height override used by Sidebar */
  rectH?: number | string;
  /** Whether the tile is the currently‑active item (Sidebar selection). */
  active?: boolean;
  /** Styling hooks consumed by callers – no runtime effect here. */
  layer?: string;
  tone?: string;
};

/**
 * PreviewTile — ProjectTile-style thread card (two layers)
 * - Outer base: var(--chip-bg)
 * - Inset sheet: var(--panel-bg)  (same as Guardian Chat panel background)
 * - Ultra-thin frosted rim: var(--panel-border, rgba(255,255,255,0.10))
 * - Rounded corners: 19px everywhere
 * - No drop shadows
 */
export default function PreviewTile({
  title,
  snippet,
  children,
  onClick,
  className = "",
  style,
  rectH,
  active = false, // kept for API compatibility (not used yet)
  layer,          // accepted but unused
  tone,           // accepted but unused
  minHeight = 96,
  strongRim = false, // accepted but unused (FrameCard handles rim internally)
}: PreviewTileProps) {
  const effectiveMinHeight = rectH ?? minHeight;

  // Derive media vs. text‑tile intent
  const nodes = React.Children.toArray(children ?? []);
  const onlyChild = nodes.length === 1 ? nodes[0] : null;
  const isImgElement =
    !!onlyChild &&
    React.isValidElement(onlyChild) &&
    (onlyChild as any).type === "img";
  const isMedia = !title && !snippet && isImgElement;

  const resolvedTitle = title ?? (nodes.length > 0 ? nodes[0] : null);
  const resolvedSnippet = snippet ?? (nodes.length > 1 ? nodes[1] : null);

  return (
    <FrameCard
      hoverPop
      className={["relative w-full", className].join(" ")}
      style={{
        ...(isMedia
          ? { aspectRatio: "1 / 1" }
          : { minHeight: effectiveMinHeight }),
        cursor: onClick ? "pointer" : undefined,
        ...style,
      }}
      ariaLabel={
        typeof resolvedTitle === "string" ? (resolvedTitle as string) : ""
      }
      onClick={onClick}
    >
      {isMedia ? (
        React.cloneElement(onlyChild as React.ReactElement<any>, {
          className: [
            "absolute inset-0 block w-full h-full object-cover",
            (onlyChild as any).props?.className || "",
          ].join(" "),
          style: {
            borderRadius: "inherit",
            ...(onlyChild as any).props?.style,
          },
        })
      ) : (
        <div className="relative flex h-full flex-col justify-between">
          <div className="px-3 pt-3 text-left text-base font-medium truncate">
            {resolvedTitle}
          </div>
          {resolvedSnippet ? (
            <div className="px-3 pb-3 text-left text-xs opacity-70 truncate">
              {resolvedSnippet}
            </div>
          ) : (
            <div className="pb-[6px]" />
          )}
        </div>
      )}
    </FrameCard>
  );
}
