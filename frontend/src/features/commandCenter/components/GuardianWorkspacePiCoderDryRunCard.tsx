import * as React from "react";

/** Read-only Pi/Coder dry-run validation card for Guardian Operator Workspace.
 *
 * Displays safe dry-run response truth from the validation-only
 * `POST /api/agents/pi-invocation/dry-run` route.
 *
 * Does NOT:
 *  - execute Pi/Coder
 *  - call Pi SDK, Coder, command bus, or workers
 *  - persist records, create receipts/artifacts, or write transcripts
 *  - expose raw payloads, execution controls, or completion verdicts
 */
export default function GuardianWorkspacePiCoderDryRunCard() {
  return (
    <div data-testid="guardian-workspace-pi-coder-dry-run">
      <p className="text-sm mb-2 leading-5" style={{ color: "var(--muted)" }}>
        Validation-only Pi/Coder invocation dry-run.
        Accepted means accepted for dry-run validation only — no execution is
        performed, no data is persisted, and release support remains unsupported.
      </p>

      {/* Static truth labels */}
      <div
        className="flex flex-wrap items-center gap-2 mb-2"
        data-testid="pi-coder-dry-run-labels"
      >
        <span
          className="text-[11px] font-medium rounded-[var(--tile-radius)] border px-2 py-0.5"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
            background: "var(--surface-soft)",
          }}
        >
          Validation only
        </span>
        <span
          className="text-[11px] font-medium rounded-[var(--tile-radius)] border px-2 py-0.5"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
            background: "var(--surface-soft)",
          }}
        >
          No execution performed
        </span>
        <span
          className="text-[11px] font-medium rounded-[var(--tile-radius)] border px-2 py-0.5"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
            background: "var(--surface-soft)",
          }}
        >
          No persistence performed
        </span>
        <span
          className="text-[11px] font-medium rounded-[var(--tile-radius)] border px-2 py-0.5"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
            background: "var(--surface-soft)",
          }}
        >
          Release support: unsupported
        </span>
      </div>

      {/* Acceptance note */}
      <p className="text-xs mb-2 leading-5" style={{ color: "var(--muted)" }}>
        Any accepted result means accepted for dry-run validation only.
        This does not prove autonomous delegation, Pi/Coder execution,
        recursive tool use, artifact creation, receipt creation, or work-order
        completion.
      </p>

      {/* Deferred — the route exists but no interactive surface is wired yet */}
      <p
        className="text-sm rounded-[var(--tile-radius)] border p-3"
        style={{
          background: "var(--surface-soft)",
          borderColor: "var(--panel-border)",
          color: "var(--muted)",
        }}
        data-testid="pi-coder-dry-run-deferred"
      >
        Interactive Pi/Coder dry-run validation is not yet wired.
        The route <code>POST /api/agents/pi-invocation/dry-run</code> exists
        and is validated. Future C04 tasks will add envelope entry and
        response display.
      </p>
    </div>
  );
}
