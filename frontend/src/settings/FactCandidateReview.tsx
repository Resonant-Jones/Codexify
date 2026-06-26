import React from "react";
import {
  fetchPersonalFacts,
  fetchPersonalFactEvidence,
  PersonalFactEvidenceRecord,
  PersonalFactRecord,
  GuardrailMetadata,
  approveFactCandidate,
  rejectFactCandidate,
} from "@/lib/api";

type Props = {
  userId?: string;
};

type ReviewCandidate = PersonalFactRecord & {
  _evidence?: PersonalFactEvidenceRecord[];
};

/** Key patterns that require explicit force_sensitive=true to approve. */
const SENSITIVE_KEY_PATTERNS: readonly string[] = [
  "ssn",
  "password",
  "credit_card",
  "bank",
  "pin",
  "secret",
  "token",
];

function isSensitiveKey(key: string): boolean {
  const lowered = key.toLowerCase();
  return SENSITIVE_KEY_PATTERNS.some(
    (pattern) => lowered.startsWith(pattern) || lowered.includes(pattern)
  );
}

/** Reason label -> readable display map.  Unknown labels fall through safely. */
const REASON_DISPLAY: Record<string, string> = {
  source_role_assistant: "Source role: assistant",
  source_role_system_like: "Source role: system-like",
  source_role_ambiguous: "Source role: ambiguous",
  quoted_or_hypothetical: "Quoted or hypothetical",
  sentence_fragment_key: "Sentence-fragment key",
  excessive_key_length: "Excessive key length",
  invalid_fact_domain: "Invalid fact domain",
  incomplete_value_fragment: "Incomplete value fragment",
  stale_or_time_sensitive: "Stale or time-sensitive",
  contradiction_possible: "Possible contradiction",
  sensitive_identity_like_claim: "Sensitive identity-like claim",
  missing_evidence: "Missing evidence",
  low_confidence: "Low confidence",
  import_noise: "Import noise",
  user_review_required: "User review required",
};

function formatReasonLabel(reason: string): string {
  return REASON_DISPLAY[reason] ?? reason.replace(/_/g, " ");
}

function GuardrailBlock({
  meta,
}: {
  meta: GuardrailMetadata | null | undefined;
}) {
  if (!meta || meta.disposition == null) return null;

  const reasons: string[] = Array.isArray(meta.reasons) ? meta.reasons : [];

  return (
    <div
      className="mt-2 rounded border p-2 space-y-1"
      style={{
        borderColor: "var(--panel-border)",
        background: "var(--surface-alt)",
      }}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className="px-1.5 py-0.5 rounded text-[10px] font-medium"
          style={{
            background:
              meta.disposition === "reviewable"
                ? "var(--accent-bg)"
                : meta.disposition === "quarantine"
                  ? "var(--warning-bg)"
                  : "var(--panel-border)",
            color:
              meta.disposition === "reviewable"
                ? "var(--accent)"
                : meta.disposition === "quarantine"
                  ? "var(--warning)"
                  : "var(--muted)",
          }}
        >
          {meta.disposition}
        </span>
        {meta.promotion_blocked && (
          <span
            className="px-1.5 py-0.5 rounded text-[10px]"
            style={{
              background: "var(--danger-bg)",
              color: "var(--danger)",
            }}
          >
            promotion blocked
          </span>
        )}
        {meta.review_required && (
          <span
            className="px-1.5 py-0.5 rounded text-[10px]"
            style={{ color: "var(--muted)" }}
          >
            review required
          </span>
        )}
      </div>

      {reasons.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap text-[10px]">
          {reasons.map((r) => (
            <span
              key={r}
              className="px-1 py-0.5 rounded"
              style={{
                background: "var(--tag-bg)",
                color: "var(--tag-text)",
              }}
            >
              {formatReasonLabel(r)}
            </span>
          ))}
        </div>
      )}

      {meta.runtime_eligible === false && (
        <div
          className="text-[10px] opacity-60"
          style={{ color: "var(--muted)" }}
        >
          Not runtime-eligible &mdash; candidate remains excluded from
          retrieval, prompt assembly, and runtime behavior.
        </div>
      )}
    </div>
  );
}

function buildEvidenceSummary(
  evidence: PersonalFactEvidenceRecord[] | undefined
): string | null {
  if (!evidence?.length) return null;
  const meta = evidence[0]?.evidence_meta as Record<string, unknown> | undefined;
  const threadId = meta?.thread_id;
  const sourceMsgId = meta?.source_message_id;
  const personaId = meta?.persona_id;
  const parts: string[] = [];
  if (sourceMsgId) parts.push(`msg #${sourceMsgId}`);
  if (threadId) parts.push(`thread #${threadId}`);
  if (personaId) parts.push(`persona: ${personaId}`);
  return parts.length > 0 ? parts.join(" | ") : null;
}

