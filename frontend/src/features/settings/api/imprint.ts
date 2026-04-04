import api from "@/lib/api";

export type ImprintReviewContext = {
  projectId?: number | null;
  threadId?: number;
};

type SystemPromptMetaPayload = {
  docs_count?: number | null;
  estimated_tokens?: number | null;
};

type ImprintStatusResponse = {
  imprint?: {
    created_at?: string | null;
    heat_score?: number | null;
    id?: number | null;
    preferred_name?: string | null;
    status?: string | null;
  } | null;
  persona?: {
    created_at?: string | null;
    id?: number | null;
    snippet?: string | null;
    source?: string | null;
  } | null;
  system_prompt_meta?: SystemPromptMetaPayload | null;
};

type ImprintProposalRecordResponse = {
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
};

type ImprintProposalResponse = {
  imprint_draft?: {
    guardian_name?: string | null;
    heat_score?: number | null;
    id?: number | null;
    preferred_name?: string | null;
    project_id?: number | null;
    status?: string | null;
    user_id?: string | null;
  } | null;
  proposal?: ImprintProposalRecordResponse | null;
  name?: string | null;
  persona_draft?: string | null;
  prompt_metadata?: Record<string, unknown> | null;
};

type AcceptImprintResponse = {
  imprint?: {
    guardian_name?: string | null;
    heat_score?: number | null;
    id?: number | null;
    preferred_name?: string | null;
    status?: string | null;
  } | null;
  persona?: {
    body?: string | null;
    created_at?: string | null;
    id?: number | null;
    is_active?: boolean | null;
    source?: string | null;
  } | null;
};

type RejectImprintResponse = {
  id?: number | null;
  imprint_id?: number | null;
  ok?: boolean | null;
  status?: string | null;
};

export type ImprintReviewStatus = {
  activeImprint: {
    createdAt: string | null;
    heatScore: number | null;
    id: number | null;
    preferredName: string | null;
    status: string | null;
  } | null;
  personaSummary: {
    createdAt: string | null;
    id: number | null;
    snippet: string | null;
    source: string | null;
  } | null;
  promptMeta: {
    docsCount: number | null;
    estimatedTokens: number | null;
  } | null;
};

export type ImprintProposal = {
  imprintDraft: {
    guardianName: string | null;
    heatScore: number | null;
    id: number | null;
    preferredName: string | null;
    projectId: number | null;
    status: string | null;
    userId: string | null;
  } | null;
  name: string | null;
  personaDraft: string | null;
  promptMetadata: Record<string, unknown> | null;
  proposal: {
    generatorVersion: string | null;
    personaDraft: string | null;
    preferredName: string | null;
    projectId: number | null;
    proposalHash: string | null;
    proposalName: string | null;
    proposalVersion: number | null;
    promptMetadata: Record<string, unknown> | null;
    scopeKind: string | null;
    snapshotHash: string | null;
    snapshotVersion: number | null;
    userId: string | null;
  } | null;
};

export type AcceptedImprintReview = {
  imprint: {
    guardianName: string | null;
    heatScore: number | null;
    id: number | null;
    preferredName: string | null;
    status: string | null;
  } | null;
  persona: {
    createdAt: string | null;
    id: number | null;
    isActive: boolean;
    source: string | null;
  } | null;
};

export type RejectedImprintReview = {
  imprintId: number | null;
  ok: boolean;
  status: string | null;
};

