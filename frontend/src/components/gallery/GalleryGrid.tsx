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

import type { GalleryItem } from "./GalleryView";

type GalleryGridProps = {
  items: GalleryItem[];
  onOpen: (item: GalleryItem) => void;
  onDelete?: (item: GalleryItem) => void;
};

export default function GalleryGrid({ items, onOpen, onDelete }: GalleryGridProps) {
  return (
    <MediaGrid className="codexifyMediaGrid--gallery">
      {items.map((item, i) => {
        const provenance = item.tag || "unclassified";
        const provenanceLabel =
          provenance.charAt(0).toUpperCase() + provenance.slice(1);
        return (
          <div key={`${item.id || item.src}-${i}`} className="relative">
            <MediaTile
              id={item.id ?? `gallery-${i}`}
              assetId={item.id}
              src={normalizeMediaUrl(item.src)}
              alt={item.prompt}
              sizeVariant="gallery-image"
              onOpen={() => onOpen(item)}
              onDeleted={() => onDelete?.(item)}
            />
            <span className="pointer-events-none absolute bottom-2 left-2 rounded-full border border-white/20 bg-black/65 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
              {provenanceLabel}
            </span>
          </div>
        );
      })}
    </MediaGrid>
  );
}
