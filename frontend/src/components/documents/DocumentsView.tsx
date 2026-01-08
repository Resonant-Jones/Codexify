import React, { useMemo, useState } from "react";
import DocumentTile from "@/components/documents/DocumentTile";
import ContextMenu from "@/components/ui/ContextMenu";
import useUploader from "@/hooks/useUploader";
import { ExtColors } from "@/types/ui";
import { DocumentLike } from "@/types/documents";

interface DocumentsViewProps {
  documents: DocumentLike[];
  extColors: ExtColors;
  onDocumentClick?: (doc: DocumentLike) => void;
  onOpenInThread?: (doc: DocumentLike) => void;
  onDeleteDocument?: (doc: DocumentLike) => void;
  defaultBehavior?: "workspace" | "thread";
}

/**
 * DocumentsView
 *
 * Structure:
 * - FrameCard wrapper (glass + bezel)
 *   - Header (title + pill tabs)
 *   - Content area (scrollable grid of documents)
 *   - Footer (upload UI + controls)
 *
 * Layout principle: fill parent completely, no internal card nesting
 */
export default function DocumentsView({
  documents,
  extColors: _extColors,
  onDocumentClick,
  onOpenInThread,
  onDeleteDocument,
  defaultBehavior = "workspace",
}: DocumentsViewProps) {
  const [behavior, setBehavior] = useState<"workspace" | "thread">(defaultBehavior);
  const [hideMocks, setHideMocks] = useState<boolean>(() => (typeof window !== "undefined" ? localStorage.getItem("cfy.hideMocks") === "true" : false));
  const [menu, setMenu] = useState<{x:number;y:number;doc?:DocumentLike}|null>(null);

  const uploader = useUploader({
    tag: "upload",
    onImages: () => {},
    onDocuments: (items) => {
      const normalized = (items || []).map((item: any, idx: number) => ({
        ...item,
        id: item?.id || item?.name || `upload-${idx}`,
        name: item?.name || item?.title || item?.filename || "Untitled",
        title: item?.title || item?.name || item?.filename || "Untitled",
        ext: item?.ext || item?.extension || "md",
        type: "file",
      }));
      try { window.dispatchEvent(new CustomEvent("cfy:documents:add", { detail: { items: normalized } })); } catch {}
    },
    onAnyUpload: () => { try { localStorage.setItem("cfy.hasUserUpload", "true"); } catch {} },
  });

  const handleDocumentClick = (doc: DocumentLike) => {
    if (behavior === "thread" && onOpenInThread) {
      onOpenInThread(doc);
      return;
    }
    onDocumentClick?.(doc);
  };

  const docItems = useMemo(() => (hideMocks ? (documents ?? []).filter(d => !d.mock) : (documents ?? [])), [documents, hideMocks]);

  const pills = [
    { key: "workspace" as const, label: "Open in Workspace" },
    { key: "thread" as const, label: "Open in Thread" },
  ];

  return (
    <section className="flex h-full w-full min-h-0 flex-col overflow-hidden">
      {/* Content lives directly in the parent card; avoid nested rims */}
      <div className="flex h-full w-full flex-col min-h-0 overflow-hidden px-[var(--card-pad)] pb-[var(--card-pad)]">
        {/* Header: Title + Controls */}
        <div className="flex-shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--panel-border)] py-4">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>Documents</h2>
          <div className="glass-pill h-auto py-[3px] px-[6px]">
            {pills.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                className="pill-tab text-xs"
                data-state={behavior === key ? "active" : undefined}
                onClick={() => setBehavior(key)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Content Area: Scrollable document grid */}
        <div
          className="flex-1 min-h-0 overflow-auto py-4"
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
            <div className="grid auto-rows-[minmax(112px,auto)] grid-cols-[repeat(auto-fill,minmax(132px,1fr))] gap-4 pb-2">
              {docItems.map((d) => {
                const key = d.id || `${d.title}.${d.ext}`;
                const isCodex = d.type === "codex_entry";
                return (
                  <div
                    key={key}
                    className="relative"
                    onContextMenu={(e) => {
                      if (isCodex) return;
                      e.preventDefault();
                      setMenu({ x: e.clientX, y: e.clientY, doc: d });
                    }}
                  >
                    <DocumentTile
                      file={{ name: d.title, ext: d.ext }}
                      onClick={() => handleDocumentClick(d)}
                    />
                    {d.mock && (
                      <span
                        className="absolute left-2 top-2 z-10 rounded-full px-2 py-1 text-[10px] border"
                        style={{
                          background: "rgba(255,255,255,0.2)",
                          color: "#111",
                          borderColor: "rgba(255,255,255,0.5)"
                        }}
                      >
                        Mock
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer: Upload controls */}
        <div className="flex-shrink-0 flex items-center justify-between gap-2 border-t border-[var(--panel-border)] py-4 text-xs" style={{ color: "var(--muted)" }}>
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
          <label className="flex items-center gap-2 cursor-pointer hover:opacity-80">
            <input
              type="checkbox"
              checked={hideMocks}
              onChange={(e) => {
                setHideMocks(e.target.checked);
                try { localStorage.setItem("cfy.hideMocks", String(e.target.checked)); } catch {}
              }}
            />
            <span>Hide Mock Items</span>
          </label>
        </div>

        {/* Context Menu */}
        {menu && (
          <ContextMenu
            x={menu.x}
            y={menu.y}
            onClose={() => setMenu(null)}
            items={[
              ...(menu.doc && onDeleteDocument ? [{
                label: "Delete",
                onClick: () => {
                  const ev = new CustomEvent("cfy:documents:delete", { detail: { doc: menu.doc } });
                  try { window.dispatchEvent(ev); } catch {}
                  onDeleteDocument(menu.doc!);
                },
              }] : []),
              {
                label: hideMocks ? "Show Mock Items" : "Hide Mock Items",
                onClick: () => {
                  const v = !hideMocks;
                  setHideMocks(v);
                  try { localStorage.setItem("cfy.hideMocks", String(v)); } catch {}
                }
              },
            ]}
          />
        )}

        {/* Info message */}
        {behavior === "thread" && !onOpenInThread && (
          <div className="flex-shrink-0 py-3 text-xs opacity-70 border-t border-[var(--panel-border)]" style={{ color: "var(--muted)" }}>
            Configure a thread handler to open documents directly in chat.
          </div>
        )}
      </div>
    </section>
  );
}
