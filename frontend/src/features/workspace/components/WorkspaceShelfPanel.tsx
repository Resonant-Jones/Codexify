import React, { useCallback, useEffect, useState } from "react";

import DocumentTile from "@/components/documents/DocumentTile";
import PreviewTile from "@/components/ui/PreviewTile";
import { isAgentUpdatedWorkspaceItem } from "../workspaceArtifactSignals";

type MediaBase = {
  id: string;
  src_url: string;
  filename?: string;
  caption?: string;
  mime_type?: string;
  filesize?: number;
  created_at?: string;
  project_id?: string | number;
  thread_id?: string | number;
  source_tag?: string | null;
};

type DocumentItem = MediaBase;
type ImageItem = MediaBase;

type ShelfItem = { kind: "document"; item: DocumentItem } | { kind: "image"; item: ImageItem };

const WORKSPACE_SHELF_AGENT_READ_STORAGE_KEY = "cfy.workspace.shelf.agent-read.v1";

type ShelfReadState = Record<string, string>;

function loadShelfReadState(): ShelfReadState {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(WORKSPACE_SHELF_AGENT_READ_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed as ShelfReadState;
  } catch {
    return {};
  }
}

function persistShelfReadState(state: ShelfReadState) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      WORKSPACE_SHELF_AGENT_READ_STORAGE_KEY,
      JSON.stringify(state)
    );
  } catch {
    // Local persistence is best effort for this first-pass UX state.
  }
}

function getShelfItemKey(item: ShelfItem): string {
  return `${item.kind}:${item.item.id}`;
}

function getShelfItemVersion(item: MediaBase): string {
  const createdAt = String(item.created_at ?? "").trim();
  if (createdAt) return createdAt;
  const source = String(item.src_url ?? "").trim();
  if (source) return source;
  return item.id;
}

function sanitizeTestIdSegment(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]+/g, "-");
}

function getUnreadIndicatorTestId(item: ShelfItem): string {
  return `workspace-shelf-unread-${item.kind}-${sanitizeTestIdSegment(item.item.id)}`;
}

function documentItemToFile(doc: DocumentItem) {
  const name = doc.filename || "Untitled";
  const extMatch = name.match(/\.([^.]+)$/);
  const ext = extMatch ? extMatch[1].toLowerCase() : undefined;
  return {
    id: doc.id,
    name,
    ext,
    src_url: doc.src_url,
    thumb: undefined,
    type: "file" as const,
    embeddingStatus: undefined,
    embeddingError: undefined,
  };
}

function asArray<T>(resp: unknown, keys: string[]): T[] {
  if (Array.isArray(resp)) return resp as T[];
  if (resp && typeof resp === "object") {
    for (const k of keys) {
      const v = (resp as Record<string, unknown>)[k];
      if (Array.isArray(v)) return v as T[];
    }
  }
  return [];
}

function titleFor(item: MediaBase) {
  return item.filename || "Untitled";
}

function isPdf(item: MediaBase) {
  const mt = (item.mime_type || "").toLowerCase();
  const fn = (item.filename || "").toLowerCase();
  return mt.includes("pdf") || fn.endsWith(".pdf");
}

function normalizeUrl(srcUrl: string) {
  try {
    return new URL(srcUrl, window.location.origin).toString();
  } catch {
    return srcUrl;
  }
}

type WorkspaceShelfPanelProps = {
  threadIdentity?: string | number | null;
  projectId?: string | number | null;
  onItemClick?: (item: ShelfItem) => void;
};

interface ShelfState {
  documents: DocumentItem[];
  images: ImageItem[];
  loading: boolean;
  error: string | null;
  threadDocuments: DocumentItem[];
  threadImages: ImageItem[];
  projectDocuments: DocumentItem[];
  projectImages: ImageItem[];
}

