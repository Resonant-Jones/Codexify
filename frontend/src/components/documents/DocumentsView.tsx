import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BookOpen, ChevronLeft, ChevronRight, FileText } from "lucide-react";

import DocumentTile from "@/components/documents/DocumentTile";
import TileShell from "@/components/surface/TileShell";
import useUploader from "@/hooks/useUploader";
import { requestWorkspaceOpen } from "@/features/workspace/state/useWorkspaceState";
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

const DOCUMENTS_RAIL_VISIBILITY_KEY = "cfy.documentsRailVisible";

function getDocumentAccentColor(extColors: ExtColors, ext?: string): string {
  const normalizedExt = String(ext ?? "").trim().toLowerCase();
  return extColors[normalizedExt] ?? extColors.md ?? "#6B7280";
}

type MobileDocumentRowProps = {
  doc: DocumentLike;
  extColors: ExtColors;
  onClick: () => void;
  contextMenuItems?: Array<{
    label: string;
    onSelect: () => void | Promise<void>;
    destructive?: boolean;
  }>;
};

function MobileDocumentRow({
  doc,
  extColors,
  onClick,
  contextMenuItems,
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
      className="w-full cursor-pointer text-left transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
      style={{ padding: 0 }}
      onClick={onClick}
      aria-label={`Open ${doc.title} in Workspace`}
      title={`Open ${doc.title} in Workspace`}
      data-testid={`documents-mobile-row-button-${rowTestId}`}
      contextMenuItems={contextMenuItems}
      contextMenuLabel={`${doc.title} actions`}
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
 * Shared active-view contract:
 * - left rail = selection / navigation
 * - center lane = primary content / action surface
 * - right panel = AppShell-managed Workspace surface
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
  const mobileShellProfile = useMobileShellProfile();
  const shellViewportProfile = useShellViewportProfile();
  const isPhoneShell = mobileShellProfile.active;
  const [isRailVisible, setIsRailVisible] = useState(() => {
    if (typeof window === "undefined") {
      return !isPhoneShell;
    }
    const stored = window.localStorage.getItem(DOCUMENTS_RAIL_VISIBILITY_KEY);
    if (stored == null) {
      return !isPhoneShell;
    }
    return stored === "true";
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(
        DOCUMENTS_RAIL_VISIBILITY_KEY,
        String(isRailVisible)
      );
    } catch {
      /* ignore */
    }
  }, [isRailVisible]);

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
      } catch {
        /* ignore */
      }
    },
    onAnyUpload: () => {
      try {
        localStorage.setItem("cfy.hasUserUpload", "true");
      } catch {
        /* ignore */
      }
    },
  });

  const handleDocumentClick = useCallback(
    (doc: DocumentLike) => {
      requestWorkspaceOpen(
        { doc, source: "documents", targetView: "documents" },
        { source: "documents", targetView: "documents" }
      );
    },
    []
  );

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
    if (mobileShellProfile.documents.layout === "list") {
      return {
        display: "flex",
        width: "100%",
        minWidth: 0,
        minHeight: 0,
        flexDirection: "column",
        gap: mobileShellProfile.documents.contentGap,
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
  }, [mobileShellProfile.documents.contentGap, mobileShellProfile.documents.layout, shellViewportProfile.documentsGridColumns]);

  const documentsLayoutMode = isPhoneShell ? "mobile_list" : "desktop_grid";
  const railState = isRailVisible ? "open" : "collapsed";
  const railToggleLabel = isRailVisible ? "Hide thread rail" : "Show thread rail";

  return (
    <section
      className="flex h-full w-full min-h-0 flex-col overflow-hidden"
      data-active-view="documents"
      data-active-view-contract="left-center-right"
      data-documents-layout={documentsLayoutMode}
      data-documents-rail={railState}
      data-thread-rail="present"
      data-thread-rail-state={railState}
      data-view-family="documents"
      data-testid="documents-layout"
    >
      <div className="flex h-full w-full min-h-0 gap-[var(--gutter)]">
        <aside
          className="flex h-full min-h-0 shrink-0 overflow-hidden"
          aria-label="Documents thread rail"
          data-testid="documents-thread-rail"
          data-rail-state={railState}
          style={{
            width: isRailVisible ? "var(--workspace-w)" : "auto",
            minWidth: "0",
          }}
        >
          <div
            className={`flex h-full min-h-0 flex-col overflow-hidden rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] ${
              isRailVisible ? "w-full" : "w-auto"
            }`}
            style={{
              boxShadow:
                "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -12px 26px rgba(0,0,0,0.18)",
            }}
          >
            {isRailVisible ? (
              <>
                <div className="flex items-center justify-between gap-2 border-b border-[var(--panel-border)] px-[var(--card-pad)] py-[var(--card-pad)]">
                  <div className="min-w-0">
                    <div
                      className="text-sm font-semibold leading-tight"
                      style={{ color: "var(--text)" }}
                    >
                      Documents
                    </div>
                    <div
                      className="text-[11px] leading-tight"
                      style={{ color: "var(--muted)" }}
                    >
                      Selection / navigation
                    </div>
                  </div>
                  <button
                    type="button"
                    className="icon-inline shrink-0"
                    aria-label={railToggleLabel}
                    aria-expanded={isRailVisible}
                    onClick={() => setIsRailVisible((previous) => !previous)}
                    title={railToggleLabel}
                  >
                    <ChevronLeft
                      className="h-4 w-4"
                      aria-hidden="true"
                    />
                  </button>
                </div>
                <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto px-[var(--card-pad)] py-[var(--card-pad)]">
                  <div
                    className="glass-pill flex w-full max-w-full flex-wrap justify-between gap-1 px-1"
                    role="tablist"
                    aria-label="Documents scope"
                    data-testid="documents-scope-dock"
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
                  <div
                    className="text-xs leading-snug"
                    style={{ color: "var(--muted)" }}
                  >
                    Thread-scoped content uses the same rail language as the rest of the app.
                  </div>
                </div>
              </>
            ) : (
              <div className="flex min-h-0 flex-1 items-start justify-start p-[var(--card-pad)]">
                <button
                  type="button"
                  className="glass-pill inline-flex items-center gap-2 px-3 py-2 text-xs font-medium"
                  aria-label={railToggleLabel}
                  aria-expanded={isRailVisible}
                  onClick={() => setIsRailVisible((previous) => !previous)}
                  title={railToggleLabel}
                >
                  <ChevronRight className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>Thread / Project</span>
                </button>
              </div>
            )}
          </div>
        </aside>

        <div className="flex min-w-0 flex-1">
          <div
            className="flex h-full w-full min-h-0 flex-col overflow-hidden rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)]"
            data-testid="documents-center-lane"
          >
            <div className="flex flex-shrink-0 items-center justify-between gap-3 border-b border-[var(--panel-border)] px-[var(--card-pad)] py-[var(--card-pad)]">
              <div className="min-w-0">
                <div
                  className="text-sm font-semibold leading-tight"
                  style={{ color: "var(--text)" }}
                >
                  Documents
                </div>
                <div
                  className="text-[11px] leading-tight"
                  style={{ color: "var(--muted)" }}
                >
                  Primary content surface
                </div>
              </div>
              <div className="text-[11px]" style={{ color: "var(--muted)" }}>
                {docItems.length} items
              </div>
            </div>

            <div
              className="flex-1 min-h-0 overflow-auto px-[var(--card-pad)] py-[var(--card-pad)]"
              style={{ overflowX: "hidden" }}
              data-layout-mode={
                mobileShellProfile.documents.layout === "list"
                  ? "mobile-list"
                  : "grid"
              }
              onDrop={uploader.onDrop}
              onDragOver={uploader.onDragOver}
            >
              {docItems.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <div
                    className="text-sm opacity-70"
                    style={{ color: "var(--muted)" }}
                  >
                    No documents yet. Drag files here or use the button below to get started.
                  </div>
                </div>
              ) : (
                <div style={documentsGridStyle}>
                  {docItems.map((doc) => {
                    const key = doc.id || `${doc.title}.${doc.ext}`;
                    const openInThreadMenuItem =
                      onOpenInThread && doc.type !== "codex_entry"
                        ? [
                            {
                              label: "Open in Thread",
                              onSelect: () => onOpenInThread(doc),
                            },
                          ]
                        : [];

                    return (
                      <div key={key} className="relative">
                        {isPhoneShell ? (
                          <MobileDocumentRow
                            doc={doc}
                            extColors={extColors}
                            onClick={() => handleDocumentClick(doc)}
                            contextMenuItems={openInThreadMenuItem}
                          />
                        ) : (
                          <DocumentTile
                            file={{
                              name: doc.title,
                              ext: doc.ext,
                              embeddingStatus: doc.embeddingStatus,
                              embeddingError: doc.embeddingError,
                            }}
                            onClick={() => handleDocumentClick(doc)}
                            onDeleted={
                              onDeleteDocument ? () => onDeleteDocument(doc) : undefined
                            }
                            contextMenuItems={openInThreadMenuItem}
                          />
                        )}
                        {doc.mock ? (
                          <span
                            className="absolute left-2 top-2 z-10 rounded-full border px-2 py-1 text-[10px]"
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
              className="flex-shrink-0 border-t border-[var(--panel-border)] px-[var(--card-pad)] py-[var(--card-pad)] text-xs"
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
        </div>
      </div>
    </section>
  );
}
