/**
 * useChat - local chat state with semantic guards against no-op updates.
 */
import { useCallback, useRef, useState } from "react";
import api from "@/lib/api";

export type ChatMessage = { id: number; thread_id: number; role: string; content: string; created_at: string };

const normalizeMessage = (raw: any, fallbackThreadId?: number): ChatMessage | null => {
  if (!raw) return null;
  const base = raw.message && typeof raw.message === "object" ? raw.message : raw;
  const threadId = Number(base.thread_id ?? base.threadId ?? fallbackThreadId);
  const id = Number(base.id ?? base.message_id ?? base.messageId);
  const role = String(base.role ?? "").trim();
  const content = typeof base.content === "string" ? base.content : String(base.content ?? "");
  const createdAtRaw = base.created_at ?? base.createdAt;
  const createdAt = createdAtRaw ? String(createdAtRaw) : "";
  if (!Number.isFinite(threadId) || !Number.isFinite(id)) return null;
  // Drop empty content to avoid no-op UI updates.
  if (!role || !content.trim()) return null;
  return {
    id,
    thread_id: threadId,
    role,
    content,
    created_at: createdAt,
  };
};

const sameMessage = (a: ChatMessage, b: ChatMessage): boolean => {
  return a.id === b.id
    && a.thread_id === b.thread_id
    && a.role === b.role
    && a.content === b.content
    && (a.created_at || "") === (b.created_at || "");
};

const equalMessageLists = (a: ChatMessage[], b: ChatMessage[]): boolean => {
  if (a === b) return true;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (!sameMessage(a[i], b[i])) return false;
  }
  return true;
};

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const activeThreadRef = useRef<number | null>(null);

  const loadMessages = useCallback(async (threadId: number, limit = 50, offset = 0, append = false) => {
    activeThreadRef.current = threadId;
    setLoading(true);
    setError(null);
    if (!append || offset === 0) {
      setMessages((prev) => (prev.length ? [] : prev));
      setHasMore((prev) => (prev ? prev : true));
    }
    try {
      const res = await api.get(`/chat/${threadId}/messages`, { params: { limit, offset } });
      if (activeThreadRef.current !== threadId) {
        return;
      }
      if (res?.data?.ok && Array.isArray(res.data.messages)) {
        const page = res.data.messages as ChatMessage[];
        const tot = res.data.total ?? page.length;
        setTotal((prev) => (prev === tot ? prev : tot));
        const nextHasMore = offset + page.length < tot;
        setHasMore((prev) => (prev === nextHasMore ? prev : nextHasMore));
        setMessages((prev) => {
          const next = append ? mergeMessagePages(prev, page) : page;
          return equalMessageLists(prev, next) ? prev : next;
        });
      } else {
        setMessages((prev) => (prev.length ? [] : prev));
        setTotal((prev) => (prev === 0 ? prev : 0));
        setHasMore((prev) => (prev === false ? prev : false));
      }
    } catch (e: any) {
      setError(e?.message || "Failed to load messages");
      setMessages((prev) => (prev.length ? [] : prev));
      setTotal((prev) => (prev === 0 ? prev : 0));
      setHasMore((prev) => (prev === false ? prev : false));
    } finally {
      setLoading(false);
    }
  }, []);

  const appendMessage = useCallback((threadId: number, raw: any) => {
    const incoming = normalizeMessage(raw, threadId);
    if (!incoming || incoming.thread_id !== threadId) return;
    setMessages((prev) => {
      const idx = prev.findIndex((msg) => msg.id === incoming.id);
      if (idx >= 0) {
        const existing = prev[idx];
        const merged = {
          ...existing,
          ...incoming,
          created_at: incoming.created_at || existing.created_at,
        };
        if (sameMessage(existing, merged)) return prev;
        const next = [...prev];
        next[idx] = merged;
        return next;
      }
      const next = [...prev, incoming];
      setTotal((prevTotal) => prevTotal + 1);
      return next;
    });
  }, []);

  const sendMessage = useCallback(async (threadId: number, role: string, content: string) => {
    try {
      const res = await api.post(`/chat/${threadId}/messages`, { role, content });
      return res?.data;
    } catch (e) {
      setError("Failed to send message");
      return { ok: false };
    }
  }, []);

  const deleteMessage = useCallback(async (threadId: number, id: number) => {
    try {
      const res = await api.delete(`/chat/${threadId}/messages/${id}`);
      return res?.data;
    } catch (e) {
      setError("Failed to delete message");
      return { ok: false };
    }
  }, []);

  return { messages, total, loading, error, hasMore, loadMessages, appendMessage, sendMessage, deleteMessage };
}

export default useChat;

function mergeMessagePages(prev: ChatMessage[], page: ChatMessage[]): ChatMessage[] {
  if (!page.length) return prev;
  const next = [...prev];
  // Deduplicate by id so SSE inserts do not re-add fetched messages.
  const indexById = new Map<number, number>();
  next.forEach((msg, idx) => indexById.set(msg.id, idx));
  page.forEach((msg) => {
    const existingIdx = indexById.get(msg.id);
    if (existingIdx == null) {
      indexById.set(msg.id, next.length);
      next.push(msg);
      return;
    }
    const existing = next[existingIdx];
    if (!sameMessage(existing, msg)) {
      next[existingIdx] = msg;
    }
  });
  return next;
}
