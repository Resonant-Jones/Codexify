import React from "react";

type CandidateFact = {
  confidence: number;
  evidenceSummary: string;
  key: string;
  reviewPosture: string;
  value: string;
};

type VerifiedFact = {
  confidence: number;
  evidenceCount: number;
  key: string;
  updatedAt: string;
  value: string;
};

type HistoryEntry = {
  after: string;
  before: string;
  changedAt: string;
  key: string;
  reason: string;
  kind: "amendment" | "retirement";
};

const CANDIDATE_FACTS: CandidateFact[] = [
  {
    confidence: 0.91,
    evidenceSummary:
      "Imported from a legacy message and matched the location extraction rule.",
    key: "location",
    reviewPosture: "Needs human approval before promotion into the verified vault.",
    value: "Portland, Oregon",
  },
  {
    confidence: 0.67,
    evidenceSummary:
      "Detected from a preference-style sentence; the source trail is thin.",
    key: "favorite_hobby",
    reviewPosture: "Low confidence. Hold in quarantine until corroborated.",
    value: "trail running",
  },
];

const VERIFIED_FACTS: VerifiedFact[] = [
  {
    confidence: 0.98,
    evidenceCount: 3,
    key: "timezone",
    updatedAt: "2026-04-02 14:18 UTC",
    value: "America/New_York",
  },
  {
    confidence: 0.96,
    evidenceCount: 4,
    key: "preferred_name",
    updatedAt: "2026-04-04 09:02 UTC",
    value: "Ari",
  },
];

const HISTORY_ENTRIES: HistoryEntry[] = [
  {
    after: "Portland, Oregon",
    before: "San Jose, California",
    changedAt: "2026-03-28 16:40 UTC",
    key: "location",
    kind: "amendment",
    reason: "User updated the current city after moving.",
  },
  {
    after: "retired",
    before: "Primary mobile number ending in 4412",
    changedAt: "2026-04-04 09:02 UTC",
    key: "contact number",
    kind: "retirement",
    reason: "The old contact route was retired during review.",
  },
];

