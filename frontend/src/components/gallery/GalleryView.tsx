// src/components/gallery/GalleryView.tsx
import React, { useContext, useMemo } from "react";
import { ProjectContext } from "@/components/layout/ProjectContext";
import PreviewTile from "@/components/ui/PreviewTile";
import FrameCard from "@/components/surface/FrameCard";

export type GalleryItem = { src: string; prompt: string; project?: string };

type Props = {
  items: GalleryItem[];
  onSelect: (prompt: string) => void;
};

const GalleryView: React.FC<Props> = ({ items, onSelect }) => {
  const ctx = useContext(ProjectContext);
  const projectId = ctx?.projectId ?? null;

  const visible = useMemo(
    () => (projectId ? items.filter((i) => i.project === projectId) : items),
    [items, projectId]
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
        <div className="flex-1 min-h-0 overflow-auto pb-1">
          <div
            className="grid justify-start gap-5"
            style={{
              gridTemplateColumns: `repeat(auto-fill, minmax(${tileSize}px, 1fr))`,
            }}
          >
            {visible.map((item, i) => (
              <PreviewTile
                key={`${item.src}-${i}`}
                className="cursor-pointer"
                rectH={tileSize}
                onClick={() => onSelect(item.prompt)}
              >
                <img src={item.src} alt={item.prompt} className="h-full w-full object-cover" />
              </PreviewTile>
            ))}
          </div>
        </div>
      </FrameCard>
    </div>
  );
};

export default GalleryView;
