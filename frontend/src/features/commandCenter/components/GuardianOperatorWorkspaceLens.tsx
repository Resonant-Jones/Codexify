import * as React from "react";

/** Read-only Guardian Operator Workspace lens scaffold.
 *
 * This is the first C06 frontend slice. It renders static scaffold cards
 * matching the C06-T002 surface contract zones. Future tasks will compose
 * live evidence cards from existing C03/C05 surfaces.
 *
 * This component does NOT:
 *  - fetch data
 *  - invoke commands
 *  - dispatch, execute, retry, or replay
 *  - create artifacts or receipts
 *  - mutate work-order or command-run state
 *  - expose raw args, secrets, prompts, or stack traces
 */
export default function GuardianOperatorWorkspaceLens() {
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
          Read-only workspace scaffold for Guardian operator truth surfaces.
          This does not dispatch commands, execute Pi/Coder, create artifacts,
          create receipts, or mark work orders complete.
        </p>
      </div>

      {/* Work-order status card */}
      <Card title="Work-order status">
        <CardField label="Operator question" value="What work exists?" />
        <CardField label="Source of truth" value="GET /api/coding/work-orders" />
        <CardChip label="available" />
        <CardField label="Readiness" value="Work-order list exists in CodingWorkOrdersPanel. Safe to compose." />
      </Card>

      {/* Command-run evidence card */}
      <Card title="Command-run evidence">
        <CardField label="Operator question" value="What command ran?" />
        <CardField label="Source of truth" value="GET /api/coding/work-orders/{id}/latest-run → GET /api/guardian/commands/runs/{run_id}" />
        <CardChip label="available" />
        <CardField label="Readiness" value="Backend route exists. No UI card yet. Safe to compose." />
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          CommandRun evidence does not prove autonomous delegation, artifact
          creation, or work-order completion.
        </p>
      </Card>

      {/* Tool-turn observability card */}
      <Card title="Tool-turn observability">
        <CardField label="Operator question" value="What bounded tool-turn evidence exists?" />
        <CardField label="Source of truth" value="GET /api/guardian/commands/tool-turns/{message_id}/observability" />
        <CardChip label="conditional" />
        <CardField
          label="Readiness"
          value="Backend route exists. Conditional on stable assistant_message_id. Safe to compose when ID available."
        />
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Read-only bounded tool-turn evidence. This does not prove autonomous
          delegation, Pi/Coder execution, artifact creation, or work-order
          completion.
        </p>
      </Card>

      {/* Receipt evidence card */}
      <Card title="Receipt evidence">
        <CardField label="Operator question" value="What receipt evidence backs this?" />
        <CardField label="Source of truth" value="GET /api/coding/work-orders/{id}/receipts/{receipt_id}" />
        <CardChip label="available" />
        <CardChip label="deferred" secondary>
          receipt linkage
        </CardChip>
        <CardField
          label="Readiness"
          value="Receipt readback exists in CodingWorkOrdersPanel. Safe to compose. Receipt enrichment deferred."
        />
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Receipt evidence records observed results. This does not prove
          completion, artifact creation, coding-agent execution, or autonomous
          delegation.
        </p>
      </Card>

      {/* Runtime / health card */}
      <Card title="Runtime / health">
        <CardField label="Operator question" value="Can I run?" />
        <CardField label="Source of truth" value="Provider/runtime health verdict (C01/C02)" />
        <CardChip label="available" />
        <CardField
          label="Readiness"
          value="Health verdict exists in HealthOverview lens. Safe to compose."
        />
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Provider and runtime health snapshot. Does not guarantee request
          completion, model availability, or end-to-end execution.
        </p>
      </Card>

      {/* Gaps and unavailable evidence card */}
      <Card title="Gaps and unavailable evidence">
        <CardField label="Receipt linkage" value="Deferred — C03 receipt store not wired in command bus routes." />
        <CardField label="Assistant message ID" value="Conditional — tool-turn observability gated on stable assistant_message_id." />
        <CardField label="EventConsole" value="Not composed — raw event stream not redaction-reviewed for workspace." />
        <CardField label="Workspace composition" value="Not yet wired beyond scaffold. C06-T004+ will compose live surfaces." />
      </Card>

      {/* Safety boundary note */}
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
