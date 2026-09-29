import React, { useEffect, useRef, useState } from "react";

import { buildAuthenticatedFetchInit } from "@/lib/api";

import WorkspaceImageViewerModal, {
  clampWorkspaceImageZoom,
  useWorkspaceImageSizing,
  WorkspaceImageZoomControls,
} from "./WorkspaceImageViewerModal";
import {
  normalizeWorkspaceMediaUrl,
  type WorkspaceDocumentRecord,
  type WorkspaceImageRecord,
  type WorkspaceSelection,
} from "../workspaceSelection";

type Props = {
  selectedItem: WorkspaceSelection | null;
};

type DocumentDetailState = {
  key: string;
  item: Partial<WorkspaceDocumentRecord>;
};

function nonEmptyText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function formatFileSize(bytes?: number | null): string {
  if (bytes == null || !Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function getProvenance(item: WorkspaceDocumentRecord | WorkspaceImageRecord) {
  if (item.thread_id != null) return `Thread #${item.thread_id}`;
  if (item.project_id != null) return `Project #${item.project_id}`;
  return null;
}

function isPdf(item: WorkspaceDocumentRecord): boolean {
  const name = `${item.filename ?? ""} ${item.title ?? ""} ${item.format ?? ""}`.toLowerCase();
  return item.mime_type?.toLowerCase().includes("pdf") === true || /\.pdf\b|\bpdf\b/.test(name);
}

function getOriginalDocumentUrl(item: WorkspaceDocumentRecord): string | null {
  if (
    item.artifact_type?.toLowerCase() === "generated" ||
    item.source_tag?.toLowerCase() === "generated"
  ) {
    return null;
  }
  return normalizeWorkspaceMediaUrl(item.src_url);
}

function DocumentPreview({ item, loading }: { item: WorkspaceDocumentRecord; loading: boolean }) {
  const name = item.filename || item.title || "Untitled Document";
  const extension =
    item.format?.replace(/^\./, "").toUpperCase() ||
    item.filename?.match(/\.([^.]+)$/)?.[1]?.toUpperCase() ||
    null;
  const size = formatFileSize(item.filesize);
  const created = formatDate(item.created_at);
  const provenance = getProvenance(item);
  const originalUrl = getOriginalDocumentUrl(item);
  const content = nonEmptyText(item.content)
    ? item.content
    : nonEmptyText(item.parsed_text)
      ? item.parsed_text
      : null;
  const pdf = isPdf(item);

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col gap-3 overflow-hidden">
      <header className="flex flex-none min-w-0 items-start gap-3">
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border text-[10px] font-semibold"
          style={{
            borderColor: "var(--panel-border)",
            background: "var(--panel-bg)",
            color: "var(--text-subtle)",
          }}
          aria-hidden="true"
        >
          {extension || "DOC"}
        </div>
        <div className="min-w-0 flex-1">
          <h3
            className="truncate text-sm font-semibold"
            style={{ color: "var(--text)" }}
            title={name}
          >
            {name}
          </h3>
          <div
            className="mt-1 flex min-w-0 flex-wrap gap-x-3 gap-y-1 text-xs"
            style={{ color: "var(--text-subtle)" }}
          >
            {provenance && <span>{provenance}</span>}
            {size && <span>{size}</span>}
            {created && <span>Added {created}</span>}
            {item.mime_type && <span className="break-all">{item.mime_type}</span>}
          </div>
        </div>
        {originalUrl && (
          <a
            className="flex-none rounded-md border px-2.5 py-2 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--panel-bg)",
              color: "var(--text)",
            }}
            href={originalUrl}
            target="_blank"
            rel="noreferrer noopener"
          >
            Open original
          </a>
        )}
      </header>

      <section
        className="flex min-h-0 min-w-0 flex-1 overflow-auto rounded-md border p-3"
        style={{
          borderColor: "var(--panel-border)",
          background: "var(--panel-bg)",
          color: "var(--text)",
        }}
        aria-label="Document preview"
        data-testid="workspace-document-viewport"
      >
        {loading ? (
          <p className="text-sm" style={{ color: "var(--text-subtle)" }} role="status">
            Loading document preview…
          </p>
        ) : content ? (
          <pre
            className="m-0 min-w-0 w-full whitespace-pre-wrap break-words font-sans text-sm leading-6"
            style={{ overflowWrap: "anywhere" }}
            data-testid="workspace-document-text"
          >
            {content}
          </pre>
        ) : pdf && originalUrl ? (
          <iframe
            className="min-h-[240px] min-w-0 flex-1 border-0"
            src={originalUrl}
            title={`PDF preview: ${name}`}
            data-testid="workspace-pdf-preview"
          />
        ) : (
          <p className="text-sm" style={{ color: "var(--text-subtle)" }}>
            Preview unavailable for this document.
          </p>
        )}
      </section>
    </div>
  );
}

