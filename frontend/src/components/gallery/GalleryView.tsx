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

type GallerySourceFilter = "all" | "uploaded" | "generated";

// ──────── Demo Gallery Items ────────
const DEMO_GALLERY_ITEMS: GalleryItem[] = [
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g1' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%23ff6b6b;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%23ee5a6f;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g1)'/%3E%3C/svg%3E",
    prompt: "Demo: Warm Gradient",
    tag: "demo",
  },
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g2' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%234c2a7d;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%236d28d9;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g2)'/%3E%3C/svg%3E",
    prompt: "Demo: Deep Purple",
    tag: "demo",
  },
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g3' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%2360a5fa;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%233b82f6;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g3)'/%3E%3C/svg%3E",
    prompt: "Demo: Cool Blue",
    tag: "demo",
  },
  {
    src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256'%3E%3Cdefs%3E%3ClinearGradient id='g4' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%2310b981;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%23059669;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='256' height='256' fill='url(%23g4)'/%3E%3C/svg%3E",
    prompt: "Demo: Fresh Green",
    tag: "demo",
  },
];

type Props = {
  items?: GalleryItem[];
  onSelect: (prompt: string) => void;
};

function readStoredGeneralProjectId(): string | null {
  if (typeof window === "undefined") return null;
  const candidates = [
    window.localStorage.getItem("cfy.generalProjectId"),
    window.localStorage.getItem("cfy.defaultProjectId"),
  ];
  for (const raw of candidates) {
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed > 0) {
      return String(parsed);
    }
  }
  return null;
}

const GalleryView: React.FC<Props> = ({ items: propItems = [], onSelect }) => {
  const ctx = useContext(ProjectContext);
  const projectId = ctx?.projectId ?? readStoredGeneralProjectId();

  const [showDemoGallery, setShowDemoGallery] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem("cfy.hideMockGallery") !== "1";
  });

  const [backendImages, setBackendImages] = useState<GalleryItem[]>([]);
  const [deletedKeys, setDeletedKeys] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showImageGen, setShowImageGen] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<GallerySourceFilter>("all");
  const [refreshVersion, setRefreshVersion] = useState(0);
  const activeThreadId = useMemo(() => {
    if (typeof window === "undefined") return null;
    const match = window.location.pathname.match(/\/chat\/(\d+)/i);
    if (!match) return null;
    const parsed = Number(match[1]);
    return Number.isFinite(parsed) ? parsed : null;
  }, []);

  // Fetch images from backend on mount
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    const requestedTags =
      sourceFilter === "all"
        ? (["uploaded", "generated", "unclassified"] as const)
        : ([sourceFilter] as const);
    Promise.all(
      requestedTags.map(async (requestedTag) => {
        const params = new URLSearchParams();
        params.set("tag", requestedTag);
        params.set("limit", "100");
        if (sourceFilter !== "all" && projectId !== null) {
          params.set("project_id", String(projectId));
        }
        const response = await fetch(
          `/api/media/images?${params.toString()}`,
          buildAuthenticatedFetchInit({ method: "GET" })
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        return Array.isArray(data.images)
          ? data.images
              .map((img: any) => {
                const tag =
                  img.source_tag ||
                  img.tag ||
                  requestedTag;
                return {
                  id: img.id,
                  src: resolveMediaAssetSrc(img),
                  prompt: img.filename || "Untitled",
                  project: img.project_id,
                  tag,
                } satisfies GalleryItem;
              })
              .filter((img: GalleryItem) => Boolean(img.src))
          : [];
      })
    )
      .then((groups) => {
        if (cancelled) return;
        const deduped = new Map<string, GalleryItem>();
        for (const image of groups.flat()) {
          const key = image.id ? `id:${image.id}` : `src:${image.src}`;
          if (!deduped.has(key)) deduped.set(key, image);
        }
        setBackendImages(Array.from(deduped.values()));
      })
      .catch(() => {
        if (!cancelled) setBackendImages([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, refreshVersion, sourceFilter]);

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
          tag: item?.tag || item?.source_tag || "unclassified",
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

  useEffect(() => {
    if (typeof window === "undefined") return;
    const refresh = () => setRefreshVersion((value) => value + 1);
    window.addEventListener("cfy:gallery:refresh", refresh);
    return () => window.removeEventListener("cfy:gallery:refresh", refresh);
  }, []);

  // Merge prop items with backend images
  const allItems = useMemo(
    () => [...propItems, ...backendImages],
    [propItems, backendImages]
  );

  // Filter by source tag and project when selected.
  const visible = useMemo(() => {
    const tagFiltered =
      sourceFilter === "all"
        ? allItems
        : allItems.filter(
            (item) => (item.tag || "unclassified") === sourceFilter
          );
    const projectFiltered = projectId && sourceFilter !== "all"
      ? tagFiltered.filter(
          (item) => String(item.project || "") === String(projectId)
        )
      : tagFiltered;
    return projectFiltered.filter((item) => {
      const key = item.id ? `id:${item.id}` : `src:${item.src}`;
      return !deletedKeys.includes(key);
    });
  }, [allItems, deletedKeys, projectId, sourceFilter]);

  const unclassifiedCount = useMemo(
    () =>
      visible.filter((item) => (item.tag || "unclassified") === "unclassified")
        .length,
    [visible]
  );

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
    // Only show demo items in Uploaded so All remains backend-truthful.
    if (showDemoGallery && sourceFilter === "uploaded") return DEMO_GALLERY_ITEMS;
    return [];
  }, [visible, hasRealGallery, showDemoGallery, sourceFilter]);

  const handleDelete = async (item: GalleryItem) => {
    const key = item.id ? `id:${item.id}` : `src:${item.src}`;
    setDeletedKeys((prev) => (prev.includes(key) ? prev : [...prev, key]));
    setBackendImages((prev) =>
      prev.filter((img) =>
        item.id ? img.id !== item.id : img.src !== item.src
      )
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
                onClick={() => setSourceFilter("all")}
                className={`rounded-full px-3 py-1 border ${
                  sourceFilter === "all"
                    ? "border-[var(--accent-strong)] text-[var(--text)]"
                    : "border-[var(--panel-border)] opacity-70"
                }`}
              >
                All
              </button>
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
        {sourceFilter === "all" && unclassifiedCount > 0 && (
          <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] px-3 py-2 text-xs opacity-80">
            Unclassified: {unclassifiedCount} imported {unclassifiedCount === 1 ? "asset has" : "assets have"} no provable uploaded or generated origin.
          </div>
        )}
        {!hasRealGallery && showDemoGallery && sourceFilter === "uploaded" && (
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
              onDelete={handleDelete}
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