export default function FactCandidateReview({ userId }: Props) {
  const [candidates, setCandidates] = React.useState<ReviewCandidate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [editingId, setEditingId] = React.useState<number | null>(null);
  const [editValue, setEditValue] = React.useState("");
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [sensitiveIds, setSensitiveIds] = React.useState<Set<number>>(
    new Set()
  );
  const [blockedIds, setBlockedIds] = React.useState<Set<number>>(
    new Set()
  );
  const [overrideNote, setOverrideNote] = React.useState("");

  const loadCandidates = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const facts = await fetchPersonalFacts({
        status: "candidate",
        activeOnly: true,
        limit: 200,
      });
      const enriched: ReviewCandidate[] = [];
      const sens = new Set<number>();
      const blocked = new Set<number>();
      for (const fact of facts) {
        try {
          const evidence = await fetchPersonalFactEvidence(fact.id);
          enriched.push({ ...fact, _evidence: evidence });
        } catch {
          enriched.push(fact);
        }
        if (isSensitiveKey(fact.key)) {
          sens.add(fact.id);
        }
        if (fact.guardrail_metadata?.promotion_blocked === true) {
          blocked.add(fact.id);
        }
      }
      setCandidates(enriched);
      setSensitiveIds(sens);
      setBlockedIds(blocked);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to load candidates"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  const handleApprove = async (
    factId: number,
    editedValue?: string,
    opts?: { overrideGuardrail?: boolean; overrideNote?: string }
  ) => {
    setActionError(null);
    const sensitive = sensitiveIds.has(factId);
    const isBlocked = blockedIds.has(factId);
    const requiresOverrideReason = isBlocked || opts?.overrideGuardrail === true;
    const overrideReason = opts?.overrideNote?.trim();

    if (requiresOverrideReason && !overrideReason) {
      setActionError("Override reason is required for blocked candidates.");
      return;
    }

    try {
      await approveFactCandidate(factId, {
        reason: sensitive
          ? "user explicitly approved sensitive candidate"
          : "user approved from review panel",
        value: editedValue?.trim() || undefined,
        force_sensitive: sensitive || undefined,
        override_guardrail: requiresOverrideReason ? true : undefined,
        override_note: requiresOverrideReason ? overrideReason : undefined,
      });
      setCandidates((prev) => prev.filter((c) => c.id !== factId));
      setEditingId(null);
      setEditValue("");
      setOverrideNote("");
    } catch (e: unknown) {
      setActionError(
        e instanceof Error ? e.message : "Approval failed"
      );
    }
  };

  const handleReject = async (factId: number, reason: string) => {
    setActionError(null);
    try {
      await rejectFactCandidate(factId, { reason });
      setCandidates((prev) => prev.filter((c) => c.id !== factId));
    } catch (e: unknown) {
      setActionError(
        e instanceof Error ? e.message : "Rejection failed"
      );
    }
  };

  const startEdit = (fact: ReviewCandidate) => {
    setEditingId(fact.id);
    setEditValue(fact.value);
    setOverrideNote("");
    setActionError(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue("");
    setOverrideNote("");
  };

  return (
    <div
      className="rounded-xl border p-4 space-y-4"
      style={{ borderColor: "var(--panel-border)" }}
    >
      <div className="flex items-center justify-between">
        <div>
          <div
            className="text-sm font-semibold"
            style={{ color: "var(--text)" }}
          >
            Fact Candidates
          </div>
          <div
            className="text-xs opacity-70"
            style={{ color: "var(--muted)" }}
          >
            Review and approve personal facts extracted from chat.
          </div>
        </div>
        <button
          className="px-2 py-1 text-xs rounded border"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--text)",
          }}
          onClick={loadCandidates}
          disabled={loading}
          aria-label="Refresh candidates"
        >
          {loading ? "⟳" : "Refresh"}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="text-xs p-2 rounded"
          style={{ background: "var(--danger-bg)", color: "var(--danger)" }}
        >
          {error}
        </div>
      )}

      {actionError && (
        <div
          role="alert"
          className="text-xs p-2 rounded"
          style={{ background: "var(--danger-bg)", color: "var(--danger)" }}
        >
          {actionError}
        </div>
      )}

      {loading && candidates.length === 0 && (
        <div className="text-xs" style={{ color: "var(--muted)" }}>
          Loading candidates...
        </div>
      )}

      {!loading && candidates.length === 0 && !error && (
        <div className="text-xs" style={{ color: "var(--muted)" }}>
          No pending candidates.
        </div>
      )}

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {candidates.map((fact) => (
          <div
            key={fact.id}
            className="rounded border p-3 space-y-2 text-xs"
            style={{ borderColor: "var(--panel-border)" }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span
                    className="font-mono px-1.5 py-0.5 rounded"
                    style={{
                      background: "var(--tag-bg)",
                      color: "var(--tag-text)",
                    }}
                  >
                    {fact.key}
                  </span>
                  {sensitiveIds.has(fact.id) && (
                    <span
                      className="px-1.5 py-0.5 rounded text-[10px]"
                      style={{
                        background: "var(--danger-bg)",
                        color: "var(--danger)",
                      }}
                    >
                      ⚠ sensitive
                    </span>
                  )}
                  <span className="opacity-50">
                    conf: {(fact.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                {editingId === fact.id ? (
                  <textarea
                    className="w-full rounded border p-1.5 text-xs"
                    style={{
                      borderColor: "var(--panel-border)",
                      color: "var(--text)",
                      background: "var(--input-bg)",
                      minHeight: "48px",
                    }}
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    rows={2}
                    aria-label="Edit fact value"
                  />
                ) : (
                  <div
                    className="opacity-90"
                    style={{ color: "var(--text)" }}
                  >
                    {fact.value}
                  </div>
                )}

                {buildEvidenceSummary(fact._evidence) && (
                  <div className="opacity-50 text-[10px]">
                    {buildEvidenceSummary(fact._evidence)}
                  </div>
                )}

                <GuardrailBlock meta={fact.guardrail_metadata} />

                {blockedIds.has(fact.id) && (
                  <div
                    className="mt-2 text-[10px] opacity-70"
                    style={{ color: "var(--muted)" }}
                  >
                    This candidate is blocked from direct approval. Use edit +
                    override only if you have reviewed and corrected or
                    explicitly confirmed the fact.
                  </div>
                )}

                {blockedIds.has(fact.id) && editingId === fact.id && (
                  <input
                    type="text"
                    className="w-full rounded border p-1 text-xs mt-1"
                    style={{
                      borderColor: "var(--panel-border)",
                      color: "var(--text)",
                      background: "var(--input-bg)",
                    }}
                    value={overrideNote}
                    onChange={(e) => setOverrideNote(e.target.value)}
                    placeholder="Override reason (required)"
                    aria-label="Override reason"
                  />
                )}
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {editingId === fact.id ? (
                <>
                  <button
                    className="px-2 py-0.5 rounded text-[11px] font-medium"
                    style={{
                      background: "var(--accent)",
                      color: "#fff",
                    }}
                    onClick={() =>
                      handleApprove(fact.id, editValue, {
                        overrideNote,
                      })
                    }
                    disabled={
                      blockedIds.has(fact.id) &&
                      editingId === fact.id &&
                      overrideNote.trim().length === 0
                    }
                    aria-label="Save edited value and approve"
                  >
                    {blockedIds.has(fact.id)
                      ? "\u2713 Override & Approve"
                      : "\u2713 Save &amp; Approve"}
                  </button>
                  <button
                    className="px-2 py-0.5 rounded text-[11px]"
                    style={{
                      border: "1px solid var(--panel-border)",
                      color: "var(--muted)",
                    }}
                    onClick={cancelEdit}
                    aria-label="Cancel editing"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  {!blockedIds.has(fact.id) && (
                    <button
                      className="px-2 py-0.5 rounded text-[11px] font-medium"
                      style={{
                        background: "var(--accent)",
                        color: "#fff",
                      }}
                      onClick={() => handleApprove(fact.id)}
                      aria-label={`Approve ${fact.key} candidate`}
                    >
                      \u2713 Approve
                    </button>
                  )}
                  <button
                    className="px-2 py-0.5 rounded text-[11px]"
                    style={{
                      border: "1px solid var(--accent)",
                      color: "var(--accent)",
                    }}
                    onClick={() => startEdit(fact)}
                    aria-label={`Edit ${fact.key} candidate`}
                  >
                    \u270e Edit
                  </button>
                  <button
                    className="px-2 py-0.5 rounded text-[11px]"
                    style={{
                      border: "1px solid var(--panel-border)",
                      color: "var(--muted)",
                    }}
                    onClick={() =>
                      handleReject(fact.id, "rejected from review panel")
                    }
                    aria-label={`Reject ${fact.key} candidate`}
                  >
                    \u2715 Reject
                  </button>
                  {sensitiveIds.has(fact.id) && (
                    <span className="text-[10px] opacity-50">
                      force required
                    </span>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
