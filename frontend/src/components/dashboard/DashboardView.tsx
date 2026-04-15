import * as React from "react";
import { BookOpen, ChevronRight, FileText, ImagePlus } from "lucide-react";
import DocumentTile, { type DocumentFile } from "@/components/documents/DocumentTile";
import FrameCard from "@/components/surface/FrameCard";
import { Button } from "@/components/ui/button";
import { ExtColors, GalleryItem } from "@/types/ui";
import api from "@/lib/api";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import TileShell from "@/components/surface/TileShell";
import { checkAuthGate, useAuthState } from "@/lib/authState";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import ImagePreviewModal from "@/components/modals/ImagePreviewModal";
import DashboardGallery from "@/features/dashboard/components/DashboardGallery";
import { requestWorkspaceOpen } from "@/features/workspace/state/useWorkspaceState";
import { useMobileShellProfile } from "@/components/persona/layout/mobileShellProfile";

const DASHBOARDVIEW_SIGNATURE = "DashboardView.tsx (components/dashboard) signature: 2026-02-01";

const DEMO_RECENT_DOCS: string[] = [
  "Codexify Design Tokens.pdf",
  "UI Architecture Guide.md",
  "Integration Roadmap.doc",
];

function inferDocumentExtension(filename: string): string {
  const match = filename.toLowerCase().match(/\.([a-z0-9]+)$/i);
  return match?.[1] || "";
}

function getDocumentAccentColor(extColors: ExtColors, ext?: string): string {
  const normalizedExt = String(ext ?? "").trim().toLowerCase();
  return extColors[normalizedExt] ?? extColors.md ?? "#6B7280";
}

