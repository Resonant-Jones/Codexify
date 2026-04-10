import { useCallback, useEffect, useRef, useState } from "react";

import api from "@/lib/api";
import type {
  PersonalFactEvidenceRecord,
  PersonalFactRecord,
  PersonalFactRevisionRecord,
} from "@/lib/api";

type PersonalFactsListResponse = {
  ok?: boolean;
  facts?: PersonalFactRecord[];
};

type PersonalFactDetailResponse = {
  ok?: boolean;
  fact?: PersonalFactRecord | null;
  evidence?: PersonalFactEvidenceRecord[];
};

type PersonalFactRevisionsResponse = {
  ok?: boolean;
  revisions?: PersonalFactRevisionRecord[];
};

type PersonalFactMutationBody = {
  confidence?: number;
  reason?: string;
  status?: string;
  value?: string;
};

export type PersonalFactCandidateView = {
  confidenceLabel: string;
  evidence: PersonalFactEvidenceRecord[];
  evidenceCount: number;
  evidenceSummary: string;
  fact: PersonalFactRecord;
  reviewPosture: string;
  runtimePosture: string;
};

export type PersonalFactVerifiedView = {
  confidenceLabel: string;
  evidence: PersonalFactEvidenceRecord[];
  evidenceCount: number;
  evidenceSummary: string;
  fact: PersonalFactRecord;
  runtimePosture: string;
  updatedAtLabel: string;
};

export type PersonalFactHistoryView = {
  action: string;
  after: string;
  before: string;
  factId: number;
  fieldLabel: string;
  id: string;
  key: string;
  kind: "amendment" | "dispute" | "retirement" | "verification";
  reason: string | null;
  timestamp: string | null;
  timestampLabel: string;
};

export type UsePersonalFactsResult = {
  approveCandidate: (factId: number, reason?: string) => Promise<boolean>;
  amendVerified: (
    factId: number,
    value: string,
    reason?: string
  ) => Promise<boolean>;
  busyFactId: number | null;
  candidates: PersonalFactCandidateView[];
  deleteCandidate: (factId: number, reason?: string) => Promise<boolean>;
  disputeCandidate: (factId: number, reason?: string) => Promise<boolean>;
  editThenApproveCandidate: (
    factId: number,
    value: string,
    reason?: string
  ) => Promise<boolean>;
  error: string | null;
  hasLoaded: boolean;
  history: PersonalFactHistoryView[];
  loading: boolean;
  reload: () => Promise<void>;
  retireVerified: (factId: number, reason?: string) => Promise<boolean>;
  quarantinedCount: number;
  runtimePolicySummary: string;
  verified: PersonalFactVerifiedView[];
  verifiedCount: number;
};

const PERSONAL_FACTS_BASE_PATH = "/api/personal-facts";

