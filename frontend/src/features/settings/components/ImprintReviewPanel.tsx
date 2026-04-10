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

  return (
    <SettingsSectionCard
      data-testid="imprint-review-panel"
      className={[
        "space-y-4",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="space-y-1">
        <h2 className="text-base font-semibold" style={{ color: "var(--text)" }}>
          Imprint Review
        </h2>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Imprint is a deeper style and reasoning layer. Persona is the
          user-editable mask or voice layer. This panel consumes the backend
          proposal response directly, and the backend result wins over any
          preview state.
        </p>
      </div>

      {loading ? (
        <div
          className="rounded-xl border px-3 py-4 text-sm"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          role="status"
        >
          Loading imprint review state…
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <section
              className="space-y-2 rounded-xl border p-3"
              style={{ borderColor: "var(--panel-border)" }}
            >
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Active imprint
              </div>
              {reviewStatus?.activeImprint ? (
                <div className="space-y-2 text-sm" style={{ color: "var(--text)" }}>
                  <div>Active imprint available</div>
                  <ul className="flex flex-wrap gap-2 text-xs">
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      ID: {reviewStatus.activeImprint.id ?? "—"}
                    </li>
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Status: {reviewStatus.activeImprint.status ?? "—"}
                    </li>
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Preferred name: {reviewStatus.activeImprint.preferredName ?? "—"}
                    </li>
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Heat: {reviewStatus.activeImprint.heatScore ?? "—"}
                    </li>
                  </ul>
                </div>
              ) : (
                <div className="text-sm" style={{ color: "var(--muted)" }}>
                  No active imprint
                </div>
              )}
            </section>

            <section
              className="space-y-2 rounded-xl border p-3"
              style={{ borderColor: "var(--panel-border)" }}
            >
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Pending proposal
              </div>
              {proposal?.imprintDraft ? (
                <div className="space-y-2 text-sm" style={{ color: "var(--text)" }}>
                  <div>Proposal available for review</div>
                  <ul className="flex flex-wrap gap-2 text-xs">
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Draft ID: {proposal.imprintDraft.id ?? "—"}
                    </li>
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Status: {proposal.imprintDraft.status ?? "—"}
                    </li>
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Guardian name: {proposal.imprintDraft.guardianName ?? proposal.proposal?.proposalName ?? proposal.name ?? "—"}
                    </li>
                    <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Preferred name: {proposal.imprintDraft.preferredName ?? "—"}
                    </li>
                  </ul>
                </div>
              ) : (
                <div className="text-sm" style={{ color: "var(--muted)" }}>
                  No pending proposal
                </div>
              )}
            </section>
          </div>

          {proposal ? (
            <section
              className="space-y-3 rounded-xl border p-3"
              style={{ borderColor: "var(--panel-border)" }}
            >
              <div className="space-y-1">
                <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  Backend proposal
                </div>
                <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
                  Review the backend-generated proposal record before taking a
                  terminal action. This view is consumer-shaped, not the source
                  of truth.
                </p>
              </div>

              <div className="grid gap-3 lg:grid-cols-2">
                <div
                  className="space-y-2 rounded-xl border px-3 py-3 text-sm"
                  style={{
                    borderColor: "var(--panel-border)",
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
                  className="space-y-2 rounded-xl border px-3 py-3 text-sm"
                  style={{
                    borderColor: "var(--panel-border)",
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
                className="rounded-xl border px-3 py-3 text-sm whitespace-pre-wrap"
                style={{
                  borderColor: "var(--panel-border)",
                  background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
                  color: "var(--text)",
                }}
              >
                {proposal.proposal?.personaDraft ??
                  proposal.personaDraft ??
                  "No proposal text returned."}
              </div>

              <div
                className="rounded-xl border px-3 py-2 text-sm"
                style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
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
            </section>
          ) : (
            <section
              className="rounded-xl border px-3 py-3 text-sm"
              style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
            >
              No pending proposal
            </section>
          )}

          {outcome ? (
            <section
              className="space-y-2 rounded-xl border px-3 py-3 text-sm"
              style={{
                borderColor:
                  outcome.kind === "accepted"
                    ? "rgba(34, 197, 94, 0.35)"
                    : "rgba(148, 163, 184, 0.28)",
                background:
                  outcome.kind === "accepted"
                    ? "rgba(34, 197, 94, 0.12)"
                    : "rgba(148, 163, 184, 0.10)",
                color: "var(--text)",
              }}
              role="status"
            >
              <div className="font-medium">{outcome.message}</div>
              {outcome.kind === "accepted" && outcome.accepted.persona ? (
                <ul className="flex flex-wrap gap-2 text-xs">
                  <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                    Persona upsert returned by backend
                  </li>
                  <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                    Persona ID: {outcome.accepted.persona.id ?? "—"}
                  </li>
                  <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                    Source: {outcome.accepted.persona.source ?? "—"}
                  </li>
                  <li className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                    Active: {outcome.accepted.persona.isActive ? "Yes" : "No"}
                  </li>
                </ul>
              ) : null}
              {outcome.kind === "rejected" ? (
                <div className="text-xs opacity-85">
                  Imprint ID: {outcome.rejected.imprintId ?? "—"} | Status:{" "}
                  {outcome.rejected.status ?? "rejected"}
                </div>
              ) : null}
            </section>
          ) : null}
        </>
      )}

      {error ? (
        <div
          className="rounded-xl border px-3 py-2 text-sm"
          style={{
            borderColor: "rgba(239, 68, 68, 0.35)",
            background: "rgba(239, 68, 68, 0.12)",
            color: "var(--text)",
          }}
          role="alert"
        >
          {error}
        </div>
      ) : null}
    </SettingsSectionCard>
  );
}
