/**
 * ChatView - renders message history with scroll/stream coherence.
 */
import React, { useCallback, useEffect, useRef, useState, useLayoutEffect } from "react";
import { useChat, parseMessagesResponse, CompletionState } from "@/features/chat/useChat";
import ChatBubble from "@/features/chat/components/ChatBubble";
import ContextMenu from "@/components/ui/ContextMenu";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { useChatAutoScroll } from "@/features/chat/hooks/useChatAutoScroll";
import { usePollWithBackoff } from "@/lib/polling/usePollWithBackoff";
import { logOnce } from "@/lib/logging/logOnce";

type PollSession = {
  token: number;
  tid: number;
  reason: string;
  startedAt: number;
  initialAssistantId: number;
};

export function ChatView({
  threadId,
  guardianName,
  reloadVersion = 0,
  completionState,
  endCompletion,
  className,
  bottomPadding = 0,
}: {
  threadId: number;
  guardianName?: string;
  reloadVersion?: number;
  completionState: CompletionState;
  endCompletion: () => void;
  className?: string;
  bottomPadding?: number;
}) {
  const { messages, loadMessages, appendMessage, loading, error, hasMore, shouldRefresh, markRefreshed } = useChat();
  const { containerRef, endRef } = useChatAutoScroll(messages.length);
  const initialScrollRef = useRef(true);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [zenMode, setZenMode] = React.useState(false);
  const scrollMeasuredRef = useRef(false);
  const { subscribe } = useLiveEvents({ passive: true });
  const PAGE_SIZE = 100;
  const POLL_INTERVAL_MS = 900;
  const POLL_TIMEOUT_MS = 30000;
  const pollTokenRef = useRef(0);
  const [pollSession, setPollSession] = useState<PollSession | null>(null);
  const lastMessageIdRef = useRef(0);
  const lastAssistantIdRef = useRef(0);
  const lastPolledUserIdRef = useRef(0);
  const lastReloadVersionRef = useRef(reloadVersion);



  const ingestIncoming = useCallback(
    (payload: any) => {
      if (!payload) return;
      const tid = Number(payload.thread_id ?? payload.threadId ?? payload.thread?.id);
      if (!Number.isFinite(tid) || tid !== threadId) return;
      appendMessage(threadId, payload);
    },
    [appendMessage, threadId]
  );

  const stopPolling = useCallback(() => {
    pollTokenRef.current += 1;
    setPollSession(null);
  }, []);

  const startPolling = useCallback(
    (tid: number, reason: string) => {
      if (!Number.isFinite(tid)) return;
      stopPolling();
      const token = ++pollTokenRef.current;
      setPollSession({
        token,
        tid,
        reason,
        startedAt: Date.now(),
        initialAssistantId: lastAssistantIdRef.current,
      });
    },
    [stopPolling]
  );

  const pollOnce = useCallback(async () => {
    if (!pollSession) return;
    if (pollTokenRef.current !== pollSession.token) return;

    if (Date.now() - pollSession.startedAt >= POLL_TIMEOUT_MS) {
      logOnce("poll:messages:timeout", 10_000, () => {
        console.info(`[chat] polling timed out (${pollSession.reason})`);
      });
      stopPolling();
      return;
    }

    try {
      const res = await api.get(`/chat/${pollSession.tid}/messages`, {
        params: { limit: PAGE_SIZE, offset: 0 },
      });
      if (pollTokenRef.current !== pollSession.token) return;

      const parsed = parseMessagesResponse(res?.data);
      if (parsed) {
        const [page] = parsed;
        console.debug(
          `[chat:poll] Parsed ${page.length} messages for thread ${pollSession.tid}`
        );
        let maxId = lastMessageIdRef.current;
        let maxAssistantId = pollSession.initialAssistantId;
        const newMessages = [];
        const getMessageId = (msg: any) => {
          const value = Number(msg?.id ?? msg?.message_id ?? msg?.messageId);
          return Number.isFinite(value) ? value : 0;
        };

        for (const msg of page) {
          const id = getMessageId(msg);
          if (!Number.isFinite(id)) continue;
          if (id > maxId) {
            maxId = id;
          }
          if (msg?.role && msg.role !== "user" && id > maxAssistantId) {
            maxAssistantId = id;
          }
          if (id > lastMessageIdRef.current) {
            newMessages.push(msg);
          }
        }

        if (newMessages.length) {
          console.debug(
            `[chat:poll] Found ${newMessages.length} new messages for thread ${pollSession.tid}`
          );
          newMessages
            .sort((a, b) => getMessageId(a) - getMessageId(b))
            .forEach((msg) => appendMessage(pollSession.tid, msg));
        }

        if (maxId > lastMessageIdRef.current) {
          lastMessageIdRef.current = maxId;
        }
        if (maxAssistantId > lastAssistantIdRef.current) {
          lastAssistantIdRef.current = maxAssistantId;
        }
        if (maxAssistantId > pollSession.initialAssistantId) {
          stopPolling();
        }
      }
    } catch (err) {
      logOnce("poll:messages", 10_000, () => {
        console.warn(`[chat] polling failed (${pollSession.reason})`, err);
      });
      throw err;
    }
  }, [appendMessage, pollSession, stopPolling]);

  usePollWithBackoff(pollOnce, {
    enabled: Boolean(pollSession),
    intervalMs: POLL_INTERVAL_MS,
    maxBackoffMs: 8_000,
    onErrorKey: "poll:messages",
    logTtlMs: 10_000,
  });

  useEffect(() => {
    stopPolling();
    initialScrollRef.current = true;
    loadMessages(threadId, PAGE_SIZE, 0, false);
    if (reloadVersion !== lastReloadVersionRef.current) {
      lastReloadVersionRef.current = reloadVersion;
      startPolling(threadId, "completion");
    }
  }, [threadId, reloadVersion, loadMessages, startPolling, stopPolling]);

  // Live updates: append message for active thread without refetching
  useEffect(() => {
    const offMessage = subscribe("message.created", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      const messageRole = payload?.role ?? "";
      const tid = Number(payload?.thread_id ?? payload?.threadId);

      // Ingest the message into the UI
      ingestIncoming(payload);

      // If this is an assistant message for the active thread and we're completing, end completion tracking
      if (
        messageRole === "assistant" &&
        Number.isFinite(tid) &&
        tid === threadId &&
        completionState.isCompleting
      ) {
        console.debug(
          `[chat] Assistant message arrived for thread ${tid}, ending completion tracking`
        );
        // Small delay to ensure message is visible before hiding loader
        setTimeout(() => {
          endCompletion();
          // Trigger a debounced refresh to ensure all messages are loaded
          if (shouldRefresh(threadId, messages.length)) {
            loadMessages(threadId, 50, 0, false);
            markRefreshed(threadId, messages.length + 1);
          }
        }, 150);
      }
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
  }, [ingestIncoming, subscribe, threadId, completionState.isCompleting, endCompletion, messages.length, shouldRefresh, loadMessages, markRefreshed]);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const overflowing = el.scrollHeight > el.clientHeight + 1;
    setHasOverflow(overflowing);
  }, [messages.length]);

  useLayoutEffect(() => {
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

    if (initialScrollRef.current) {
      el.scrollTop = el.scrollHeight;
      initialScrollRef.current = false;
    }
  }, [messages.length, threadId]);

  useEffect(() => {
    let maxId = 0;
    let maxAssistantId = 0;
    for (const msg of messages) {
      const id = Number(msg.id);
      if (!Number.isFinite(id)) continue;
      if (id > maxId) {
        maxId = id;
      }
      if (msg.role && msg.role !== "user" && id > maxAssistantId) {
        maxAssistantId = id;
      }
    }
    if (maxId > lastMessageIdRef.current) {
      lastMessageIdRef.current = maxId;
    }
    if (maxAssistantId > lastAssistantIdRef.current) {
      lastAssistantIdRef.current = maxAssistantId;
    }
  }, [messages]);

  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.role !== "user") return;
    const lastId = Number(lastMessage.id);
    if (!Number.isFinite(lastId)) return;
    if (lastId <= lastPolledUserIdRef.current) return;
    lastPolledUserIdRef.current = lastId;
    startPolling(threadId, "user-message");
  }, [messages, startPolling, threadId]);

  useEffect(() => () => stopPolling(), [stopPolling]);

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
    paddingBottom: bottomPadding ?? 0,
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
    <div
      className={cn(
        "flex flex-col h-full min-h-0",
        className
      )}
    >
      <div
        ref={containerRef}
        onScroll={onScroll}
        data-testid="chat-container"
        data-debug-scroll
        className="flex-1 min-h-0 flex flex-col overflow-y-auto overscroll-contain px-4 space-y-4"
        style={scrollStyle}
      >
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
                attachments: m.attachments?.map((att) => ({
                  id: att.id,
                  kind: att.kind,
                  src: att.src_url,
                  name: att.filename,
                })),
              }}
              isGuardian={m.role !== "user"}
            />
          </div>
        ))}
        {completionState.isCompleting && (
          <div className="max-w-full" data-testid="chat-completing-indicator">
            <div className="flex items-start gap-3 px-4 py-3">
              {/* Guardian avatar skeleton */}
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex-shrink-0 animate-pulse" />

              {/* Skeleton content with pulsing animation */}
              <div className="flex-1 space-y-2 min-w-0">
                <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
                <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
                <div className="flex items-center gap-2 mt-3">
                  <div
                    className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                  <span className="text-xs ml-2 opacity-60" style={{ color: "var(--muted)" }}>
                    Guardian is thinking…
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
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
        <div ref={endRef} />
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
