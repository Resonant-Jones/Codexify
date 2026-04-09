import React, { useMemo } from "react";

import DocumentTile from "@/components/documents/DocumentTile";
import useUploader from "@/hooks/useUploader";
import { requestWorkspaceOpen } from "@/features/workspace/state/useWorkspaceState";
import { DocumentLike, type DocumentScope } from "@/types/documents";
import { ExtColors } from "@/types/ui";
import { useShellViewportProfile } from "@/components/persona/layout/shellBreakpointContract";

interface DocumentsViewProps {
  documents: DocumentLike[];
  extColors: ExtColors;
  onOpenInThread?: (doc: DocumentLike) => void;
  onDeleteDocument?: (doc: DocumentLike) => void;
  defaultProjectId?: number | string | null;
  documentScope?: DocumentScope;
  onDocumentScopeChange?: (mode: DocumentScope) => void;
  threadScopeEnabled?: boolean;
}

/**
 * DocumentsView
 *
 * Structure:
 * - FrameCard wrapper (glass + bezel)
 *   - Header (title + scope pill)
 *   - Content area (scrollable grid of documents)
 *   - Footer (upload UI + controls)
 */
export default function DocumentsView({
  documents,
  extColors: _extColors,
  onOpenInThread,
  onDeleteDocument,
  defaultProjectId,
  documentScope = "project",
  onDocumentScopeChange,
  threadScopeEnabled = true,
}: DocumentsViewProps) {
  const shellViewportProfile = useShellViewportProfile();
  const uploader = useUploader({
    tag: "upload",
    projectId: defaultProjectId ?? undefined,
    onImages: () => {},
    onDocuments: (items) => {
      const normalized = (items || []).map((item: any, idx: number) => ({
        ...item,
        id: item?.id || item?.name || `upload-${idx}`,
        name: item?.name || item?.title || item?.filename || "Untitled",
        title: item?.title || item?.name || item?.filename || "Untitled",
        ext: item?.ext || item?.extension || "md",
        type: "file",
        projectId: item?.project_id ?? item?.projectId,
        threadId: item?.thread_id ?? item?.threadId ?? null,
      }));
      try {
        window.dispatchEvent(
          new CustomEvent("cfy:documents:add", { detail: { items: normalized } })
        );
      } catch {}
    },
    onAnyUpload: () => {
      try {
        localStorage.setItem("cfy.hasUserUpload", "true");
      } catch {}
    },
  });

  const handleDocumentClick = (doc: DocumentLike) => {
    requestWorkspaceOpen(
      { doc, source: "documents", targetView: "documents" },
      { source: "documents", targetView: "documents" }
    );
  };

  const realDocuments = useMemo(
    () => (documents ?? []).filter((doc) => !doc.mock),
    [documents]
  );
  const docItems = useMemo(
    () => (realDocuments.length > 0 ? realDocuments : (documents ?? [])),
    [documents, realDocuments]
  );

  const scopePills = [
    { key: "thread" as const, label: "Thread", disabled: !threadScopeEnabled },
    { key: "project" as const, label: "Project", disabled: false },
  ];

  const documentsGridStyle = useMemo<React.CSSProperties>(() => {
    const columns = shellViewportProfile.documentsGridColumns;
    const gridTemplateColumns =
      columns === 4
        ? "repeat(auto-fill, minmax(132px, 1fr))"
        : `repeat(${columns}, minmax(0, 1fr))`;

    return {
      display: "grid",
      width: "100%",
      minWidth: 0,
      minHeight: 0,
      gap: "var(--shell-gap)",
      gridTemplateColumns,
      gridAutoRows: "minmax(112px, auto)",
      gridAutoFlow: "row",
      alignItems: "start",
      alignContent: "start",
      justifyContent: "stretch",
      overflow: "auto",
      paddingBottom: "0.5rem",
    };
  }, [shellViewportProfile.documentsGridColumns]);

  return (
    <section className="flex h-full w-full min-h-0 flex-col overflow-hidden">
      <div className="flex h-full w-full flex-col min-h-0 overflow-hidden px-[var(--card-pad)] pb-[var(--card-pad)]">
        <div className="flex-shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--panel-border)] py-4">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
            Documents
          </h2>
          <div className="glass-pill h-auto py-[3px] px-[6px]">
            {scopePills.map(({ key, label, disabled }) => (
              <button
                key={key}
                type="button"
                className="pill-tab text-xs"
                data-state={documentScope === key ? "active" : undefined}
                disabled={disabled}
                onClick={() => {
                  if (disabled) return;
                  onDocumentScopeChange?.(key);
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div
          className="flex-1 min-h-0 overflow-auto py-4"
          style={{ overflowX: "hidden" }}
          onDrop={uploader.onDrop}
          onDragOver={uploader.onDragOver}
        >
          {docItems.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-sm opacity-70" style={{ color: "var(--muted)" }}>
                No documents yet. Drag files here or use the button below to get started.
              </div>
            </div>
          ) : (
            <div style={documentsGridStyle}>
              {docItems.map((d) => {
                const key = d.id || `${d.title}.${d.ext}`;
                const isCodex = d.type === "codex_entry";
                const contextMenuItems =
                  isCodex || !onOpenInThread
                    ? []
                    : [
                        {
                          label: "Open in Thread",
                          onSelect: () => onOpenInThread(d),
                        },
                      ];

                return (
                  <div key={key} className="relative">
                    <DocumentTile
                      file={{
                        name: d.title,
                        ext: d.ext,
                        embeddingStatus: d.embeddingStatus,
                        embeddingError: d.embeddingError,
                      }}
                      onClick={() => handleDocumentClick(d)}
                      onDeleted={onDeleteDocument ? () => onDeleteDocument(d) : undefined}
                      contextMenuItems={contextMenuItems}
                    />
                    {d.mock ? (
                      <span
                        className="absolute left-2 top-2 z-10 rounded-full px-2 py-1 text-[10px] border"
                        style={{
                          background: "rgba(255,255,255,0.2)",
                          color: "#111",
                          borderColor: "rgba(255,255,255,0.5)",
                        }}
                      >
                        Mock
                      </span>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div
          className="flex-shrink-0 flex items-center gap-2 border-t border-[var(--panel-border)] py-4 text-xs"
          style={{ color: "var(--muted)" }}
        >
          <div className="flex items-center gap-2">
            <span>Drag & drop files here, or</span>
            <button
              type="button"
              className="underline hover:opacity-80"
              onClick={uploader.pick}
            >
              choose files
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
