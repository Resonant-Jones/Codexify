import api from "@/lib/api";

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
  system_prompt_meta?: {
    estimated_tokens?: number;
    docs_count?: number;
    segments_present?: Record<string, boolean>;
    segments?: Record<string, number>;
    cap_tokens?: number;
    docs_truncated?: boolean;
    overflow?: boolean;
    warnings?: string[];
  };
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
  persona_draft: string;
  name: string;
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
  const res = await api.get("/api/system_prompt/summary", { params });
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