export default function WorkspaceShelfPanel({
  threadIdentity,
  projectId,
  onItemClick,
}: WorkspaceShelfPanelProps) {
  const [state, setState] = useState<ShelfState>({
    documents: [],
    images: [],
    loading: false,
    error: null,
    threadDocuments: [],
    threadImages: [],
    projectDocuments: [],
    projectImages: [],
  });
  const [shelfReadState, setShelfReadState] = useState<ShelfReadState>(() =>
    loadShelfReadState()
  );

  const apiKey = (import.meta as any).env?.VITE_GUARDIAN_API_KEY as string | undefined;

  const fetchShelfData = useCallback(async () => {
    const tid = threadIdentity != null ? String(threadIdentity) : null;
    const pid = projectId != null ? String(projectId) : null;

    if (!tid && !pid) {
      setState({
        documents: [],
        images: [],
        loading: false,
        error: null,
        threadDocuments: [],
        threadImages: [],
        projectDocuments: [],
        projectImages: [],
      });
      return;
    }

    const ac = new AbortController();
    const headers: Record<string, string> = {};
    if (apiKey) headers["X-API-Key"] = apiKey;
    const base = "/api";

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const promises: Promise<unknown>[] = [];
      const queries: { key: string; qp: URLSearchParams }[] = [];

      if (tid) {
        const threadQp = new URLSearchParams({ thread_id: tid });
        queries.push({ key: "thread", qp: threadQp });
        promises.push(
          fetch(`${base}/media/documents?${threadQp.toString()}`, {
            headers,
            signal: ac.signal,
          }).then((r) => r.json())
        );
        promises.push(
          fetch(`${base}/media/images?${threadQp.toString()}`, {
            headers,
            signal: ac.signal,
          }).then((r) => r.json())
        );
      }

      if (pid && pid !== String(tid)) {
        const projectQp = new URLSearchParams({ project_id: pid });
        queries.push({ key: "project", qp: projectQp });
        promises.push(
          fetch(`${base}/media/documents?${projectQp.toString()}`, {
            headers,
            signal: ac.signal,
          }).then((r) => r.json())
        );
        promises.push(
          fetch(`${base}/media/images?${projectQp.toString()}`, {
            headers,
            signal: ac.signal,
          }).then((r) => r.json())
        );
      }

      const results = await Promise.all(promises);

      const newState: ShelfState = {
        documents: [],
        images: [],
        loading: false,
        error: null,
        threadDocuments: [],
        threadImages: [],
        projectDocuments: [],
        projectImages: [],
      };

      let idx = 0;
      for (const q of queries) {
        if (q.key === "thread") {
          const docs = asArray<DocumentItem>(results[idx], ["documents", "items", "data"]);
          const imgs = asArray<ImageItem>(results[idx + 1], ["images", "items", "data"]);
          newState.threadDocuments = docs;
          newState.threadImages = imgs;
          idx += 2;
        } else if (q.key === "project") {
          const docs = asArray<DocumentItem>(results[idx], ["documents", "items", "data"]);
          const imgs = asArray<ImageItem>(results[idx + 1], ["images", "items", "data"]);
          newState.projectDocuments = docs;
          newState.projectImages = imgs;
          idx += 2;
        }
      }

      newState.documents = [...newState.threadDocuments, ...newState.projectDocuments];
      newState.images = [...newState.threadImages, ...newState.projectImages];

      setState(newState);
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") return;
      const msg = (e as Error)?.message || "Failed to load shelf items";
      setState((prev) => ({
        ...prev,
        loading: false,
        error: msg,
        documents: [],
        images: [],
        threadDocuments: [],
        threadImages: [],
        projectDocuments: [],
        projectImages: [],
      }));
    }

    return () => ac.abort();
  }, [threadIdentity, projectId, apiKey]);

  useEffect(() => {
    fetchShelfData();
  }, [fetchShelfData]);

  useEffect(() => {
    persistShelfReadState(shelfReadState);
  }, [shelfReadState]);

  const markShelfItemAsRead = useCallback((item: ShelfItem) => {
    if (!isAgentUpdatedWorkspaceItem(item.item)) return;
    const key = getShelfItemKey(item);
    const version = getShelfItemVersion(item.item);
    setShelfReadState((previous) => {
      if (previous[key] === version) return previous;
      return { ...previous, [key]: version };
    });
  }, []);

  const hasUnreadAgentUpdate = useCallback(
    (item: ShelfItem) => {
      if (!isAgentUpdatedWorkspaceItem(item.item)) return false;
      const key = getShelfItemKey(item);
      const version = getShelfItemVersion(item.item);
      return shelfReadState[key] !== version;
    },
    [shelfReadState]
  );

  const handleItemClick = useCallback(
    (item: ShelfItem) => {
      markShelfItemAsRead(item);
      onItemClick?.(item);
    },
    [markShelfItemAsRead, onItemClick]
  );

  const renderUnreadIndicator = (item: ShelfItem) => {
    if (!hasUnreadAgentUpdate(item)) return null;
    return (
      <span
        className="pointer-events-none absolute right-2 top-2 z-10 inline-flex h-2.5 w-2.5 rounded-full border"
        style={{
          background: "var(--accent-strong)",
          borderColor: "var(--panel-bg)",
        }}
        data-testid={getUnreadIndicatorTestId(item)}
        aria-label="Unread agent update"
        title="Unread agent update"
      />
    );
  };

  const renderDocumentTile = (doc: DocumentItem) => {
    const shelfItem: ShelfItem = { kind: "document", item: doc };
    return (
      <div
      key={doc.id}
      className="relative"
      draggable
      onDragStart={(event) => {
        try {
          event.dataTransfer.setData(
            "application/x-cfy-asset",
            JSON.stringify({ kind: "document", item: doc })
          );
          event.dataTransfer.effectAllowed = "copy";
        } catch {}
      }}
    >
      {renderUnreadIndicator(shelfItem)}
      <DocumentTile
        file={documentItemToFile(doc)}
        onClick={() => handleItemClick(shelfItem)}
      />
    </div>
    );
  };

  const renderImageTile = (img: ImageItem) => {
    const shelfItem: ShelfItem = { kind: "image", item: img };
    return (
      <div
      key={img.id}
      className="relative"
      draggable
      onDragStart={(event) => {
        try {
          event.dataTransfer.setData(
            "application/x-cfy-asset",
            JSON.stringify({ kind: "image", item: img })
          );
          event.dataTransfer.effectAllowed = "copy";
        } catch {}
      }}
    >
      {renderUnreadIndicator(shelfItem)}
      <PreviewTile
        tone="panel"
        className="cursor-pointer transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 active:translate-y-0"
        onClick={() => handleItemClick(shelfItem)}
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
    </div>
    );
  };

  const hasThreadItems = state.threadDocuments.length > 0 || state.threadImages.length > 0;
  const hasProjectItems = state.projectDocuments.length > 0 || state.projectImages.length > 0;
  const hasAnyItems = hasThreadItems || hasProjectItems;

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto">
      <div className="flex items-center justify-between gap-3">
        <span
          className="text-sm font-semibold"
          style={{ color: "var(--text)" }}
        >
          Shelf
        </span>
        <span
          data-testid="workspace-shelf-status"
          className="text-[11px] font-medium"
          style={{ color: "var(--text-subtle)" }}
        >
          {state.loading
            ? "Loading…"
            : state.error
              ? "Offline"
              : `${state.documents.length} docs · ${state.images.length} images`}
        </span>
      </div>

      {state.error && (
        <div
          className="rounded-[var(--radius)] border p-3 text-xs"
          style={{
            borderColor: "var(--panel-border)",
            background: "var(--panel-bg)",
            color: "var(--muted)",
          }}
        >
          Failed to load shelf: {state.error}
        </div>
      )}

      {!state.loading && !state.error && !hasAnyItems && (
        <div
          className="rounded-[var(--radius)] border p-4 text-center text-xs"
          style={{
            borderColor: "var(--panel-border)",
            background: "var(--panel-bg)",
            color: "var(--muted)",
          }}
        >
          {threadIdentity == null && projectId == null
            ? "Select a thread or project to see linked items."
            : "No items linked to this context yet."}
        </div>
      )}

      {hasThreadItems && (
        <section>
          <div
            data-testid="workspace-shelf-thread-label"
            className="mb-2 text-[11px] font-semibold uppercase tracking-wide"
            style={{ color: "var(--text-subtle)" }}
          >
            Thread {threadIdentity ? `#${threadIdentity}` : ""}
          </div>
          {state.threadDocuments.length > 0 && (
            <div className="mb-3">
              <div className="mb-2 text-[11px] font-medium" style={{ color: "var(--text-subtle)" }}>
                Documents
              </div>
              <div className="grid grid-flow-col auto-cols-[140px] gap-2 overflow-x-auto pr-1">
                {state.threadDocuments.map(renderDocumentTile)}
              </div>
            </div>
          )}
          {state.threadImages.length > 0 && (
            <div>
              <div className="mb-2 text-[11px] font-medium" style={{ color: "var(--text-subtle)" }}>
                Images
              </div>
              <div className="grid grid-flow-col auto-cols-[140px] gap-2 overflow-x-auto pr-1">
                {state.threadImages.map(renderImageTile)}
              </div>
            </div>
          )}
        </section>
      )}

      {hasProjectItems && (
        <section>
          <div
            data-testid="workspace-shelf-project-label"
            className="mb-2 text-[11px] font-semibold uppercase tracking-wide"
            style={{ color: "var(--text-subtle)" }}
          >
            Project {projectId ? `#${projectId}` : ""}
          </div>
          {state.projectDocuments.length > 0 && (
            <div className="mb-3">
              <div className="mb-2 text-[11px] font-medium" style={{ color: "var(--text-subtle)" }}>
                Documents
              </div>
              <div className="grid grid-flow-col auto-cols-[140px] gap-2 overflow-x-auto pr-1">
                {state.projectDocuments.map(renderDocumentTile)}
              </div>
            </div>
          )}
          {state.projectImages.length > 0 && (
            <div>
              <div className="mb-2 text-[11px] font-medium" style={{ color: "var(--text-subtle)" }}>
                Images
              </div>
              <div className="grid grid-flow-col auto-cols-[140px] gap-2 overflow-x-auto pr-1">
                {state.projectImages.map(renderImageTile)}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
