import React from "react";
import { motion } from "framer-motion";
import { Message } from "@/types/ui";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Attachment = {
  kind: "image" | "document";
  id?: string;
  src?: string;
  name?: string;
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

  const openInWorkspace = (att: Attachment) => {
    if (!att?.src) return;
    // Dispatch a cancelable event; if a listener handles it, it should call preventDefault().
    try {
      const ev = new CustomEvent("cfy:workspace:open", {
        detail: {
          kind: att.kind,
          src: att.src,
          id: att.id,
          name: att.name,
        },
        cancelable: true,
      });
      const notCanceled = window.dispatchEvent(ev);
      const handled = !notCanceled;
      if (handled) return;
      try {
        window.dispatchEvent(new CustomEvent("cfy:workspace:toggleWorkspacePanel"));
      } catch {}
    } catch {
      // fall through to default
    }

    // No fallback navigation (avoids the "jump-scare" new-tab behavior).
    // If nothing handles the event yet, surface a toast so it’s obvious what’s missing.
    try {
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: {
            message:
              "Workspace open isn’t wired yet for attachments (missing cfy:workspace:open listener).",
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
                  onClick={() => openInWorkspace(att)}
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
                onClick={() => openInWorkspace(att)}
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
}: {
  message: Message;
  isGuardian: boolean;
}) {
  const fmtTime = (ts: number) =>
    new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const { attachments, text } = parseAttachments(message.content || "");
  const cleanedContent = text;
  const hasAttachments = attachments.length > 0;
  const hasText = Boolean(cleanedContent.trim());

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
    pre: ({ children }: any) => (
      <pre className="overflow-x-auto rounded bg-black/10 dark:bg-black/30 p-2 my-2">
        {children}
      </pre>
    ),
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
        <div className="text-[10px] opacity-50" style={{ color: "var(--muted)" }}>
          {fmtTime(message.createdAt)}
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
          <div className="mt-1.5 flex items-center justify-end gap-2">
            <span className="text-[10px] opacity-70">{fmtTime(message.createdAt)}</span>
          </div>
        </div>
      ) : (
        <div className="text-[10px] opacity-70">{fmtTime(message.createdAt)}</div>
      )}
    </motion.div>
  );
}

export default ChatBubble;
