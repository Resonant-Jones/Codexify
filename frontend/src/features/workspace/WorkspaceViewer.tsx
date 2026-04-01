import React, { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodexEntry } from "@/api/codex";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import { DocumentLike } from "@/types/documents";

type WorkspaceViewerProps = {
  activeDoc?: DocumentLike | null;
  previewUrl: string | null;
  previewText: string | null;
  previewMimeType: string | null;
  isImage: boolean;
  isPdf: boolean;
  codexEntry: CodexEntry | null;
  loading: boolean;
  error: string | null;
};

type PreviewKind = "image" | "pdf" | "markdown" | "text" | "unsupported";
type PreviewPhase = "idle" | "loading" | "ready" | "error";

const MARKDOWN_EXTENSIONS = new Set([
  "md",
  "markdown",
  "mdown",
  "mkd",
  "mkdn",
  "mdx",
]);

const TEXT_EXTENSIONS = new Set([
  "txt",
  "text",
  "log",
  "csv",
  "tsv",
  "json",
  "jsonl",
  "yaml",
  "yml",
  "xml",
  "html",
  "htm",
  "ini",
  "conf",
  "env",
  "toml",
  "css",
  "scss",
  "js",
  "jsx",
  "ts",
  "tsx",
  "py",
  "rb",
  "go",
  "rs",
  "java",
  "c",
  "cc",
  "cpp",
  "cxx",
  "h",
  "hpp",
  "sh",
  "bash",
  "zsh",
  "sql",
  "graphql",
  "gql",
  "swift",
  "kt",
  "kts",
  "php",
  "patch",
  "diff",
]);

function readStringField(
  source: Record<string, unknown> | null | undefined,
  fields: string[]
): string | null {
  if (!source) return null;
  for (const field of fields) {
    const value = source[field];
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed) return value;
  }
  return null;
}

function normalizeText(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  return value.trim() ? value : null;
}

function resolveDocumentExtension(doc: DocumentLike | null | undefined): string {
  if (!doc) return "";
  const direct = readStringField(doc as Record<string, unknown>, [
    "ext",
    "extension",
    "format",
  ]);
  if (direct) return direct.replace(/^\./, "").toLowerCase();

  const filename = readStringField(doc as Record<string, unknown>, [
    "filename",
    "name",
    "title",
  ]);
  if (!filename) return "";

  const lowered = filename.toLowerCase();
  if (lowered === "dockerfile") return "dockerfile";

  const match = lowered.match(/\.([a-z0-9]+)$/i);
  return match?.[1] ?? "";
}

function resolveDocumentMimeType(
  doc: DocumentLike | null | undefined,
  explicit?: string | null
): string {
  const direct = normalizeText(explicit);
  if (direct) return direct.toLowerCase();
  if (!doc) return "";
  return (
    readStringField(doc as Record<string, unknown>, [
      "mime_type",
      "mimeType",
      "content_type",
      "contentType",
    ])?.toLowerCase() ?? ""
  );
}

function resolveInlinePreviewText(
  doc: DocumentLike | null | undefined
): string | null {
  if (!doc) return null;
  return readStringField(doc as Record<string, unknown>, [
    "content",
    "body",
    "text",
    "parsed_text",
    "parsedText",
    "markdown",
    "preview",
    "rawText",
    "snippet",
  ]);
}

