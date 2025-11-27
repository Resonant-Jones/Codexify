import React from "react";
import clsx from "clsx";
import TileShell from "@/components/surface/TileShell";

type PreviewTileProps = {
  src: string;
  alt?: string;
  onClick?: () => void;
  className?: string;
  style?: React.CSSProperties;
};

export default function PreviewTile({ src, alt, onClick, className, style }: PreviewTileProps) {
  const content = (
    <div className="relative h-full w-full">
      <img src={src} alt={alt || "Gallery image"} className="absolute inset-0 h-full w-full object-cover" />
    </div>
  );

  const baseClasses = clsx(
    "relative aspect-square w-full cursor-pointer transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]",
    className
  );

  if (onClick) {
    return (
      <TileShell
        as="button"
        type="button"
        className={baseClasses}
        style={{ padding: 0, ...style }}
        onClick={onClick}
        aria-label={alt || "Open gallery image"}
      >
        {content}
      </TileShell>
    );
  }

  return (
    <TileShell className={clsx("relative aspect-square w-full", className)} style={{ padding: 0, ...style }}>
      {content}
    </TileShell>
  );
}
