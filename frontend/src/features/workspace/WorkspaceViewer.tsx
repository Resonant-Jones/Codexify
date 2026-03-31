import React, { useEffect, useMemo, useState } from "react";
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

type SupportedTextExtension = "txt" | "md" | "json";

type PreviewContext = {
  activeDoc: DocumentLike;
  normalizedExt: string;
  previewUrl: string;
  resolvedPreviewUrl: string;
  isImage: boolean;
  isPdf: boolean;
};

type PreviewRegistration = {
  kind: "pdf" | "image" | "text";
  supports: (context: PreviewContext) => boolean;
  render: (context: PreviewContext) => React.ReactNode;
};

const SUPPORTED_TEXT_EXTENSIONS: readonly SupportedTextExtension[] = [
  "txt",
  "md",
  "json",
] as const;

function normalizeExtension(value: string | null | undefined): string {
  return (value || "").trim().replace(/^\./, "").toLowerCase();
}

function inferExtension(activeDoc?: DocumentLike | null, previewUrl?: string | null): string {
  const explicitExt = normalizeExtension(activeDoc?.ext);
  if (explicitExt) {
    return explicitExt;
  }

  const candidates = [activeDoc?.title, previewUrl];
  for (const candidate of candidates) {
    if (!candidate) continue;

    const trimmedCandidate = candidate.trim();
    if (!trimmedCandidate) continue;

    try {
      const pathname = new URL(trimmedCandidate, "http://workspace.local").pathname;
      const match = pathname.match(/\.([a-z0-9]+)$/i);
      if (match?.[1]) {
        return normalizeExtension(match[1]);
      }
    } catch {
      const base = trimmedCandidate.split(/[?#]/, 1)[0];
      const match = base.match(/\.([a-z0-9]+)$/i);
      if (match?.[1]) {
        return normalizeExtension(match[1]);
      }
    }
  }

  return "";
}

function isSupportedTextExtension(
  value: string
): value is SupportedTextExtension {
  return SUPPORTED_TEXT_EXTENSIONS.includes(value as SupportedTextExtension);
}

function PdfPreview({
  title,
  resolvedPreviewUrl,
}: {
  title: string;
  resolvedPreviewUrl: string;
}) {
  return (
    <div className="codexifyWorkspaceViewer codexifyWorkspaceViewer--embed">
      <iframe title={title} src={resolvedPreviewUrl} />
    </div>
  );
}

function ImagePreview({
  title,
  resolvedPreviewUrl,
}: {
  title: string;
  resolvedPreviewUrl: string;
}) {
  return (
    <div className="codexifyWorkspaceViewer codexifyWorkspaceViewer--image">
      <img
        src={resolvedPreviewUrl}
        alt={title}
        className="codexifyWorkspaceImage"
        loading="lazy"
      />
    </div>
  );
}

function TextPreview({
  activeDoc,
  normalizedExt,
  resolvedPreviewUrl,
}: {
  activeDoc: DocumentLike;
  normalizedExt: SupportedTextExtension;
  resolvedPreviewUrl: string;
}) {
  const [content, setContent] = useState("");
  const [loadingContent, setLoadingContent] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    setContent("");
    setLoadError(null);
    setLoadingContent(true);

    fetch(resolvedPreviewUrl, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load ${normalizedExt.toUpperCase()} preview`);
        }
        return response.text();
      })
      .then((nextContent) => {
        if (!cancelled) {
          setContent(nextContent);
        }
      })
      .catch((err) => {
        if (err?.name === "AbortError" || cancelled) {
          return;
        }
        setLoadError(err?.message || "Failed to load preview");
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingContent(false);
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [normalizedExt, resolvedPreviewUrl]);

  const formattedJson = useMemo(() => {
    if (normalizedExt !== "json") {
      return content;
    }

    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      return content;
    }
  }, [content, normalizedExt]);

  if (loadingContent) {
    return (
      <div className="codexifyWorkspaceViewer">
        <div className="codexifyWorkspaceHint">Loading preview…</div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="codexifyWorkspaceViewer">
        <div className="codexifyWorkspaceError">
          <div className="codexifyWorkspaceErrorTitle">Error loading preview</div>
          <div>{loadError}</div>
          <div className="codexifyWorkspaceHint">
            Try opening the original file in a new tab.
          </div>
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

  if (normalizedExt === "md") {
    return (
      <div className="codexifyWorkspaceViewer">
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
            {content || "_No content available._"}
          </ReactMarkdown>
        </div>
      </div>
    );
  }

  return (
    <div className="codexifyWorkspaceViewer">
      <div
        className="max-h-full overflow-auto whitespace-pre-wrap break-words rounded-xl border p-4 text-sm"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in srgb, var(--panel-bg) 90%, black 10%)",
          color: "var(--text)",
        }}
      >
        <div className="mb-3 text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
          {activeDoc.title || "Untitled"}
          {normalizedExt ? ` · ${normalizedExt.toUpperCase()}` : ""}
        </div>
        <pre className="m-0 whitespace-pre-wrap break-words font-mono text-xs leading-6">
          {normalizedExt === "json" ? formattedJson : content}
        </pre>
      </div>
    </div>
  );
}

const previewRegistry: readonly PreviewRegistration[] = [
  {
    kind: "pdf",
    supports: (context) => context.isPdf,
    render: ({ activeDoc, resolvedPreviewUrl }) => (
      <PdfPreview
        title={activeDoc?.title || "PDF"}
        resolvedPreviewUrl={resolvedPreviewUrl}
      />
    ),
  },
  {
    kind: "image",
    supports: (context) => context.isImage,
    render: ({ activeDoc, resolvedPreviewUrl }) => (
      <ImagePreview
        title={activeDoc?.title || "Image"}
        resolvedPreviewUrl={resolvedPreviewUrl}
      />
    ),
  },
  {
    kind: "text",
    supports: (context) => isSupportedTextExtension(context.normalizedExt),
    render: ({ activeDoc, normalizedExt, resolvedPreviewUrl }) => (
      <TextPreview
        activeDoc={activeDoc}
        normalizedExt={normalizedExt as SupportedTextExtension}
        resolvedPreviewUrl={resolvedPreviewUrl}
      />
    ),
  },
] as const;

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
  const normalizedExt = inferExtension(activeDoc, previewUrl);
  const previewContext = useMemo<PreviewContext | null>(() => {
    if (!activeDoc || !previewUrl || !resolvedPreviewUrl) {
      return null;
    }

    return {
      activeDoc,
      normalizedExt,
      previewUrl,
      resolvedPreviewUrl,
      isImage,
      isPdf,
    };
  }, [activeDoc, isImage, isPdf, normalizedExt, previewUrl, resolvedPreviewUrl]);
  const previewRegistration = useMemo(() => {
    if (!previewContext) {
      return null;
    }

    return previewRegistry.find((entry) => entry.supports(previewContext)) || null;
  }, [previewContext]);

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

    if (previewRegistration && previewContext) {
      return previewRegistration.render(previewContext);
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
