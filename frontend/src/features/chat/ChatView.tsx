import React, { useCallback, useEffect, useRef, useState, useLayoutEffect } from "react";
import clsx from "clsx";
import { useChat } from "@/features/chat/useChat";
import ChatBubble from "@/features/chat/components/ChatBubble";
import ContextMenu from "@/components/ui/ContextMenu";
import { useLiveEvents } from "@/hooks/useLiveEvents";

export function ChatView({
  threadId,
  guardianName,
  reloadVersion = 0,
  className,
  bottomPadding = 0,
}: {
  threadId: number;
  guardianName?: string;
  reloadVersion?: number;
  className?: string;
  bottomPadding?: number;
}) {
  const { messages, loadMessages, appendMessage, loading, error, hasMore } = useChat();
  const containerRef = useRef<HTMLDivElement>(null);
  const initialScrollRef = useRef(true);
  const [hasOverflow, setHasOverflow] = useState(false);
  const scrollMeasuredRef = useRef(false);
  const { subscribe } = useLiveEvents({ passive: true });
  const PAGE_SIZE = 100;



  const ingestIncoming = useCallback(
    (payload: any) => {
      if (!payload) return;
      const tid = Number(payload.thread_id ?? payload.threadId ?? payload.thread?.id);
      if (!Number.isFinite(tid) || tid !== threadId) return;
      appendMessage(threadId, payload);
    },
    [appendMessage, threadId]
  );

  useEffect(() => {
    initialScrollRef.current = true;
    loadMessages(threadId, PAGE_SIZE, 0, false);
  }, [threadId, reloadVersion, loadMessages]);

  // Live updates: append message for active thread without refetching
  useEffect(() => {
    const offMessage = subscribe("message.created", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      ingestIncoming(payload);
    });
    const onLocal = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      ingestIncoming(detail.message ?? detail);
    };
    window.addEventListener("cfy:chat:message", onLocal as EventListener);
    return () => {
      offMessage();
      window.removeEventListener("cfy:chat:message", onLocal as EventListener);
    };
  }, [ingestIncoming, subscribe]);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const overflowing = el.scrollHeight > el.clientHeight + 1;
    setHasOverflow(overflowing);
  }, [messages.length]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // On initial load, try to restore saved scroll position
    if (initialScrollRef.current && typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem(`chat-scroll-${threadId}`);
        if (saved) {
          requestAnimationFrame(() => {
            if (containerRef.current) {
              containerRef.current.scrollTop = parseInt(saved, 10);
            }
          });
          initialScrollRef.current = false;
          return;
        }
      } catch {}
    }

    // Otherwise, auto-scroll to bottom only when explicitly at bottom
    const atBottom = Math.abs(el.scrollHeight - el.clientHeight - el.scrollTop) < 24;
    if (initialScrollRef.current || atBottom) {
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      });
      initialScrollRef.current = false;
    }
  }, [messages, threadId]);

  const onScroll = async () => {
    const el = containerRef.current;
    if (!el) return;

    // Save scroll position
    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem(`chat-scroll-${threadId}`, String(el.scrollTop));
      } catch {}
    }

    // Infinite scroll at top
    if (loading || !hasMore) return;
    if (el.scrollTop === 0) {
      const prevHeight = el.scrollHeight;
      await loadMessages(threadId, PAGE_SIZE, messages.length, true);
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight - prevHeight;
        }
      });
    }
  };

  // Context menu: Save to Prompt Library
  const [menu, setMenu] = useState<{ x: number; y: number; text: string } | null>(null);
  function savePrompt(text: string) {
    const title = window.prompt("Optional title", "");
    const category = window.prompt("Optional category", "");
    const tagsRaw = window.prompt("Optional tags (comma-separated)", "");
    const pin = window.confirm("Pin this prompt to top?");
    const item = {
      text,
      ts: Date.now(),
      source: "manual",
      title: title || undefined,
      category: category || undefined,
      tags: (tagsRaw || "").split(",").map((t) => t.trim()).filter(Boolean),
      pinned: pin || false,
    };
    try {
      const raw = localStorage.getItem("cfy.prompts");
      const arr = raw ? JSON.parse(raw) : [];
      const next = [item, ...(Array.isArray(arr) ? arr : [])];
      localStorage.setItem("cfy.prompts", JSON.stringify(next));
      window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: "Saved to Prompt Library" } }));
    } catch {}
  }

  const shouldMask = hasOverflow && bottomPadding > 0;
  const scrollStyle: React.CSSProperties = {
    ...(bottomPadding > 0 ? { paddingBottom: bottomPadding } : {}),
    ...(shouldMask
      ? {
          maskImage:
            "linear-gradient(to bottom, black 0%, black calc(100% - 80px), transparent 100%)",
          WebkitMaskImage:
            "linear-gradient(to bottom, black 0%, black calc(100% - 80px), transparent 100%)",
        }
      : {}),
  };

  return (
    <div className={clsx("flex flex-col h-full w-full min-h-0", className)}>
      <div
        ref={containerRef}
        onScroll={onScroll}
        data-testid="chat-container"
        className="flex-1 min-h-0 overflow-y-auto overscroll-contain px-[var(--card-pad)]"
        style={scrollStyle}
      >
        <div className="space-y-3">
          {messages.map((m, index) => (
            <div
              data-testid="chat-message"
              key={m.id ?? `${m.role}-${m.created_at ?? index}`}
              className="max-w-full"
              onContextMenu={(e) => {
                e.preventDefault();
                const content = String(m.content ?? "");
                if (!content.trim()) return;
                setMenu({ x: e.clientX, y: e.clientY, text: content });
              }}
            >
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
                isGuardian={m.role !== "user"}
              />
            </div>
          ))}
          {loading && (
            <div className="text-xs opacity-70" data-testid="chat-loading">
              Loading…
            </div>
          )}
          {error && (
            <div className="text-xs text-red-500" data-testid="chat-error">
              {error}
            </div>
          )}
        </div>
      </div>
      {menu && (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          onClose={() => setMenu(null)}
          items={[
            { label: "Save to Prompt Library", onClick: () => savePrompt(menu.text) },
          ]}
        />
      )}
    </div>
  );
}

export default ChatView;
