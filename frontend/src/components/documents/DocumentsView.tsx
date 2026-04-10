import React, { useMemo } from "react";
import { BookOpen, ChevronRight, FileText } from "lucide-react";

import DocumentTile from "@/components/documents/DocumentTile";
import useUploader from "@/hooks/useUploader";
import { requestWorkspaceOpen } from "@/features/workspace/state/useWorkspaceState";
import TileShell from "@/components/surface/TileShell";
import { DocumentLike, type DocumentScope } from "@/types/documents";
import { ExtColors } from "@/types/ui";
import { useMobileShellProfile } from "@/components/persona/layout/mobileShellProfile";
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

function getDocumentAccentColor(extColors: ExtColors, ext?: string): string {
  const normalizedExt = String(ext ?? "").trim().toLowerCase();
  return extColors[normalizedExt] ?? extColors.md ?? "#6B7280";
}

type MobileDocumentRowProps = {
  doc: DocumentLike;
  extColors: ExtColors;
  onClick: () => void;
};

function MobileDocumentRow({
  doc,
  extColors,
  onClick,
}: MobileDocumentRowProps) {
  const Icon = doc.type === "codex_entry" ? BookOpen : FileText;
  const accentColor = getDocumentAccentColor(extColors, doc.ext);
  const rowTestId = String(doc.id ?? doc.title).trim().replace(/\s+/g, "-");
  const subtitleParts = [
    doc.ext ? `.${String(doc.ext).replace(/^\./, "").toUpperCase()}` : null,
    doc.embeddingStatus ? String(doc.embeddingStatus).trim() : null,
  ].filter(Boolean);

  return (
    <TileShell
      as="button"
      type="button"
      className="w-full text-left cursor-pointer transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
      style={{ padding: 0 }}
      onClick={onClick}
      aria-label={`Open ${doc.title} in Workspace`}
      title={`Open ${doc.title} in Workspace`}
      data-testid={`documents-mobile-row-button-${rowTestId}`}
    >
      <div
        className="flex w-full min-w-0 items-center gap-[var(--shell-gap)] p-[var(--card-pad)]"
        data-testid={`documents-mobile-row-${rowTestId}`}
      >
        <div
          className="flex h-[var(--doc-chip-height)] w-[var(--doc-chip-height)] shrink-0 items-center justify-center border"
          style={{
            borderRadius: "calc(var(--tile-radius) - 6px)",
            background:
              "color-mix(in oklab, var(--panel-bg, #111827) 82%, white 18%)",
            borderColor:
              "color-mix(in oklab, var(--panel-border, rgba(255,255,255,0.12)) 76%, transparent)",
          }}
        >
          <Icon className="h-5 w-5 shrink-0" style={{ color: accentColor }} />
        </div>

        <div className="min-w-0 flex-1">
          <div
            className="truncate text-sm font-semibold leading-tight"
            style={{ color: "var(--text)" }}
            title={doc.title}
          >
            {doc.title}
          </div>
          <div
            className="mt-1 flex flex-wrap items-center gap-2 text-[11px]"
            style={{ color: "var(--muted)" }}
          >
            <span className="rounded-full border border-[var(--panel-border)] px-2 py-0.5">
              Open in Workspace
            </span>
            {subtitleParts.length > 0 ? (
              <span className="truncate">{subtitleParts.join(" • ")}</span>
            ) : null}
            {doc.mock ? (
              <span className="rounded-full border border-[var(--panel-border)] px-2 py-0.5">
                Mock
              </span>
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
  extColors,
  onOpenInThread,
  onDeleteDocument,
  defaultProjectId,
  documentScope = "project",
  onDocumentScopeChange,
  threadScopeEnabled = true,
}: DocumentsViewProps) {
  const shellViewportProfile = useShellViewportProfile();
  const mobileShellProfile = useMobileShellProfile();
  const isPhoneShell = mobileShellProfile.active;
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
    if (isPhoneShell) {
      return {
        display: "flex",
        width: "100%",
        minWidth: 0,
        minHeight: 0,
        flexDirection: "column",
        gap: "var(--shell-gap)",
        alignItems: "stretch",
        justifyContent: "flex-start",
        overflow: "visible",
        paddingBottom: "0.5rem",
      };
    }

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
  }, [isPhoneShell, shellViewportProfile.documentsGridColumns]);

  const documentsLayoutMode = isPhoneShell ? "mobile_list" : "desktop_grid";

  return (
    <section
      className="flex h-full w-full min-h-0 flex-col overflow-hidden"
      data-documents-layout={documentsLayoutMode}
      data-testid="documents-layout"
    >
      <div className="flex h-full w-full flex-col min-h-0 overflow-hidden px-[var(--card-pad)] pb-[var(--card-pad)]">
        <div
          className={`flex-shrink-0 border-b border-[var(--panel-border)] py-4 ${
            isPhoneShell
              ? "flex flex-col items-start gap-2"
              : "flex flex-wrap items-center justify-between gap-3"
          }`}
        >
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
            Documents
          </h2>
          <div
            className={`glass-pill h-auto py-[3px] px-[6px] ${
              isPhoneShell ? "w-full justify-between" : ""
            }`}
          >
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

                return (
                  <div key={key} className="relative">
                    {isPhoneShell ? (
                      <MobileDocumentRow
                        doc={d}
                        extColors={extColors}
                        onClick={() => handleDocumentClick(d)}
                      />
                    ) : (
                      <DocumentTile
                        file={{
                          name: d.title,
                          ext: d.ext,
                          embeddingStatus: d.embeddingStatus,
                          embeddingError: d.embeddingError,
                        }}
                        onClick={() => handleDocumentClick(d)}
                        onDeleted={onDeleteDocument ? () => onDeleteDocument(d) : undefined}
                        contextMenuItems={
                          d.type === "codex_entry" || !onOpenInThread
                            ? []
                            : [
                                {
                                  label: "Open in Thread",
                                  onSelect: () => onOpenInThread(d),
                                },
                              ]
                        }
                      />
                    )}
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
          className={`flex-shrink-0 border-t border-[var(--panel-border)] py-4 text-xs ${
            isPhoneShell
              ? "flex flex-col items-start gap-2"
              : "flex items-center gap-2"
          }`}
          style={{ color: "var(--muted)" }}
        >
          <div className={`flex items-center gap-2 ${isPhoneShell ? "flex-wrap" : ""}`}>
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
