import * as React from "react";
import DocumentPreviewTile from "@/components/ui/DocumentPreviewTile";
import FrameCard from "@/components/surface/FrameCard";
import { Button } from "@/components/ui/button";
import { ExtColors, GalleryItem } from "@/types/ui";
import api from "@/lib/api";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { ImagePlus } from "lucide-react";

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
  onImagePrompt,
  onRequestNewProject,
  onRequestNewThread,
  onNavigateDocuments,
  onNavigateGallery,
  threadGridRows,
}: DashboardViewProps) {
  const [pinnedThreads, setPinnedThreads] = React.useState<
    { id: string; title: string; lastMessage?: string; archivedAt?: string | null }[]
  >([]);
  const [showImgGen, setShowImgGen] = React.useState(false);
  const [recentDocs, setRecentDocs] = React.useState<string[]>([]);

  React.useEffect(() => {
    let cancelled = false;
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
  }, []);

  // Load recent documents from API (PCX_UI_QUIKWINS_002)
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/api/media/documents", { params: { limit: 4 } });
        const docs = res?.data || [];
        const names = docs.map((d: any) => d.filename || d.name || "Untitled");
        if (!cancelled) setRecentDocs(names);
      } catch (e) {
        console.warn("[dashboard] failed to load documents", e);
        // Fall back to empty array (no mock data)
        if (!cancelled) setRecentDocs([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const openThread = (id: string) => {
    if (typeof window !== "undefined") {
      const url = `/chat/${id}`;
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

  const galleryItems = React.useMemo(() => gallery.slice(0, 12), [gallery]);

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
                        <button
                          key={t.id}
                          className="flex flex-col justify-between gap-3 rounded-[var(--tile-radius,19px)] border border-[color-mix(in oklab,var(--panel-border) 85%,transparent)] bg-[color-mix(in oklab,var(--panel-sheet,rgba(12,19,32,0.78)) 96%,transparent)] px-4 py-4 text-left transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]"
                          onClick={() => openThread(t.id)}
                          type="button"
                        >
                          <span className="text-base font-semibold truncate">{t.title}</span>
                          {t.lastMessage ? (
                            <span className="text-xs opacity-70 truncate">{t.lastMessage}</span>
                          ) : (
                            <span className="text-xs italic opacity-50">No replies yet</span>
                          )}
                        </button>
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
                <div className="flex-1 min-h-0 overflow-hidden">
                  <div className="grid h-full grid-cols-[repeat(auto-fill,minmax(125px,1fr))] gap-[var(--gutter)] justify-items-center">
                    {recentDocs.map((d) => (
                      <DocumentPreviewTile
                        key={d}
                        file={{ name: d }}
                        className="dashboard-doc-tile focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
                      />
                    ))}
                  </div>
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
              <div className="flex-1 min-h-0 overflow-hidden">
                <div className="grid h-full grid-cols-[repeat(auto-fill,minmax(125px,1fr))] gap-[var(--gutter)]">
                  {galleryItems.map((item, index) => (
                    <button
                      key={`${item.src}-${index}`}
                      className="relative aspect-square w-full overflow-hidden rounded-[var(--tile-radius,19px)] border border-[color-mix(in oklab,var(--panel-border) 85%,transparent)] bg-[color-mix(in oklab,var(--panel-sheet,rgba(12,19,32,0.78)) 90%,transparent)] transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]"
                      onClick={() => onImagePrompt(item.prompt)}
                      aria-label={item.prompt || "Open gallery image"}
                      type="button"
                    >
                      <img src={item.src} alt={item.prompt || "Gallery image"} className="absolute inset-0 h-full w-full object-cover" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </FrameCard>
        </div>
      </div>
      <ImageGenModal open={showImgGen} onOpenChange={setShowImgGen} />
    </section>
  );
}
