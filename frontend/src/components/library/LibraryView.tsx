import React, { useEffect, useMemo, useState } from "react";
import type { GalleryItem } from "@/components/gallery/GalleryView";
import GalleryGrid from "@/components/gallery/GalleryGrid";
import DocumentsView from "@/components/documents/DocumentsView";
import DocumentTile from "@/components/documents/DocumentTile";
import {
  buildLibraryResourceProjection,
  LIBRARY_FILTERS,
  type LibraryFilter,
  type LibraryResource,
  type LibraryResourceProjection,
} from "@/components/library/libraryResourceProjection";
import {
  requestWorkspaceOpen,
} from "@/features/workspace/state/useWorkspaceState";
import useUploader from "@/hooks/useUploader";
import type { DocumentLike } from "@/types/documents";
import type { ExtColors } from "@/types/ui";
import type { DocumentsScope } from "@/components/documents/documentScopeProjection";

export const LIBRARY_FILTER_LABELS: Record<LibraryFilter, string> = {
  all: "All",
  images: "Images",
  documents: "Documents",
  widgets: "Widgets",
};

type LibraryViewProps = {
  scope: DocumentsScope;
  extColors: ExtColors;
  onOpenInThread?: (doc: DocumentLike) => void;
  onDeleteDocument?: (doc: DocumentLike) => void;
  onImageSelect?: (prompt: string) => void;
};

function resourceExtension(resource: LibraryResource): string {
  const filename = resource.filename ?? "";
  const filenameMatch = filename.match(/\.([a-z0-9]+)$/i);
  if (filenameMatch?.[1]) return filenameMatch[1].toLowerCase();
  const mimeMatch = resource.mimeType?.match(/\/([a-z0-9.+-]+)$/i);
  return mimeMatch?.[1]?.split("+")[0]?.toLowerCase() || "md";
}

function toDocumentLike(resource: LibraryResource): DocumentLike {
  return {
    ...(resource.raw as Record<string, unknown>),
    id: resource.sourceId,
    name: resource.filename ?? resource.title,
    title: resource.title,
    ext: resourceExtension(resource),
    type: "file",
    src_url: resource.srcUrl ?? undefined,
    srcUrl: resource.srcUrl ?? undefined,
    artifactType:
      resource.sourceFamily === "generated_document" ? "generated" : "uploaded",
    projectId: resource.projectId ?? undefined,
    threadIds: [...resource.threadIds],
    sourceTag: resource.sourceTag,
    createdAt: resource.createdAt ?? undefined,
  } as DocumentLike;
}

function toGalleryItem(resource: LibraryResource): GalleryItem {
  return {
    id: resource.presentationKey,
    src: resource.srcUrl ?? "",
    prompt: resource.title,
    project: resource.projectId ?? undefined,
    tag: resource.origin,
  };
}

function ProjectionStatus({
  projection,
}: {
  projection: LibraryResourceProjection;
}) {
  if (projection.completeness.coverage === "unavailable") {
    return (
      <div
        role="status"
        aria-live="polite"
        data-testid="library-unavailable"
        className="rounded-[var(--tile-radius,19px)] border px-3 py-2 text-sm"
        style={{
          borderColor: "var(--panel-border)",
          color: "var(--muted)",
        }}
      >
        {projection.completeness.detail}
      </div>
    );
  }

  if (projection.completeness.complete) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="library-incomplete"
      className="rounded-[var(--tile-radius,19px)] border px-3 py-2 text-sm"
      style={{
        borderColor: "color-mix(in oklab, #f59e0b 55%, var(--panel-border))",
        color: "var(--text)",
      }}
    >
      Incomplete results: {projection.completeness.detail}
    </div>
  );
}