function personalFactPath(factId: number | string): string {
  return `${PERSONAL_FACTS_BASE_PATH}/${encodeURIComponent(String(factId))}`;
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const response = error.response as {
      data?: { detail?: unknown; error?: unknown };
    };
    if (
      typeof response.data?.detail === "string" &&
      response.data.detail.trim()
    ) {
      return response.data.detail;
    }
    if (
      typeof response.data?.error === "string" &&
      response.data.error.trim()
    ) {
      return response.data.error;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

function clampConfidence(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(1, parsed));
}

function formatConfidenceLabel(value: unknown): string {
  return `${Math.round(clampConfidence(value) * 100)}% confidence`;
}

function toText(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value == null) return "";
  return String(value);
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function trimSnippet(value: string | null | undefined, maxLength = 120): string {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function formatEvidenceSummary(
  evidence: PersonalFactEvidenceRecord[]
): string {
  if (!evidence.length) {
    return "No evidence trail loaded yet.";
  }

  const first = evidence[0];
  const sourceLabel = [first.source_type, first.modality]
    .filter((part) => typeof part === "string" && part.trim())
    .join(" · ");
  const excerpt = trimSnippet(first.excerpt, 96);
  const suffix =
    evidence.length > 1 ? ` (+${evidence.length - 1} more)` : "";

  if (sourceLabel && excerpt) {
    return `${sourceLabel}: ${excerpt}${suffix}`;
  }
  if (sourceLabel) {
    return `${sourceLabel}${suffix}`;
  }
  if (excerpt) {
    return `${excerpt}${suffix}`;
  }
  return `Evidence trail loaded (${evidence.length}).`;
}

function buildRuntimePosture(fact: PersonalFactRecord): string {
  if (fact.status === "verified" && fact.is_active) {
    return "Runtime eligible while active and verified.";
  }
  return "Quarantined only. Not eligible for retrieval, prompt assembly, or runtime behavior.";
}

function buildReviewPosture(
  fact: PersonalFactRecord,
  evidenceCount: number
): string {
  const confidence = clampConfidence(fact.confidence);
  if (fact.status === "disputed") {
    return "Disputed. Keep quarantined until a human review resolves the conflict.";
  }
  if (evidenceCount === 0) {
    return "No evidence trail. Keep quarantined until source material is attached.";
  }
  if (confidence >= 0.9) {
    return "High confidence, but still quarantined until user approval.";
  }
  if (confidence >= 0.7) {
    return "Moderate confidence. Review the source trail before promotion.";
  }
  return "Low confidence. Leave quarantined unless corroborated.";
}

function humanizeFieldName(field: string | null | undefined): string {
  if (!field) return "Change";
  const normalized = field.replace(/_/g, " ").trim();
  if (!normalized) return "Change";
  return normalized
    .split(/\s+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function humanizeStatus(value: string | null | undefined): string {
  const normalized = toText(value).trim();
  if (!normalized) return "—";
  return normalized
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function classifyHistoryKind(
  revision: PersonalFactRevisionRecord
): PersonalFactHistoryView["kind"] {
  const field = revision.field_changed?.trim().toLowerCase() ?? "";
  const action = revision.action.trim().toLowerCase();
  const newValue = revision.new_value?.trim().toLowerCase() ?? "";

  if (field === "status" && newValue === "archived") {
    return "retirement";
  }
  if (field === "status" && newValue === "verified") {
    return "verification";
  }
  if (field === "status" && newValue === "disputed") {
    return "dispute";
  }
  if (action.includes("deactivat")) {
    return "retirement";
  }
  if (action.includes("disput")) {
    return "dispute";
  }
  if (action.includes("confirm") || action.includes("verify")) {
    return "verification";
  }
  return "amendment";
}

function formatRevisionValue(
  field: string | null | undefined,
  value: string | null | undefined
): string {
  if (value == null || value.trim() === "") return "—";
  if ((field?.trim().toLowerCase() ?? "") === "status") {
    return humanizeStatus(value);
  }
  return value;
}

function buildCandidateView(
  fact: PersonalFactRecord,
  evidence: PersonalFactEvidenceRecord[]
): PersonalFactCandidateView {
  return {
    confidenceLabel: formatConfidenceLabel(fact.confidence),
    evidence,
    evidenceCount: evidence.length,
    evidenceSummary: formatEvidenceSummary(evidence),
    fact,
    reviewPosture: buildReviewPosture(fact, evidence.length),
    runtimePosture: buildRuntimePosture(fact),
  };
}

function buildVerifiedView(
  fact: PersonalFactRecord,
  evidence: PersonalFactEvidenceRecord[]
): PersonalFactVerifiedView {
  return {
    confidenceLabel: formatConfidenceLabel(fact.confidence),
    evidence,
    evidenceCount: evidence.length,
    evidenceSummary: formatEvidenceSummary(evidence),
    fact,
    runtimePosture: buildRuntimePosture(fact),
    updatedAtLabel: formatTimestamp(fact.updated_at ?? fact.last_confirmed_at),
  };
}

function buildHistoryView(
  fact: PersonalFactRecord,
  revision: PersonalFactRevisionRecord
): PersonalFactHistoryView {
  return {
    action: revision.action,
    after: formatRevisionValue(
      revision.field_changed,
      revision.new_value ?? null
    ),
    before: formatRevisionValue(
      revision.field_changed,
      revision.old_value ?? null
    ),
    factId: fact.id,
    fieldLabel: humanizeFieldName(revision.field_changed),
    id: `${fact.id}-${revision.id}`,
    key: fact.key,
    kind: classifyHistoryKind(revision),
    reason: revision.reason ?? null,
    timestamp: revision.created_at ?? null,
    timestampLabel: formatTimestamp(revision.created_at),
  };
}

function sortByTimestampDesc(
  left: string | null | undefined,
  right: string | null | undefined
): number {
  const leftTime = left ? Date.parse(left) : NaN;
  const rightTime = right ? Date.parse(right) : NaN;
  const normalizedLeft = Number.isFinite(leftTime) ? leftTime : 0;
  const normalizedRight = Number.isFinite(rightTime) ? rightTime : 0;
  return normalizedRight - normalizedLeft;
}

async function patchPersonalFact(
  factId: number,
  body: PersonalFactMutationBody
): Promise<PersonalFactRecord | null> {
  const response = await api.patch<{
    ok?: boolean;
    fact?: PersonalFactRecord | null;
  }>(personalFactPath(factId), {
    ...(body.value !== undefined ? { value: body.value } : {}),
    ...(body.status !== undefined ? { status: body.status } : {}),
    ...(body.confidence !== undefined ? { confidence: body.confidence } : {}),
    ...(body.reason !== undefined ? { reason: body.reason } : {}),
  });
  return response.data?.fact ?? null;
}

async function postPersonalFactAction(
  factId: number,
  action: "confirm" | "dispute",
  reason?: string
): Promise<PersonalFactRecord | null> {
  const response = await api.post<{
    ok?: boolean;
    fact?: PersonalFactRecord | null;
  }>(
    `${personalFactPath(factId)}/${action}`,
    reason !== undefined ? { reason } : {}
  );
  return response.data?.fact ?? null;
}

export function usePersonalFacts(): UsePersonalFactsResult {
  const [candidates, setCandidates] = useState<PersonalFactCandidateView[]>([]);
  const [verified, setVerified] = useState<PersonalFactVerifiedView[]>([]);
  const [history, setHistory] = useState<PersonalFactHistoryView[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [busyFactId, setBusyFactId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadSeqRef = useRef(0);

  const reload = useCallback(async () => {
    const loadSeq = ++loadSeqRef.current;
    setLoading(true);
    setError(null);

    try {
      const response = await api.get<PersonalFactsListResponse>(
        PERSONAL_FACTS_BASE_PATH,
        {
          params: {
            active_only: false,
            limit: 100,
          },
        }
      );
      const facts = Array.isArray(response.data?.facts)
        ? response.data.facts
        : [];
      const visibleFacts = facts.filter(
        (fact) => fact.status === "candidate" || fact.status === "verified"
      );

      const [detailResults, revisionResults] = await Promise.all([
        Promise.allSettled(
          visibleFacts.map((fact) =>
            api.get<PersonalFactDetailResponse>(personalFactPath(fact.id))
          )
        ),
        Promise.allSettled(
          facts.map((fact) =>
            api.get<PersonalFactRevisionsResponse>(
              `${personalFactPath(fact.id)}/revisions`
            )
          )
        ),
      ]);

      if (loadSeq !== loadSeqRef.current) return;

      const candidateViews: PersonalFactCandidateView[] = [];
      const verifiedViews: PersonalFactVerifiedView[] = [];
      const historyViews: PersonalFactHistoryView[] = [];
      let hadPartialFailure = false;

      visibleFacts.forEach((fact, index) => {
        const detailResult = detailResults[index];
        if (detailResult.status === "rejected") {
          hadPartialFailure = true;
        }

        const detail = detailResult.status === "fulfilled"
          ? detailResult.value.data
          : undefined;
        const resolvedFact = detail?.fact ?? fact;
        const evidence = Array.isArray(detail?.evidence)
          ? detail.evidence
          : [];

        if (resolvedFact.status === "candidate" && resolvedFact.is_active) {
          candidateViews.push(buildCandidateView(resolvedFact, evidence));
        }
        if (resolvedFact.status === "verified" && resolvedFact.is_active) {
          verifiedViews.push(buildVerifiedView(resolvedFact, evidence));
        }
      });

      facts.forEach((fact, index) => {
        const revisionResult = revisionResults[index];
        if (revisionResult.status === "rejected") {
          hadPartialFailure = true;
          return;
        }
        const revisions = Array.isArray(revisionResult.value.data?.revisions)
          ? revisionResult.value.data.revisions
          : [];
        revisions.forEach((revision) => {
          historyViews.push(buildHistoryView(fact, revision));
        });
      });

      candidateViews.sort((left, right) =>
        sortByTimestampDesc(left.fact.updated_at, right.fact.updated_at)
      );
      verifiedViews.sort((left, right) =>
        sortByTimestampDesc(left.fact.updated_at, right.fact.updated_at)
      );
      historyViews.sort((left, right) =>
        sortByTimestampDesc(left.timestamp, right.timestamp)
      );

      setCandidates(candidateViews);
      setVerified(verifiedViews);
      setHistory(historyViews);
      if (hadPartialFailure) {
        setError("Some personal facts details failed to load.");
      }
    } catch (nextError) {
      if (loadSeq !== loadSeqRef.current) return;
      setError(getErrorMessage(nextError, "Failed to load personal facts."));
    } finally {
      if (loadSeq === loadSeqRef.current) {
        setLoading(false);
        setHasLoaded(true);
      }
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const runMutation = useCallback(
    async (
      factId: number,
      mutate: () => Promise<PersonalFactRecord | null>
    ): Promise<boolean> => {
      setBusyFactId(factId);
      setError(null);
      try {
        await mutate();
        await reload();
        return true;
      } catch (nextError) {
        setError(
          getErrorMessage(nextError, "Failed to update personal facts.")
        );
        return false;
      } finally {
        setBusyFactId((current) => (current === factId ? null : current));
      }
    },
    [reload]
  );

  const approveCandidate = useCallback(
    (factId: number, reason?: string) =>
      runMutation(factId, () => postPersonalFactAction(factId, "confirm", reason)),
    [runMutation]
  );

  const editThenApproveCandidate = useCallback(
    (factId: number, value: string, reason?: string) =>
      runMutation(factId, () =>
        patchPersonalFact(factId, {
          reason,
          status: "verified",
          value,
        })
      ),
    [runMutation]
  );

  const disputeCandidate = useCallback(
    (factId: number, reason?: string) =>
      runMutation(factId, () => postPersonalFactAction(factId, "dispute", reason)),
    [runMutation]
  );

  const deleteCandidate = useCallback(
    (factId: number, reason?: string) =>
      runMutation(factId, () =>
        patchPersonalFact(factId, {
          reason,
          status: "archived",
        })
      ),
    [runMutation]
  );

  const amendVerified = useCallback(
    (factId: number, value: string, reason?: string) =>
      runMutation(factId, () =>
        patchPersonalFact(factId, {
          reason,
          status: "verified",
          value,
        })
      ),
    [runMutation]
  );

  const retireVerified = useCallback(
    (factId: number, reason?: string) =>
      runMutation(factId, () =>
        patchPersonalFact(factId, {
          reason,
          status: "archived",
        })
      ),
    [runMutation]
  );

  return {
    approveCandidate,
    amendVerified,
    busyFactId,
    candidates,
    deleteCandidate,
    disputeCandidate,
    editThenApproveCandidate,
    error,
    hasLoaded,
    history,
    loading,
    reload,
    retireVerified,
    quarantinedCount: candidates.length,
    runtimePolicySummary:
      "Only verified, active facts are runtime-eligible. Candidate facts stay quarantined, and retired or disputed facts remain outside runtime use.",
    verified,
    verifiedCount: verified.length,
  };
}

export default usePersonalFacts;
