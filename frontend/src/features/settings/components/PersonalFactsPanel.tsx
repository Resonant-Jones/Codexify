import {
  type CSSProperties,
  type ComponentType,
  type KeyboardEvent,
  type ReactNode,
  useCallback,
  useRef,
  useState,
} from "react";

import {
  BadgeCheck,
  Eye,
  History,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SettingsSectionCard from "@/features/settings/components/SettingsSectionCard";
import usePersonalFacts, {
  type PersonalFactCandidateView,
  type PersonalFactHistoryView,
  type PersonalFactVerifiedView,
} from "@/features/settings/hooks/usePersonalFacts";

type SectionId = "candidates" | "verified" | "history";

type FactEditorState = {
  factId: number;
  mode: "candidate" | "verified";
  reason: string;
  value: string;
};

type SectionMeta = {
  badge: string;
  description: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  id: SectionId;
  label: string;
};

const SECTION_META: Record<SectionId, SectionMeta> = {
  candidates: {
    badge: "Quarantined",
    description:
      "Candidate facts remain in quarantine until a user explicitly approves them.",
    icon: ShieldAlert,
    id: "candidates",
    label: "Candidates",
  },
  verified: {
    badge: "Runtime eligible",
    description:
      "Verified facts are stable while active and can continue to serve runtime use.",
    icon: BadgeCheck,
    id: "verified",
    label: "Verified",
  },
  history: {
    badge: "Before / after",
    description:
      "History preserves amendments, disputes, and retirements as an identity ledger.",
    icon: History,
    id: "history",
    label: "History",
  },
};

const SECTION_ORDER: SectionId[] = ["candidates", "verified", "history"];

function MetaItem({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="space-y-[calc(var(--radius-micro)/2)]">
      <dt className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
        {label}
      </dt>
      <dd className="break-words text-sm leading-5 text-[var(--text)]">
        {value}
      </dd>
    </div>
  );
}

function SummaryStat({
  icon: Icon,
  label,
  value,
  detail,
  tone,
}: {
  detail: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  label: string;
  tone: "neutral" | "quarantine" | "verified";
  value: string;
}) {
  const toneClass =
    tone === "quarantine"
      ? "bg-[var(--tag-surface)] text-[var(--tag-text)]"
      : tone === "verified"
        ? "bg-[var(--info-surface)] text-[var(--info-text)]"
        : "bg-[var(--chip-bg)] text-[var(--text)]";

  return (
    <div className="space-y-[calc(var(--radius-micro)/1.5)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]">
      <div className="flex items-start justify-between gap-[var(--shell-gap)]">
        <div className="space-y-[calc(var(--radius-micro)/2)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            {label}
          </div>
          <div className="text-2xl font-semibold leading-none text-[var(--text)]">
            {value}
          </div>
        </div>
        <div
          className={[
            "flex h-8 w-8 items-center justify-center rounded-full border border-[var(--panel-border)]",
            toneClass,
          ].join(" ")}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
      <p className="text-xs leading-5 text-[var(--muted)]">{detail}</p>
    </div>
  );
}

function LifecycleChip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full border border-[var(--panel-border)] px-[var(--radius-micro)] py-[calc(var(--radius-micro)/2)] text-[11px] font-medium",
        className ?? "bg-[var(--chip-bg)] text-[var(--text)]",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
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

function isLikelyAbsenceError(message: string | null): boolean {
  if (!message) return false;
  return /(^|\b)(not found|404|no (?:personal facts|history|evidence|proposal)|unavailable)(\b|$)/i.test(
    message
  );
}

function SectionTabRail({
  activeSection,
  onSectionChange,
}: {
  activeSection: SectionId;
  onSectionChange: (section: SectionId) => void;
}) {
  const tabRefs = useRef<Partial<Record<SectionId, HTMLButtonElement | null>>>({});

  const focusSection = useCallback(
    (section: SectionId) => {
      onSectionChange(section);
      tabRefs.current[section]?.focus();
    },
    [onSectionChange]
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
      if (
        event.key !== "ArrowRight" &&
        event.key !== "ArrowLeft" &&
        event.key !== "Home" &&
        event.key !== "End"
      ) {
        return;
      }

      event.preventDefault();

      if (event.key === "Home") {
        focusSection(SECTION_ORDER[0]);
        return;
      }
      if (event.key === "End") {
        focusSection(SECTION_ORDER[SECTION_ORDER.length - 1]);
        return;
      }

      const delta = event.key === "ArrowRight" ? 1 : -1;
      const nextIndex = (index + delta + SECTION_ORDER.length) % SECTION_ORDER.length;
      focusSection(SECTION_ORDER[nextIndex]);
    },
    [focusSection]
  );

  return (
    <div
      role="tablist"
      aria-label="Personal facts sections"
      data-testid="personal-facts-section-tabs"
      className="glass-pill flex w-full items-center overflow-x-auto"
      style={
        {
          "--pill-active-text": "var(--text-on-accent)",
          "--pill-gap": "var(--radius-micro)",
          "--pill-font": "0.82rem",
        } as CSSProperties
      }
    >
      {SECTION_ORDER.map((section, index) => {
        const meta = SECTION_META[section];
        const isActive = section === activeSection;

        return (
          <button
            key={meta.id}
            ref={(node) => {
              tabRefs.current[section] = node;
            }}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`personal-facts-section-${meta.id}`}
            tabIndex={isActive ? 0 : -1}
            data-state={isActive ? "active" : "inactive"}
            data-testid={`personal-facts-section-tab-${meta.id}`}
            className={[
              "pill-tab shrink-0 whitespace-nowrap text-xs transition-opacity",
              isActive
                ? "opacity-100"
                : "opacity-25 hover:opacity-100 focus-visible:opacity-100",
            ].join(" ")}
            style={{
              color: isActive ? "var(--text-on-accent)" : "var(--text)",
            }}
            onClick={() => onSectionChange(section)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {meta.label}
          </button>
        );
      })}
    </div>
  );
}

