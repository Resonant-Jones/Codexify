import React, { useEffect, useRef } from "react";
import { useChat } from "@/features/chat/useChat";
import ChatBubble from "@/features/chat/components/ChatBubble";

export function ChatView({ threadId, guardianName }: { threadId: number; guardianName?: string }) {
  const { messages, loadMessages, loading, error, hasMore } = useChat();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadMessages(threadId, 50, 0, false);
    const el = containerRef.current;
    if (el) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [threadId]);

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
    <div ref={containerRef} onScroll={onScroll} data-testid="chat-container" className="flex-1 overflow-y-auto px-[var(--card-pad)] pb-[var(--card-pad)]">
      <div className="space-y-3">
        {messages.map((m) => (
          <div data-testid="chat-message" key={m.id}>
            <ChatBubble
              message={{ id: String(m.id), authorId: m.role === "user" ? "me" : "bot", authorName: m.role, content: m.content, createdAt: Date.parse(m.created_at) || Date.now() }}
              isMe={m.role === "user"}
              guardianName={guardianName || "Guardian"}
            />
          </div>
        ))}
        {loading && <div className="text-xs opacity-70" data-testid="chat-loading">Loading…</div>}
        {error && <div className="text-xs text-red-500" data-testid="chat-error">{error}</div>}
      </div>
    </div>
  );
}

export default ChatView;
