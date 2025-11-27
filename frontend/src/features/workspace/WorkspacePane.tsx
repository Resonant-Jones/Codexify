import React, { useEffect, useMemo, useState } from "react";
import FrameCard from "@/components/surface/FrameCard";
import { DocumentLike } from "@/types/documents";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getCodexEntry, getCodexExportUrl, CodexEntry } from "@/api/codex";

type WorkspacePaneProps = {
  activeDoc?: DocumentLike | null;
  onOpenInThread?: (doc: DocumentLike | null) => void;
};

export default function WorkspacePane({ activeDoc, onOpenInThread }: WorkspacePaneProps) {
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
    <FrameCard
      refractiveFallback
      shimmerMode="subtle"
      className="flex-1 overflow-auto"
      style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%" }}
    >
      <div style={{ padding: 12, borderBottom: "1px solid var(--panel-border)" }} className="flex items-center justify-between gap-3">
        <div style={{ color: "var(--text)", fontWeight: 600 }}>{headerTitle}</div>
        <div className="flex items-center gap-2 text-xs" style={{ color: "var(--muted)" }}>
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

      <div style={{ padding: 12, overflow: "auto", flex: 1 }}>
        {!activeDoc && (
          <div style={{ color: "var(--muted)" }}>
            Select a document to view it here. Codex entries render as read-only markdown.
          </div>
        )}

        {activeDoc && activeDoc.type !== "codex_entry" && (
          <div className="rounded-[var(--tile-radius)] border p-4" style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)", color: "var(--text)" }}>
            <div className="text-sm font-semibold">{activeDoc?.title || "Untitled"}{activeDoc?.ext ? `.${activeDoc.ext}` : ""}</div>
            <p className="mt-2 text-sm opacity-70">
              Preview is not available for this document type. Use Export or open in thread to review.
            </p>
          </div>
        )}

        {activeDoc && activeDoc.type === "codex_entry" && (
          <div className="rounded-[var(--tile-radius)] border p-4 space-y-3" style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)", color: "var(--text)" }}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold">{activeDoc?.title || "Untitled Codex Entry"}</div>
                <div className="text-xs opacity-70">
                  {codexEntry?.thread_id ? `Thread: ${codexEntry.thread_id}` : "Codex entry"}
                </div>
              </div>
              {codexEntry?.created_at && (
                <div className="text-xs opacity-70">
                  Created {new Date(codexEntry.created_at).toLocaleString()}
                </div>
              )}
            </div>

            {loading && (
              <div className="text-sm opacity-70">Loading Codex entry…</div>
            )}
            {error && (
              <div className="text-sm text-red-400">
                <div className="font-semibold">Error loading Codex entry</div>
                <div className="mt-1">{error}</div>
                <div className="mt-2 opacity-70">The entry may have been deleted or the endpoint may be unavailable.</div>
              </div>
            )}
            {!loading && !error && codexEntry && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {codexEntry?.body || "_No content available._"}
                </ReactMarkdown>
              </div>
            )}
            {!loading && !error && !codexEntry && (
              <div className="text-sm opacity-70">No content available.</div>
            )}
          </div>
        )}
      </div>
    </FrameCard>
  );
}
