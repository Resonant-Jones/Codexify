// src/components/gallery/GalleryView.tsx
import React, { useContext, useMemo } from "react";
import { ProjectContext } from "@/components/layout/ProjectContext";
import PreviewTile from "@/components/ui/PreviewTile";

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

  return (
    <div className="h-full w-full p-[6px]">
      <div className="flex h-full min-h-0 flex-col px-4 pt-3 pb-2">
        <div className="text-lg font-semibold mb-2" style={{ color: "var(--text)" }}>
          Gallery
        </div>
        <div className="grid flex-1 min-h-0 gap-5 content-start justify-start" style={{ gridTemplateColumns: "repeat(auto-fill, 112px)" }}>
          {visible.map((item, i) => (
            <PreviewTile key={i} tone="panel" layer="flat" square bezel="simple" elevation="md" bevel="soft" className="w-[112px] cursor-pointer" onClick={() => onSelect(item.prompt)}>
              <img src={item.src} alt={item.prompt} />
            </PreviewTile>
          ))}
        </div>
      </div>
    </div>
  );
};

export default GalleryView;
