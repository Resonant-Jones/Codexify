/**
 * ChatBubble.tsx
 *
 * Renders chat bubbles with inline attachment tiles and dispatches workspace
 * open events for attachments without navigating away from the chat view.
 */
import React from "react";
import { motion } from "framer-motion";
import { Volume2 } from "lucide-react";
import { Message, MessageAttachment } from "@/types/ui";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

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
      src: att.src,
      name: att.name,
    }));
  }
  // Otherwise fall back to parsed content attachments
  return contentAttachments;
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

  const text = content
    .replace(/<!--\s*(cfy-media(?:-src|-name)?):([^>]*?)\s*-->/gi, "")
    .trim();
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
    <div className={`flex flex-col gap-2 ${alignClass}`}>
      {attachments.map((att, idx) => {
        const key = `${att.kind}-${att.id ?? idx}`;
        if (att.kind === "image") {
          return (
            <div key={key} className={`${tileFrame} ${tileSize}`}>
              {att.src ? (
                <button
                  type="button"
                  onClick={() => openInWorkspace(att, idx)}
                  className="block w-full text-left"
                  aria-label="Open image"
                >
                  <img
                    src={att.src}
                    alt="uploaded image"
                    loading="lazy"
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
            {att.src ? (
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

export function ChatBubble({
  message,
  isGuardian,
  showPlay = false,
  playing = false,
  playState,
  onPlay,
}: {
  message: Message;
  isGuardian: boolean;
  showPlay?: boolean;
  playing?: boolean;
  playState?: "idle" | "playing" | "pending" | "unavailable" | "disabled";
  onPlay?: () => void;
}) {
  const fmtTime = (ts: number | null | undefined) => {
    if (!Number.isFinite(ts)) return null;
    const date = new Date(ts);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const { attachments: contentAttachments, text } = parseAttachments(message.content || "");
  const attachments = mergeAttachments(message.attachments, contentAttachments);
  const cleanedContent = text;
  const hasAttachments = attachments.length > 0;
  const hasText = Boolean(cleanedContent.trim());
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

  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      if (inline) {
        return (
          <code
            className="rounded bg-black/10 dark:bg-black/30 px-1 py-0.5"
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
          <pre className="overflow-x-auto rounded bg-black/10 dark:bg-black/30 p-2 my-2">
            {children}
          </pre>
        );
      }
      const label = normalizeLanguageLabel(extracted.className);
      return <CodeBlock code={extracted.code} label={label} />;
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

  const renderedMarkdown = hasText ? (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {cleanedContent}
    </ReactMarkdown>
  ) : null;

  if (isGuardian) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        className="mr-auto max-w-[85%] space-y-1"
      >
        <div
          className="flex items-center gap-2 text-xs font-medium opacity-70"
          style={{ color: "var(--text)" }}
        >
          {message.authorName}
        </div>
        {hasAttachments ? (
          <AttachmentTiles attachments={attachments} align="left" />
        ) : null}
        {hasText ? (
          <div
            className="text-sm leading-relaxed prose prose-sm max-w-none break-words dark:prose-invert"
            style={{
              color: "var(--text)",
              overflowWrap: "break-word",
              wordWrap: "break-word",
            }}
          >
            {renderedMarkdown}
          </div>
        ) : null}
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
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      className="ml-auto max-w-[78%] flex flex-col items-end gap-2"
    >
      {hasAttachments ? (
        <AttachmentTiles attachments={attachments} align="right" />
      ) : null}
      {hasText ? (
        <div
          className="max-w-full rounded-[var(--tile-radius)] p-3 shadow-sm"
          style={{ background: "var(--accent)", color: "var(--pill-active-text)" }}
        >
          <div className="text-sm leading-relaxed prose prose-sm max-w-none break-words dark:prose-invert">
            {renderedMarkdown}
          </div>
          {formattedTime ? (
            <div className="mt-1.5 flex items-center justify-end gap-2">
              <span className="text-[10px] opacity-70">{formattedTime}</span>
            </div>
          ) : null}
        </div>
      ) : (
        formattedTime ? <div className="text-[10px] opacity-70">{formattedTime}</div> : null
      )}
    </motion.div>
  );
}

export default ChatBubble;
