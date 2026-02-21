/**
 * MediaGrid.tsx
 *
 * Reusable responsive grid component for displaying media tiles.
 * Used by both Dashboard and Gallery for consistent layout.
 */
import React from "react";
import "./media.css";

type MediaGridProps = {
  children: React.ReactNode;
  className?: string;
};

export function MediaGrid({ children, className }: MediaGridProps) {
  return (
    <div className={`codexifyMediaGrid ${className ?? ""}`.trim()}>
      {children}
    </div>
  );
}

export default MediaGrid;
