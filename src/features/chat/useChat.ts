import { useCallback, useState } from "react";
import api from "@/lib/api";

export type ChatMessage = { id: number; thread_id: number; role: string; content: string; created_at: string };

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const loadMessages = useCallback(async (threadId: number, limit = 50, offset = 0, append = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/api/chat/${threadId}/messages`, { params: { limit, offset } });
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
      const res = await api.post(`/api/chat/${threadId}/messages`, { role, content });
      return res?.data;
    } catch (e) {
      setError("Failed to send message");
      return { ok: false };
    }
  }, []);

  const deleteMessage = useCallback(async (threadId: number, id: number) => {
    try {
      const res = await api.delete(`/api/chat/${threadId}/messages/${id}`);
      return res?.data;
    } catch (e) {
      setError("Failed to delete message");
      return { ok: false };
    }
  }, []);

  return { messages, total, loading, error, hasMore, loadMessages, sendMessage, deleteMessage };
}

export default useChat;