function toRequestParams(context: ImprintReviewContext) {
  return {
    ...(context.projectId !== undefined ? { project_id: context.projectId } : {}),
    ...(context.threadId !== undefined ? { thread_id: context.threadId } : {}),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function normalizeStatus(data: ImprintStatusResponse): ImprintReviewStatus {
  return {
    activeImprint: data.imprint
      ? {
          createdAt:
            typeof data.imprint.created_at === "string"
              ? data.imprint.created_at
              : null,
          heatScore:
            typeof data.imprint.heat_score === "number"
              ? data.imprint.heat_score
              : null,
          id:
            typeof data.imprint.id === "number" ? data.imprint.id : null,
          preferredName:
            typeof data.imprint.preferred_name === "string"
              ? data.imprint.preferred_name
              : null,
          status:
            typeof data.imprint.status === "string"
              ? data.imprint.status
              : null,
        }
      : null,
    personaSummary: data.persona
      ? {
          createdAt:
            typeof data.persona.created_at === "string"
              ? data.persona.created_at
              : null,
          id:
            typeof data.persona.id === "number" ? data.persona.id : null,
          snippet:
            typeof data.persona.snippet === "string"
              ? data.persona.snippet
              : null,
          source:
            typeof data.persona.source === "string"
              ? data.persona.source
              : null,
        }
      : null,
    promptMeta: data.system_prompt_meta
      ? {
          docsCount:
            typeof data.system_prompt_meta.docs_count === "number"
              ? data.system_prompt_meta.docs_count
              : null,
          estimatedTokens:
            typeof data.system_prompt_meta.estimated_tokens === "number"
              ? data.system_prompt_meta.estimated_tokens
              : null,
        }
      : null,
  };
}

function normalizeProposal(
  data: ImprintProposalResponse | null | undefined
): ImprintProposal | null {
  if (
    !data ||
    (!data.imprint_draft &&
      !data.persona_draft &&
      !data.name &&
      !data.prompt_metadata &&
      !data.proposal)
  ) {
    return null;
  }

  const proposal = data.proposal ?? null;
  const promptMetadata = isRecord(data.prompt_metadata)
    ? data.prompt_metadata
    : isRecord(proposal?.prompt_metadata)
      ? proposal.prompt_metadata
      : null;

  return {
    imprintDraft: data.imprint_draft
      ? {
          guardianName:
            typeof data.imprint_draft.guardian_name === "string"
              ? data.imprint_draft.guardian_name
              : null,
          heatScore:
            typeof data.imprint_draft.heat_score === "number"
              ? data.imprint_draft.heat_score
              : null,
          id:
            typeof data.imprint_draft.id === "number"
              ? data.imprint_draft.id
              : null,
          preferredName:
            typeof data.imprint_draft.preferred_name === "string"
              ? data.imprint_draft.preferred_name
              : null,
          projectId:
            typeof data.imprint_draft.project_id === "number"
              ? data.imprint_draft.project_id
              : null,
          status:
            typeof data.imprint_draft.status === "string"
              ? data.imprint_draft.status
              : null,
          userId:
            typeof data.imprint_draft.user_id === "string"
              ? data.imprint_draft.user_id
              : null,
        }
      : null,
    name:
      typeof data.name === "string"
        ? data.name
        : typeof proposal?.proposal_name === "string"
          ? proposal.proposal_name
          : null,
    personaDraft:
      typeof data.persona_draft === "string"
        ? data.persona_draft
        : typeof proposal?.persona_draft === "string"
          ? proposal.persona_draft
          : null,
    promptMetadata,
    proposal: proposal
      ? {
          generatorVersion:
            typeof proposal.generator_version === "string"
              ? proposal.generator_version
              : null,
          personaDraft:
            typeof proposal.persona_draft === "string"
              ? proposal.persona_draft
              : null,
          preferredName:
            typeof proposal.preferred_name === "string"
              ? proposal.preferred_name
              : null,
          projectId:
            typeof proposal.project_id === "number"
              ? proposal.project_id
              : null,
          proposalHash:
            typeof proposal.proposal_hash === "string"
              ? proposal.proposal_hash
              : null,
          proposalName:
            typeof proposal.proposal_name === "string"
              ? proposal.proposal_name
              : null,
          proposalVersion:
            typeof proposal.proposal_version === "number"
              ? proposal.proposal_version
              : null,
          promptMetadata,
          scopeKind:
            typeof proposal.scope_kind === "string"
              ? proposal.scope_kind
              : null,
          snapshotHash:
            typeof proposal.snapshot_hash === "string"
              ? proposal.snapshot_hash
              : null,
          snapshotVersion:
            typeof proposal.snapshot_version === "number"
              ? proposal.snapshot_version
              : null,
          userId:
            typeof proposal.user_id === "string" ? proposal.user_id : null,
        }
      : null,
  };
}

function normalizeAcceptedImprint(
  data: AcceptImprintResponse
): AcceptedImprintReview {
  return {
    imprint: data.imprint
      ? {
          guardianName:
            typeof data.imprint.guardian_name === "string"
              ? data.imprint.guardian_name
              : null,
          heatScore:
            typeof data.imprint.heat_score === "number"
              ? data.imprint.heat_score
              : null,
          id:
            typeof data.imprint.id === "number" ? data.imprint.id : null,
          preferredName:
            typeof data.imprint.preferred_name === "string"
              ? data.imprint.preferred_name
              : null,
          status:
            typeof data.imprint.status === "string"
              ? data.imprint.status
              : null,
        }
      : null,
    persona: data.persona
      ? {
          createdAt:
            typeof data.persona.created_at === "string"
              ? data.persona.created_at
              : null,
          id:
            typeof data.persona.id === "number" ? data.persona.id : null,
          isActive: Boolean(data.persona.is_active),
          source:
            typeof data.persona.source === "string"
              ? data.persona.source
              : null,
        }
      : null,
  };
}

function normalizeRejectedImprint(
  data: RejectImprintResponse
): RejectedImprintReview {
  return {
    imprintId:
      typeof data.imprint_id === "number"
        ? data.imprint_id
        : typeof data.id === "number"
        ? data.id
        : null,
    ok: Boolean(data.ok ?? data.status === "rejected"),
    status: typeof data.status === "string" ? data.status : null,
  };
}

export async function fetchImprintReviewStatus(
  context: ImprintReviewContext = {}
): Promise<ImprintReviewStatus> {
  const response = await api.get<ImprintStatusResponse>("/api/imprint/status", {
    params: toRequestParams(context),
  });
  return normalizeStatus(response.data ?? {});
}

export async function requestImprintProposalForReview(
  context: ImprintReviewContext = {}
): Promise<ImprintProposal | null> {
  const response = await api.post<ImprintProposalResponse>(
    "/api/imprint/proposal",
    toRequestParams(context)
  );
  return normalizeProposal(response.data);
}

export async function acceptImprintProposal(
  input: { imprintId: number } & ImprintReviewContext
): Promise<AcceptedImprintReview> {
  const response = await api.post<AcceptImprintResponse>("/api/imprint/accept", {
    imprint_id: input.imprintId,
    ...toRequestParams(input),
  });
  return normalizeAcceptedImprint(response.data ?? {});
}

export async function rejectImprintProposal(
  input: { imprintId: number }
): Promise<RejectedImprintReview> {
  const response = await api.post<RejectImprintResponse>("/api/imprint/reject", {
    imprint_id: input.imprintId,
  });
  return normalizeRejectedImprint(response.data ?? {});
}
