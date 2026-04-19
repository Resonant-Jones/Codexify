/**
 * ChatBubble.tsx
 *
 * Renders chat bubbles with inline attachment tiles and dispatches workspace
 * open events for attachments without navigating away from the chat view.
 */
import React from "react";
import { motion } from "framer-motion";
import { Volume2 } from "lucide-react";
import { useRenderableMediaSrc } from "@/hooks/useRenderableMediaSrc";
import { Message, MessageAttachment } from "@/types/ui";
import { resolveMediaSrc } from "@/lib/mediaUrl";
import {
  parseDocumentContextContent,
} from "@/lib/documentContext";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import DocumentContextTileView from "@/features/chat/components/DocumentContextTile";

type Attachment = {
  kind: "image" | "document";
  id?: string;
  src?: string;
  name?: string;
};

/**
 * Merge attachments from message.attachments with those parsed from content.
 * Message.attachments takes precedence.
 */
const mergeAttachments = (
  messageAttachments: MessageAttachment[] | undefined,
  contentAttachments: Attachment[]
): Attachment[] => {
  // If message has attachments, use those (they're the canonical source)
  if (messageAttachments && messageAttachments.length > 0) {
    return messageAttachments.map((att) => ({
      kind: att.kind,
      id: att.id,
      src: att.src ? resolveMediaSrc(att.src) : att.src,
      name: att.name,
    }));
  }
  // Otherwise fall back to parsed content attachments
  return contentAttachments.map((att) => ({
    ...att,
    src: att.src ? resolveMediaSrc(att.src) : att.src,
  }));
};

const parseAttachments = (content: string) => {
  if (!content) return { attachments: [] as Attachment[], text: "" };

  const attachments: Attachment[] = [];
  const markerRe = /<!--\s*(cfy-media(?:-src|-name)?):([^>]*?)\s*-->/gi;
  let current: Attachment | null = null;
  let match: RegExpExecArray | null = null;

  while ((match = markerRe.exec(content)) !== null) {
    const type = (match[1] || "").toLowerCase();
    const value = (match[2] || "").trim();

    if (type === "cfy-media") {
      const [kindRaw, ...rest] = value.split(":");
      const kind =
        kindRaw === "image" || kindRaw === "document"
          ? (kindRaw as Attachment["kind"])
          : undefined;
      if (!kind) {
        current = null;
        continue;
      }
      const id = rest.join(":").trim();
      current = { kind, id: id || undefined };
      attachments.push(current);
      continue;
    }

    const target = current ?? attachments[attachments.length - 1];
    if (!target || !value) continue;

    if (type === "cfy-media-src") {
      target.src = value;
    } else if (type === "cfy-media-name") {
      target.name = value;
    }
  }

  const text = content.replace(/<!--\s*(cfy-media(?:-src|-name)?):([^>]*?)\s*-->/gi, "");
  return { attachments, text };
};

type CodeBlockProps = {
  code: string;
  label: string;
};

