import React, { useEffect, useRef } from "react";
import { useChat } from "@/features/chat/useChat";
import ChatBubble from "@/features/chat/components/ChatBubble";

export function ChatView({
  threadId,
  guardianName,
  reloadVersion = 0,
}: {
  threadId: number;
  guardianName?: string;
  /** parent‑supplied bump to force a reload, e.g. when a new message is posted */
  reloadVersion?: number;
}) {
  const { messages, loadMessages, loading, error, hasMore } = useChat();
  const containerRef = useRef<HTMLDivElement>(null);
  const initialScrollRef = useRef(true);

  useEffect(() => {
    initialScrollRef.current = true;
    loadMessages(threadId, 50, 0, false);
  }, [threadId, reloadVersion, loadMessages]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (initialScrollRef.current || nearBottom) {
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      });
      initialScrollRef.current = false;
    }
  }, [messages]);

  const onScroll = async () => {
    const el = containerRef.current;
    if (!el || loading || !hasMore) return;
    if (el.scrollTop === 0) {
      const prevHeight = el.scrollHeight;
      await loadMessages(threadId, 50, messages.length, true);
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight - prevHeight;
        }
      });
    }
  };

  return (
    <div
      ref={containerRef}
      onScroll={onScroll}
      data-testid="chat-container"
      className="flex-1 min-h-0 overflow-y-auto overscroll-contain px-[var(--card-pad)] pb-[96px]"
    >
      <div className="space-y-3">
        {messages.map((m, index) => (
          <div data-testid="chat-message" key={m.id ?? `${m.role}-${m.created_at ?? index}`}
            className="max-w-full">
            <ChatBubble
              message={{
                id: String(m.id ?? `${m.role}-${m.created_at ?? index}`),
                authorId: m.role === "user" ? "me" : "bot",
                authorName: m.role === "user" ? "You" : (guardianName || "Guardian"),
                content: m.content ?? "",
                createdAt:
                  typeof m.created_at === "number"
                    ? m.created_at
                    : typeof m.created_at === "string"
                      ? Date.parse(m.created_at)
                      : Date.now(),
              }}
              isMe={m.role === "user"}
              guardianName={guardianName || "Guardian"}
            />
          </div>
        ))}
        {loading && <div className="text-xs opacity-70" data-testid="chat-loading">Loading…</div>}
        {error && <div className="text-xs text-red-500" data-testid="chat-error">{error}</div>}
        <div aria-hidden className="h-[96px] shrink-0" />
      </div>
    </div>
  );
}

export default ChatView;
