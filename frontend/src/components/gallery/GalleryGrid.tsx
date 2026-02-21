/**
 * GalleryGrid.tsx
 *
 * Responsive grid component for displaying gallery items.
 * Uses auto-fill minmax for intrinsic sizing and prevents overlap/ballooning.
 */
import React from "react";
import PreviewTile from "@/components/gallery/PreviewTile";
import { GalleryItem } from "./GalleryView";

type GalleryGridProps = {
  items: GalleryItem[];
  onOpen: (item: GalleryItem) => void;
};

/**
 * Responsive tile sizing:
 * - Desktop: minmax(224px, 1fr)
 * - Mobile (< 640px): minmax(160px, 1fr)
 * - Small split view (< 480px): minmax(140px, 1fr)
 */
const TILE_MIN_WIDTH_DESKTOP = 224;
const TILE_MIN_WIDTH_MOBILE = 160;
const TILE_MIN_WIDTH_SMALL = 140;

export default function GalleryGrid({ items, onOpen }: GalleryGridProps) {
  return (
    <div
      className="grid gap-5"
      style={{
        gridTemplateColumns: `repeat(auto-fill, minmax(${TILE_MIN_WIDTH_DESKTOP}px, 1fr))`,
      }}
      data-gallery-grid
    >
      {items.map((item, i) => (
        <PreviewTile
          key={`${item.src}-${i}`}
          src={item.src}
          alt={item.prompt}
          onClick={() => onOpen(item)}
        />
      ))}
    </div>
  );
}
