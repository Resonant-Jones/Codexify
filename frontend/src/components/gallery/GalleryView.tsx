/**
 * GalleryView.tsx
 *
 * Renders the gallery surface and supports filtering images by source tag.
 */
import React, { useContext, useMemo, useState, useEffect } from "react";
import { ProjectContext } from "@/components/layout/ProjectContext";
import GalleryGrid from "@/components/gallery/GalleryGrid";
import FrameCard from "@/components/surface/FrameCard";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import useUploader from "@/hooks/useUploader";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { resolveMediaAssetSrc } from "@/lib/mediaUrl";
import { X } from "lucide-react";
import "@/components/gallery/gallery.css";

export type GalleryItem = {
  id?: string;
  src: string;
  prompt: string;
  project?: string | number;
  tag?: string;
};

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
  items?: GalleryItem[];
  onSelect: (prompt: string) => void;
};

const GalleryView: React.FC<Props> = ({ items: propItems = [], onSelect }) => {
  const ctx = useContext(ProjectContext);
  const projectId = ctx?.projectId ?? null;

  const [showDemoGallery, setShowDemoGallery] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem("cfy.hideMockGallery") !== "1";
  });

  const [backendImages, setBackendImages] = useState<GalleryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showImageGen, setShowImageGen] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<"uploaded" | "generated">("uploaded");
  const activeThreadId = useMemo(() => {
    if (typeof window === "undefined") return null;
    const match = window.location.pathname.match(/\/chat\/(\d+)/i);
    if (!match) return null;
    const parsed = Number(match[1]);
    return Number.isFinite(parsed) ? parsed : null;
  }, []);

  // Fetch images from backend on mount
  useEffect(() => {
    setIsLoading(true);
    const params = new URLSearchParams();
    params.set("tag", sourceFilter);
    if (projectId !== null) params.set("project_id", String(projectId));
    const qs = params.toString();
    fetch(
      `/api/media/images${qs ? `?${qs}` : ""}`,
      buildAuthenticatedFetchInit(
        { method: "GET" },
        { forceApiKey: true }
      )
    )
      .then((resp) => {
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
      })
      .then((data) => {
        // Convert backend image objects to GalleryItem format
        const images = Array.isArray(data.images)
          ? data.images.map((img: any) => ({
              id: img.id,
              src: resolveMediaAssetSrc(img),
              prompt: img.filename || "Untitled",
              project: img.project_id,
              tag: img.source_tag || img.tag || sourceFilter,
            }))
              .filter((img: GalleryItem) => !!img.src)
          : [];
        setBackendImages(images);
      })
      .catch(() => {
        // Silently fail, fall back to demo gallery
        setBackendImages([]);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [projectId, sourceFilter]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onAdd = (event: Event) => {
      const items = (event as CustomEvent).detail?.items || [];
      if (!Array.isArray(items) || items.length === 0) return;
      const additions = items
        .map((item: any) => ({
          src: resolveMediaAssetSrc(item),
          prompt: item?.prompt || item?.filename || "Generated image",
          project: item?.project || item?.project_id,
          tag: item?.tag || item?.source_tag || "uploaded",
        }))
        .filter((item: GalleryItem) => item.src);
      if (additions.length === 0) return;
      setBackendImages((prev) => {
        const seen = new Set(prev.map((entry) => entry.src));
        const next = additions.filter((entry) => !seen.has(entry.src));
        return next.length ? [...next, ...prev] : prev;
      });
    };
    window.addEventListener("cfy:gallery:add", onAdd as EventListener);
    return () =>
      window.removeEventListener("cfy:gallery:add", onAdd as EventListener);
  }, []);

  // Merge prop items with backend images
  const allItems = useMemo(
    () => [...propItems, ...backendImages],
    [propItems, backendImages]
  );

  // Filter by source tag and project when selected.
  const visible = useMemo(() => {
    const tagFiltered = allItems.filter(
      (item) => (item.tag || "uploaded") === sourceFilter
    );
    return projectId
      ? tagFiltered.filter((item) => item.project === projectId)
      : tagFiltered;
  }, [allItems, projectId, sourceFilter]);

  // Setup uploader for image uploads
  const uploader = useUploader({
    tag: "gallery",
    projectId,
    explicitAuth: true,
    onImages: (newImages) => {
      // Add newly uploaded images to the gallery
      setBackendImages((prev) => [
        ...prev,
        ...newImages.map((img: any) => ({
          id: img?.id,
          src: resolveMediaAssetSrc(img),
          prompt: img?.prompt || img?.filename || "Uploaded image",
          project: img?.project || img?.project_id,
          tag: "uploaded",
        })),
      ].filter((img) => !!img.src));
    },
    onDocuments: () => {},
    onAnyUpload: () => {
      try { localStorage.setItem("cfy.hasUserUpload", "true"); } catch {}
    },
  });

  // Compute which gallery items to show
  const hasRealGallery = visible && visible.length > 0;
  const galleryToRender = useMemo(() => {
    if (hasRealGallery) return visible;
    // Only show demo items in the uploaded tab so filters stay honest.
    if (showDemoGallery && sourceFilter === "uploaded") return DEMO_GALLERY_ITEMS;
    return [];
  }, [visible, hasRealGallery, showDemoGallery, sourceFilter]);

  const handleDelete = async (item: GalleryItem) => {
    // Try to delete from backend (if it's from backend)
    // For now, just remove from local state
    setBackendImages((prev) =>
      prev.filter((img) => img.src !== item.src)
    );
  };

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
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={() => setSourceFilter("uploaded")}
                className={`rounded-full px-3 py-1 border ${
                  sourceFilter === "uploaded"
                    ? "border-[var(--accent-strong)] text-[var(--text)]"
                    : "border-[var(--panel-border)] opacity-70"
                }`}
              >
                Uploaded
              </button>
              <button
                type="button"
                onClick={() => setSourceFilter("generated")}
                className={`rounded-full px-3 py-1 border ${
                  sourceFilter === "generated"
                    ? "border-[var(--accent-strong)] text-[var(--text)]"
                    : "border-[var(--panel-border)] opacity-70"
                }`}
              >
                Generated
              </button>
            </div>
            <button
              type="button"
              className="text-xs underline hover:opacity-80"
              onClick={() => setShowImageGen(true)}
            >
              Generate Image
            </button>
          </div>
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
        <div
          className="flex-1 min-h-0 overflow-auto pb-1"
          onDrop={uploader.onDrop}
          onDragOver={uploader.onDragOver}
        >
          {galleryToRender.length === 0 ? (
            <div className="flex h-full items-center justify-center flex-col gap-3 text-sm opacity-70">
              <div>No gallery images yet. Generate or upload to get started.</div>
              <button
                type="button"
                onClick={uploader.pick}
                className="text-xs underline hover:opacity-80"
              >
                Choose images to upload
              </button>
            </div>
          ) : (
            <GalleryGrid
              items={galleryToRender}
              onOpen={(item) => onSelect(item.prompt)}
            />
          )}
        </div>
        <div className="flex-shrink-0 flex items-center justify-between gap-2 border-t border-[var(--panel-border)] py-3 text-xs" style={{ color: "var(--muted)" }}>
          <div className="flex items-center gap-2">
            <span>Drag & drop images here, or</span>
            <button
              type="button"
              className="underline hover:opacity-80"
              onClick={uploader.pick}
            >
              upload images
            </button>
          </div>
          {isLoading && <span className="text-xs opacity-60">Loading...</span>}
        </div>
      </FrameCard>
      <ImageGenModal
        open={showImageGen}
        onOpenChange={setShowImageGen}
        projectId={projectId}
        threadId={activeThreadId}
      />
    </div>
  );
};

export default GalleryView;