export default function LibraryView({
  scope,
  extColors,
  onOpenInThread,
  onDeleteDocument,
  onImageSelect,
}: LibraryViewProps) {
  const [filter, setFilter] = useState<LibraryFilter>("all");
  const [projection, setProjection] = useState<LibraryResourceProjection | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);

  const requestRefresh = React.useCallback(() => {
    setRefreshVersion((value) => value + 1);
  }, []);

  const uploader = useUploader({
    tag: "upload",
    projectId: scope.projectId ?? undefined,
    threadId: scope.threadId ?? undefined,
    onImages: requestRefresh,
    onDocuments: requestRefresh,
    onAnyUpload: requestRefresh,
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    void buildLibraryResourceProjection({
      filter,
      scope,
    })
      .then((nextProjection) => {
        if (!cancelled) setProjection(nextProjection);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setProjection(null);
        setLoadError(error instanceof Error ? error.message : "Failed to load Library.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filter, refreshVersion, scope.kind, scope.projectId, scope.threadId]);

  const resources = projection?.resources ?? [];
  const images = useMemo(
    () =>
      resources
        .filter((resource) => resource.resourceType === "image")
        .map(toGalleryItem),
    [resources]
  );
  const documents = useMemo(
    () =>
      resources
        .filter((resource) => resource.resourceType === "document")
        .map(toDocumentLike),
    [resources]
  );

  const openDocument = (doc: DocumentLike) => {
    requestWorkspaceOpen(
      { doc, source: "documents", targetView: "documents" },
      { source: "documents", targetView: "documents" }
    );
  };

  const deleteDocument = (doc: DocumentLike) => {
    onDeleteDocument?.(doc);
    requestRefresh();
  };

  const renderImageSurface = () => (
    <section
      aria-labelledby="library-images-heading"
      data-testid="library-images-surface"
      className="flex min-h-0 flex-1 flex-col gap-[var(--shell-gap)]"
    >
      <h2 id="library-images-heading" className="text-base font-semibold">
        Images
      </h2>
      {images.length > 0 ? (
        <div
          className="min-h-0 flex-1 overflow-auto"
          onDrop={uploader.onDrop}
          onDragOver={uploader.onDragOver}
        >
          <GalleryGrid
            items={images}
            onOpen={(item) => onImageSelect?.(item.prompt)}
            onDelete={() => requestRefresh()}
          />
        </div>
      ) : (
        <div
          className="flex min-h-[12rem] flex-1 items-center justify-center text-sm"
          style={{ color: "var(--muted)" }}
        >
          No images yet. Upload or generate an image to get started.
        </div>
      )}
      <div
        className="flex shrink-0 items-center gap-2 border-t pt-3 text-xs"
        style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
      >
        <span>Drag & drop images here, or</span>
        <button type="button" className="underline" onClick={uploader.pick}>
          choose files
        </button>
      </div>
    </section>
  );

  const renderAllSurface = () => (
    <div
      className="flex min-h-0 flex-1 flex-col gap-[var(--shell-gap)] overflow-auto"
      data-testid="library-all-surface"
    >
      {images.length > 0 && (
        <section aria-labelledby="library-all-images-heading">
          <h2 id="library-all-images-heading" className="mb-2 text-base font-semibold">
            Images
          </h2>
          <GalleryGrid
            items={images}
            onOpen={(item) => onImageSelect?.(item.prompt)}
            onDelete={() => requestRefresh()}
          />
        </section>
      )}
      {documents.length > 0 && (
        <section aria-labelledby="library-all-documents-heading">
          <h2 id="library-all-documents-heading" className="mb-2 text-base font-semibold">
            Documents
          </h2>
          <div className="grid min-w-0 grid-cols-[repeat(auto-fill,minmax(132px,1fr))] gap-[var(--shell-gap)]">
            {documents.map((doc, index) => (
              <DocumentTile
                key={resources.filter((resource) => resource.resourceType === "document")[index]?.presentationKey ?? doc.id ?? index}
                file={{
                  id: doc.id,
                  name: doc.name ?? doc.title,
                  ext: doc.ext,
                  src_url: doc.src_url,
                  srcUrl: doc.srcUrl,
                  src: doc.src,
                  url: doc.url,
                  type: doc.type,
                  artifactType: doc.artifactType,
                  provenanceLabel: doc.sourceTag ?? undefined,
                }}
                onClick={() => openDocument(doc)}
                onDeleted={() => deleteDocument(doc)}
                contextMenuItems={
                  onOpenInThread
                    ? [{ label: "Open in Thread", onSelect: () => onOpenInThread(doc) }]
                    : []
                }
              />
            ))}
          </div>
        </section>
      )}
      {images.length === 0 && documents.length === 0 && (
        <div
          className="flex min-h-[12rem] items-center justify-center text-sm"
          style={{ color: "var(--muted)" }}
        >
          No resources in this scope yet.
        </div>
      )}
      <div
        className="flex shrink-0 items-center gap-2 border-t pt-3 text-xs"
        style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
      >
        <span>Drag & drop files here, or</span>
        <button type="button" className="underline" onClick={uploader.pick}>
          choose files
        </button>
      </div>
    </div>
  );

  return (
    <section
      className="flex h-full min-h-0 w-full flex-col gap-[var(--shell-gap)] p-[var(--card-pad)]"
      data-testid="library-view"
      data-library-filter={filter}
    >
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-[var(--shell-gap)]">
        <div>
          <h1 className="text-lg font-semibold">Library</h1>
          <p className="text-xs" style={{ color: "var(--muted)" }}>
            Authorized resources in the selected scope
          </p>
        </div>
        <div
          role="tablist"
          aria-label="Library filters"
          className="flex flex-wrap gap-2"
        >
          {LIBRARY_FILTERS.map((candidate) => {
            const selected = candidate === filter;
            return (
              <button
                key={candidate}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls="library-filter-panel"
                data-testid={`library-filter-${candidate}`}
                className="rounded-full border px-3 py-1 text-xs"
                style={{
                  borderColor: selected
                    ? "var(--accent-strong)"
                    : "var(--panel-border)",
                  color: "var(--text)",
                  opacity: candidate === "widgets" ? 0.8 : 1,
                }}
                onClick={() => setFilter(candidate)}
              >
                {LIBRARY_FILTER_LABELS[candidate]}
              </button>
            );
          })}
        </div>
      </header>

      {loading && (
        <div role="status" aria-live="polite" data-testid="library-loading">
          Loading Library…
        </div>
      )}
      {loadError && (
        <div role="alert" data-testid="library-load-error">
          {loadError}
        </div>
      )}
      {projection && <ProjectionStatus projection={projection} />}

      <div
        id="library-filter-panel"
        role="tabpanel"
        aria-label={LIBRARY_FILTER_LABELS[filter]}
        className="min-h-0 flex-1 overflow-hidden"
      >
        {filter === "widgets" ? (
          <div
            className="flex h-full min-h-[12rem] items-center justify-center text-center text-sm"
            data-testid="library-widgets-unavailable"
            style={{ color: "var(--muted)" }}
          >
            <p>
              Widgets are unavailable until an authoritative persistence and
              listing mechanism exists. Nothing is synthesized here.
            </p>
          </div>
        ) : filter === "documents" ? (
          <DocumentsView
            documents={documents}
            extColors={extColors}
            onOpenInThread={onOpenInThread}
            onDeleteDocument={deleteDocument}
            projectId={scope.projectId}
            threadId={scope.threadId}
            loading={loading}
            error={loadError}
          />
        ) : filter === "images" ? (
          renderImageSurface()
        ) : (
          renderAllSurface()
        )}
      </div>
    </section>
  );
}