function ImagePreview({ item }: { item: WorkspaceImageRecord }) {
  const [zoom, setZoom] = useState(100);
  const source = normalizeWorkspaceMediaUrl(item.src_url);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">(
    source ? "loading" : "error"
  );
  const [expanded, setExpanded] = useState(false);
  const expandButtonRef = useRef<HTMLButtonElement>(null);
  const sizing = useWorkspaceImageSizing(zoom);
  const name = item.caption || item.filename || item.title || "Untitled Image";
  const created = formatDate(item.created_at);
  const provenance = getProvenance(item);
  const errorText = source
    ? "This image could not be loaded. The Shelf item is unchanged."
    : "Image preview unavailable because no safe image URL was provided.";

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col gap-3 overflow-hidden">
      <header className="flex flex-none min-w-0 items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3
            className="truncate text-sm font-semibold"
            style={{ color: "var(--text)" }}
            title={name}
          >
            {name}
          </h3>
          {(provenance || created) && (
            <div
              className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs"
              style={{ color: "var(--text-subtle)" }}
            >
              {provenance && <span>{provenance}</span>}
              {created && <span>Added {created}</span>}
            </div>
          )}
        </div>
      </header>

      <WorkspaceImageZoomControls
        zoom={zoom}
        onZoomChange={(nextZoom) => setZoom(clampWorkspaceImageZoom(nextZoom))}
        onExpand={() => setExpanded(true)}
        canExpand={status === "loaded"}
        expandButtonRef={expandButtonRef}
      />

      <div
        ref={sizing.viewportRef}
        className="flex min-h-0 min-w-0 flex-1 overflow-auto rounded-md bg-neutral-950"
        role="region"
        aria-label="Image preview viewport"
        data-testid="workspace-image-viewport"
        data-zoom={zoom}
      >
        <div style={sizing.canvasStyle}>
          {status === "error" ? (
            <p className="p-4 text-center text-sm text-white" role="alert">
              {errorText}
            </p>
          ) : (
            <img
              src={source ?? undefined}
              alt={name}
              draggable={false}
              onLoad={(event) => {
                sizing.onImageLoad(event);
                setStatus("loaded");
              }}
              onError={() => setStatus("error")}
              style={sizing.imageStyle}
            />
          )}
        </div>
      </div>

      {expanded && (
        <WorkspaceImageViewerModal
          key={`${item.id}:${item.src_url}`}
          image={item}
          zoom={zoom}
          onZoomChange={(nextZoom) => setZoom(clampWorkspaceImageZoom(nextZoom))}
          onClose={() => setExpanded(false)}
          returnFocusRef={expandButtonRef}
        />
      )}
    </div>
  );
}

export default function WorkspaceInspectorPanel({ selectedItem }: Props) {
  const [documentDetail, setDocumentDetail] = useState<DocumentDetailState | null>(null);
  const [loadingDetailKey, setLoadingDetailKey] = useState<string | null>(null);
  const document = selectedItem?.kind === "document" ? selectedItem.item : null;
  const documentKey = document ? `${document.artifact_type ?? "any"}:${document.id}` : null;
  const alreadyHasText =
    document !== null && (nonEmptyText(document.content) || nonEmptyText(document.parsed_text));

  useEffect(() => {
    if (!document || !documentKey || alreadyHasText) return;
    const controller = new AbortController();
    let active = true;
    setLoadingDetailKey(documentKey);

    const headers: Record<string, string> = {};
    const apiKey = (import.meta as any).env?.VITE_GUARDIAN_API_KEY as string | undefined;
    if (apiKey) headers["X-API-Key"] = apiKey;
    const typeQuery = document.artifact_type
      ? `?artifact_type=${encodeURIComponent(document.artifact_type)}`
      : "";

    void fetch(
      `/api/media/document-artifacts/${encodeURIComponent(document.id)}${typeQuery}`,
      buildAuthenticatedFetchInit({ headers, signal: controller.signal })
    )
      .then((response) => {
        if (!response.ok) throw new Error(`Document preview unavailable (${response.status})`);
        return response.json();
      })
      .then((payload: Partial<WorkspaceDocumentRecord>) => {
        if (payload.id != null && String(payload.id) !== document.id) {
          throw new Error("Document preview returned a different artifact");
        }
        if (active) setDocumentDetail({ key: documentKey, item: payload });
      })
      .catch((error: unknown) => {
        if ((error as Error)?.name !== "AbortError" && active) {
          setDocumentDetail({ key: documentKey, item: {} });
        }
      })
      .finally(() => {
        if (active) setLoadingDetailKey((current) => (current === documentKey ? null : current));
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [document, documentKey, alreadyHasText]);

  if (!selectedItem) {
    return (
      <div className="flex h-full min-h-0 flex-col justify-center">
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Select a document or image from the Shelf to inspect it here.
        </p>
      </div>
    );
  }

  if (selectedItem.kind === "image") {
    return (
      <ImagePreview
        key={`${selectedItem.item.id}:${selectedItem.item.src_url}`}
        item={selectedItem.item}
      />
    );
  }

  const detail = documentDetail?.key === documentKey ? documentDetail.item : null;
  const resolvedDocument: WorkspaceDocumentRecord = detail
    ? {
        ...selectedItem.item,
        ...detail,
        filename: detail.filename ?? selectedItem.item.filename,
        title: detail.title ?? selectedItem.item.title,
        format: detail.format ?? selectedItem.item.format,
        src_url: detail.src_url ?? selectedItem.item.src_url,
        content: detail.content ?? selectedItem.item.content,
        parsed_text: detail.parsed_text ?? selectedItem.item.parsed_text,
      }
    : selectedItem.item;

  return (
    <DocumentPreview
      item={resolvedDocument}
      loading={!alreadyHasText && loadingDetailKey === documentKey}
    />
  );
}