function LoadingState({
  label,
}: {
  label: string;
}) {
  return (
    <div
      className="rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--card-pad)] py-[calc(var(--card-pad)*1.2)] text-sm text-[var(--muted)]"
      role="status"
    >
      Loading live {label.toLowerCase()}…
    </div>
  );
}

function EmptyState({
  description,
  label,
}: {
  description: string;
  label: string;
}) {
  return (
    <div
      className="space-y-[calc(var(--radius-micro)/2)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--card-pad)] py-[calc(var(--card-pad)*1.1)]"
      role="status"
    >
      <div className="text-sm font-semibold text-[var(--text)]">{label}</div>
      <p className="text-xs leading-5 text-[var(--muted)]">{description}</p>
    </div>
  );
}

function EvidenceTrail({
  evidence,
}: {
  evidence: PersonalFactVerifiedView["evidence"];
}) {
  if (!evidence.length) {
    return (
      <div className="rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] px-[var(--card-pad)] py-[calc(var(--card-pad)*0.9)] text-xs leading-5 text-[var(--muted)]">
        No evidence captured yet.
      </div>
    );
  }

  return (
    <div className="space-y-[var(--shell-gap)]">
      {evidence.map((row) => (
        <article
          key={row.id}
          className="space-y-[calc(var(--radius-micro)/2)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]"
        >
          <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
            <div className="space-y-[calc(var(--radius-micro)/2)]">
              <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                {row.source_type} · {row.modality}
              </div>
              <div className="text-sm font-medium text-[var(--text)]">
                Message {row.source_message_id ?? "—"}
              </div>
            </div>
            <LifecycleChip className="bg-[var(--info-surface)] text-[var(--info-text)]">
              {Math.round(Math.max(0, Math.min(1, row.confidence)) * 100)}%
            </LifecycleChip>
          </div>
          <p className="text-sm leading-5 text-[var(--text)]">
            {row.excerpt?.trim() || "No excerpt recorded."}
          </p>
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            {formatTimestamp(row.created_at)}
          </div>
        </article>
      ))}
    </div>
  );
}

