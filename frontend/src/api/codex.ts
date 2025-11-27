import api from "@/lib/api";
import { ENV } from "@/lib/env";

export type CodexEntrySummary = {
  id: string;
  title: string;
  ext: "codex";
  created_at?: string;
  updated_at?: string;
  thread_id?: string;
  author_id?: string;
  heat_score?: number;
};

export type CodexEntry = CodexEntrySummary & {
  body: string;
  message_ids?: string[];
};

export async function listCodexEntries(): Promise<CodexEntrySummary[]> {
  try {
    const res = await api.get<CodexEntrySummary[]>("/codex/entries");
    return res.data || [];
  } catch (err: any) {
    if (err?.response?.status === 404) {
      console.warn("[codex] /codex/entries endpoint not found, returning empty list");
      return [];
    }
    console.warn("[codex] failed to load entries, returning empty list", err);
    return [];
  }
}

export async function getCodexEntry(id: string): Promise<CodexEntry> {
  try {
    const res = await api.get<CodexEntry>(`/codex/entries/${id}`);
    return res.data;
  } catch (err: any) {
    console.warn(`[codex] failed to load entry ${id}`, err);
    throw err;
  }
}

export function getCodexExportUrl(id: string): string {
  const base = (ENV.apiBase || "").replace(/\/+$/, "");
  const path = `/codex/entries/${id}/export`;
  if (!base) return path;
  const needsSlash = !path.startsWith("/");
  return `${base}${needsSlash ? "/" : ""}${path}`;
}