function ActionChip({ children }: { children: React.ReactNode }) {
  return (
    <button
      type="button"
      className="pill-tab shrink-0 whitespace-nowrap px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] opacity-100"
      style={{
        background: "var(--chip-bg)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      {children}
    </button>
  );
}

function SurfaceCard({
  children,
  label,
  testId,
}: {
  children: React.ReactNode;
  label: string;
  testId?: string;
}) {
  return (
    <section
      className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]"
      data-testid={testId}
      aria-label={label}
    >
      {children}
    </section>
  );
}

function MetaBlock({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="space-y-[calc(var(--radius-micro)/2)]">
      <dt className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
        {label}
      </dt>
      <dd className="text-sm leading-5 text-[var(--text)]">{value}</dd>
    </div>
  );
}

function CandidateCard({ fact }: { fact: CandidateFact }) {
  return (
    <article
      className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] p-[var(--card-pad)]"
      data-testid={`personal-facts-candidate-${fact.key}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
        <div className="space-y-[calc(var(--radius-micro)/2)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Quarantined candidate
          </div>
          <div className="text-sm font-semibold text-[var(--text)]">
            {fact.key}
          </div>
        </div>
        <div className="rounded-full border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] font-medium text-[var(--text)]">
          Confidence {Math.round(fact.confidence * 100)}%
        </div>
      </div>

      <dl className="grid gap-[var(--shell-gap)] md:grid-cols-2">
        <MetaBlock label="Value" value={fact.value} />
        <MetaBlock label="Evidence / source summary" value={fact.evidenceSummary} />
        <MetaBlock
          label="Risk / review posture"
          value={fact.reviewPosture}
        />
        <MetaBlock
          label="Runtime posture"
          value="Quarantined only. Not eligible for retrieval, prompt assembly, or runtime behavior."
        />
      </dl>

      <div className="flex flex-wrap gap-[var(--shell-gap)]">
        <ActionChip>Approve</ActionChip>
        <ActionChip>Edit then approve</ActionChip>
        <ActionChip>Dispute</ActionChip>
        <ActionChip>Delete</ActionChip>
      </div>
    </article>
  );
}

function VerifiedCard({ fact }: { fact: VerifiedFact }) {
  return (
    <article
      className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] p-[var(--card-pad)]"
      data-testid={`personal-facts-verified-${fact.key}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
        <div className="space-y-[calc(var(--radius-micro)/2)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Stable vault slice
          </div>
          <div className="text-sm font-semibold text-[var(--text)]">
            {fact.key}
          </div>
        </div>
        <div className="rounded-full border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] font-medium text-[var(--text)]">
          Active
        </div>
      </div>

      <dl className="grid gap-[var(--shell-gap)] md:grid-cols-2">
        <MetaBlock label="Value" value={fact.value} />
        <MetaBlock
          label="Confidence"
          value={`${Math.round(fact.confidence * 100)}%`}
        />
        <MetaBlock
          label="Evidence count"
          value={fact.evidenceCount.toString()}
        />
        <MetaBlock label="Updated timestamp" value={fact.updatedAt} />
      </dl>

      <div className="flex flex-wrap gap-[var(--shell-gap)]">
        <ActionChip>Amend</ActionChip>
        <ActionChip>View evidence</ActionChip>
        <ActionChip>Retire</ActionChip>
      </div>
    </article>
  );
}

function HistoryCard({ entry }: { entry: HistoryEntry }) {
  return (
    <article
      className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] p-[var(--card-pad)]"
      data-testid={`personal-facts-history-${entry.key}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
        <div className="space-y-[calc(var(--radius-micro)/2)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            {entry.kind}
          </div>
          <div className="text-sm font-semibold text-[var(--text)]">
            {entry.key}
          </div>
        </div>
        <div className="text-[11px] font-medium text-[var(--muted)]">
          {entry.changedAt}
        </div>
      </div>

      <div className="grid gap-[var(--shell-gap)] md:grid-cols-2">
        <div className="space-y-[var(--radius-micro)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Before
          </div>
          <div className="text-sm leading-5 text-[var(--text)]">
            {entry.before}
          </div>
        </div>
        <div className="space-y-[var(--radius-micro)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            After
          </div>
          <div className="text-sm leading-5 text-[var(--text)]">
            {entry.after}
          </div>
        </div>
      </div>

      <div className="space-y-[calc(var(--radius-micro)/2)]">
        <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
          Reason
        </div>
        <p className="text-sm leading-5 text-[var(--text)]">{entry.reason}</p>
      </div>
    </article>
  );
}

export default function PersonalFactsPanel() {
  return (
    <div
      className="space-y-[var(--shell-gap)] text-[var(--text)]"
      data-testid="personal-facts-panel"
    >
      <SurfaceCard label="Personal facts guardrail" testId="personal-facts-guardrail">
        <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
          <div className="space-y-[var(--radius-micro)]">
            <div className="text-sm font-semibold text-[var(--text)]">
              Quarantine before trust
            </div>
            <p className="text-xs leading-5 text-[var(--muted)]">
              Candidate facts must never participate in retrieval, prompt
              assembly, or runtime behavior. Only user-approved, verified,
              active facts are runtime-eligible.
            </p>
          </div>
          <div className="rounded-full border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] font-medium text-[var(--text)]">
            Quarantine only
          </div>
        </div>
      </SurfaceCard>

      <SurfaceCard label="Candidate facts" testId="personal-facts-candidates">
        <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
          <div className="space-y-[var(--radius-micro)]">
            <div className="text-sm font-semibold text-[var(--text)]">
              Candidates
            </div>
            <p className="text-xs leading-5 text-[var(--muted)]">
              Quarantine-state items extracted from evidence. They are visible
              for review but never treated as runtime-trusted.
            </p>
          </div>
          <div className="rounded-full border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] font-medium text-[var(--text)]">
            Not runtime-trusted
          </div>
        </div>

        <div className="space-y-[var(--shell-gap)]">
          {CANDIDATE_FACTS.map((fact) => (
            <CandidateCard key={fact.key} fact={fact} />
          ))}
        </div>
      </SurfaceCard>

      <SurfaceCard label="Verified facts" testId="personal-facts-verified">
        <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
          <div className="space-y-[var(--radius-micro)]">
            <div className="text-sm font-semibold text-[var(--text)]">
              Verified
            </div>
            <p className="text-xs leading-5 text-[var(--muted)]">
              Stable personal facts vault slice. These are approved and
              runtime-eligible until amended or retired.
            </p>
          </div>
          <div className="rounded-full border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] font-medium text-[var(--text)]">
            Runtime eligible
          </div>
        </div>

        <div className="space-y-[var(--shell-gap)]">
          {VERIFIED_FACTS.map((fact) => (
            <VerifiedCard key={fact.key} fact={fact} />
          ))}
        </div>
      </SurfaceCard>

      <SurfaceCard label="Fact history" testId="personal-facts-history">
        <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
          <div className="space-y-[var(--radius-micro)]">
            <div className="text-sm font-semibold text-[var(--text)]">
              History
            </div>
            <p className="text-xs leading-5 text-[var(--muted)]">
              Identity change ledger. Amendments and retirements remain visible
              so fact drift is auditable instead of hidden.
            </p>
          </div>
          <div className="rounded-full border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] font-medium text-[var(--text)]">
            Before / after
          </div>
        </div>

        <div className="space-y-[var(--shell-gap)]">
          {HISTORY_ENTRIES.map((entry) => (
            <HistoryCard key={`${entry.key}-${entry.changedAt}`} entry={entry} />
          ))}
        </div>
      </SurfaceCard>
    </div>
  );
}