function formatDate(value: string | undefined | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function buildSourceLabel(
  previewUrl: string | null,
  previewText: string | null,
  fetchedText: string | null,
  activeDoc: DocumentLike | null | undefined,
  previewKind: PreviewKind
): string {
  if (activeDoc?.type === "codex_entry") return "Codex entry body";
  if (previewText) return "Inline text";
  if (fetchedText) return previewUrl ? "Remote document source" : "Loaded preview text";
  if (previewUrl) {
    if (previewKind === "image" || previewKind === "pdf") {
      return "Embedded asset";
    }
    return "Remote document source";
  }
  return "No preview source";
}

function buildPreviewKind(options: {
  activeDoc: DocumentLike | null | undefined;
  previewMimeType: string;
  previewText: string | null;
  isImage: boolean;
  isPdf: boolean;
}): PreviewKind {
  const { activeDoc, previewMimeType, previewText, isImage, isPdf } = options;
  if (isImage) return "image";
  if (isPdf) return "pdf";

  const extension = resolveDocumentExtension(activeDoc).toLowerCase();
  const mimeType = previewMimeType.toLowerCase();
  const markdownLike =
    activeDoc?.type === "codex_entry" ||
    MARKDOWN_EXTENSIONS.has(extension) ||
    mimeType.includes("markdown") ||
    mimeType.endsWith("+markdown");

  if (markdownLike) return "markdown";

  const textLike =
    Boolean(previewText) ||
    TEXT_EXTENSIONS.has(extension) ||
    mimeType.startsWith("text/") ||
    mimeType.includes("json") ||
    mimeType.includes("xml") ||
    mimeType.includes("yaml") ||
    mimeType.includes("toml") ||
    mimeType.includes("csv") ||
    mimeType.includes("javascript") ||
    mimeType.includes("typescript") ||
    mimeType.includes("sql");

  return textLike ? "text" : "unsupported";
}

export default function WorkspaceViewer({
  activeDoc,
  previewUrl,
  previewText,
  previewMimeType,
  isImage,
  isPdf,
  codexEntry,
  loading,
  error,
}: WorkspaceViewerProps) {
  const inlinePreviewText = useMemo(
    () => normalizeText(previewText) ?? resolveInlinePreviewText(activeDoc),
    [activeDoc, previewText]
  );

  const mimeType = useMemo(
    () => resolveDocumentMimeType(activeDoc, previewMimeType),
    [activeDoc, previewMimeType]
  );

  const previewKind = useMemo(
    () =>
      buildPreviewKind({
        activeDoc,
        previewMimeType: mimeType,
        previewText: inlinePreviewText,
        isImage,
        isPdf,
      }),
    [activeDoc, inlinePreviewText, isImage, isPdf, mimeType]
  );

  const codexBody = useMemo(() => {
    const body = codexEntry?.body;
    if (typeof body !== "string") return null;
    return body.trim() ? body : null;
  }, [codexEntry?.body]);

  const sourceText = activeDoc?.type === "codex_entry" ? codexBody : inlinePreviewText;
  const needsRemoteText = (previewKind === "markdown" || previewKind === "text") && !sourceText;
  const normalizedPreviewUrl = useMemo(
    () => (previewUrl ? normalizeMediaUrl(previewUrl) : ""),
    [previewUrl]
  );

  const [fetchedText, setFetchedText] = useState<string | null>(null);
  const [fetchPhase, setFetchPhase] = useState<PreviewPhase>("idle");
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    setFetchedText(null);
    setFetchError(null);

    if (!needsRemoteText || !normalizedPreviewUrl) {
      setFetchPhase(needsRemoteText && !normalizedPreviewUrl ? "error" : "idle");
      if (needsRemoteText && !normalizedPreviewUrl) {
        setFetchError("Missing preview source URL");
      }
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    setFetchPhase("loading");

    fetch(
      normalizedPreviewUrl,
      buildAuthenticatedFetchInit(
        { method: "GET", signal: controller.signal },
        { forceApiKey: true }
      )
    )
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Preview request failed (${response.status})`);
        }
        return response.text();
      })
      .then((text) => {
        if (cancelled) return;
        setFetchedText(text);
        setFetchPhase("ready");
      })
      .catch((err) => {
        if (cancelled || err?.name === "AbortError") return;
        setFetchError(err?.message || "Failed to load preview content");
        setFetchPhase("error");
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [needsRemoteText, normalizedPreviewUrl]);

  const resolvedText = sourceText ?? fetchedText;
  const title = activeDoc?.title || activeDoc?.name || "Untitled document";
  const extension = resolveDocumentExtension(activeDoc);
  const createdAt = formatDate(
    activeDoc?.createdAt ?? (activeDoc as any)?.created_at ?? codexEntry?.created_at ?? null
  );
  const threadId = activeDoc?.thread_id ?? activeDoc?.threadId ?? codexEntry?.thread_id ?? null;
  const embeddingStatus = activeDoc?.embeddingStatus ?? null;

  const metadataRows = useMemo(() => {
    if (!activeDoc) return [];

    const rows: Array<{ label: string; value: string }> = [];
    rows.push({ label: "Title", value: title });
    rows.push({
      label: "Format",
      value:
        previewKind === "unsupported"
          ? extension
            ? `Unsupported (.${extension})`
            : "Unsupported"
          : previewKind === "markdown"
            ? extension
              ? `Markdown (.${extension})`
              : "Markdown"
            : previewKind === "text"
              ? extension
                ? `Text (.${extension})`
                : "Text"
              : previewKind === "image"
                ? "Image"
                : "PDF",
    });
    rows.push({
      label: "Source",
      value: buildSourceLabel(
        normalizedPreviewUrl || previewUrl,
        sourceText,
        fetchedText,
        activeDoc,
        previewKind
      ),
    });

    if (threadId !== null && threadId !== undefined) {
      rows.push({ label: "Thread", value: String(threadId) });
    }
    if (createdAt) {
      rows.push({ label: "Created", value: createdAt });
    }
    if (embeddingStatus) {
      rows.push({ label: "Embedding", value: embeddingStatus });
    }

    return rows;
  }, [
    activeDoc,
    createdAt,
    embeddingStatus,
    extension,
    fetchedText,
    normalizedPreviewUrl,
    previewKind,
    previewUrl,
    sourceText,
    threadId,
    title,
  ]);

  if (!activeDoc) {
    return (
      <div className="codexifyWorkspaceViewer">
        <div
          className="codexifyWorkspacePreviewSurface"
          data-testid="workspace-empty-state"
          role="status"
          aria-live="polite"
          style={{ minHeight: 0, overflow: "auto" }}
        >
          <div className="codexifyWorkspaceState">
            <div className="codexifyWorkspaceStateTitle">No document selected</div>
            <div className="codexifyWorkspaceHint">
              Select a workspace document to see its preview here.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const renderPreviewSurface = () => {
    if (previewKind === "image") {
      return (
        <div className="codexifyWorkspaceMediaPreview">
          <img
            src={normalizedPreviewUrl || previewUrl || undefined}
            alt={title}
            className="codexifyWorkspaceImage"
            loading="lazy"
          />
        </div>
      );
    }

    if (previewKind === "pdf") {
      return (
        <div className="codexifyWorkspaceMediaPreview">
          <iframe title={title} src={normalizedPreviewUrl || previewUrl || undefined} />
        </div>
      );
    }

    if (previewKind === "markdown") {
      if (loading && activeDoc.type === "codex_entry" && !resolvedText) {
        return <PreviewMessage title="Loading preview…" hint="Fetching markdown content." />;
      }

      if (error && activeDoc.type === "codex_entry" && !resolvedText) {
        return (
          <PreviewMessage
            title="Preview load failed"
            hint={error}
            tone="error"
            detail="The entry may have been deleted or the endpoint may be unavailable."
          />
        );
      }

      if (fetchPhase === "loading" && !resolvedText) {
        return <PreviewMessage title="Loading preview…" hint="Fetching document markdown." />;
      }

      if (fetchPhase === "error" && !resolvedText) {
        return (
          <PreviewMessage
            title="Preview unavailable"
            hint="The document body could not be loaded."
            tone="error"
            detail={fetchError || undefined}
          />
        );
      }

      if (!resolvedText) {
        return (
          <PreviewMessage
            title="Preview unavailable"
            hint="This document has no previewable markdown content."
          />
        );
      }

      return (
        <div
          className="prose prose-sm max-w-none dark:prose-invert codexifyWorkspaceMarkdown"
          data-testid="workspace-preview-content"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{resolvedText}</ReactMarkdown>
        </div>
      );
    }

    if (previewKind === "text") {
      if (fetchPhase === "loading" && !resolvedText) {
        return <PreviewMessage title="Loading preview…" hint="Fetching document text." />;
      }

      if (fetchPhase === "error" && !resolvedText) {
        return (
          <PreviewMessage
            title="Preview unavailable"
            hint="The document body could not be loaded."
            tone="error"
            detail={fetchError || undefined}
          />
        );
      }

      if (!resolvedText) {
        return (
          <PreviewMessage
            title="Preview unavailable"
            hint="This document has no previewable text content."
          />
        );
      }

      return (
        <pre
          className="codexifyWorkspacePlaintext"
          data-testid="workspace-preview-content"
        >
          {resolvedText}
        </pre>
      );
    }

    return (
      <PreviewMessage
        title="Preview unavailable for this file type"
        hint="Metadata is still available below."
        tone="muted"
        detail={
          normalizedPreviewUrl || previewUrl
            ? "Open the source asset in a new tab if you need the raw file."
            : undefined
        }
      />
    );
  };

  return (
    <div className="codexifyWorkspaceViewer">
      <div
        className="codexifyWorkspacePreviewSurface"
        data-testid="workspace-preview-surface"
        data-state={previewKind}
        style={{ minHeight: 0, overflow: "auto" }}
      >
        {renderPreviewSurface()}
      </div>

      <div className="codexifyWorkspaceMetadata" data-testid="workspace-metadata">
        <div className="codexifyWorkspaceMetadataHeader">
          <div className="codexifyWorkspaceMetadataTitle">{title}</div>
          <div className="codexifyWorkspaceHint">
            {previewKind === "unsupported"
              ? "Unsupported document"
              : previewKind === "markdown"
                ? "Markdown preview"
                : previewKind === "text"
                  ? "Text preview"
                  : previewKind === "image"
                    ? "Image preview"
                    : "PDF preview"}
          </div>
        </div>

        <dl className="codexifyWorkspaceMetadataGrid">
          {metadataRows.map((row) => (
            <div key={row.label} className="codexifyWorkspaceMetadataItem">
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

function PreviewMessage({
  title,
  hint,
  detail,
  tone = "default",
}: {
  title: string;
  hint?: string;
  detail?: string;
  tone?: "default" | "muted" | "error";
}) {
  return (
    <div className={`codexifyWorkspaceState codexifyWorkspaceState--${tone}`}>
      <div className="codexifyWorkspaceStateTitle">{title}</div>
      {hint && <div className="codexifyWorkspaceHint">{hint}</div>}
      {detail && <div className="codexifyWorkspaceHint">{detail}</div>}
    </div>
  );
}
