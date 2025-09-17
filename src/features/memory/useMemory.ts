import { useCallback, useState } from "react";
import api from "@/lib/api";

export type MemoryEntry = { id: number; user_id: string; silo: string; content: string; tags: string; pinned: boolean; created_at: string; updated_at: string };

export function useMemory() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const listMemories = useCallback(async (silo: string, limit = 50, offset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/api/memory/${silo}`, { params: { limit, offset } });
      if (res?.data?.ok && Array.isArray(res.data.entries)) {
        setEntries(res.data.entries);
        setCount(res.data.count ?? res.data.entries.length);
      } else {
        setEntries([]);
        setCount(0);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to list memory");
      setEntries([]);
      setCount(0);
    } finally {
      setLoading(false);
    }
  }, []);

  const addMemory = useCallback(async (silo: string, content: string, tags?: string[], pinned?: boolean) => {
    try {
      const res = await api.post(`/api/memory/${silo}`, { content, tags, pinned });
      return res?.data;
    } catch (e) {
      setError("Failed to add memory");
      return { ok: false };
    }
  }, []);

  const updateMemory = useCallback(async (silo: string, id: number, data: Partial<Pick<MemoryEntry, "content" | "tags" | "pinned">>) => {
    try {
      const res = await api.patch(`/api/memory/${silo}/${id}`, data);
      return res?.data;
    } catch (e) {
      setError("Failed to update memory");
      return { ok: false };
    }
  }, []);

  const deleteMemory = useCallback(async (silo: string, id: number) => {
    try {
      const res = await api.delete(`/api/memory/${silo}/${id}`);
      return res?.data;
    } catch (e) {
      setError("Failed to delete memory");
      return { ok: false };
    }
  }, []);

  return { entries, count, loading, error, listMemories, addMemory, updateMemory, deleteMemory };
}

export default useMemory;