function FactEditor({
  busy,
  label,
  onCancel,
  onReasonChange,
  onSubmit,
  onValueChange,
  reason,
  value,
}: {
  busy: boolean;
  label: string;
  onCancel: () => void;
  onReasonChange: (next: string) => void;
  onSubmit: () => void;
  onValueChange: (next: string) => void;
  reason: string;
  value: string;
}) {
  return (
    <div className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]">
      <div className="space-y-[calc(var(--radius-micro)/2)]">
        <div className="text-sm font-semibold text-[var(--text)]">{label}</div>
        <p className="text-xs leading-5 text-[var(--muted)]">
          Edit the value, then commit the lifecycle update.
        </p>
      </div>

      <label className="block space-y-[calc(var(--radius-micro)/2)]">
        <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
          Value
        </span>
        <Input
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          disabled={busy}
          className="rounded-[var(--tile-radius,19px)]"
        />
      </label>

      <label className="block space-y-[calc(var(--radius-micro)/2)]">
        <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
          Reason
        </span>
        <Textarea
          value={reason}
          onChange={(event) => onReasonChange(event.target.value)}
          rows={3}
          disabled={busy}
          className="rounded-[var(--tile-radius,19px)]"
        />
      </label>

      <div className="flex flex-wrap gap-[var(--shell-gap)]">
        <Button
          type="button"
          onClick={onSubmit}
          disabled={busy}
        >
          {busy ? "Saving…" : label}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}

function CandidateCard({
  busy,
  fact,
  onApprove,
  onDelete,
  onDispute,
  onEdit,
}: {
  busy: boolean;
  fact: PersonalFactCandidateView;
  onApprove: (fact: PersonalFactCandidateView) => void;
  onDelete: (fact: PersonalFactCandidateView) => void;
  onDispute: (fact: PersonalFactCandidateView) => void;
  onEdit: (fact: PersonalFactCandidateView) => void;
}) {
  return (
    <article
      className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] p-[var(--card-pad)]"
      data-testid={`personal-facts-candidate-${fact.fact.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
        <div className="space-y-[calc(var(--radius-micro)/2)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Quarantined candidate
          </div>
          <div className="text-sm font-semibold text-[var(--text)]">
            {fact.fact.key}
          </div>
        </div>
        <div className="flex flex-wrap gap-[var(--radius-micro)]">
          <LifecycleChip className="bg-[var(--tag-surface)] text-[var(--tag-text)]">
            Not runtime-trusted
          </LifecycleChip>
          <LifecycleChip className="bg-[var(--chip-bg)] text-[var(--text)]">
            {fact.confidenceLabel}
          </LifecycleChip>
        </div>
      </div>

      <dl className="grid gap-[var(--shell-gap)] md:grid-cols-2 xl:grid-cols-3">
        <MetaItem label="Key" value={fact.fact.key} />
        <MetaItem label="Value" value={fact.fact.value} />
        <MetaItem label="Confidence" value={fact.confidenceLabel} />
        <MetaItem label="Evidence / source summary" value={fact.evidenceSummary} />
        <MetaItem label="Risk / review posture" value={fact.reviewPosture} />
        <MetaItem label="Runtime posture" value={fact.runtimePosture} />
      </dl>

      <div className="flex flex-wrap gap-[var(--shell-gap)]">
        <Button
          type="button"
          size="sm"
          onClick={() => onApprove(fact)}
          disabled={busy}
        >
          Approve
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => onEdit(fact)}
          disabled={busy}
        >
          Edit then approve
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => onDispute(fact)}
          disabled={busy}
        >
          Dispute
        </Button>
        <Button
          type="button"
          size="sm"
          variant="destructive"
          onClick={() => onDelete(fact)}
          disabled={busy}
        >
          Delete
        </Button>
      </div>
    </article>
  );
}

function VerifiedCard({
  busy,
  fact,
  expanded,
  onAmend,
  onRetire,
  onToggleEvidence,
}: {
  busy: boolean;
  expanded: boolean;
  fact: PersonalFactVerifiedView;
  onAmend: (fact: PersonalFactVerifiedView) => void;
  onRetire: (fact: PersonalFactVerifiedView) => void;
  onToggleEvidence: (factId: number) => void;
}) {
  return (
    <article
      className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] p-[var(--card-pad)]"
      data-testid={`personal-facts-verified-${fact.fact.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
        <div className="space-y-[calc(var(--radius-micro)/2)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Stable vault slice
          </div>
          <div className="text-sm font-semibold text-[var(--text)]">
            {fact.fact.key}
          </div>
        </div>
        <div className="flex flex-wrap gap-[var(--radius-micro)]">
          <LifecycleChip className="bg-[var(--info-surface)] text-[var(--info-text)]">
            Runtime eligible
          </LifecycleChip>
          <LifecycleChip className="bg-[var(--chip-bg)] text-[var(--text)]">
            {fact.evidenceCount} evidence item{fact.evidenceCount === 1 ? "" : "s"}
          </LifecycleChip>
        </div>
      </div>

      <dl className="grid gap-[var(--shell-gap)] md:grid-cols-2 xl:grid-cols-3">
        <MetaItem label="Key" value={fact.fact.key} />
        <MetaItem label="Value" value={fact.fact.value} />
        <MetaItem label="Confidence" value={fact.confidenceLabel} />
        <MetaItem label="Evidence count" value={fact.evidenceCount.toString()} />
        <MetaItem label="Updated timestamp" value={fact.updatedAtLabel} />
        <MetaItem label="Runtime posture" value={fact.runtimePosture} />
      </dl>

      <div className="flex flex-wrap gap-[var(--shell-gap)]">
        <Button
          type="button"
          size="sm"
          onClick={() => onAmend(fact)}
          disabled={busy}
        >
          Amend
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => onToggleEvidence(fact.fact.id)}
          disabled={busy}
        >
          <Eye className="h-4 w-4" aria-hidden="true" />
          <span>View evidence</span>
        </Button>
        <Button
          type="button"
          size="sm"
          variant="destructive"
          onClick={() => onRetire(fact)}
          disabled={busy}
        >
          Retire
        </Button>
      </div>

      {expanded && (
        <div className="space-y-[var(--shell-gap)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Evidence trail
          </div>
          <EvidenceTrail evidence={fact.evidence} />
        </div>
      )}
    </article>
  );
}

