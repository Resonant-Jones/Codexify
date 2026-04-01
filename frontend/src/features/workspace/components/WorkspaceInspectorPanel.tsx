import React from "react";

type DocumentItem = {
  id: string;
  filename?: string;
  src_url: string;
  caption?: string;
  mime_type?: string;
  filesize?: number;
  created_at?: string;
  project_id?: string | number;
  thread_id?: string | number;
};

type ImageItem = {
  id: string;
  src_url: string;
  filename?: string;
  caption?: string;
  created_at?: string;
  project_id?: string | number;
  thread_id?: string | number;
};

export type ShelfItem =
  | { kind: "document"; item: DocumentItem }
  | { kind: "image"; item: ImageItem };

type Props = {
  selectedItem: ShelfItem | null;
};

function formatFileSize(bytes?: number): string {
  if (bytes == null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getDocumentMeta(doc: DocumentItem) {
  const name = doc.filename || "Untitled Document";
  const extMatch = name.match(/\.([^.]+)$/);
  const ext = extMatch ? extMatch[1].toUpperCase() : null;
  const size = formatFileSize(doc.filesize);
  const created = doc.created_at
    ? new Date(doc.created_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;
  const provenance = doc.thread_id
    ? `Thread #${doc.thread_id}`
    : doc.project_id
      ? `Project #${doc.project_id}`
      : null;

  return { name, ext, size, created, provenance };
}

function getImageMeta(img: ImageItem) {
  const name = img.caption || img.filename || "Untitled Image";
  const created = img.created_at
    ? new Date(img.created_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;
  const provenance = img.thread_id
    ? `Thread #${img.thread_id}`
    : img.project_id
      ? `Project #${img.project_id}`
      : null;

  return { name, created, provenance };
}

function DocumentPreview({ item }: { item: DocumentItem }) {
  const { name, ext, size, created, provenance } = getDocumentMeta(item);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto">
      <div className="flex items-start gap-3">
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border text-xs font-semibold"
          style={{
            borderColor: "var(--panel-border)",
            background: "var(--panel-bg)",
            color: "var(--text-subtle)",
          }}
        >
          {ext || "DOC"}
        </div>
        <div className="min-w-0 flex-1">
          <h3
            className="truncate text-sm font-semibold"
            style={{ color: "var(--text)" }}
            title={name}
          >
            {name}
          </h3>
          {provenance && (
            <p
              className="text-xs"
              style={{ color: "var(--text-subtle)" }}
            >
              {provenance}
            </p>
          )}
        </div>
      </div>

      <div
        className="rounded-[var(--radius)] border p-3"
        style={{
          borderColor: "var(--panel-border)",
          background: "var(--panel-bg)",
        }}
      >
        <div className="grid grid-cols-2 gap-2 text-xs">
          {size && (
            <div>
              <span style={{ color: "var(--text-subtle)" }}>Size</span>
              <p className="font-medium" style={{ color: "var(--text)" }}>
                {size}
              </p>
            </div>
          )}
          {created && (
            <div>
              <span style={{ color: "var(--text-subtle)" }}>Added</span>
              <p className="font-medium" style={{ color: "var(--text)" }}>
                {created}
              </p>
            </div>
          )}
          {item.mime_type && (
            <div className="col-span-2">
              <span style={{ color: "var(--text-subtle)" }}>Type</span>
              <p className="font-medium" style={{ color: "var(--text)" }}>
                {item.mime_type}
              </p>
            </div>
          )}
        </div>
      </div>

      <div
        className="mt-auto rounded-[var(--radius)] border px-3 py-2 text-xs"
        style={{
          borderColor: "var(--chip-border)",
          background: "var(--chip-bg)",
          color: "var(--text-subtle)",
        }}
      >
        Lightweight preview only.
      </div>
    </div>
  );
}

export default function WorkspaceInspectorPanel({ selectedItem }: Props) {
  if (!selectedItem) {
    return (
      <div className="flex h-full min-h-0 flex-col justify-between gap-4">
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Select a document from the Shelf to preview it here.
        </p>
        <div
          className="rounded-[var(--radius-micro)] border px-3 py-2 text-xs"
          style={{
            borderColor: "var(--chip-border)",
            background: "var(--chip-bg)",
            color: "var(--text-subtle)",
          }}
        >
          Phase 1 shell only.
        </div>
      </div>
    );
  }

  if (selectedItem.kind === "document") {
    return <DocumentPreview item={selectedItem.item} />;
  }

  return (
    <div className="flex h-full min-h-0 flex-col justify-between gap-4">
      <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
        Image preview not yet available.
      </p>
      <div
        className="rounded-[var(--radius-micro)] border px-3 py-2 text-xs"
        style={{
          borderColor: "var(--chip-border)",
          background: "var(--chip-bg)",
          color: "var(--text-subtle)",
        }}
      >
        Phase 1 shell only.
      </div>
    </div>
  );
}
