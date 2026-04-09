import { Button } from "@/components/ui/button";

import SettingsSectionCard from "@/features/settings/components/SettingsSectionCard";
import useImprintReview from "@/features/settings/hooks/useImprintReview";

function countList(
  metadata: Record<string, unknown> | null,
  key: string
): number | null {
  const value = metadata?.[key];
  return Array.isArray(value) ? value.length : null;
}

function stringValue(
  metadata: Record<string, unknown> | null,
  key: string
): string | null {
  const value = metadata?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function numberValue(
  metadata: Record<string, unknown> | null,
  key: string
): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function shortHash(value: string | null | undefined): string {
  if (!value) return "—";
  if (value.length <= 12) return value;
  return `${value.slice(0, 8)}…${value.slice(-4)}`;
}

type ImprintReviewPanelProps = {
  className?: string;
  projectId?: number | null;
  threadId?: number;
};

export default function ImprintReviewPanel({
  className,
  projectId,
  threadId,
}: ImprintReviewPanelProps) {
  const {
    accepting,
    error,
    loading,
    outcome,
    generateProposal,
    proposal,
    rejectProposal,
    rejecting,
    reviewStatus,
    acceptProposal,
  } = useImprintReview({ projectId, threadId });
  const showErrorNotice = Boolean(error);

  return (
    <div
      className={className ?? ""}
      data-testid="imprint-review-panel"
    >
      <SettingsSectionCard
        eyebrow="Review workspace"
        title="Imprint Review"
        subtitle="Imprint is a persisted style and presentation layer. Persona is the user-editable voice layer. This panel consumes the backend proposal response directly, and the backend result wins over any preview state."
        testId="imprint-review-overview"
      >
        {loading ? (
          <div
            className="rounded-[var(--card-radius)] border border-[var(--panel-border)] px-[var(--card-pad)] py-[calc(var(--card-pad)*0.9)] text-sm text-[var(--muted)]"
            role="status"
          >
            Loading imprint review state…
          </div>
        ) : (
          <div className="space-y-[var(--shell-gap)]">
            <div className="grid gap-[var(--shell-gap)] xl:grid-cols-2">
              <SettingsSectionCard
                eyebrow="Preview / editor"
                title="Active imprint"
                subtitle="The current imprint returned by the backend."
                testId="imprint-active-imprint"
              >
                {reviewStatus?.activeImprint ? (
                  <div className="space-y-[var(--radius-micro)] text-sm text-[var(--text)]">
                    <div>Active imprint available</div>
                    <ul className="flex flex-wrap gap-2 text-xs">
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        ID: {reviewStatus.activeImprint.id ?? "—"}
                      </li>
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Status: {reviewStatus.activeImprint.status ?? "—"}
                      </li>
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Preferred name: {reviewStatus.activeImprint.preferredName ?? "—"}
                      </li>
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Heat: {reviewStatus.activeImprint.heatScore ?? "—"}
                      </li>
                    </ul>
                  </div>
                ) : (
                  <div className="text-sm text-[var(--muted)]">
                    No active imprint
                  </div>
                )}
              </SettingsSectionCard>

              <SettingsSectionCard
                eyebrow="Preview / editor"
                title="Pending proposal"
                subtitle="A proposal enters review only when the backend returns a draft."
                testId="imprint-pending-proposal"
              >
                {proposal?.imprintDraft ? (
                  <div className="space-y-[var(--radius-micro)] text-sm text-[var(--text)]">
                    <div>Proposal available for review</div>
                    <ul className="flex flex-wrap gap-2 text-xs">
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Draft ID: {proposal.imprintDraft.id ?? "—"}
                      </li>
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Status: {proposal.imprintDraft.status ?? "—"}
                      </li>
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Guardian name: {proposal.imprintDraft.guardianName ?? proposal.proposal?.proposalName ?? proposal.name ?? "—"}
                      </li>
                      <li
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Preferred name: {proposal.imprintDraft.preferredName ?? "—"}
                      </li>
                    </ul>
                  </div>
                ) : (
                  <div className="text-sm text-[var(--muted)]">
                    No pending proposal
                  </div>
                )}
              </SettingsSectionCard>
            </div>

            {proposal ? (
              <SettingsSectionCard
                eyebrow="Review / data"
                title="Backend proposal"
                subtitle="Review the backend-generated proposal record before taking a terminal action. This view is consumer-shaped, not the source of truth."
                testId="imprint-backend-proposal"
              >
                <div className="grid gap-[var(--shell-gap)] lg:grid-cols-2">
                  <div
                    className="space-y-2 rounded-[var(--card-radius)] border border-[var(--panel-border)] px-[var(--card-pad)] py-[var(--card-pad)] text-sm"
                    style={{
                      background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
                      color: "var(--text)",
                    }}
                  >
                    <div className="text-xs uppercase tracking-wide opacity-70">
                      Proposal record
                    </div>
                    <div className="text-xs uppercase tracking-wide opacity-70">
                      Proposal name
                    </div>
                    <div className="text-sm font-semibold">
                      {proposal.proposal?.proposalName ?? proposal.name ?? "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      Preferred name:{" "}
                      {proposal.proposal?.preferredName ??
                        proposal.imprintDraft?.preferredName ??
                        "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      Scope: {proposal.proposal?.scopeKind ?? "—"} | Generator:{" "}
                      {proposal.proposal?.generatorVersion ?? "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      Snapshot: {shortHash(proposal.proposal?.snapshotHash)} | Proposal:{" "}
                      {shortHash(proposal.proposal?.proposalHash)}
                    </div>
                  </div>

                  <div
                    className="space-y-2 rounded-[var(--card-radius)] border border-[var(--panel-border)] px-[var(--card-pad)] py-[var(--card-pad)] text-sm"
                    style={{
                      background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
                      color: "var(--text)",
                    }}
                  >
                    <div className="text-xs uppercase tracking-wide opacity-70">
                      Prompt metadata
                    </div>
                    <div className="text-xs opacity-80">
                      Prompt hints: {countList(proposal.promptMetadata, "prompt_hints") ?? "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      Persona hints: {countList(proposal.promptMetadata, "persona_hints") ?? "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      Name hints: {countList(proposal.promptMetadata, "name_hints") ?? "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      Requested depth:{" "}
                      {stringValue(proposal.promptMetadata, "requested_depth") ?? "—"}
                    </div>
                    <div className="text-xs opacity-80">
                      Heat score: {numberValue(proposal.promptMetadata, "heat_score") ?? "—"}
                    </div>
                  </div>
                </div>

                <div
                  className="rounded-[var(--card-radius)] border border-[var(--panel-border)] px-[var(--card-pad)] py-[var(--card-pad)] text-sm whitespace-pre-wrap"
                  style={{
                    background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
                    color: "var(--text)",
                  }}
                >
                  {proposal.proposal?.personaDraft ??
                    proposal.personaDraft ??
                    "No proposal text returned."}
                </div>

                <div
                  className="rounded-[var(--card-radius)] border border-[var(--panel-border)] px-[var(--card-pad)] py-[calc(var(--card-pad)*0.75)] text-sm text-[var(--text)]"
                >
                  Accepting an imprint proposal may also upsert persona as returned
                  by the backend. This panel shows returned metadata only; persona
                  editing stays elsewhere.
                </div>

                <div className="flex flex-wrap justify-end gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    className="border border-[var(--panel-border)]"
                    onClick={() => void generateProposal()}
                    disabled={loading || accepting || rejecting}
                  >
                    {loading ? "Generating…" : "Generate Proposal"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className="border border-rose-400/35 text-rose-200"
                    onClick={() => void rejectProposal()}
                    disabled={accepting || rejecting}
                  >
                    {rejecting ? "Rejecting…" : "Reject"}
                  </Button>
                  <Button
                    type="button"
                    onClick={() => void acceptProposal()}
                    disabled={accepting || rejecting}
                  >
                    {accepting ? "Accepting…" : "Accept"}
                  </Button>
                </div>
              </SettingsSectionCard>
            ) : (
              <SettingsSectionCard
                eyebrow="Review / data"
                title="Backend proposal"
                subtitle="No pending proposal has been returned yet."
                testId="imprint-backend-proposal-empty"
              >
                <div className="text-sm text-[var(--muted)]">No pending proposal</div>
              </SettingsSectionCard>
            )}

            {outcome ? (
              <SettingsSectionCard
                eyebrow="Review outcome"
                title={outcome.message}
                subtitle={
                  outcome.kind === "accepted"
                    ? "The backend accepted the proposal and returned the resulting imprint state."
                    : "The backend rejected the proposal and returned the terminal review result."
                }
                testId="imprint-outcome"
              >
                {outcome.kind === "accepted" && outcome.accepted.persona ? (
                  <ul className="flex flex-wrap gap-2 text-xs text-[var(--text)]">
                    <li
                      className="rounded-full border px-2 py-1"
                      style={{ borderColor: "var(--panel-border)" }}
                    >
                      Persona upsert returned by backend
                    </li>
                    <li
                      className="rounded-full border px-2 py-1"
                      style={{ borderColor: "var(--panel-border)" }}
                    >
                      Persona ID: {outcome.accepted.persona.id ?? "—"}
                    </li>
                    <li
                      className="rounded-full border px-2 py-1"
                      style={{ borderColor: "var(--panel-border)" }}
                    >
                      Source: {outcome.accepted.persona.source ?? "—"}
                    </li>
                    <li
                      className="rounded-full border px-2 py-1"
                      style={{ borderColor: "var(--panel-border)" }}
                    >
                      Active: {outcome.accepted.persona.isActive ? "Yes" : "No"}
                    </li>
                  </ul>
                ) : null}
                {outcome.kind === "rejected" ? (
                  <div className="text-xs text-[var(--muted)]">
                    Imprint ID: {outcome.rejected.imprintId ?? "—"} | Status:{" "}
                    {outcome.rejected.status ?? "rejected"}
                  </div>
                ) : null}
              </SettingsSectionCard>
            ) : null}
          </div>
        )}
      </SettingsSectionCard>

      {showErrorNotice ? (
        <SettingsSectionCard
          eyebrow="Status"
          title="Imprint review issue"
          subtitle="Some review details could not be loaded right now."
          testId="imprint-review-error"
        >
          <p className="text-xs leading-5 text-[var(--muted)]">
            The panel keeps the backend-shaped data that already arrived. Retry
            after the backend recovers.
          </p>
        </SettingsSectionCard>
      ) : null}
    </div>
  );
}
