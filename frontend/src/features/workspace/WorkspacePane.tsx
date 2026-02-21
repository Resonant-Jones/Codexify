import React, { useCallback, useEffect, useMemo, useState } from "react";
import { DocumentLike } from "@/types/documents";
import { Button } from "@/components/ui/button";
import { getCodexEntry, getCodexExportUrl, CodexEntry } from "@/api/codex";
import WorkspaceViewer from "./WorkspaceViewer";
import "./workspace.css";

type WorkspacePaneProps = {
  activeDoc?: DocumentLike | null;
  onOpenInThread?: (doc: DocumentLike | null) => void;
};

export default function WorkspacePane({ activeDoc, onOpenInThread }: WorkspacePaneProps) {
  const resolvePreviewUrl = useCallback((): string | null => {
    if (!activeDoc) return null;
    // DocumentLike varies across the app; tolerate several common shapes.
    const anyDoc: any = activeDoc as any;
    const url =
      (typeof anyDoc.src_url === "string" && anyDoc.src_url) ||
      (typeof anyDoc.srcUrl === "string" && anyDoc.srcUrl) ||
      (typeof anyDoc.url === "string" && anyDoc.url) ||
      (typeof anyDoc.src === "string" && anyDoc.src) ||
      null;
    return url && url.trim() ? url : null;
  }, [activeDoc]);

  const previewUrl = resolvePreviewUrl();

  const isImage = useMemo(() => {
    if (!previewUrl) return false;
    const u = previewUrl.toLowerCase();
    return u.endsWith(".png") || u.endsWith(".jpg") || u.endsWith(".jpeg") || u.endsWith(".webp") || u.startsWith("data:image/");
  }, [previewUrl]);

  const isPdf = useMemo(() => {
    if (!previewUrl) return false;
    return previewUrl.toLowerCase().includes(".pdf") || previewUrl.toLowerCase().startsWith("data:application/pdf");
  }, [previewUrl]);
  const [codexEntry, setCodexEntry] = useState<CodexEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeDoc || activeDoc.type !== "codex_entry" || !activeDoc.id) {
      setCodexEntry(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getCodexEntry(activeDoc.id)
      .then((entry) => {
        if (!cancelled) {
          setCodexEntry(entry);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message || "Failed to load Codex entry");
          setCodexEntry(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeDoc?.id, activeDoc?.type]);

  const headerTitle = useMemo(() => {
    if (!activeDoc) return "Workspace";
    const title = activeDoc?.title || "Untitled";
    const ext = activeDoc?.ext ? `.${activeDoc.ext}` : "";
    return `Workspace · ${title}${ext}`;
  }, [activeDoc]);

  const exportHref = activeDoc?.type === "codex_entry" && activeDoc.id ? getCodexExportUrl(activeDoc.id) : null;

  return (
    <div className="codexifyWorkspacePane">
      <div className="codexifyWorkspacePaneHeader">
        <div className="codexifyWorkspacePaneHeaderTitle truncate">{headerTitle}</div>
        <div className="codexifyWorkspacePaneHeaderActions">
          {activeDoc && onOpenInThread && (
            <Button
              size="sm"
              className="rounded-[var(--radius-micro)] px-3"
              onClick={() => onOpenInThread(activeDoc)}
            >
              Open in Thread
            </Button>
          )}
          {exportHref && (
            <a
              href={exportHref}
              className="rounded-[var(--radius-micro)] border px-3 py-1 text-xs"
              style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
              target="_blank"
              rel="noreferrer"
            >
              Export .md
            </a>
          )}
        </div>
      </div>
      <WorkspaceViewer
        activeDoc={activeDoc}
        previewUrl={previewUrl}
        isImage={isImage}
        isPdf={isPdf}
        codexEntry={codexEntry}
        loading={loading}
        error={error}
      />
    </div>
  );
}
