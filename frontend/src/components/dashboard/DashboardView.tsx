import * as React from "react";
import DocumentTile from "@/components/documents/DocumentTile";
import FrameCard from "@/components/surface/FrameCard";
import { Button } from "@/components/ui/button";
import { ExtColors, GalleryItem } from "@/types/ui";
import api from "@/lib/api";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { ImagePlus } from "lucide-react";
import TileShell from "@/components/surface/TileShell";
import { checkAuthGate, useAuthState } from "@/lib/authState";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import ImagePreviewModal from "@/components/modals/ImagePreviewModal";
import DashboardGallery from "@/features/dashboard/components/DashboardGallery";
import type { DocumentFile } from "@/components/documents/DocumentTile";

// Debug signature: helps confirm which DashboardView module the browser is actually running.
const DASHBOARDVIEW_SIGNATURE = "DashboardView.tsx (components/dashboard) signature: 2026-02-01";

// ──────── Demo Data ────────
const DEMO_RECENT_DOCS: string[] = [
  "Codexify Design Tokens.pdf",
  "UI Architecture Guide.md",
  "Integration Roadmap.doc",
];

function inferDocumentExtension(filename: string): string {
  const match = filename.toLowerCase().match(/\.([a-z0-9]+)$/i);
  return match?.[1] || "";
}

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

type DashboardViewProps = {
  extColors: ExtColors;
  gallery: GalleryItem[];
  onImagePrompt: (p: string) => void;
  onRequestNewProject: () => void;
  onRequestNewThread: () => void;
  onNavigateDocuments: () => void;
  onNavigateGallery: () => void;
  threadGridRows: number;
};