function MobileRecentDocumentRow({
  doc,
  extColors,
  onClick,
}: {
  doc: DocumentFile;
  extColors: ExtColors;
  onClick: () => void;
}) {
  const Icon = String(doc.ext ?? "").trim().toLowerCase() === "codex" ? BookOpen : FileText;
  const accentColor = getDocumentAccentColor(extColors, doc.ext);
  const rowTestId = String(doc.id ?? doc.name).trim().replace(/\s+/g, "-");
  const subtitleParts = [
    doc.ext ? `.${String(doc.ext).replace(/^\./, "").toUpperCase()}` : null,
    doc.embeddingStatus ? String(doc.embeddingStatus).trim() : null,
  ].filter(Boolean);

  return (
    <TileShell
      as="button"
      type="button"
      className="w-full cursor-pointer text-left transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
      style={{ padding: 0 }}
      onClick={onClick}
      aria-label={`Open ${doc.name} in Workspace`}
      title={`Open ${doc.name} in Workspace`}
      data-testid={`dashboard-mobile-doc-row-button-${rowTestId}`}
    >
      <div
        className="flex w-full min-w-0 items-center gap-[var(--shell-gap)] p-[var(--card-pad)]"
        data-testid={`dashboard-mobile-doc-row-${rowTestId}`}
      >
        <div
          className="flex h-[var(--doc-chip-height)] w-[var(--doc-chip-height)] shrink-0 items-center justify-center border"
          style={{
            borderRadius: "calc(var(--tile-radius) - 6px)",
            background: "color-mix(in oklab, var(--panel-bg, #111827) 82%, white 18%)",
            borderColor: "color-mix(in oklab, var(--panel-border, rgba(255,255,255,0.12)) 76%, transparent)",
          }}
        >
          <Icon className="h-5 w-5 shrink-0" style={{ color: accentColor }} />
        </div>

        <div className="min-w-0 flex-1">
          <div
            className="truncate text-sm font-semibold leading-tight"
            style={{ color: "var(--text)" }}
            title={doc.name}
          >
            {doc.name}
          </div>
          <div
            className="mt-[calc(var(--card-pad)/4)] flex flex-wrap items-center gap-[var(--pill-gap)] text-[11px]"
            style={{ color: "var(--muted)" }}
          >
            <span className="rounded-full border border-[var(--panel-border)] px-2 py-0.5">
              Open in Workspace
            </span>
            {subtitleParts.length > 0 ? (
              <span className="truncate">{subtitleParts.join(" • ")}</span>
            ) : null}
          </div>
        </div>

        <ChevronRight
          className="h-4 w-4 shrink-0"
          style={{ color: "var(--icon-muted)" }}
          aria-hidden="true"
        />
      </div>
    </TileShell>
  );
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
  extColors,
  gallery,
  onImagePrompt: _onImagePrompt,
  onRequestNewProject,
  onRequestNewThread,
  onNavigateDocuments,
  onNavigateGallery,
  threadGridRows,
}: DashboardViewProps) {
  const auth = useAuthState();
  const mobileShellProfile = useMobileShellProfile();
  const isPhoneShell = mobileShellProfile.active;
  const [pinnedThreads, setPinnedThreads] = React.useState<
    { id: string; title: string; lastMessage?: string; archivedAt?: string | null }[]
  >([]);
  const [showImgGen, setShowImgGen] = React.useState(false);
  const [recentDocs, setRecentDocs] = React.useState<DocumentFile[]>([]);
  const [previewImage, setPreviewImage] = React.useState<{
    src: string;
    alt: string;
  } | null>(null);

  const openRecentDocument = React.useCallback((doc: DocumentFile) => {
    requestWorkspaceOpen(
      { doc, source: "documents", targetView: "documents" },
      { source: "documents", targetView: "documents" }
    );
  }, []);

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
      } catch (error) {
        console.warn("[dashboard] failed to load threads", error);
        if (!cancelled) setPinnedThreads([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [auth]);

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
        const res = await api.get("/media/documents", { params: { limit: 4 } });
        const data = res?.data;

        const unwrap = (value: any): any => {
          if (!value || typeof value !== "object") return value;
          return (value as any).documents ?? (value as any).items ?? (value as any).data ?? (value as any).results ?? value;
        };

        const candidate1 = Array.isArray(data) ? data : unwrap(data);
        const candidate2 = Array.isArray(candidate1) ? candidate1 : unwrap(candidate1);
        const docs: any[] = Array.isArray(candidate2) ? candidate2 : [];

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
      } catch (error) {
        console.warn("[dashboard] failed to load documents", error);
        if (!cancelled) setRecentDocs([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [auth]);

  const openThread = React.useCallback((id: string) => {
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
  }, []);

  const rows = Math.max(1, Number.isFinite(threadGridRows) ? threadGridRows : 2);
  const threadColumns = mobileShellProfile.dashboard.threadColumns;
  const threadLimit = threadColumns * rows;
  const threadList = pinnedThreads.slice(0, threadLimit);
  const dashboardCardPadding = mobileShellProfile.dashboard.contentPadding;
  const surfaceActionClusterStyle: React.CSSProperties = {
    paddingInline: mobileShellProfile.surfaceActions.clusterPaddingX,
    paddingBlock: mobileShellProfile.surfaceActions.clusterPaddingY,
  };

  const hasRealDocs = recentDocs.length > 0;
  const docsToRender = hasRealDocs
    ? recentDocs
    : DEMO_RECENT_DOCS.map((name) => ({
        name,
        ext: inferDocumentExtension(name),
        type: "file" as const,
      }));

  const realGallery = React.useMemo(() => gallery.filter((item) => !item.mock), [gallery]);
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

  const dashboardLayoutMode = isPhoneShell ? "mobile_stack" : "desktop_split";
  const dashboardSurfaceClassName = isPhoneShell
    ? "flex min-h-0 flex-col gap-[var(--shell-gap)]"
    : "flex h-full min-h-0 gap-[var(--shell-gap)]";
  const dashboardOuterClassName = isPhoneShell
    ? "flex-1 min-h-0 overflow-auto p-[var(--board-edge)]"
    : "flex-1 min-h-0 p-[var(--board-edge)]";
  const primaryColumnClassName = isPhoneShell
    ? "flex min-h-0 flex-col gap-[var(--shell-gap)]"
    : "flex min-h-0 flex-1 flex-col gap-[var(--shell-gap)]";
  const cardFrameClassName = isPhoneShell ? "w-full min-h-[248px]" : "flex-1 min-h-[260px]";
  const cardContentClassName = "flex h-full min-h-0 flex-col gap-[var(--shell-gap)]";
  const cardHeaderClassName = isPhoneShell
    ? "flex flex-col items-start gap-[var(--card-pad)]"
    : "flex items-center justify-between gap-[var(--shell-gap)]";
  const compactButtonRowClassName = "glass-pill h-auto flex-wrap justify-start";
  const threadGridStyle = React.useMemo<React.CSSProperties>(
    () => ({
      gridTemplateColumns: `repeat(${threadColumns}, minmax(0, 1fr))`,
    }),
    [threadColumns]
  );
  const recentDocumentsGridStyle = React.useMemo<React.CSSProperties>(
    () => ({
      gridTemplateColumns:
        mobileShellProfile.dashboard.documentColumns === 1
          ? "minmax(0, 1fr)"
          : "repeat(auto-fit, 127px)",
    }),
    [mobileShellProfile.dashboard.documentColumns]
  );
  const dashboardGalleryOuterClassName = isPhoneShell
    ? "flex-1 min-h-0 overflow-visible"
    : "flex-1 min-h-0 overflow-auto pr-1";

  return (
    <section
      className="flex h-full w-full min-h-0 flex-col"
      data-dashboard-layout={dashboardLayoutMode}
      data-testid="dashboard-layout"
    >
      <div className={dashboardOuterClassName}>
        <div
          className={dashboardSurfaceClassName}
          data-layout-mode={isPhoneShell ? "mobile-stack" : "desktop-split"}
        >
          <div className={primaryColumnClassName}>
            <FrameCard
              refractiveFallback
              shimmerMode="subtle"
              className={cardFrameClassName}
            >
              <div className={cardContentClassName} style={{ padding: dashboardCardPadding }}>
                <div className={cardHeaderClassName}>
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">Recent Threads</h2>
                    <p className="text-xs leading-6 opacity-70">
                      Jump back into a conversation or spin up something new.
                    </p>
                  </div>
                  <div className={compactButtonRowClassName} style={surfaceActionClusterStyle}>
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
                    <div className="flex h-full items-center justify-center text-sm leading-6 opacity-70">
                      No threads yet. Start one above.
                    </div>
                  ) : (
                    <div className="grid h-full gap-[var(--shell-gap)]" style={threadGridStyle}>
                      {threadList.map((t) => (
                        <TileShell
                          key={t.id}
                          as="button"
                          type="button"
                          className="flex h-full w-full cursor-pointer flex-col justify-between gap-[var(--shell-gap)] px-[var(--card-pad)] py-[var(--card-pad)] text-left transition-all duration-150 ease-out hover:-translate-y-0.5 hover:bg-white/[0.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]"
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
              className={isPhoneShell ? "w-full min-h-[240px]" : "flex-1 min-h-[240px]"}
            >
              <div className={cardContentClassName} style={{ padding: dashboardCardPadding }}>
                <div className={cardHeaderClassName}>
                  <h2 className="text-lg font-semibold tracking-tight">Recent Documents</h2>
                  <Button type="button" variant="ghost" size="sm" onClick={onNavigateDocuments}>
                    See All
                  </Button>
                </div>
                {!hasRealDocs && (
                  <div className="flex items-center justify-between gap-[var(--shell-gap)] rounded-[var(--tile-radius)] border border-[var(--panel-border)] bg-[color-mix(in oklab,var(--panel-bg) 95%,transparent)] p-[var(--card-pad)]">
                    <p className="text-xs leading-6 opacity-75">
                      Demo documents. Create or upload to replace.
                    </p>
                  </div>
                )}
                <div className="flex-1 min-h-0 overflow-hidden">
                  {docsToRender.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-sm leading-6 opacity-70">
                      No documents yet. Create or upload to get started.
                    </div>
                  ) : (
                    <div
                      className={`h-full content-start justify-start gap-[var(--shell-gap)] ${
                        isPhoneShell ? "flex flex-col overflow-visible" : "grid"
                      }`}
                      style={isPhoneShell ? undefined : recentDocumentsGridStyle}
                    >
                      {docsToRender.map((d) =>
                        isPhoneShell ? (
                          <MobileRecentDocumentRow
                            key={d.id ?? d.name}
                            doc={d}
                            extColors={extColors}
                            onClick={() => openRecentDocument(d)}
                          />
                        ) : (
                          <DocumentTile
                            key={d.id ?? d.name}
                            file={d}
                            onClick={() => openRecentDocument(d)}
                            onDeleted={(deletedDoc) => {
                              if (!deletedDoc.id) return;
                              setRecentDocs((prev) =>
                                prev.filter((doc) => doc.id !== deletedDoc.id)
                              );
                            }}
                            className="dashboard-doc-tile focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
                          />
                        )
                      )}
                    </div>
                  )}
                </div>
              </div>
            </FrameCard>
          </div>

          <FrameCard
            refractiveFallback
            shimmerMode="subtle"
            className={isPhoneShell ? "w-full min-h-[336px]" : "flex-[1.15] min-h-0"}
          >
            <div className={cardContentClassName} style={{ padding: dashboardCardPadding }}>
              <div className={cardHeaderClassName}>
                <h2 className="text-lg font-semibold tracking-tight">Gallery</h2>
                <div className={`flex items-center gap-[var(--pill-gap)] ${isPhoneShell ? "flex-wrap justify-start" : ""}`}>
                  <Button type="button" variant="ghost" size="sm" onClick={() => setShowImgGen(true)}>
                    <ImagePlus className="mr-1 h-4 w-4" />
                    Generate
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={onNavigateGallery}>
                    See All
                  </Button>
                </div>
              </div>
              {!hasRealGallery && (
                <div className="flex items-center justify-between gap-[var(--shell-gap)] rounded-[var(--tile-radius)] border border-[var(--panel-border)] bg-[color-mix(in oklab,var(--panel-bg) 95%,transparent)] p-[var(--card-pad)]">
                  <p className="text-xs leading-6 opacity-75">
                    Demo gallery images. They'll disappear once you add your own.
                  </p>
                </div>
              )}
              <div className={dashboardGalleryOuterClassName}>
                {galleryToRender.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-sm leading-6 opacity-70">
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