const CodeBlock = ({ code, label }: CodeBlockProps) => {
  const [copied, setCopied] = React.useState(false);
  const timeoutRef = React.useRef<number | null>(null);

  const copyWithFallback = async (text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        // Continue to fallback copy method below.
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
    <div className="codexifyCodeBlock max-w-full min-w-0">
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
    Array.isArray(classNameProp) ? classNameProp.join(" ") :
      typeof classNameProp === "string" ? classNameProp :
        undefined;
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
  if (Array.isArray(codeChildren) && codeChildren.every((node) => typeof node === "string" || typeof node === "number")) {
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

type MarkdownNode = {
  type?: string;
  value?: unknown;
  children?: MarkdownNode[];
};

const normalizeAssistantProse = (value: string) => {
  return value
    .replace(/\$\s*\\rightarrow\s*\$/g, "→")
    .replace(/\$\s*\\leftarrow\s*\$/g, "←")
    .replace(/\$\s*\\leftrightarrow\s*\$/g, "↔")
    .replace(/\$\s*\\to\s*\$/g, "→")
    .replace(/\\rightarrow/g, "→")
    .replace(/\\leftarrow/g, "←")
    .replace(/\\leftrightarrow/g, "↔")
    .replace(/\\to/g, "→");
};

const remarkNormalizeAssistantProse = () => (tree: MarkdownNode) => {
  const walk = (node: MarkdownNode) => {
    if (node.type === "text" && typeof node.value === "string") {
      node.value = normalizeAssistantProse(node.value);
    }
    node.children?.forEach(walk);
  };

  walk(tree);
};

const OVERSIZED_USER_MESSAGE_CHAR_LIMIT = 1200;
const OVERSIZED_USER_MESSAGE_LINE_LIMIT = 18;
const COLLAPSED_USER_MESSAGE_MAX_HEIGHT = 224;
const EXPANDED_USER_MESSAGE_MAX_HEIGHT = 360;

function isOversizedUserMessage(content: string): boolean {
  const normalized = content.trim();
  if (!normalized) return false;
  const lineCount = normalized.split(/\r?\n/).length;
  return (
    normalized.length > OVERSIZED_USER_MESSAGE_CHAR_LIMIT ||
    lineCount > OVERSIZED_USER_MESSAGE_LINE_LIMIT
  );
}

function looksLikeCodeContent(content: string): boolean {
  const normalized = content.trim();
  if (!normalized) return false;
  return (
    /```|^\s{4,}/m.test(normalized) ||
    /(?:\bfunction\b|\bclass\b|\bconst\b|\blet\b|\bvar\b|\bimport\b|\bexport\b|\breturn\b|=>|;\s*$)/m.test(
      normalized
    )
  );
}

const AttachmentTiles = ({
  attachments,
  align,
}: {
  attachments: Attachment[];
  align: "left" | "right";
}) => {
  if (!attachments.length) return null;

  const alignClass = align === "right" ? "items-end" : "items-start";
  const tileFrame =
    "overflow-hidden rounded-[var(--tile-radius)] border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5";
  const tileSize = "w-full max-w-[320px]";

  const openInWorkspace = (att: Attachment, idx: number) => {
    if (!att?.src) return;
    // Normalize attachment metadata into the DocumentLike shape expected by AppShell.
    const rawName =
      att.name ||
      (() => {
        const last = att.src?.split("/").pop() || "";
        return last.split("?")[0];
      })() ||
      (att.kind === "image" ? "Image.png" : "Document.pdf");
    const extMatch = rawName.match(/\.([a-z0-9]+)$/i);
    const ext = extMatch ? extMatch[1].toLowerCase() : att.kind === "image" ? "png" : "pdf";
    const title = rawName.replace(/\.[^.]+$/, "") || (att.kind === "image" ? "Image" : "Document");

    try {
      window.dispatchEvent(
        new CustomEvent("cfy:documents:open", {
          detail: {
            doc: {
              id: att.id || `${att.kind}-${idx}`,
              title,
              name: title,
              ext,
              type: "file",
              src_url: att.src,
            },
          },
        })
      );
    } catch {}
  };

  return (
    <div className={cn("flex min-w-0 flex-col gap-2", alignClass)}>
      {attachments.map((att, idx) => {
        const key = `${att.kind}-${att.id ?? idx}`;
        const resolvedSrc = att.src ? resolveMediaSrc(att.src) : att.src;
        if (att.kind === "image") {
          return (
            <div key={key} className={`${tileFrame} ${tileSize}`}>
              {resolvedSrc ? (
                <button
                  type="button"
                  onClick={() => openInWorkspace(att, idx)}
                  className="block w-full text-left"
                  aria-label="Open image"
                >
                  <RenderableChatImage
                    src={resolvedSrc}
                    alt="uploaded image"
                    className="block w-full h-auto"
                    style={{ maxHeight: 320, objectFit: "cover" }}
                  />
                </button>
              ) : (
                <div className="flex items-center justify-center h-32 text-xs opacity-70">
                  Image
                </div>
              )}
            </div>
          );
        }

        return (
          <div key={key} className={`${tileFrame} ${tileSize} px-3 py-2`}>
            {resolvedSrc ? (
              <button
                type="button"
                onClick={() => openInWorkspace(att, idx)}
                className="flex w-full items-center gap-3 text-left"
                aria-label="Open document"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-black/10 dark:bg-white/10">
                  📄
                </div>
                <div className="text-sm font-medium">Document</div>
              </button>
            ) : (
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-black/10 dark:bg-white/10">
                  📄
                </div>
                <div className="text-sm font-medium">Document</div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

function RenderableChatImage({
  src,
  alt,
  className,
  style,
}: {
  src: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const renderableSrc = useRenderableMediaSrc(src);
  const [hasLoadError, setHasLoadError] = React.useState(false);

  React.useEffect(() => {
    setHasLoadError(false);
  }, [renderableSrc.src]);

  const showImage =
    renderableSrc.status === "ready" &&
    !!renderableSrc.src &&
    !hasLoadError;

  if (!showImage) {
    return (
      <div className="flex items-center justify-center h-32 text-xs opacity-70">
        {renderableSrc.status === "loading" ? "Loading image" : "Image unavailable"}
      </div>
    );
  }

  return (
    <img
      src={renderableSrc.src}
      alt={alt}
      loading="lazy"
      className={className}
      style={style}
      onError={() => setHasLoadError(true)}
    />
  );
}

export function ChatBubble({
  message,
  isGuardian,
  showPlay = false,
  playing = false,
  playState,
  onPlay,
  isPhoneShell = false,
}: {
  message: Message;
  isGuardian: boolean;
  showPlay?: boolean;
  playing?: boolean;
  playState?: "idle" | "playing" | "pending" | "unavailable" | "disabled";
  onPlay?: () => void;
  isPhoneShell?: boolean;
}) {
  const fmtTime = (ts: number | null | undefined) => {
    if (!Number.isFinite(ts)) return null;
    const date = new Date(ts);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const { tiles: documentTiles, text: documentCleanText } = parseDocumentContextContent(
    message.content || ""
  );
  const { attachments: contentAttachments, text } = parseAttachments(documentCleanText);
  const attachments = mergeAttachments(message.attachments, contentAttachments);
  const cleanedContent = text;
  const assistantContent = cleanedContent.trim();
  const hasDocumentTiles = documentTiles.length > 0;
  const hasAttachments = attachments.length > 0;
  const hasText = Boolean(assistantContent);
  const hasVisibleContent = hasText || hasAttachments || hasDocumentTiles;
  const formattedTime = fmtTime(message.createdAt);
  const execution = message.execution;
  const executionBadgeLabel =
    execution && execution.final_model !== execution.attempted_model
      ? `⚠ Executed on ${execution.final_model}`
      : null;
  const resolvedPlayState =
    playState ?? (playing ? "playing" : "idle");
  const playButtonTitle =
    resolvedPlayState === "playing"
      ? "Playing..."
      : resolvedPlayState === "pending"
        ? "Generating audio"
      : resolvedPlayState === "unavailable"
        ? "Audio unavailable"
        : resolvedPlayState === "disabled"
          ? "Voice disabled"
          : "Read Aloud";
  const playButtonAriaLabel =
    resolvedPlayState === "playing"
      ? "Playing audio"
      : resolvedPlayState === "pending"
        ? "Generating audio"
        : "Read message aloud";
  const playDisabled =
    resolvedPlayState === "pending" ||
    resolvedPlayState === "unavailable" ||
    resolvedPlayState === "disabled";
  const boundedUserMessage = !isGuardian && isOversizedUserMessage(cleanedContent);
  const [expandedUserMessage, setExpandedUserMessage] = React.useState(false);

  React.useEffect(() => {
    setExpandedUserMessage(false);
  }, [cleanedContent, isGuardian, message.id]);

  const userMessageLooksLikeCode =
    boundedUserMessage && looksLikeCodeContent(cleanedContent);
  const userMessagePreviewStyle: React.CSSProperties | undefined = boundedUserMessage
    ? {
        maxHeight: expandedUserMessage
          ? EXPANDED_USER_MESSAGE_MAX_HEIGHT
          : COLLAPSED_USER_MESSAGE_MAX_HEIGHT,
        overflowY: expandedUserMessage ? "auto" : "hidden",
        overscrollBehavior: "contain",
      }
    : undefined;
  // Keep padding on the content node itself so collapsed messages still have
  // inset text when max-height clipping is active.
  const userMessageTextClass = cn(
    "w-full min-w-0 px-4 py-3 text-left text-sm leading-relaxed whitespace-pre-wrap break-words",
    userMessageLooksLikeCode ? "font-mono text-[13px] leading-5" : null
  );

  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      if (inline) {
        return (
          <code
            className={cn(
              "rounded bg-black/10 dark:bg-black/30 px-1 py-0.5",
              isPhoneShell ? "break-all" : "break-words"
            )}
            style={{
              overflowWrap: "anywhere",
              wordBreak: isPhoneShell ? "break-all" : "break-word",
            }}
            {...props}
          >
            {children}
          </code>
        );
      }

      // For fenced/indented code blocks, react-markdown renders: <pre><code/></pre>.
      // IMPORTANT: do not return a <div> here, or you can trip React validateDOMNesting.
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
          <pre className="my-2 max-w-full min-w-0 overflow-x-auto rounded bg-black/10 dark:bg-black/30 p-2">
            {children}
          </pre>
        );
      }
      const label = normalizeLanguageLabel(extracted.className);
      return <CodeBlock code={extracted.code} label={label} />;
    },
    p: ({ children }: any) => <p className="mb-2 last:mb-0 break-words">{children}</p>,
    ul: ({ children }: any) => <ul className="mb-2 list-disc pl-4 break-words">{children}</ul>,
    ol: ({ children }: any) => <ol className="mb-2 list-decimal pl-4 break-words">{children}</ol>,
    li: ({ children }: any) => <li className="break-words">{children}</li>,
    a: ({ href, children }: any) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="break-words text-blue-500 hover:underline"
        style={{ overflowWrap: "anywhere", wordBreak: "break-word" }}
      >
        {children}
      </a>
    ),
    img: ({ src, alt }: any) => (
      <RenderableChatImage
        src={resolveMediaSrc(String(src ?? ""))}
        alt={alt || "uploaded media"}
        className="my-2 max-w-full rounded-xl border border-black/10 dark:border-white/10"
        style={{ maxHeight: 320, objectFit: "cover" }}
      />
    ),
  };

  const renderedContent = hasText ? (
    isGuardian ? (
      <div
        className="text-sm leading-relaxed prose prose-sm max-w-none min-w-0 break-words dark:prose-invert"
        style={{
          color: "var(--text)",
          overflowWrap: "anywhere",
          wordBreak: "break-word",
        }}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkNormalizeAssistantProse]}
          components={markdownComponents}
        >
          {assistantContent}
        </ReactMarkdown>
      </div>
    ) : (
      <div
        data-testid={boundedUserMessage ? "guardian-user-message-content" : undefined}
        id={boundedUserMessage ? `guardian-user-message-${message.id}` : undefined}
        className={userMessageTextClass}
        style={{
          color: "var(--pill-active-text)",
          overflowWrap: "anywhere",
          wordBreak: "break-word",
          ...userMessagePreviewStyle,
        }}
      >
        {cleanedContent}
      </div>
    )
  ) : null;

  if (isGuardian) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        className={cn(
          "mr-auto min-w-0 space-y-1",
          isPhoneShell ? "w-full max-w-full" : "max-w-[85%]"
        )}
      >
        <div
          className="flex items-center gap-2 text-xs font-medium opacity-70"
          style={{ color: "var(--text)" }}
        >
          {message.authorName}
        </div>
        {hasDocumentTiles ? (
          <div className="flex flex-col gap-2">
            {documentTiles.map((tile) => (
              <DocumentContextTileView
                key={tile.id}
                tile={tile}
                className="max-w-[min(34rem,100%)]"
              />
            ))}
          </div>
        ) : null}
        {hasAttachments ? (
          <AttachmentTiles attachments={attachments} align="left" />
        ) : null}
        {renderedContent}
        {hasVisibleContent ? (
          <div className="mt-1.5 flex items-center gap-2">
            {executionBadgeLabel ? (
              <span
                className="inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium"
                style={{
                  borderColor: "color-mix(in srgb, var(--panel-border) 70%, transparent)",
                  color: "var(--muted)",
                  background:
                    "color-mix(in srgb, var(--panel-sheet, var(--panel-bg)) 90%, transparent)",
                }}
              >
                {executionBadgeLabel}
              </span>
            ) : null}
            {formattedTime ? (
              <div className="text-[10px] opacity-50" style={{ color: "var(--muted)" }}>
                {formattedTime}
              </div>
            ) : null}
            {showPlay && (
              <button
                type="button"
                className={cn(
                  "inline-flex h-6 w-6 items-center justify-center rounded border",
                  playDisabled ? "opacity-55 cursor-not-allowed" : "opacity-80 hover:opacity-100"
                )}
                style={{
                  borderColor: "var(--panel-border)",
                  color: "var(--text)",
                  background: "transparent",
                }}
                onClick={playDisabled ? undefined : onPlay}
                disabled={playDisabled}
                aria-label={playButtonAriaLabel}
                title={playButtonTitle}
              >
                <Volume2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        ) : null}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      className={cn(
        "ml-auto flex min-w-0 flex-col items-end gap-2",
        isPhoneShell ? "w-full max-w-full" : "max-w-[78%]"
      )}
    >
      {hasVisibleContent ? (
        <div
          className="max-w-full min-w-0 rounded-[var(--tile-radius)] p-3 shadow-sm"
          style={{ background: "var(--accent)", color: "var(--pill-active-text)" }}
        >
          <div className="flex flex-col gap-2">
            {hasDocumentTiles ? (
              <div className="flex w-full flex-col items-end gap-2">
                {documentTiles.map((tile) => (
                  <DocumentContextTileView
                    key={tile.id}
                    tile={tile}
                    className="max-w-[min(34rem,100%)]"
                  />
                ))}
              </div>
            ) : null}
            {hasAttachments ? (
              <AttachmentTiles attachments={attachments} align="right" />
            ) : null}
            {renderedContent}
            {boundedUserMessage ? (
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  className="rounded-full border px-2 py-1 text-[11px] font-medium transition-opacity hover:opacity-90"
                  style={{
                    borderColor:
                      "color-mix(in srgb, var(--panel-border) 72%, transparent)",
                    background:
                      "color-mix(in srgb, var(--panel-sheet, var(--panel-bg)) 88%, transparent)",
                    color: "var(--text)",
                  }}
                  onClick={() => setExpandedUserMessage((previous) => !previous)}
                  aria-expanded={expandedUserMessage}
                  aria-controls={
                    boundedUserMessage ? `guardian-user-message-${message.id}` : undefined
                  }
                >
                  {expandedUserMessage ? "Show less" : "See more"}
                </button>
                {formattedTime ? (
                  <span className="text-[10px] opacity-70">{formattedTime}</span>
                ) : null}
              </div>
            ) : formattedTime ? (
              <div className="mt-1.5 flex items-center justify-end gap-2">
                <span className="text-[10px] opacity-70">{formattedTime}</span>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </motion.div>
  );
}

export default ChatBubble;