export default function DashboardView({
  extColors: _extColors,
  gallery,
  onImagePrompt: _onImagePrompt,
  onRequestNewProject,
  onRequestNewThread,
  onNavigateDocuments,
  onNavigateGallery,
  threadGridRows,
}: DashboardViewProps) {
  const auth = useAuthState();
  const [pinnedThreads, setPinnedThreads] = React.useState<
    { id: string; title: string; lastMessage?: string; archivedAt?: string | null }[]
  >([]);
  const [showImgGen, setShowImgGen] = React.useState(false);
  const [recentDocs, setRecentDocs] = React.useState<DocumentFile[]>([]);
  const [previewImage, setPreviewImage] = React.useState<{
    src: string;
    alt: string;
  } | null>(null);

  React.useEffect(() => {
    try {
      console.debug("[dashboard]", DASHBOARDVIEW_SIGNATURE);
    } catch {
      // ignore
    }
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    if (!checkAuthGate(auth, "threads list load")) {
      if (!cancelled) setPinnedThreads([]);
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      try {
        const res = await api.get("/chat/threads");
        const raw = (res?.data && (Array.isArray(res.data) ? res.data : res.data.threads)) || [];
        const mapped = (raw || [])
          .map((r: any) => ({
            id: String(r.id ?? r.thread_id ?? r.threadId),
            title: r.title ?? r.summary ?? "Untitled Chat",
            lastMessage: r.lastMessage ?? r.last_message ?? "",
            archivedAt: r.archived_at ?? r.archivedAt ?? null,
          }))
          .filter((t: any) => t.id && !t.archivedAt);
        if (!cancelled) setPinnedThreads(mapped);
      } catch (e) {
        console.warn("[dashboard] failed to load threads", e);
        if (!cancelled) setPinnedThreads([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth]);

  // Load recent documents from API (PCX_UI_QUIKWINS_002)
  React.useEffect(() => {
    let cancelled = false;
    if (!checkAuthGate(auth, "documents list load")) {
      if (!cancelled) setRecentDocs([]);
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      try {
        // NOTE: `api` is configured with the `/api` base; keep paths base-relative.
        // Backend route: GET /api/media/documents
        const res = await api.get("/media/documents", { params: { limit: 4 } });
        const data = res?.data;

        // Backend may return either:
        //  - an array of docs
        //  - an envelope like { documents: [...], count: number }
        //  - an envelope like { items: [...] } or { data: [...] }
        //  - an error object (e.g. { detail: [...] })
        //  - a nested envelope (proxy / wrapper)
        const unwrap = (v: any): any => {
          if (!v || typeof v !== "object") return v;
          return (v as any).documents ?? (v as any).items ?? (v as any).data ?? (v as any).results ?? v;
        };

        const candidate1 = Array.isArray(data) ? data : unwrap(data);
        const candidate2 = Array.isArray(candidate1) ? candidate1 : unwrap(candidate1);
        const docs: any[] = Array.isArray(candidate2) ? candidate2 : [];

        // Optional debug signal: helps identify weird backend shapes without crashing UI
        if (docs.length === 0 && data != null) {
          try {
            console.debug("[dashboard] documents payload shape", {
              type: typeof data,
              keys: typeof data === "object" && data ? Object.keys(data as any) : undefined,
            });
          } catch {
            // ignore
          }
        }

        const normalizedDocs = docs
          .map((d: any) => {
            const name = d?.filename || d?.name || d?.title || "Untitled";
            if (typeof name !== "string" || !name.trim()) return null;
            return {
              id: typeof d?.id === "string" ? d.id : undefined,
              name,
              ext: d?.ext || d?.extension || inferDocumentExtension(name),
              src_url:
                typeof d?.src_url === "string"
                  ? d.src_url
                  : typeof d?.srcUrl === "string"
                    ? d.srcUrl
                    : typeof d?.src === "string"
                      ? d.src
                      : typeof d?.url === "string"
                        ? d.url
                        : undefined,
              type: "file" as const,
              embeddingStatus: d?.embedding_status || d?.embeddingStatus,
              embeddingError: d?.embedding_error || d?.embeddingError,
            };
          })
          .filter((doc: DocumentFile | null): doc is DocumentFile => !!doc);

        if (!cancelled) setRecentDocs(normalizedDocs);
      } catch (e) {
        console.warn("[dashboard] failed to load documents", e);
        // Fall back to empty array (dashboard will show demo docs if enabled)
        if (!cancelled) setRecentDocs([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth]);

  const openThread = (id: string) => {
    const normalizedId = String(id ?? "").trim();
    if (!normalizedId) return;
    if (typeof window !== "undefined") {
      const url = `/chat/${encodeURIComponent(normalizedId)}`;
      try {
        window.history.pushState({}, "", url);
        window.dispatchEvent(new PopStateEvent("popstate"));
      } catch {
        window.location.href = url;
      }
    }
  };

  const rows = Math.max(1, Number.isFinite(threadGridRows) ? threadGridRows : 2);
  const threadColumns = 2;
  const threadLimit = threadColumns * rows;
  const threadList = pinnedThreads.slice(0, threadLimit);

  // Compute which docs and gallery items to show
  const hasRealDocs = recentDocs && recentDocs.length > 0;
  const docsToRender = hasRealDocs
    ? recentDocs
    : DEMO_RECENT_DOCS.map((name) => ({
        name,
        ext: inferDocumentExtension(name),
        type: "file" as const,
      }));

  const realGallery = React.useMemo(
    () => gallery.filter((item) => !item.mock),
    [gallery]
  );
  const hasRealGallery = realGallery.length > 0;
  const galleryToRender = React.useMemo(
    () =>
      hasRealGallery
        ? realGallery
        : gallery.length > 0
        ? gallery
        : DEMO_GALLERY_ITEMS,
    [gallery, hasRealGallery, realGallery]
  );

  return (
    <section className="flex h-full w-full min-h-0 flex-col">
      <div className="flex-1 min-h-0 p-[var(--board-edge)]">
        <div className="flex h-full min-h-0 gap-[var(--gutter)]">
          <div className="flex min-h-0 flex-1 flex-col gap-[var(--gutter)]">
            <FrameCard
              refractiveFallback
              shimmerMode="subtle"
              className="flex-1 min-h-[260px]"
            >
              <div className="flex h-full min-h-0 flex-col p-5 gap-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">Recent Threads</h2>
                    <p className="text-xs opacity-70">Jump back into a conversation or spin up something new.</p>
                  </div>
                  <div className="glass-pill h-auto py-[3px] px-[6px]">
                    <button
                      type="button"
                      className="pill-tab text-xs"
                      data-state="active"
                      onClick={onRequestNewThread}
                      aria-label="Create new thread"
                    >
                      New Thread
                    </button>
                    <button
                      type="button"
                      className="pill-tab text-xs"
                      onClick={onRequestNewProject}
                      aria-label="Create new project"
                    >
                      New Project
                    </button>
                  </div>
                </div>
                <div className="relative flex-1 min-h-0">
                  {threadList.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-sm opacity-70">
                      No threads yet. Start one above.
                    </div>
                  ) : (
                    <div className="grid h-full grid-cols-2 gap-[var(--gutter)]">
                      {threadList.map((t) => (
                        <TileShell
                          key={t.id}
                          as="button"
                          type="button"
                          className="flex h-full w-full cursor-pointer flex-col justify-between gap-3 px-4 py-4 text-left transition-all duration-150 ease-out hover:-translate-y-0.5 hover:bg-white/[0.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]"
                          style={{
                            background:
                              "color-mix(in oklab,var(--panel-sheet,rgba(12,19,32,0.78)) 96%,transparent)",
                            borderColor: "color-mix(in oklab,var(--panel-border) 85%,transparent)",
                          }}
                          onClick={() => openThread(t.id)}
                          onKeyDown={(event) => {
                            if (event.key !== "Enter" && event.key !== " ") return;
                            event.preventDefault();
                            event.stopPropagation();
                            openThread(t.id);
                          }}
                          aria-label={`Open thread ${t.title}`}
                        >
                          <span className="text-base font-semibold truncate">{t.title}</span>
                          {t.lastMessage ? (
                            <span className="text-xs opacity-70 truncate">{t.lastMessage}</span>
                          ) : (
                            <span className="text-xs italic opacity-50">No replies yet</span>
                          )}
                        </TileShell>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </FrameCard>

            <FrameCard
              refractiveFallback
              shimmerMode="subtle"
              className="flex-1 min-h-[240px]"
            >
              <div className="flex h-full min-h-0 flex-col p-5 gap-4">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold tracking-tight">Recent Documents</h2>
                  <Button type="button" variant="ghost" size="sm" onClick={onNavigateDocuments}>
                    See All
                  </Button>
                </div>
                {!hasRealDocs && (
                  <div className="rounded-[var(--tile-radius)] bg-[color-mix(in oklab,var(--panel-bg) 95%,transparent)] border border-[var(--panel-border)] p-3 flex items-center justify-between gap-3">
                    <p className="text-xs opacity-75">Demo documents. Create or upload to replace.</p>
                  </div>
                )}
                <div className="flex-1 min-h-0 overflow-hidden">
                  {docsToRender.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-sm opacity-70">
                      No documents yet. Create or upload to get started.
                    </div>
                  ) : (
                    <div
                      className="grid h-full content-start justify-start gap-[var(--gutter)]"
                      style={{ gridTemplateColumns: "repeat(auto-fit, 127px)" }}
                    >
                      {docsToRender.map((d) => (
                        <DocumentTile
                          key={d.id ?? d.name}
                          file={d}
                          onDeleted={(deletedDoc) => {
                            if (!deletedDoc.id) return;
                            setRecentDocs((prev) =>
                              prev.filter((doc) => doc.id !== deletedDoc.id)
                            );
                          }}
                          className="dashboard-doc-tile focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </FrameCard>
          </div>

          <FrameCard
            refractiveFallback
            shimmerMode="subtle"
            className="flex-[1.15] min-h-0"
          >
            <div className="flex h-full min-h-0 flex-col p-5 gap-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold tracking-tight">Gallery</h2>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="ghost" size="sm" onClick={() => setShowImgGen(true)}>
                    <ImagePlus className="h-4 w-4 mr-1" />
                    Generate
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={onNavigateGallery}>
                    See All
                  </Button>
                </div>
              </div>
              {!hasRealGallery && (
                <div className="rounded-[var(--tile-radius)] bg-[color-mix(in oklab,var(--panel-bg) 95%,transparent)] border border-[var(--panel-border)] p-3 flex items-center justify-between gap-3">
                  <p className="text-xs opacity-75">Demo gallery images. They'll disappear once you add your own.</p>
                </div>
              )}
              <div className="flex-1 min-h-0 overflow-auto pr-1">
                {galleryToRender.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-sm opacity-70">
                    No gallery images yet. Generate or upload to get started.
                  </div>
                ) : (
                  <DashboardGallery
                    items={galleryToRender}
                    onOpenPreview={(item) =>
                      setPreviewImage({
                        src: normalizeMediaUrl(item.src),
                        alt: item.prompt || "Gallery image",
                      })
                    }
                    onAddToThread={(item) =>
                      _onImagePrompt(item.prompt || normalizeMediaUrl(item.src))
                    }
                  />
                )}
              </div>
            </div>
          </FrameCard>
        </div>
      </div>
      <ImageGenModal open={showImgGen} onOpenChange={setShowImgGen} />
      <ImagePreviewModal
        open={!!previewImage}
        src={previewImage?.src}
        alt={previewImage?.alt}
        onOpenChange={(next) => {
          if (!next) setPreviewImage(null);
        }}
      />
    </section>
  );
}
