import * as React from "react";

import HealthOverview from "@/features/commandCenter/components/HealthOverview";
import CodingWorkOrdersPanel from "@/features/commandCenter/components/CodingWorkOrdersPanel";
import GuardianWorkspaceCommandRunEvidenceCard from "@/features/commandCenter/components/GuardianWorkspaceCommandRunEvidenceCard";
import GuardianWorkspaceToolTurnEvidenceCard from "@/features/commandCenter/components/GuardianWorkspaceToolTurnEvidenceCard";
import GuardianWorkspaceReceiptEvidenceCard from "@/features/commandCenter/components/GuardianWorkspaceReceiptEvidenceCard";
import GuardianWorkspacePiCoderDryRunCard from "@/features/commandCenter/components/GuardianWorkspacePiCoderDryRunCard";
import type { CommandCenterHealthItem } from "@/features/commandCenter/types";

/** Read-only Guardian Operator Workspace lens.
 *
 * C06-T004: Composed live read-only cards from existing Command Center surfaces.
 *
 * This component does NOT:
 *  - fetch data
 *  - invoke commands
 *  - dispatch, execute, retry, or replay
 *  - create artifacts or receipts
 *  - mutate work-order or command-run state
 *  - expose raw args, secrets, prompts, or stack traces
 */

export interface GuardianOperatorWorkspaceLensProps {
  healthItems: CommandCenterHealthItem[];
  lastCheckedAt: number | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
}

export default function GuardianOperatorWorkspaceLens(props: GuardianOperatorWorkspaceLensProps) {
  const { healthItems, lastCheckedAt, loading, onRefresh } = props;

  return (
    <div
      className="space-y-5"
      data-testid="guardian-operator-workspace"
      style={{ color: "var(--text)" }}
    >
      {/* Header */}
      <div
        style={{
          background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
          border: "1px solid var(--panel-border)",
          borderRadius: "var(--tile-radius)",
          padding: "var(--card-pad)",
        }}
      >
        <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
          Guardian Operator Workspace
        </h2>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Read-only workspace for Guardian operator truth surfaces.
          This does not dispatch commands, execute Pi/Coder, create artifacts,
          create receipts, or mark work orders complete.
        </p>
      </div>

      {/* ── Work-order status card (live composition) ── */}
      <Section title="Work-order status">
        <p className="text-sm mb-2" style={{ color: "var(--muted)" }}>
          Existing coding work-order evidence, rendered read-only inside the workspace.
        </p>
        <CodingWorkOrdersPanel />
      </Section>

      {/* ── Command-run evidence card (live composition) ── */}
      <Section title="Command-run evidence">
        <GuardianWorkspaceCommandRunEvidenceCard />
      </Section>

      {/* ── Tool-turn observability card (live composition) ── */}
      <Section title="Tool-turn observability">
        <GuardianWorkspaceToolTurnEvidenceCard />
      </Section>

      {/* ── Receipt evidence card (live composition) ── */}
      <Section title="Receipt evidence">
        <GuardianWorkspaceReceiptEvidenceCard />
      </Section>

      {/* ── Pi/Coder dry-run card ── */}
      <Section title="Pi/Coder dry-run validation">
        <GuardianWorkspacePiCoderDryRunCard />
      </Section>

      {/* ── Runtime / health card (live composition) ── */}
      <Section title="Runtime / health">
        <p className="text-sm mb-2" style={{ color: "var(--muted)" }}>
          Existing Command Center health evidence, rendered read-only inside the workspace.
        </p>
        <HealthOverview
          healthItems={healthItems}
          lastCheckedAt={lastCheckedAt}
          loading={loading}
          onRefresh={onRefresh}
        />
      </Section>

      {/* ── Gaps and unavailable evidence card ── */}
      <Card title="Gaps and unavailable evidence">
        <CardField label="Receipt linkage" value="Deferred — C03 receipt store not wired in command bus routes." />
        <CardField label="Assistant message ID" value="Conditional — tool-turn observability gated on stable assistant_message_id." />
        <CardField label="EventConsole" value="Not composed — raw event stream not redaction-reviewed for workspace." />
        <CardField label="Command-run evidence" value="Not separately composed — deferred to later C06 task." />
        <CardField label="Workspace composition" value="Two live cards composed (work-order + health). Remaining cards deferred." />
      </Card>

      {/* ── Safety boundary note ── */}
      <div
        data-testid="guardian-workspace-safety-boundary"
        style={{
          background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
          border: "1px solid var(--panel-border)",
          borderRadius: "var(--tile-radius)",
          padding: "var(--card-pad)",
        }}
      >
        <h3 className="text-base font-semibold" style={{ color: "var(--text)" }}>
          Safety boundary
        </h3>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm" style={{ color: "var(--muted)" }}>
          <li>No autonomous delegation</li>
          <li>No Pi/Coder execution</li>
          <li>No recursive tool loops</li>
          <li>No artifact creation</li>
          <li>No receipt creation</li>
          <li>No work-order completion semantics</li>
        </ul>
      </div>
    </div>
  );
}

/* ── tiny internal sub-components ── */

function Section({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <div
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        border: "1px solid var(--panel-border)",
        borderRadius: "var(--tile-radius)",
        padding: "var(--card-pad)",
      }}
    >
      <h3 className="text-base font-semibold mb-2" style={{ color: "var(--text)" }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

function Card({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <div
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        border: "1px solid var(--panel-border)",
        borderRadius: "var(--tile-radius)",
        padding: "var(--card-pad)",
      }}
    >
      <h3 className="text-base font-semibold mb-2" style={{ color: "var(--text)" }}>
        {title}
      </h3>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function CardField({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-sm">
      <span className="font-medium" style={{ color: "var(--muted)" }}>
        {label}:{" "}
      </span>
      <span style={{ color: "var(--text)" }}>{value}</span>
    </div>
  );
}

function CardChip({
  label,
  children,
  secondary,
}: {
  label: string;
  children?: React.ReactNode;
  secondary?: boolean;
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs"
      style={{
        background: secondary
          ? "var(--surface-soft)"
          : "color-mix(in oklab, var(--chip-bg) 82%, var(--accent-strong) 18%)",
        border: `1px solid ${secondary ? "var(--panel-border)" : "color-mix(in oklab, var(--accent-strong) 42%, var(--panel-border))"}`,
        borderRadius: "var(--tile-radius)",
        color: "var(--text)",
        padding: "2px 8px",
      }}
    >
      {label}
      {children}
    </span>
  );
}
