import api from "@/lib/api";
import { ENV } from "@/lib/env";

export type CodexEntrySummary = {
  id: string;
  title: string;
  ext: "codex";
  created_at?: string;
  updated_at?: string;
  thread_id?: string;
  source_thread_id?: string;
  source_message_id?: string;
  trigger_message_id?: string;
  author_id?: string;
  heat_score?: number;
  created_from?: string;
  retrieval_enabled?: boolean;
  project_id?: string;
  persona_id?: string;
};

export type CodexEntry = CodexEntrySummary & {
  body: string;
  message_ids?: string[];
};

export type CodexDraftLineage = {
  thread_id: number;
  trigger_message_id: number | null;
  source_message_ids: number[];
  first_source_message_id: number | null;
  last_source_message_id: number | null;
};

export type CodexDraft = {
  title: string;
  body: string;
  lineage: CodexDraftLineage;
  source_summary: string;
};

export type CodexDraftResponse = {
  ok: boolean;
  draft: CodexDraft | null;
  reason?: string;
  detail?: string;
};

export type CodexSaveRequest = {
  title: string;
  body: string;
  thread_id?: number | null;
  source_thread_id?: number | null;
  source_message_id?: number | null;
  trigger_message_id?: number | null;
  message_ids?: number[] | null;
  author_id?: string | null;
  created_from?: string | null;
  retrieval_enabled?: boolean;
  project_id?: number | null;
  persona_id?: string | null;
};

export type CodexSaveResponse = {
  ok: boolean;
  entry: {
    id: string;
    title: string;
    created_at?: string;
    thread_id?: string;
    source_thread_id?: string;
    source_message_id?: string;
    trigger_message_id?: string;
    created_from?: string;
    retrieval_enabled?: boolean;
  };
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

export async function generateCodexDraft(
  threadId: number,
  triggerMessageId?: number | null,
): Promise<CodexDraftResponse> {
  const res = await api.post<CodexDraftResponse>("/codex/entries/draft", {
    thread_id: threadId,
    trigger_message_id: triggerMessageId ?? null,
  });
  return res.data;
}

export async function saveCodexEntry(
  payload: CodexSaveRequest,
): Promise<CodexSaveResponse> {
  const res = await api.post<CodexSaveResponse>("/codex/entries", payload);
  return res.data;
}

export function getCodexExportUrl(id: string): string {
  const base = (ENV.apiBase || "").replace(/\/+$/, "");
  const path = `/codex/entries/${id}/export`;
  if (!base) return path;
  const needsSlash = !path.startsWith("/");
  return `${base}${needsSlash ? "/" : ""}${path}`;
}

export function downloadCodexDraftAsMarkdown(draft: CodexDraft): void {
  const frontmatter = [
    "---",
    `title: ${draft.title}`,
    `thread_id: ${draft.lineage.thread_id}`,
    `created_from: slash_command`,
    `retrieval_enabled: false`,
    "---",
    "",
  ].join("\n");
  const content = `${frontmatter}\n${draft.body}`;
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${draft.title.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase() || "codex-entry"}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
