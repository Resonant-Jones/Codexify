import React, { useContext, useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import PreviewTile from "@/components/ui/PreviewTile";
import { Button } from "@/components/ui/button";
import { ProjectContext } from "@/components/layout/ProjectContext";

export function DocChip({
  label,
  onClick,
  active = false,
  variant = "default",
  className = "",
}: {
  label: string;
  onClick?: () => void;
  active?: boolean;
  variant?: "default" | "dock";
  className?: string;
}) {
  const isDark =
    typeof window !== "undefined"
      ? document.documentElement.classList.contains("dark")
      : false;
  const ink = isDark ? "#ffffff" : "#000000";
  // Prefer simple, widely supported fallbacks so chips render consistently
  // across browsers; avoid color-mix to prevent invalid background results.
  const backPlate =
    typeof window !== "undefined"
      ? (
          getComputedStyle(document.documentElement)
            .getPropertyValue("--chip-bg")
            .trim() || "var(--chip-bg, var(--panel-bg))"
        )
      : "var(--chip-bg, var(--panel-bg))";
  const paperBg =
    typeof window !== "undefined"
      ? (
          getComputedStyle(document.documentElement)
            .getPropertyValue("--panel-bg")
            .trim() || "var(--panel-bg)"
        )
      : "var(--panel-bg)";

  // Base outer shell (beveled plate)
  const outer =
    "group w-full rounded-2xl border p-[3px] text-left appearance-none transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-white/10";
  const ring = active ? "ring-1" : "";

  // Inner face (paper) — default keeps your original shadows; dock trims padding/weight
  const innerBase =
    "rounded-xl border text-sm shadow-[0_0_18px_rgba(0,0,0,0.12),0_8px_18px_rgba(0,0,0,0.18),0_2px_6px_rgba(0,0,0,0.12),inset_0_1px_0_rgba(255,255,255,0.28),inset_0_-1px_0_rgba(0,0,0,0.08)] group-hover:shadow-[0_0_24px_rgba(0,0,0,0.14),0_12px_24px_rgba(0,0,0,0.22),0_4px_12px_rgba(0,0,0,0.16),inset_0_1px_0_rgba(255,255,255,0.30),inset_0_-1px_0_rgba(0,0,0,0.10)] group-active:shadow-[0_0_14px_rgba(0,0,0,0.12),0_6px_16px_rgba(0,0,0,0.18),0_2px_6px_rgba(0,0,0,0.14),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(0,0,0,0.08)]";
  const innerPadding = variant === "dock" ? "px-3 py-1.5" : "px-3 py-2";
  const innerRadius = variant === "dock" ? "rounded-xl" : "rounded-xl"; // same radius, different density
  const innerClasses = [innerBase, innerPadding, innerRadius].join(" ");

  return (
    <button
      onClick={onClick}
      className={[outer, ring, className].join(" ")}
      style={{ background: backPlate, borderColor: "var(--panel-bezel)" }}
    >
      <div
        className={innerClasses}
        style={{
          background: paperBg,
          borderColor: "var(--panel-bezel)",
          color: ink,
        }}
      >
        <span className="workspace-ink truncate">{label}</span>
      </div>
    </button>
  );
}

// Convenience alias for top dock chips without changing other files:
export const DockChip = (
  props: Omit<Parameters<typeof DocChip>[0], "variant">
) => <DocChip {...props} variant="dock" />;

type MediaBase = {
  id: string;
  src_url: string;
  filename?: string;
  mime_type?: string;
  created_at?: string;
  project_id?: string | number;
  thread_id?: string | number;
};

type DocumentItem = MediaBase;

type ImageItem = MediaBase & {
  caption?: string;
};

type SelectedAsset =
  | { kind: "document"; item: DocumentItem }
  | { kind: "image"; item: ImageItem };

function asArray<T>(resp: any, keys: string[]): T[] {
  if (Array.isArray(resp)) return resp as T[];
  if (resp && typeof resp === "object") {
    for (const k of keys) {
      const v = (resp as any)[k];
      if (Array.isArray(v)) return v as T[];
    }
  }
  return [];
}

function titleFor(item: MediaBase) {
  return item.filename || (item as any).name || "Untitled";
}

function isPdf(item: MediaBase) {
  const mt = (item.mime_type || "").toLowerCase();
  const fn = (item.filename || "").toLowerCase();
  return mt.includes("pdf") || fn.endsWith(".pdf");
}

function normalizeUrl(srcUrl: string) {
  // Most deployments serve media from the same origin.
  // If your dev proxy forwards /media -> backend, this “just works”.
  try {
    return new URL(srcUrl, window.location.origin).toString();
  } catch {
    return srcUrl;
  }
}

export default function WorkspacePane({
  bare = false,
  activeDoc,
  onOpenInThread,
  showPrompts = false,
  onPromptSelect,
}: {
  bare?: boolean;
  activeDoc?: string | null;
  onOpenInThread?: (doc: string) => void;
  // NOTE: kept for backwards compatibility; Workspace no longer renders a prompt gallery.
  showPrompts?: boolean;
  // NOTE: kept for backwards compatibility.
  onPromptSelect?: (prompt: string) => void;
}) {
  const { projectId } = useContext(ProjectContext);

  const isDark =
    typeof window !== "undefined"
      ? document.documentElement.classList.contains("dark")
      : false;
  const ink = isDark ? "#ffffff" : "#000000";

  // Thread id is not currently provided via context; derive from URL as a pragmatic MVP.
  const threadId = useMemo(() => {
    if (typeof window === "undefined") return null;
    const m = window.location.pathname.match(/\/chat\/(\d+)/);
    return m?.[1] || null;
  }, []);

  const apiKey = (import.meta as any).env?.VITE_GUARDIAN_API_KEY as
    | string
    | undefined;
  const base = "/api";

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [images, setImages] = useState<ImageItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selected, setSelected] = useState<SelectedAsset | null>(null);

  // Seed selection from `activeDoc` (legacy prop) if possible.
  useEffect(() => {
    if (!activeDoc) return;
    const found = documents.find(
      (d) => (d.filename || "").toLowerCase() === activeDoc.toLowerCase()
    );
    if (found) setSelected({ kind: "document", item: found });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeDoc, documents.length]);

  useEffect(() => {
    const pid = projectId ?? null;
    const tid = threadId ?? null;

    // Without a project/thread context, we can’t query meaningfully.
    if (!pid || !tid) {
      setDocuments([]);
      setImages([]);
      return;
    }

    const ac = new AbortController();
    const headers: Record<string, string> = {};
    if (apiKey) headers["X-API-Key"] = apiKey;

    async function load() {
      setLoading(true);
      setLoadError(null);
      try {
        const qp = new URLSearchParams({
          project_id: String(pid),
          thread_id: String(tid),
        });

        const [docsResp, imgsResp] = await Promise.all([
          fetch(`${base}/media/documents?${qp.toString()}`, {
            headers,
            signal: ac.signal,
          }).then((r) => r.json()),
          fetch(`${base}/media/images?${qp.toString()}`, {
            headers,
            signal: ac.signal,
          }).then((r) => r.json()),
        ]);

        const docs = asArray<DocumentItem>(docsResp, [
          "documents",
          "items",
          "data",
        ]);
        const imgs = asArray<ImageItem>(imgsResp, ["images", "items", "data"]);

        setDocuments(docs);
        setImages(imgs);
      } catch (e: any) {
        if (e?.name === "AbortError") return;
        console.warn("[workspace] failed to load media", e);
        setLoadError(e?.message || "Failed to load media");
        setDocuments([]);
        setImages([]);
      } finally {
        setLoading(false);
      }
    }

    load();
    return () => ac.abort();
  }, [projectId, threadId, apiKey]);

  const headerTitle = selected
    ? selected.kind === "image"
      ? `Workspace · Image`
      : `Workspace · Document`
    : "Workspace";

  const docCount = documents.length;
  const imgCount = images.length;

  const viewFinder = selected ? (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-2 flex items-center justify-between">
        <Button
          size="sm"
          variant="ghost"
          className="rounded-[var(--tile-radius,19px)] px-2"
          onClick={() => setSelected(null)}
          title="Back to shelf"
        >
          {/* left chevron */}
          <span className="text-lg leading-none">‹</span>
        </Button>
        <div className="min-w-0 flex-1 px-2 text-xs font-semibold opacity-80 truncate">
          {selected.kind === "image"
            ? selected.item.caption || titleFor(selected.item)
            : titleFor(selected.item)}
        </div>
        {selected.kind === "document" && onOpenInThread && (
          <Button
            size="sm"
            className="rounded-[var(--tile-radius,19px)] px-3"
            onClick={() => onOpenInThread(titleFor(selected.item))}
          >
            Open in Thread
          </Button>
        )}
      </div>

      <div className="flex-1 min-h-0 rounded-2xl border border-[var(--panel-border)] bg-[color-mix(in oklab,var(--panel-bg) 94%,transparent)] p-2 shadow-inner overflow-hidden">
        {selected.kind === "image" ? (
          <div className="h-full w-full flex items-center justify-center">
            <img
              src={normalizeUrl(selected.item.src_url)}
              alt={selected.item.caption || titleFor(selected.item)}
              className="max-h-full max-w-full object-contain rounded-xl"
            />
          </div>
        ) : (
          <div className="h-full w-full rounded-xl overflow-hidden">
            {isPdf(selected.item) ? (
              <iframe
                title={titleFor(selected.item)}
                src={normalizeUrl(selected.item.src_url)}
                className="h-full w-full"
              />
            ) : (
              <div className="h-full w-full flex items-center justify-center text-xs opacity-70">
                Unsupported document type
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  ) : (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-2 flex items-center justify-between text-sm font-semibold opacity-90">
        <span className="truncate">{headerTitle}</span>
        <span className="text-[11px] font-medium opacity-70">
          {loading
            ? "Loading…"
            : loadError
              ? "Offline"
              : `${docCount} docs · ${imgCount} images`}
        </span>
      </div>

      <div className="rounded-2xl border border-[var(--panel-border)] bg-[color-mix(in oklab,var(--panel-bg) 94%,transparent)] p-4 text-sm leading-relaxed shadow-inner">
        {loadError ? (
          <div className="text-xs opacity-80">
            Failed to load workspace media: {loadError}
          </div>
        ) : !projectId || !threadId ? (
          <div className="text-xs opacity-70">
            Workspace shelf needs an active project + thread.
          </div>
        ) : (
          <div className="text-xs opacity-70">
            Select a document or image to open it in the ViewFinder.
          </div>
        )}
      </div>

      {/* Documents shelf */}
      <div className="pt-4">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide opacity-70">
          Documents
        </div>
        {documents.length === 0 ? (
          <div className="text-xs opacity-60">No documents in this thread yet.</div>
        ) : (
          <div className="grid grid-rows-2 grid-flow-col auto-cols-[160px] gap-3 overflow-x-auto pr-1">
            {documents.map((d) => (
              <PreviewTile
                key={d.id}
                tone="panel"
                className="cursor-pointer transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 active:translate-y-0"
                onClick={() => setSelected({ kind: "document", item: d })}
              >
                <div className="min-h-[112px]">
                  <div
                    className="rounded-[10px] aspect-[4/3] flex items-center justify-center text-[11px] font-semibold"
                    style={{ background: "var(--panel-bg)" }}
                  >
                    PDF
                  </div>
                  <div className="mt-2 text-sm font-medium truncate">
                    {titleFor(d)}
                  </div>
                  <div className="text-xs opacity-70 truncate">&nbsp;</div>
                </div>
              </PreviewTile>
            ))}
          </div>
        )}
      </div>

      {/* Images shelf */}
      <div className="pt-4">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide opacity-70">
          Images
        </div>
        {images.length === 0 ? (
          <div className="text-xs opacity-60">No images in this thread yet.</div>
        ) : (
          <div className="grid grid-rows-2 grid-flow-col auto-cols-[160px] gap-3 overflow-x-auto pr-1">
            {images.map((img) => (
              <PreviewTile
                key={img.id}
                tone="panel"
                className="cursor-pointer transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 active:translate-y-0"
                onClick={() => setSelected({ kind: "image", item: img })}
              >
                <div className="min-h-[112px]">
                  <div className="rounded-[10px] aspect-[4/3] overflow-hidden">
                    <img
                      src={normalizeUrl(img.src_url)}
                      alt={img.caption || titleFor(img)}
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="mt-2 text-sm font-medium truncate">
                    {img.caption || titleFor(img)}
                  </div>
                  <div className="text-xs opacity-70 truncate">&nbsp;</div>
                </div>
              </PreviewTile>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1" />
    </div>
  );

  const content = (
    <div className="flex h-full min-h-0 flex-col p-4" style={{ color: ink }}>
      <style>{`
        :root:not(.dark) .workspace-ink { color: #000 !important; }
        .dark .workspace-ink { color: #fff !important; }
      `}</style>
      {viewFinder}
    </div>
  );

  if (bare) {
    return content;
  }

  return (
    <Card
      className="h-full min-h-0 w-[340px] shrink-0 overflow-hidden rounded-2xl border shadow-sm !text-black dark:!text-white"
      style={{
        background: "var(--panel-bg)",
        borderColor: "var(--panel-border)",
        color: ink,
      }}
    >
      <CardContent className="h-full min-h-0 p-0">{content}</CardContent>
    </Card>
  );
}
