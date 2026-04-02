import api from "@/lib/api";

export type PromptCostStatus = "ok" | "warn" | "hard" | "unknown";

export type SystemPromptSummarySegment = {
  name: string;
  chars: number;
  estimated_tokens: number;
  truncated: boolean;
};

export type SystemPromptSummary = {
  estimated_tokens_total?: number | null;
  threshold?: {
    warn_tokens: number;
    hard_tokens: number;
    status: PromptCostStatus;
  };
  segments?: SystemPromptSummarySegment[];
  docs_count?: number | null;
  generated_at?: string;
  // Legacy compatibility fields
  estimated_tokens?: number | null;
  cap_tokens?: number | null;
  docs_truncated?: boolean;
  overflow?: boolean;
  warnings?: string[];
};

export type ImprintStatus = {
  imprint?: {
    id: number;
    status: string;
    heat_score?: number;
    preferred_name?: string | null;
    created_at?: string;
  } | null;
  persona?: {
    id: number;
    source: string;
    snippet?: string | null;
    created_at?: string;
  } | null;
  system_prompt_meta?: SystemPromptSummary;
};

export type ImprintProposal = {
  imprint_draft: {
    id: number;
    user_id: string;
    project_id?: number | null;
    guardian_name?: string | null;
    preferred_name?: string | null;
    status: string;
    heat_score?: number;
  };
  proposal?: {
    generator_version?: string | null;
    persona_draft?: string | null;
    preferred_name?: string | null;
    project_id?: number | null;
    proposal_hash?: string | null;
    proposal_name?: string | null;
    proposal_version?: number | null;
    prompt_metadata?: Record<string, unknown> | null;
    scope_kind?: string | null;
    snapshot_hash?: string | null;
    snapshot_version?: number | null;
    user_id?: string | null;
  } | null;
  persona_draft: string;
  name: string;
  prompt_metadata?: Record<string, unknown> | null;
};

export async function fetchImprintStatus(params?: { thread_id?: number; project_id?: number | null }) {
  const res = await api.get<ImprintStatus>("/api/imprint/status", { params });
  return res.data;
}

export async function requestImprintProposal(body?: { project_id?: number | null; thread_id?: number }) {
  const res = await api.post<ImprintProposal>("/api/imprint/proposal", body ?? {});
  return res.data;
}

export async function acceptImprint(imprintId: number, personaOverride?: string) {
  const res = await api.post("/api/imprint/accept", {
    imprint_id: imprintId,
    persona_text_override: personaOverride,
  });
  return res.data;
}

export async function rejectImprint(imprintId: number) {
  const res = await api.post("/api/imprint/reject", { imprint_id: imprintId });
  return res.data;
}

export async function fetchSystemPromptSummary(params?: { thread_id?: number; project_id?: number | null }) {
  const res = await api.get<SystemPromptSummary>("/api/system_prompt/summary", {
    params,
  });
  return res.data;
}

export async function updatePersonaApi(body: string) {
  const res = await api.post("/api/imprint/persona", { body });
  return res.data;
}

export async function fetchSystemDocs(params?: { project_id?: number | null }) {
  const res = await api.get("/api/system_docs", { params });
  return res.data as { docs: Array<{ id: number; title: string; scope: string; enabled: boolean; token_estimate: number }> };
}

export async function toggleSystemDocApi(docId: number, enabled: boolean) {
  const res = await api.post("/api/system_docs/toggle", { doc_id: docId, enabled });
  return res.data;
}
