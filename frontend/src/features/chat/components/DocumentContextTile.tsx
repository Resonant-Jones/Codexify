import * as React from "react";
import { FileText, X } from "lucide-react";

import { cn } from "@/lib/utils";
import type { DocumentContextTile as DocumentContextTileData } from "@/lib/documentContext";
import { requestWorkspaceOpen } from "@/features/workspace/state/useWorkspaceState";

type DocumentContextTileProps = {
  tile: DocumentContextTileData;
  onRemove?: () => void;
  className?: string;
};

export function DocumentContextTile({
  tile,
  onRemove,
  className,
}: DocumentContextTileProps) {
  const openWorkspace = React.useCallback(() => {
    if (!tile?.id) return;
    requestWorkspaceOpen(
      {
        doc: {
          id: tile.id,
          title: tile.title,
          name: tile.title,
          ext: tile.ext || "md",
          type: "file",
        },
        source: "guardian-chat",
        targetView: "guardian",
      },
      { source: "guardian-chat", targetView: "guardian" }
    );
  }, [tile]);

  const preview = tile.preview?.trim() || "";
  const title = tile.title?.trim() || "Untitled";
  const label = preview ? `${title}. ${preview}` : title;

  return (
    <div
      className={cn(
        "relative inline-flex w-full max-w-full overflow-hidden rounded-[16px] border",
        "border-black/10 bg-black/5 shadow-sm dark:border-white/10 dark:bg-white/5",
        className
      )}
      title={label}
      data-testid="document-context-tile"
    >
      <button
        type="button"
        className="flex w-full min-w-0 items-start gap-2 px-3 py-2 text-left"
        onClick={openWorkspace}
        aria-label={title}
      >
        <span
          className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border"
          style={{
            borderColor: "color-mix(in oklab, var(--panel-border) 78%, transparent)",
            background:
              "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 92%, transparent)",
          }}
          aria-hidden="true"
        >
          <FileText className="h-4 w-4 opacity-80" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-medium leading-5" style={{ color: "var(--text)" }}>
            {title}
          </span>
          {preview ? (
            <span
              className="mt-0.5 block max-h-[3.2em] overflow-hidden text-[11px] leading-snug opacity-70"
              style={{ color: "var(--muted)", overflowWrap: "anywhere" }}
            >
              {preview}
            </span>
          ) : null}
        </span>
      </button>
      {onRemove ? (
        <button
          type="button"
          aria-label={`Remove ${title}`}
          className="absolute right-1.5 top-1.5 grid h-5 w-5 place-items-center rounded-full border text-[10px] transition-opacity hover:opacity-90"
          style={{
            borderColor: "color-mix(in oklab, var(--panel-border) 78%, transparent)",
            background: "color-mix(in oklab, var(--panel-bg) 82%, transparent)",
            color: "var(--text)",
          }}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            onRemove();
          }}
        >
          <X className="h-3 w-3" />
        </button>
      ) : null}
    </div>
  );
}

export default DocumentContextTile;
