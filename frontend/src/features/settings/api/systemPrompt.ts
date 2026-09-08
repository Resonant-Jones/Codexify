import api from "@/lib/api";

export type PromptCostStatus = "ok" | "warn" | "hard" | "unknown";
export type SystemPromptInspectorLayerState =
  | "present"
  | "absent"
  | "unavailable";

export type SystemPromptInspectorContext = {
  projectId?: number | null;
  threadId?: number;
};

type SegmentPayload = {
  name?: string | null;
  chars?: number | null;
  estimated_tokens?: number | null;
  truncated?: boolean | null;
};

type CanonicalThresholdResponse = {
  warn_tokens?: number | null;
  hard_tokens?: number | null;
  status?: PromptCostStatus | null;
};

type CanonicalPersonaProfileResponse = {
  state: SystemPromptInspectorLayerState;
  error_code: string | null;
  profile_id: string | null;
  revision: number | null;
  source: string | null;
};

type CanonicalImprintResponse = {
  state: SystemPromptInspectorLayerState;
  error_code: string | null;
  id: number | null;
  status: string | null;
  preferred_name: string | null;
  heat_score: number | null;
  style: string | null;
};

type CanonicalSystemDocsResponse = {
  state: SystemPromptInspectorLayerState;
  error_code: string | null;
  count: number | null;
  truncated: boolean | null;
};

type CanonicalPromptResponse = {
  state: SystemPromptInspectorLayerState;
  error_code: string | null;
  projection_kind: string;
  legacy_persona_included: boolean;
  estimated_tokens_total: number | null;
  threshold: CanonicalThresholdResponse;
  segments: SegmentPayload[];
  docs_count: number | null;
  docs_truncated: boolean | null;
  warnings?: string[] | null;
};

type SystemPromptInspectResponse = {
  generated_at: string;
  scope: {
    user_id: string;
    thread_id: number | null;
    project_id: number | null;
  };
  persona_profile: CanonicalPersonaProfileResponse;
  imprint: CanonicalImprintResponse;
  system_docs: CanonicalSystemDocsResponse;
  prompt: CanonicalPromptResponse;
};

export type SystemPromptSegment = {
  name: string;
  chars: number;
  estimatedTokens: number;
  truncated: boolean;
};

export type SystemPromptInspectorSnapshot = {
  docsCount: number | null;
  docsTruncated: boolean | null;
  estimatedTokensTotal: number | null;
  generatedAt: string | null;
  imprint: {
    errorCode: string | null;
    heatScore: number | null;
    id: number | null;
    preferredName: string | null;
    state: SystemPromptInspectorLayerState;
    status: string | null;
    style: string | null;
  };
  persona: {
    errorCode: string | null;
    profileId: string | null;
    revision: number | null;
    source: string | null;
    state: SystemPromptInspectorLayerState;
  };
  prompt: {
    docsCount: number | null;
    docsTruncated: boolean | null;
    errorCode: string | null;
    legacyPersonaIncluded: boolean | null;
    projectionKind: string | null;
    state: SystemPromptInspectorLayerState;
  };
  segments: SystemPromptSegment[];
  systemDocs: {
    count: number | null;
    errorCode: string | null;
    state: SystemPromptInspectorLayerState;
    truncated: boolean | null;
  };
  threshold: {
    hardTokens: number | null;
    status: PromptCostStatus;
    warnTokens: number | null;
  };
  warnings: string[];
};

function toRequestParams(context: SystemPromptInspectorContext) {
  return {
    ...(context.projectId !== undefined ? { project_id: context.projectId } : {}),
    ...(context.threadId !== undefined ? { thread_id: context.threadId } : {}),
  };
}

function normalizeLayerState(
  state: unknown
): SystemPromptInspectorLayerState {
  if (state === "present" || state === "absent" || state === "unavailable") {
    return state;
  }
  return "unavailable";
}

function normalizeNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeNullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function normalizeErrorCode(value: unknown): string | null {
  return normalizeNullableString(value);
}

function normalizePromptCostStatus(value: unknown): PromptCostStatus {
  if (value === "ok" || value === "warn" || value === "hard" || value === "unknown") {
    return value;
  }
  return "unknown";
}

function normalizeSegment(segment: SegmentPayload): SystemPromptSegment | null {
  const name = normalizeNullableString(segment?.name)?.trim();
  if (!name) return null;

  return {
    name,
    chars: Math.max(0, normalizeNullableNumber(segment.chars) ?? 0),
    estimatedTokens: Math.max(
      0,
      normalizeNullableNumber(segment.estimated_tokens) ?? 0
    ),
    truncated: Boolean(segment.truncated),
  };
}

function normalizeWarnings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter(
        (warning): warning is string =>
          typeof warning === "string" && warning.trim().length > 0
      )
    : [];
}

export async function fetchSystemPromptInspectorSnapshot(
  context: SystemPromptInspectorContext = {}
): Promise<SystemPromptInspectorSnapshot> {
  const response = await api.get<SystemPromptInspectResponse>(
    "/api/system_prompt/inspect",
    { params: toRequestParams(context) }
  );
  const data = response.data;
  const persona = data.persona_profile;
  const imprint = data.imprint;
  const systemDocs = data.system_docs;
  const prompt = data.prompt;
  const segments = (prompt.segments ?? [])
    .map(normalizeSegment)
    .filter((segment): segment is SystemPromptSegment => segment !== null);
  const docsCount = normalizeNullableNumber(systemDocs.count);
  const docsTruncated =
    typeof systemDocs.truncated === "boolean" ? systemDocs.truncated : null;
  const promptDocsCount = normalizeNullableNumber(prompt.docs_count);
  const promptDocsTruncated =
    typeof prompt.docs_truncated === "boolean" ? prompt.docs_truncated : null;

  return {
    docsCount,
    docsTruncated,
    estimatedTokensTotal: normalizeNullableNumber(prompt.estimated_tokens_total),
    generatedAt: normalizeNullableString(data.generated_at),
    imprint: {
      errorCode: normalizeErrorCode(imprint.error_code),
      heatScore: normalizeNullableNumber(imprint.heat_score),
      id: normalizeNullableNumber(imprint.id),
      preferredName: normalizeNullableString(imprint.preferred_name),
      state: normalizeLayerState(imprint.state),
      status: normalizeNullableString(imprint.status),
      style: normalizeNullableString(imprint.style),
    },
    persona: {
      errorCode: normalizeErrorCode(persona.error_code),
      profileId: normalizeNullableString(persona.profile_id),
      revision:
        typeof persona.revision === "number" && Number.isInteger(persona.revision)
          ? persona.revision
          : null,
      source: normalizeNullableString(persona.source),
      state: normalizeLayerState(persona.state),
    },
    prompt: {
      docsCount: promptDocsCount,
      docsTruncated: promptDocsTruncated,
      errorCode: normalizeErrorCode(prompt.error_code),
      legacyPersonaIncluded:
        typeof prompt.legacy_persona_included === "boolean"
          ? prompt.legacy_persona_included
          : null,
      projectionKind: normalizeNullableString(prompt.projection_kind),
      state: normalizeLayerState(prompt.state),
    },
    segments,
    systemDocs: {
      count: docsCount,
      errorCode: normalizeErrorCode(systemDocs.error_code),
      state: normalizeLayerState(systemDocs.state),
      truncated: docsTruncated,
    },
    threshold: {
      hardTokens: normalizeNullableNumber(prompt.threshold?.hard_tokens),
      status: normalizePromptCostStatus(prompt.threshold?.status),
      warnTokens: normalizeNullableNumber(prompt.threshold?.warn_tokens),
    },
    warnings: normalizeWarnings(prompt.warnings),
  };
}