function HistoryCard({
  entry,
}: {
  entry: PersonalFactHistoryView;
}) {
  return (
    <article
      className="space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] p-[var(--card-pad)]"
      data-testid={`personal-facts-history-${entry.id}`}
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
        <LifecycleChip className="bg-[var(--chip-bg)] text-[var(--text)]">
          {entry.timestampLabel}
        </LifecycleChip>
      </div>

      <div className="grid gap-[var(--shell-gap)] md:grid-cols-2">
        <div className="space-y-[var(--radius-micro)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Before
          </div>
          <div className="break-words text-sm leading-5 text-[var(--text)]">
            {entry.before}
          </div>
        </div>
        <div className="space-y-[var(--radius-micro)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--chip-bg)] p-[var(--card-pad)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            After
          </div>
          <div className="break-words text-sm leading-5 text-[var(--text)]">
            {entry.after}
          </div>
        </div>
      </div>

      <div className="grid gap-[var(--shell-gap)] md:grid-cols-3">
        <MetaItem label="Field" value={entry.fieldLabel} />
        <MetaItem label="Reason" value={entry.reason ?? "No reason recorded."} />
        <MetaItem label="Action" value={entry.action} />
      </div>
    </article>
  );
}

function SectionContent({
  activeSection,
  busyFactId,
  candidates,
  history,
  loading,
  onApproveCandidate,
  onDeleteCandidate,
  onDisputeCandidate,
  onEditCandidate,
  onEditVerified,
  onRetireVerified,
  onToggleEvidence,
  expandedEvidenceFactId,
  verified,
}: {
  activeSection: SectionId;
  busyFactId: number | null;
  candidates: PersonalFactCandidateView[];
  history: PersonalFactHistoryView[];
  loading: boolean;
  onApproveCandidate: (fact: PersonalFactCandidateView) => Promise<void>;
  onDeleteCandidate: (fact: PersonalFactCandidateView) => Promise<void>;
  onDisputeCandidate: (fact: PersonalFactCandidateView) => Promise<void>;
  onEditCandidate: (fact: PersonalFactCandidateView) => void;
  onEditVerified: (fact: PersonalFactVerifiedView) => void;
  onRetireVerified: (fact: PersonalFactVerifiedView) => Promise<void>;
  onToggleEvidence: (factId: number) => void;
  expandedEvidenceFactId: number | null;
  verified: PersonalFactVerifiedView[];
}) {
  const meta = SECTION_META[activeSection];
  const sectionHeading =
    activeSection === "verified" ? "Verified vault" : meta.label;

  if (loading && !candidates.length && !verified.length && !history.length) {
    return <LoadingState label={meta.label} />;
  }

  if (activeSection === "candidates") {
    return (
      <SettingsSectionCard
        eyebrow="Review surface"
        title={sectionHeading}
        subtitle={meta.description}
        actions={
          <LifecycleChip className="bg-[var(--tag-surface)] text-[var(--tag-text)]">
            {meta.badge}
          </LifecycleChip>
        }
        testId="personal-facts-section-candidates"
      >
        {candidates.length ? (
          <div className="space-y-[var(--shell-gap)]">
            {candidates.map((fact) => (
              <CandidateCard
                key={fact.fact.id}
                busy={busyFactId === fact.fact.id}
                fact={fact}
                onApprove={onApproveCandidate}
                onDelete={onDeleteCandidate}
                onDispute={onDisputeCandidate}
                onEdit={onEditCandidate}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            label="No candidate facts yet"
            description="This quarantine queue is empty. When the backend returns real candidate facts, they will appear here automatically."
          />
        )}
      </SettingsSectionCard>
    );
  }

  if (activeSection === "verified") {
    return (
      <SettingsSectionCard
        eyebrow="Review surface"
        title={sectionHeading}
        subtitle={meta.description}
        actions={
          <LifecycleChip className="bg-[var(--info-surface)] text-[var(--info-text)]">
            {meta.badge}
          </LifecycleChip>
        }
        testId="personal-facts-section-verified"
      >
        {verified.length ? (
          <div className="space-y-[var(--shell-gap)]">
            {verified.map((fact) => (
              <VerifiedCard
                key={fact.fact.id}
                busy={busyFactId === fact.fact.id}
                expanded={expandedEvidenceFactId === fact.fact.id}
                fact={fact}
                onAmend={onEditVerified}
                onRetire={onRetireVerified}
                onToggleEvidence={onToggleEvidence}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            label="No verified facts yet"
            description="Once the backend returns approved facts, this stable vault slice will populate automatically."
          />
        )}
      </SettingsSectionCard>
    );
  }

  return (
    <SettingsSectionCard
      eyebrow="Review surface"
      title={sectionHeading}
      subtitle={meta.description}
      actions={
        <LifecycleChip className="bg-[var(--chip-bg)] text-[var(--text)]">
          {meta.badge}
        </LifecycleChip>
      }
      testId="personal-facts-section-history"
    >
      {history.length ? (
        <div className="space-y-[var(--shell-gap)]">
          {history.map((entry) => (
            <HistoryCard key={entry.id} entry={entry} />
          ))}
        </div>
      ) : (
        <EmptyState
          label="No history entries yet"
          description="Amendments, disputes, and retirements will appear here once the backend returns revision rows."
        />
      )}
    </SettingsSectionCard>
  );
}

export default function PersonalFactsPanel() {
  const {
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
    retireVerified,
    quarantinedCount,
    runtimePolicySummary,
    verified,
    verifiedCount,
  } = usePersonalFacts();

  const [activeSection, setActiveSection] = useState<SectionId>("candidates");
  const [editingFact, setEditingFact] = useState<FactEditorState | null>(null);
  const [expandedEvidenceFactId, setExpandedEvidenceFactId] = useState<
    number | null
  >(null);

  const clearEditor = useCallback(() => {
    setEditingFact(null);
  }, []);

  const handleApproveCandidate = useCallback(
    async (fact: PersonalFactCandidateView) => {
      const next = await approveCandidate(fact.fact.id);
      if (next) {
        clearEditor();
        setExpandedEvidenceFactId(null);
      }
    },
    [approveCandidate, clearEditor]
  );

  const handleEditCandidate = useCallback(
    (fact: PersonalFactCandidateView) => {
      setEditingFact({
        factId: fact.fact.id,
        mode: "candidate",
        reason: "",
        value: fact.fact.value,
      });
      setActiveSection("candidates");
    },
    []
  );

  const handleCandidateDispute = useCallback(
    async (fact: PersonalFactCandidateView) => {
      const next = await disputeCandidate(fact.fact.id);
      if (next) {
        clearEditor();
        setExpandedEvidenceFactId(null);
      }
    },
    [clearEditor, disputeCandidate]
  );

  const handleCandidateDelete = useCallback(
    async (fact: PersonalFactCandidateView) => {
      const next = await deleteCandidate(fact.fact.id);
      if (next) {
        clearEditor();
        setExpandedEvidenceFactId(null);
      }
    },
    [clearEditor, deleteCandidate]
  );

  const handleSaveCandidateEdit = useCallback(async () => {
    if (!editingFact || editingFact.mode !== "candidate") {
      return;
    }
    const next = await editThenApproveCandidate(
      editingFact.factId,
      editingFact.value,
      editingFact.reason.trim() || undefined
    );
    if (next) {
      clearEditor();
      setExpandedEvidenceFactId(null);
    }
  }, [clearEditor, editThenApproveCandidate, editingFact]);

  const handleEditVerified = useCallback(
    (fact: PersonalFactVerifiedView) => {
      setEditingFact({
        factId: fact.fact.id,
        mode: "verified",
        reason: "",
        value: fact.fact.value,
      });
      setActiveSection("verified");
    },
    []
  );

  const handleSaveVerifiedEdit = useCallback(async () => {
    if (!editingFact || editingFact.mode !== "verified") {
      return;
    }
    const next = await amendVerified(
      editingFact.factId,
      editingFact.value,
      editingFact.reason.trim() || undefined
    );
    if (next) {
      clearEditor();
      setExpandedEvidenceFactId(null);
    }
  }, [amendVerified, clearEditor, editingFact]);

  const handleRetireVerified = useCallback(
    async (fact: PersonalFactVerifiedView) => {
      const next = await retireVerified(fact.fact.id);
      if (next) {
        clearEditor();
        setExpandedEvidenceFactId(null);
      }
    },
    [clearEditor, retireVerified]
  );

  const loadingLabel = loading
    ? hasLoaded
      ? "Refreshing live personal facts…"
      : "Loading live personal facts…"
    : "Live backend data only.";
  const hasAbsenceLikeError = isLikelyAbsenceError(error);
  const showErrorNotice = Boolean(error) && !hasAbsenceLikeError;
  const showAvailabilityNotice =
    hasAbsenceLikeError && !candidates.length && !verified.length && !history.length;

  return (
    <div
      className="min-w-0 space-y-[var(--shell-gap)] text-[var(--text)]"
      data-testid="personal-facts-panel"
    >
      <SettingsSectionCard
        eyebrow="Summary / policy"
        title="Personal Facts"
        subtitle="A compact lifecycle surface for quarantine, approval, amendment, and retirement. Live backend data only."
        testId="personal-facts-summary"
      >
        <div className="grid gap-[var(--shell-gap)] md:grid-cols-3">
          <SummaryStat
            icon={ShieldAlert}
            label="Quarantined"
            value={loading && !hasLoaded ? "—" : quarantinedCount.toString()}
            detail="Candidate facts stay isolated until a user approves them."
            tone="quarantine"
          />
          <SummaryStat
            icon={BadgeCheck}
            label="Verified facts"
            value={loading && !hasLoaded ? "—" : verifiedCount.toString()}
            detail="Approved facts remain runtime-eligible while active."
            tone="verified"
          />
          <SummaryStat
            icon={ShieldCheck}
            label="Runtime policy"
            value="Active"
            detail={runtimePolicySummary}
            tone="neutral"
          />
        </div>

        <div className="space-y-[calc(var(--radius-micro)/2)]">
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
            Lifecycle guide
          </div>
          <div className="flex flex-wrap gap-[var(--radius-micro)]">
            <LifecycleChip className="bg-[var(--tag-surface)] text-[var(--tag-text)]">
              Quarantine
            </LifecycleChip>
            <LifecycleChip className="bg-[var(--info-surface)] text-[var(--info-text)]">
              Verified facts
            </LifecycleChip>
            <LifecycleChip className="bg-[var(--chip-bg)] text-[var(--text)]">
              Amended / history
            </LifecycleChip>
            <LifecycleChip className="bg-[var(--danger-surface)] text-[var(--danger-text)]">
              Retired
            </LifecycleChip>
          </div>
        </div>

        <div className="text-xs leading-5 text-[var(--muted)]">{loadingLabel}</div>
      </SettingsSectionCard>

      <SettingsSectionCard
        eyebrow="Rule / guardrail"
        title="Quarantine before trust"
        subtitle="Candidate facts must never participate in retrieval, prompt assembly, or runtime behavior. Only user-approved, verified, active facts are runtime-eligible."
        actions={
          <LifecycleChip className="bg-[var(--tag-surface)] text-[var(--tag-text)]">
            Quarantine only
          </LifecycleChip>
        }
        testId="personal-facts-guardrail"
      />

      {showAvailabilityNotice ? (
        <SettingsSectionCard
          eyebrow="Status"
          title="No personal facts yet"
          subtitle="The backend has not returned any personal-facts rows for this workspace yet."
          testId="personal-facts-availability"
        >
          <p className="text-xs leading-5 text-[var(--muted)]">
            Candidate, verified, and history surfaces will populate automatically
            when live data arrives.
          </p>
        </SettingsSectionCard>
      ) : null}

      <SectionTabRail
        activeSection={activeSection}
        onSectionChange={setActiveSection}
      />

      {showErrorNotice ? (
        <SettingsSectionCard
          eyebrow="Status"
          title="Personal facts load issue"
          subtitle="Some personal facts details could not be loaded right now."
          testId="personal-facts-error"
        >
          <p className="text-xs leading-5 text-[var(--muted)]">
            The panel will keep showing the data that did arrive. You can try
            again after the backend recovers.
          </p>
        </SettingsSectionCard>
      ) : null}

      {editingFact && (
        <FactEditor
          busy={busyFactId === editingFact.factId}
          label={
            editingFact.mode === "candidate"
              ? "Edit candidate then approve"
              : "Amend verified fact"
          }
          onCancel={clearEditor}
          onReasonChange={(next) =>
            setEditingFact((current) =>
              current && current.factId === editingFact.factId
                ? { ...current, reason: next }
                : current
            )
          }
          onSubmit={() =>
            editingFact.mode === "candidate"
              ? void handleSaveCandidateEdit()
              : void handleSaveVerifiedEdit()
          }
          onValueChange={(next) =>
            setEditingFact((current) =>
              current && current.factId === editingFact.factId
                ? { ...current, value: next }
                : current
            )
          }
          reason={editingFact.reason}
          value={editingFact.value}
        />
      )}

      <SectionContent
        activeSection={activeSection}
        busyFactId={busyFactId}
        candidates={candidates}
        history={history}
        loading={loading}
        onApproveCandidate={handleApproveCandidate}
        onDeleteCandidate={handleCandidateDelete}
        onDisputeCandidate={handleCandidateDispute}
        onEditCandidate={handleEditCandidate}
        onEditVerified={handleEditVerified}
        onRetireVerified={handleRetireVerified}
        onToggleEvidence={(factId) =>
          setExpandedEvidenceFactId((current) =>
            current === factId ? null : factId
          )
        }
        expandedEvidenceFactId={expandedEvidenceFactId}
        verified={verified}
      />
    </div>
  );
}
