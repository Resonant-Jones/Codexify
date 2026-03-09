import api from "@/lib/api";

export type PersonaSettingsContext = {
  projectId?: number | null;
  threadId?: number;
};

type ImprintStatusPersonaPayload = {
  id?: number;
  source?: string | null;
  body?: string | null;
  snippet?: string | null;
  created_at?: string | null;
  allow_clearing?: boolean | null;
};

type ImprintStatusResponse = {
  persona?: ImprintStatusPersonaPayload | null;
};

type UpdatePersonaResponse = {
  id?: number;
  body?: string | null;
  source?: string | null;
  created_at?: string | null;
  allow_clearing?: boolean | null;
};

export type ActivePersonaSettings = {
  id: number | null;
  text: string;
  source: string | null;
  createdAt: string | null;
  canClear: boolean;
};

function toRequestParams(context: PersonaSettingsContext) {
  return {
    ...(context.projectId !== undefined ? { project_id: context.projectId } : {}),
    ...(context.threadId !== undefined ? { thread_id: context.threadId } : {}),
  };
}

function normalizePersona(
  persona?: ImprintStatusPersonaPayload | UpdatePersonaResponse | null
): ActivePersonaSettings {
  return {
    id: typeof persona?.id === "number" ? persona.id : null,
    text: String(persona?.body ?? persona?.snippet ?? ""),
    source: typeof persona?.source === "string" ? persona.source : null,
    createdAt: typeof persona?.created_at === "string" ? persona.created_at : null,
    canClear: Boolean(persona?.allow_clearing),
  };
}

export async function fetchPersonaSettings(
  context: PersonaSettingsContext = {}
): Promise<ActivePersonaSettings> {
  const res = await api.get<ImprintStatusResponse>("/api/imprint/status", {
    params: toRequestParams(context),
  });
  return normalizePersona(res.data?.persona);
}

export async function updatePersonaSettings(
  body: { text: string } & PersonaSettingsContext
): Promise<ActivePersonaSettings> {
  const res = await api.post<UpdatePersonaResponse>("/api/imprint/persona", {
    body: body.text,
    ...toRequestParams(body),
  });
  return normalizePersona(res.data);
}
