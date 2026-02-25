import React from "react";
import { motion } from "framer-motion";
import { Message } from "@/types/ui";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ChatBubble({
  message,
  isGuardian,
  showPlay = false,
  playing = false,
  onPlay,
}: {
  message: Message;
  isGuardian: boolean;
  showPlay?: boolean;
  playing?: boolean;
  onPlay?: () => void;
}) {
  const fmtTime = (ts: number) => new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  if (isGuardian) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        className="mr-auto max-w-[85%] space-y-1"
      >
        <div className="flex items-center gap-2 text-xs font-medium opacity-70" style={{ color: "var(--text)" }}>
          {message.authorName}
        </div>
        <div
          className="text-sm leading-relaxed prose prose-sm max-w-none break-words dark:prose-invert"
          style={{
            color: "var(--text)",
            overflowWrap: "break-word",
            wordWrap: "break-word"
          }}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({node, inline, className, children, ...props}: any) {
                return !inline ? (
                  <div className="overflow-x-auto rounded bg-black/10 dark:bg-black/30 p-2 my-2">
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </div>
                ) : (
                  <code className="rounded bg-black/10 dark:bg-black/30 px-1 py-0.5" {...props}>
                    {children}
                  </code>
                );
              },
              p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({children}) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
              ol: ({children}) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
              a: ({href, children}) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{children}</a>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        <div className="mt-1.5 flex items-center gap-2">
          <div className="text-[10px] opacity-50" style={{ color: "var(--muted)" }}>
            {fmtTime(message.createdAt)}
          </div>
          {showPlay && (
            <button
              type="button"
              className="text-[10px] px-2 py-0.5 rounded border opacity-80 hover:opacity-100"
              style={{
                borderColor: "var(--panel-border)",
                color: "var(--text)",
                background: "transparent",
              }}
              onClick={onPlay}
            >
              {playing ? "Playing…" : "Read Aloud"}
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
      className="max-w-[78%] rounded-[var(--tile-radius)] p-3 shadow-sm ml-auto"
      style={{ background: "var(--accent)", color: "var(--pill-active-text)" }}
    >
      <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
      <div className="mt-1.5 flex items-center justify-end gap-2">
        <span className="text-[10px] opacity-70">{fmtTime(message.createdAt)}</span>
      </div>
    </motion.div>
  );
}


export default ChatBubble;
