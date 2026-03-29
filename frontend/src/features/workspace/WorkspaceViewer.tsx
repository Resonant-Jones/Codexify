import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodexEntry } from "@/api/codex";
import { resolveMediaSrc } from "@/lib/mediaUrl";
import { DocumentLike } from "@/types/documents";

type WorkspaceViewerProps = {
  activeDoc?: DocumentLike | null;
  previewUrl: string | null;
  isImage: boolean;
  isPdf: boolean;
  codexEntry: CodexEntry | null;
  loading: boolean;
  error: string | null;
};

export default function WorkspaceViewer({
  activeDoc,
  previewUrl,
  isImage,
  isPdf,
  codexEntry,
  loading,
  error,
}: WorkspaceViewerProps) {
  const resolvedPreviewUrl = previewUrl ? resolveMediaSrc(previewUrl) : null;

  if (!activeDoc) {
    return (
      <div className="codexifyWorkspaceViewer">
        <div className="codexifyWorkspaceHint">
          Select a document to view it here. Codex entries render as read-only
          markdown.
        </div>
      </div>
    );
  }

  if (activeDoc.type !== "codex_entry") {
    if (!resolvedPreviewUrl) {
      return (
        <div className="codexifyWorkspaceViewer">
          <div className="codexifyWorkspaceHint">
            Preview is not available for this document type. Use “Open in
            Thread” to review.
          </div>
        </div>
      );
    }

    if (isPdf) {
      return (
        <div className="codexifyWorkspaceViewer codexifyWorkspaceViewer--embed">
          <iframe title={activeDoc?.title || "PDF"} src={resolvedPreviewUrl} />
        </div>
      );
    }

    if (isImage) {
      return (
        <div className="codexifyWorkspaceViewer codexifyWorkspaceViewer--image">
          <img
            src={resolvedPreviewUrl}
            alt={activeDoc?.title || "Image"}
            className="codexifyWorkspaceImage"
            loading="lazy"
          />
        </div>
      );
    }

    return (
      <div className="codexifyWorkspaceViewer">
        <div className="codexifyWorkspaceHint">
          This file type does not have an inline preview yet.
        </div>
        <a
          href={resolvedPreviewUrl}
          target="_blank"
          rel="noreferrer"
          className="codexifyWorkspaceLink"
        >
          Open in a new tab
        </a>
      </div>
    );
  }

  return (
    <div className="codexifyWorkspaceViewer">
      <div className="codexifyWorkspaceCodexHeader">
        <div className="codexifyWorkspaceCodexTitle">
          {activeDoc?.title || "Untitled Codex Entry"}
        </div>
        <div className="codexifyWorkspaceHint">
          {codexEntry?.thread_id ? `Thread: ${codexEntry.thread_id}` : "Codex entry"}
        </div>
        {codexEntry?.created_at && (
          <div className="codexifyWorkspaceHint">
            Created {new Date(codexEntry.created_at).toLocaleString()}
          </div>
        )}
      </div>

      {loading && <div className="codexifyWorkspaceHint">Loading Codex entry…</div>}

      {error && (
        <div className="codexifyWorkspaceError">
          <div className="codexifyWorkspaceErrorTitle">Error loading Codex entry</div>
          <div>{error}</div>
          <div className="codexifyWorkspaceHint">
            The entry may have been deleted or the endpoint may be unavailable.
          </div>
        </div>
      )}

      {!loading && !error && codexEntry && (
        <div className="prose prose-sm max-w-none dark:prose-invert codexifyWorkspaceMarkdown">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              img: ({ src, alt }) => (
                <img
                  src={resolveMediaSrc(String(src ?? ""))}
                  alt={alt || "Workspace media"}
                  loading="lazy"
                />
              ),
            }}
          >
            {codexEntry?.body || "_No content available._"}
          </ReactMarkdown>
        </div>
      )}

      {!loading && !error && !codexEntry && (
        <div className="codexifyWorkspaceHint">No content available.</div>
      )}
    </div>
  );
}
