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
  const res = await api.get<CodexEntrySummary[]>("/api/codex/entries");
  return res.data;
}

export async function getCodexEntry(id: string): Promise<CodexEntry> {
  const res = await api.get<CodexEntry>(`/api/codex/entries/${id}`);
  return res.data;
}

export function getCodexExportUrl(id: string): string {
  const base = (ENV.apiBase || "").replace(/\/+$/, "");
  const path = `/api/codex/entries/${id}/export`;
  if (!base) return path;
  const needsSlash = !path.startsWith("/");
  return `${base}${needsSlash ? "/" : ""}${path}`;
}

