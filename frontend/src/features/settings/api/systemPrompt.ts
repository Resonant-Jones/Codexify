import api from "@/lib/api";

export type PromptCostStatus = "ok" | "warn" | "hard" | "unknown";

export type SystemPromptInspectorContext = {
  projectId?: number | null;
  threadId?: number;
};

type SegmentPayload = {
  name?: string;
  chars?: number | null;
  estimated_tokens?: number | null;
  truncated?: boolean | null;
};

type ImprintStatusResponse = {
  imprint?: {
    id?: number;
    status?: string | null;
    heat_score?: number | null;
    preferred_name?: string | null;
    created_at?: string | null;
  } | null;
  persona?: {
    id?: number;
    source?: string | null;
    snippet?: string | null;
    created_at?: string | null;
  } | null;
  system_prompt_meta?: {
    estimated_tokens?: number | null;
    docs_count?: number | null;
    segments_present?: Record<string, boolean> | null;
    segments?: SegmentPayload[] | null;
  } | null;
};

type SystemPromptSummaryResponse = {
  estimated_tokens_total?: number | null;
  threshold?: {
    warn_tokens?: number | null;
    hard_tokens?: number | null;
    status?: PromptCostStatus | null;
  } | null;
  segments?: SegmentPayload[] | null;
  docs_count?: number | null;
  generated_at?: string | null;
  estimated_tokens?: number | null;
  cap_tokens?: number | null;
  docs_truncated?: boolean | null;
  overflow?: boolean | null;
  warnings?: string[] | null;
};

export type SystemPromptSegment = {
  name: string;
  chars: number;
  estimatedTokens: number;
  truncated: boolean;
};

export type SystemPromptInspectorSnapshot = {
  docsCount: number | null;
  docsTruncated: boolean;
  estimatedTokensTotal: number | null;
  generatedAt: string | null;
  imprint: {
    createdAt: string | null;
    heatScore: number | null;
    id: number | null;
    preferredName: string | null;
    status: string | null;
  } | null;
  persona: {
    createdAt: string | null;
    id: number | null;
    snippet: string | null;
    source: string | null;
  } | null;
  segments: SystemPromptSegment[];
  segmentsPresent: Record<string, boolean>;
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

function normalizeSegment(segment: SegmentPayload): SystemPromptSegment | null {
  if (typeof segment?.name !== "string" || !segment.name.trim()) {
    return null;
  }

  return {
    name: segment.name.trim(),
    chars: Math.max(0, Number(segment.chars ?? 0) || 0),
    estimatedTokens: Math.max(
      0,
      Number(segment.estimated_tokens ?? 0) || 0
    ),
    truncated: Boolean(segment.truncated),
  };
}

function mergeSegments(
  summarySegments?: SegmentPayload[] | null,
  statusSegments?: SegmentPayload[] | null
): SystemPromptSegment[] {
  const merged = new Map<string, SystemPromptSegment>();

  for (const rawSegment of statusSegments ?? []) {
    const segment = normalizeSegment(rawSegment);
    if (segment) {
      merged.set(segment.name, segment);
    }
  }

  for (const rawSegment of summarySegments ?? []) {
    const segment = normalizeSegment(rawSegment);
    if (segment) {
      merged.set(segment.name, segment);
    }
  }

  return Array.from(merged.values());
}

function mergeSegmentsPresent(
  segments: SystemPromptSegment[],
  statusPresence?: Record<string, boolean> | null
): Record<string, boolean> {
  const merged: Record<string, boolean> = {};

  for (const [name, isPresent] of Object.entries(statusPresence ?? {})) {
    merged[name] = Boolean(isPresent);
  }

  for (const segment of segments) {
    merged[segment.name] =
      merged[segment.name] ??
      (segment.chars > 0 || segment.estimatedTokens > 0);
  }

  return merged;
}

export async function fetchSystemPromptInspectorSnapshot(
  context: SystemPromptInspectorContext = {}
): Promise<SystemPromptInspectorSnapshot> {
  const params = toRequestParams(context);
  const [statusRes, summaryRes] = await Promise.all([
    api.get<ImprintStatusResponse>("/api/imprint/status", { params }),
    api.get<SystemPromptSummaryResponse>("/api/system_prompt/summary", {
      params,
    }),
  ]);

  const statusData = statusRes.data ?? {};
  const summaryData = summaryRes.data ?? {};
  const segments = mergeSegments(
    summaryData.segments,
    statusData.system_prompt_meta?.segments
  );

  return {
    docsCount:
      summaryData.docs_count ?? statusData.system_prompt_meta?.docs_count ?? null,
    docsTruncated: Boolean(summaryData.docs_truncated),
    estimatedTokensTotal:
      summaryData.estimated_tokens_total ??
      summaryData.estimated_tokens ??
      statusData.system_prompt_meta?.estimated_tokens ??
      null,
    generatedAt:
      typeof summaryData.generated_at === "string"
        ? summaryData.generated_at
        : null,
    imprint: statusData.imprint
      ? {
          createdAt:
            typeof statusData.imprint.created_at === "string"
              ? statusData.imprint.created_at
              : null,
          heatScore:
            typeof statusData.imprint.heat_score === "number"
              ? statusData.imprint.heat_score
              : null,
          id:
            typeof statusData.imprint.id === "number"
              ? statusData.imprint.id
              : null,
          preferredName:
            typeof statusData.imprint.preferred_name === "string"
              ? statusData.imprint.preferred_name
              : null,
          status:
            typeof statusData.imprint.status === "string"
              ? statusData.imprint.status
              : null,
        }
      : null,
    persona: statusData.persona
      ? {
          createdAt:
            typeof statusData.persona.created_at === "string"
              ? statusData.persona.created_at
              : null,
          id:
            typeof statusData.persona.id === "number"
              ? statusData.persona.id
              : null,
          snippet:
            typeof statusData.persona.snippet === "string"
              ? statusData.persona.snippet
              : null,
          source:
            typeof statusData.persona.source === "string"
              ? statusData.persona.source
              : null,
        }
      : null,
    segments,
    segmentsPresent: mergeSegmentsPresent(
      segments,
      statusData.system_prompt_meta?.segments_present
    ),
    threshold: {
      hardTokens:
        typeof summaryData.threshold?.hard_tokens === "number"
          ? summaryData.threshold.hard_tokens
          : null,
      status: summaryData.threshold?.status ?? "unknown",
      warnTokens:
        typeof summaryData.threshold?.warn_tokens === "number"
          ? summaryData.threshold.warn_tokens
          : null,
    },
    warnings: Array.isArray(summaryData.warnings)
      ? summaryData.warnings.filter(
          (warning): warning is string =>
            typeof warning === "string" && warning.trim().length > 0
        )
      : [],
  };
}
