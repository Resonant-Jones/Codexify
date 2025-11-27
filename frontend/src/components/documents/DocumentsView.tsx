import React, { useMemo, useState } from "react";
import DocumentTile from "@/components/documents/DocumentTile";
import ContextMenu from "@/components/ui/ContextMenu";
import useUploader from "@/hooks/useUploader";
import FrameCard from "@/components/surface/FrameCard";
import { ExtColors } from "@/types/ui";

interface DocumentsViewProps {
  documents: Array<{ name: string; ext: keyof ExtColors; mock?: boolean }>;
  extColors: ExtColors;
  onDocumentClick?: (name: string, ext: string) => void;
  onOpenInThread?: (name: string, ext: string) => void;
  onDeleteDocument?: (name: string, ext: string) => void;
  defaultBehavior?: "workspace" | "thread";
}

export default function DocumentsView({
  documents,
  extColors,
  onDocumentClick,
  onOpenInThread,
  onDeleteDocument,
  defaultBehavior = "workspace",
}: DocumentsViewProps) {
  const [behavior, setBehavior] = useState<"workspace" | "thread">(defaultBehavior);
  const [hideMocks, setHideMocks] = useState<boolean>(() => (typeof window !== "undefined" ? localStorage.getItem("cfy.hideMocks") === "true" : false));
  const [menu, setMenu] = useState<{x:number;y:number;doc?:{name:string;ext:string}}|null>(null);
  const uploader = useUploader({
    tag: "upload",
    onImages: () => {},
    onDocuments: (items) => {
      // Let the parent wire in the state update via onDeleteDocument? Not ideal.
      // We dispatch a custom event so AppShell can listen and update.
      try { window.dispatchEvent(new CustomEvent("cfy:documents:add", { detail: { items } })); } catch {}
    },
    onAnyUpload: () => { try { localStorage.setItem("cfy.hasUserUpload", "true"); } catch {} },
  });

  const handleDocumentClick = (name: string, ext: string) => {
    if (behavior === "thread" && onOpenInThread) {
      onOpenInThread(name, ext);
      return;
    }
    onDocumentClick?.(name, ext);
  };

  const docItems = useMemo(() => (hideMocks ? (documents ?? []).filter(d => !d.mock) : (documents ?? [])), [documents, hideMocks]);
  const pills = [
    { key: "workspace" as const, label: "Open in Workspace" },
    { key: "thread" as const, label: "Open in Thread" },
  ];

  return (
    <section className="flex h-full w-full min-h-0 flex-col overflow-hidden">
      <div className="flex-1 min-h-0 p-[var(--board-edge)]">
        <FrameCard
          refractiveFallback
          shimmerMode="subtle"
          className="flex h-full w-full flex-col gap-4 px-[var(--card-pad)] py-[var(--card-pad)] rounded-[var(--card-radius)]"
          style={{ color: "var(--text)" }}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--panel-border)] pb-3">
            <div className="text-lg font-semibold">Documents</div>
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

          <div className="min-h-0 flex-1 overflow-auto" onDrop={uploader.onDrop} onDragOver={uploader.onDragOver}>
            <div className="grid auto-rows-[minmax(112px,auto)] grid-cols-[repeat(auto-fit,minmax(132px,1fr))] gap-4 justify-items-center pb-1">
              {docItems.map((d) => (
                <div
                  key={`${d.name}.${d.ext}`}
                  className="relative"
                  onContextMenu={(e) => {
                    e.preventDefault();
                    setMenu({ x: e.clientX, y: e.clientY, doc: { name: d.name, ext: d.ext } });
                  }}
                >
                  <DocumentTile
                    file={{ name: `${d.name}.${d.ext}` }}
                    onClick={() => handleDocumentClick(d.name, d.ext)}
                  />
                  {d.mock && (
                    <span className="absolute left-2 top-2 z-10 rounded-full px-2 py-1 text-[10px] border" style={{ background: "rgba(255,255,255,0.2)", color: "#111", borderColor: "rgba(255,255,255,0.5)" }}>
                      Mock
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-3 text-xs opacity-80">
            <div>Drag & drop files here, or</div>
            <button type="button" className="underline" onClick={uploader.pick}>Choose files</button>
            <div className="ml-auto flex items-center gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={hideMocks} onChange={(e) => { setHideMocks(e.target.checked); try { localStorage.setItem("cfy.hideMocks", String(e.target.checked)); } catch {} }} />
                Hide Mock Items
              </label>
            </div>
          </div>

          {menu && (
            <ContextMenu
              x={menu.x}
              y={menu.y}
              onClose={() => setMenu(null)}
              items={[
                ...(menu.doc && onDeleteDocument ? [{ label: "Delete", onClick: () => {
                  const key = `${menu.doc!.name}.${menu.doc!.ext}`;
                  // Emit a request that parent should delete AND provide undo
                  const ev = new CustomEvent("cfy:documents:delete", { detail: { name: menu.doc!.name, ext: menu.doc!.ext } });
                  try { window.dispatchEvent(ev); } catch {}
                  onDeleteDocument(menu.doc!.name, menu.doc!.ext);
                }}] : []),
                { label: hideMocks ? "Show Mock Items" : "Hide Mock Items", onClick: () => { const v = !hideMocks; setHideMocks(v); try { localStorage.setItem("cfy.hideMocks", String(v)); } catch {} } },
              ]}
            />
          )}

          {behavior === "thread" && !onOpenInThread && (
            <div className="text-xs opacity-70">
              Configure a thread handler to open documents directly in chat.
            </div>
          )}
        </FrameCard>
      </div>
    </section>
  );
}
