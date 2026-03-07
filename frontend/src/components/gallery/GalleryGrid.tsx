/**
 * GalleryGrid.tsx
 *
 * Responsive grid component for displaying gallery items.
 * Uses shared MediaGrid and MediaTile for consistent styling with Dashboard.
 */
import React from "react";
import MediaGrid from "@/components/media/MediaGrid";
import MediaTile from "@/components/media/MediaTile";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import { GalleryItem } from "./GalleryView";

type GalleryGridProps = {
  items: GalleryItem[];
  onOpen: (item: GalleryItem) => void;
};

export default function GalleryGrid({ items, onOpen }: GalleryGridProps) {
  return (
    <MediaGrid className="codexifyMediaGrid--gallery">
      {items.map((item, i) => (
        <MediaTile
          key={`${item.src}-${i}`}
          id={item.id ?? `gallery-${i}`}
          src={normalizeMediaUrl(item.src)}
          alt={item.prompt}
          onOpen={() => onOpen(item)}
        />
      ))}
    </MediaGrid>
  );
}
