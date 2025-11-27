// src/components/gallery/GalleryView.tsx
import React, { useContext, useMemo, useState } from "react";
import { ProjectContext } from "@/components/layout/ProjectContext";
import PreviewTile from "@/components/gallery/PreviewTile";
import FrameCard from "@/components/surface/FrameCard";
import { X } from "lucide-react";

export type GalleryItem = { src: string; prompt: string; project?: string };

// ──────── Demo Gallery Items ────────
const DEMO_GALLERY_ITEMS: GalleryItem[] = [
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g1' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%23ff6b6b;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%23ee5a6f;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g1)'/%3E%3C/svg%3E",
    prompt: "Demo: Warm Gradient",
  },
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g2' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%234c2a7d;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%236d28d9;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g2)'/%3E%3C/svg%3E",
    prompt: "Demo: Deep Purple",
  },
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g3' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%2360a5fa;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%233b82f6;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g3)'/%3E%3C/svg%3E",
    prompt: "Demo: Cool Blue",
  },
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g4' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%2310b981;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%23059669;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g4)'/%3E%3C/svg%3E",
    prompt: "Demo: Fresh Green",
  },
];

type Props = {
  items: GalleryItem[];
  onSelect: (prompt: string) => void;
};

const GalleryView: React.FC<Props> = ({ items, onSelect }) => {
  const ctx = useContext(ProjectContext);
  const projectId = ctx?.projectId ?? null;

  const [showDemoGallery, setShowDemoGallery] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem("cfy.hideMockGallery") !== "1";
  });

  const visible = useMemo(
    () => (projectId ? items.filter((i) => i.project === projectId) : items),
    [items, projectId]
  );

  // Compute which gallery items to show
  const hasRealGallery = visible && visible.length > 0;
  const galleryToRender = useMemo(
    () => (hasRealGallery ? visible : showDemoGallery ? DEMO_GALLERY_ITEMS : []),
    [visible, hasRealGallery, showDemoGallery]
  );

  const tileSize = 224;

  return (
    <div className="h-full w-full p-[var(--board-edge)]">
      <FrameCard
        refractiveFallback
        shimmerMode="subtle"
        className="flex h-full w-full flex-col gap-4 px-[var(--card-pad)] py-[var(--card-pad)]"
        style={{ color: "var(--text)" }}
      >
        <div className="flex items-center justify-between border-b border-[var(--panel-border)] pb-3">
          <div className="text-lg font-semibold">Gallery</div>
        </div>
        {!hasRealGallery && showDemoGallery && (
          <div className="rounded-[var(--tile-radius,19px)] bg-[color-mix(in oklab,var(--panel-bg) 95%,transparent)] border border-[var(--panel-border)] p-3 flex items-center justify-between gap-3">
            <p className="text-xs opacity-75">Demo gallery images. They'll disappear once you add your own.</p>
            <button
              type="button"
              onClick={() => {
                setShowDemoGallery(false);
                window.localStorage.setItem("cfy.hideMockGallery", "1");
              }}
              className="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Dismiss demo gallery"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="flex-1 min-h-0 overflow-auto pb-1">
          {galleryToRender.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm opacity-70">
              No gallery images yet. Generate or upload to get started.
            </div>
          ) : (
            <div
              className="grid justify-start gap-5"
              style={{
                gridTemplateColumns: `repeat(auto-fill, minmax(${tileSize}px, 1fr))`,
              }}
            >
              {galleryToRender.map((item, i) => (
                <PreviewTile
                  key={`${item.src}-${i}`}
                  src={item.src}
                  alt={item.prompt}
                  onClick={() => onSelect(item.prompt)}
                  style={{ minHeight: tileSize }}
                />
              ))}
            </div>
          )}
        </div>
      </FrameCard>
    </div>
  );
};

export default GalleryView;
