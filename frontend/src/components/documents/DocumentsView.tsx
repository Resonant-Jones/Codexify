import React, { useMemo, useState } from "react";
import DocumentPreviewTile from "@/components/ui/DocumentPreviewTile";
import FrameCard from "@/components/surface/FrameCard";
import { ExtColors } from "@/types/ui";

interface DocumentsViewProps {
  documents: Array<{ name: string; ext: keyof ExtColors }>;
  extColors: ExtColors;
  onDocumentClick?: (name: string, ext: string) => void;
  onOpenInThread?: (name: string, ext: string) => void;
  defaultBehavior?: "workspace" | "thread";
}

export default function DocumentsView({ 
  documents, 
  extColors, 
  onDocumentClick,
  onOpenInThread,
  defaultBehavior = "workspace",
}: DocumentsViewProps) {
  const [behavior, setBehavior] = useState<"workspace" | "thread">(defaultBehavior);

  const handleDocumentClick = (name: string, ext: string) => {
    if (behavior === "thread" && onOpenInThread) {
      onOpenInThread(name, ext);
      return;
    }
    onDocumentClick?.(name, ext);
  };

  const docItems = useMemo(() => documents ?? [], [documents]);
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
          className="flex h-full w-full flex-col gap-4 px-[var(--card-pad)] py-[var(--card-pad)]"
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

          <div className="min-h-0 flex-1 overflow-auto">
            <div className="grid auto-rows-[minmax(112px,auto)] grid-cols-[repeat(auto-fit,minmax(132px,1fr))] gap-4 justify-items-center pb-1">
              {docItems.map((d) => (
                <DocumentPreviewTile
                  key={`${d.name}.${d.ext}`}
                  file={{ name: `${d.name}.${d.ext}` }}
                  onClick={() => handleDocumentClick(d.name, d.ext)}
                />
              ))}
            </div>
          </div>

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
