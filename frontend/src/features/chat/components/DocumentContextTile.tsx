import * as React from "react";
import { X } from "lucide-react";

import DocumentPreviewTile from "@/components/ui/DocumentPreviewTile";
import { cn } from "@/lib/utils";
import {
  documentContextToDocumentFile,
  type DocumentContextTile as DocumentContextTileData,
} from "@/lib/documentContext";
import { requestWorkspaceOpen } from "@/features/workspace/state/useWorkspaceState";

type DocumentContextTileProps = {
  tile: DocumentContextTileData;
  onRemove?: () => void;
  className?: string;
};

export function DocumentContextTile({ tile, onRemove, className }: DocumentContextTileProps) {
  const file = React.useMemo(() => documentContextToDocumentFile(tile), [tile]);
  const openWorkspace = React.useCallback(() => {
    requestWorkspaceOpen(
      {
        doc: { ...file, title: tile.title },
        source: "guardian-chat",
        targetView: "guardian",
      },
      { source: "guardian-chat", targetView: "guardian" }
    );
  }, [file, tile.title]);

  return (
    <div className={cn("relative", className)} data-testid="document-context-tile">
      <DocumentPreviewTile file={file} onClick={openWorkspace} />
      {onRemove ? (
        <button
          type="button"
          aria-label={`Remove ${tile.title}`}
          className="absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-full border bg-[var(--panel-bg)]"
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
