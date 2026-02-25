import { useCallback, useRef, useState } from "react";
import api from "@/lib/api";

export type ChatMessage = { id: number; thread_id: number; role: string; content: string; created_at: string };

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
      setMessages([]);
      setHasMore(true);
    }
    try {
      const res = await api.get(`/chat/${threadId}/messages`, { params: { limit, offset } });
      if (activeThreadRef.current !== threadId) {
        return;
      }
      if (res?.data?.ok && Array.isArray(res.data.messages)) {
        const page = res.data.messages as ChatMessage[];
        const tot = res.data.total ?? page.length;
        setTotal(tot);
        setHasMore(offset + page.length < tot);
        if (append) {
          setMessages((prev) => [...prev, ...page]);
        } else {
          setMessages(page);
        }
      } else {
        setMessages([]);
        setTotal(0);
        setHasMore(false);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to load messages");
      setMessages([]);
      setTotal(0);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
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

  const appendMessage = useCallback((threadId: number, payload: any) => {
    const normalized: ChatMessage = {
      id: Number(payload?.id ?? Date.now()),
      thread_id: Number(payload?.thread_id ?? payload?.threadId ?? threadId),
      role: String(payload?.role ?? "assistant"),
      content: String(payload?.content ?? ""),
      created_at:
        typeof payload?.created_at === "string"
          ? payload.created_at
          : new Date().toISOString(),
    };

    if (!Number.isFinite(normalized.thread_id) || normalized.thread_id !== threadId) {
      return;
    }

    setMessages((prev) => {
      if (prev.some((item) => item.id === normalized.id)) {
        return prev;
      }
      return [...prev, normalized];
    });
    setTotal((prev) => prev + 1);
  }, []);

  return { messages, total, loading, error, hasMore, loadMessages, sendMessage, deleteMessage, appendMessage };
}

export default useChat;
