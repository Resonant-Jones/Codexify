import React, { useEffect, useMemo, useState } from "react";
import { DocumentLike } from "@/types/documents";
import { Button } from "@/components/ui/button";
import { getCodexEntry, getCodexExportUrl, CodexEntry } from "@/api/codex";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import WorkspaceViewer from "./WorkspaceViewer";
import "./workspace.css";

type WorkspacePaneProps = {
  activeDoc?: DocumentLike | null;
  onOpenInThread?: (doc: DocumentLike | null) => void;
};

function readDocString(doc: DocumentLike | null | undefined, fields: string[]): string | null {
  if (!doc) return null;
  const anyDoc = doc as Record<string, unknown>;
  for (const field of fields) {
    const value = anyDoc[field];
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed) return value;
  }
  return null;
}

function resolvePreviewUrl(doc: DocumentLike | null | undefined): string | null {
  if (!doc) return null;
  const anyDoc = doc as Record<string, unknown>;
  const url =
    readDocString(doc, ["src_url", "srcUrl", "url", "src"]) ||
    (typeof anyDoc.previewUrl === "string" && anyDoc.previewUrl.trim()
      ? anyDoc.previewUrl
      : null);
  if (!url) return null;
  const normalized = normalizeMediaUrl(url);
  return normalized || null;
}

function resolvePreviewText(doc: DocumentLike | null | undefined): string | null {
  return readDocString(doc, [
    "content",
    "body",
    "text",
    "snippet",
    "parsed_text",
    "parsedText",
    "markdown",
    "preview",
    "rawText",
  ]);
}

function resolvePreviewMimeType(doc: DocumentLike | null | undefined): string | null {
  return readDocString(doc, [
    "mime_type",
    "mimeType",
    "content_type",
    "contentType",
  ]);
}

export default function WorkspacePane({ activeDoc, onOpenInThread }: WorkspacePaneProps) {
  const previewUrl = useMemo(() => resolvePreviewUrl(activeDoc), [activeDoc]);
  const previewText = useMemo(() => resolvePreviewText(activeDoc), [activeDoc]);
  const previewMimeType = useMemo(
    () => resolvePreviewMimeType(activeDoc),
    [activeDoc]
  );

  const isImage = useMemo(() => {
    if (!previewUrl) return false;
    const u = previewUrl.toLowerCase();
    return (
      u.endsWith(".png") ||
      u.endsWith(".jpg") ||
      u.endsWith(".jpeg") ||
      u.endsWith(".webp") ||
      u.endsWith(".gif") ||
      u.endsWith(".svg") ||
      u.startsWith("data:image/")
    );
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
        previewText={previewText}
        previewMimeType={previewMimeType}
        isImage={isImage}
        isPdf={isPdf}
        codexEntry={codexEntry}
        loading={loading}
        error={error}
      />
    </div>
  );
}
