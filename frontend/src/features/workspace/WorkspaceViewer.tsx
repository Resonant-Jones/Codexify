import React, { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodexEntry } from "@/api/codex";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import { getRuntimeConfigSync } from "@/lib/runtimeConfig";
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

type MarkdownCodeBlockProps = {
  code: string;
  label: string;
};

const MarkdownCodeBlock = ({ code, label }: MarkdownCodeBlockProps) => {
  const [copied, setCopied] = useState(false);
  const timeoutRef = React.useRef<number | null>(null);

  const copyWithFallback = async (text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        // Fall through to the legacy copy path below.
      }
    }

    if (typeof document !== "undefined" && typeof document.execCommand === "function") {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      try {
        return document.execCommand("copy");
      } catch {
        return false;
      } finally {
        document.body.removeChild(textarea);
      }
    }

    return false;
  };

  const handleCopy = async () => {
    const ok = await copyWithFallback(code);
    if (!ok) return;
    setCopied(true);
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = window.setTimeout(() => {
      setCopied(false);
      timeoutRef.current = null;
    }, 1000);
  };

  React.useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="codexifyCodeBlock">
      <div className="codexifyCodeBlockHeader">
        <div className="codexifyCodeBlockLabel">
          <span className="codexifyCodeBlockAccent" aria-hidden="true" />
          <span>{label}</span>
        </div>
        <button type="button" className="codexifyCodeBlockCopy" onClick={handleCopy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="codexifyCodeBlockBody">
        <pre className="codexifyCodeBlockPre">
          <code className="codexifyCodeBlockCode">{code}</code>
        </pre>
      </div>
    </div>
  );
};

type ExtractedPreCode = {
  code: string;
  className?: string;
};

const extractPreCodeFromNode = (node: any): ExtractedPreCode | null => {
  const codeNode = node?.children?.[0];
  if (!codeNode || codeNode.tagName !== "code") return null;
  const codeChildren = codeNode.children;
  if (!Array.isArray(codeChildren)) return null;
  let text = "";
  for (const child of codeChildren) {
    if (!child || child.type !== "text" || typeof child.value !== "string") return null;
    text += child.value;
  }
  const classNameProp = codeNode.properties?.className;
  const className =
    Array.isArray(classNameProp)
      ? classNameProp.join(" ")
      : typeof classNameProp === "string"
        ? classNameProp
        : undefined;
  return { code: text, className };
};

const extractPreCodeFromChildren = (children: React.ReactNode): ExtractedPreCode | null => {
  const childArray = React.Children.toArray(children);
  if (childArray.length === 0) return null;
  const firstChild = childArray[0];
  if (!React.isValidElement(firstChild) || firstChild.type !== "code") return null;
  const codeChildren = (firstChild.props as { children?: React.ReactNode }).children;
  if (typeof codeChildren === "string") {
    return {
      code: codeChildren,
      className: (firstChild.props as { className?: string }).className,
    };
  }
  if (
    Array.isArray(codeChildren) &&
    codeChildren.every((node) => typeof node === "string" || typeof node === "number")
  ) {
    return {
      code: codeChildren.join(""),
      className: (firstChild.props as { className?: string }).className,
    };
  }
  return null;
};

const extractPreCode = (node: any, children: React.ReactNode): ExtractedPreCode | null => {
  return extractPreCodeFromNode(node) ?? extractPreCodeFromChildren(children);
};

const normalizeLanguageLabel = (className?: string) => {
  const match = className?.match(/language-([a-z0-9]+)/i);
  const raw = match?.[1]?.toLowerCase();
  if (!raw) return "CODE";
  if (raw === "ts") return "TS";
  if (raw === "tsx") return "TSX";
  if (raw === "python") return "PYTHON";
  return raw.toUpperCase();
};

const markdownComponents = {
  code({ inline, className, children, ...props }: any) {
    if (inline) {
      return (
        <code className="rounded bg-black/10 dark:bg-black/30 px-1 py-0.5" {...props}>
          {children}
        </code>
      );
    }

    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children, node }: any) => {
    const extracted = extractPreCode(node, children);
    if (!extracted) {
      return (
        <pre className="overflow-x-auto rounded bg-black/10 dark:bg-black/30 p-2 my-2">
          {children}
        </pre>
      );
    }

    const label = normalizeLanguageLabel(extracted.className);
    return <MarkdownCodeBlock code={extracted.code} label={label} />;
  },
  p: ({ children }: any) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }: any) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
  a: ({ href, children }: any) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-500 hover:underline"
    >
      {children}
    </a>
  ),
  img: ({ src, alt }: any) => (
    <img
      src={src}
      alt={alt || "uploaded media"}
      loading="lazy"
      className="my-2 max-w-full rounded-xl border border-black/10 dark:border-white/10"
      style={{ maxHeight: 320, objectFit: "cover" }}
    />
  ),
};

function isTrustedPreviewUrl(previewUrl: string | null | undefined): boolean {
  const trimmed = typeof previewUrl === "string" ? previewUrl.trim() : "";
  if (!trimmed) return false;

  if (!/^https?:\/\//i.test(trimmed) && !trimmed.startsWith("//")) {
    return true;
  }

  try {
    const runtimeConfig = getRuntimeConfigSync();
    const backendOrigin = runtimeConfig.backendBaseUrl
      ? new URL(runtimeConfig.backendBaseUrl, window.location.origin).origin
      : window.location.origin;
    const resolvedUrl = new URL(trimmed, window.location.href);
    return resolvedUrl.origin === backendOrigin;
  } catch {
    return false;
  }
}

function buildPreviewFetchInit(
  previewUrl: string,
  signal: AbortSignal
): RequestInit {
  if (isTrustedPreviewUrl(previewUrl)) {
    return buildAuthenticatedFetchInit(
      { method: "GET", signal },
      { forceApiKey: true }
    );
  }

  return {
    method: "GET",
    signal,
    credentials: "omit",
  };
}

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
    "body_markdown",
    "bodyMarkdown",
    "text",
    "text_content",
    "textContent",
    "plain_text",
    "plainText",
    "parsed_text",
    "parsedText",
    "markdown",
    "preview",
    "rawText",
    "raw_text",
    "markdown_text",
    "markdownText",
    "preview_text",
    "previewText",
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
  if (previewText) {
    return previewKind === "markdown" ? "Inline markdown" : "Inline text";
  }
  if (fetchedText) {
    if (previewKind === "markdown") {
      return previewUrl ? "Remote markdown source" : "Loaded markdown text";
    }
    return previewUrl ? "Remote document source" : "Loaded preview text";
  }
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

    fetch(normalizedPreviewUrl, buildPreviewFetchInit(normalizedPreviewUrl, controller.signal))
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
          className="text-sm leading-relaxed prose prose-sm max-w-none break-words dark:prose-invert codexifyWorkspaceMarkdown"
          data-testid="workspace-preview-content"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {resolvedText}
          </ReactMarkdown>
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
