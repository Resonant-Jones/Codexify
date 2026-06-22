import * as React from "react";

import { validatePiCoderDryRun } from "@/api/piCoderDryRun";
import type { PiCoderDryRunResponse } from "@/api/piCoderDryRun";

const DEFAULT_ENVELOPE = JSON.stringify(
  {
    guardian_boundary: { owner_account_id: "acct-dry-run-fixture" },
    source_thread_id: "thread-fixture-1",
    source_message_id: "msg-fixture-1",
    invocation_id: "inv-fixture-1",
    harness_id: "harness-fixture-1",
    harness_version: "1.0.0-fixture",
    provider_lane: { provider_lane_class: "local" },
    requested_permissions: [
      { permission: "files.read", resource: "/workspace/fixture", reason: "validate fixture" },
    ],
    granted_permissions: [
      { permission: "files.read", resource: "/workspace/fixture", reason: "validate fixture" },
    ],
    status: "prepared",
  },
  null,
  2,
);

type UiState = "idle" | "loading" | "result";

/** Read-only Pi/Coder dry-run validation card for Guardian Operator Workspace.
 *
 * Wires the `validatePiCoderDryRun` API helper into a read-only operator
 * validation flow. Calls `POST /api/agents/pi-invocation/dry-run`.
 *
 * Does NOT execute Pi/Coder, persist records, create receipts/artifacts,
 * or expose raw payloads, execution controls, or completion verdicts.
 */
export default function GuardianWorkspacePiCoderDryRunCard() {
  const [envelope, setEnvelope] = React.useState(DEFAULT_ENVELOPE);
  const [uiState, setUiState] = React.useState<UiState>("idle");
  const [result, setResult] = React.useState<PiCoderDryRunResponse | null>(null);
  const [fetchError, setFetchError] = React.useState<string | null>(null);

  const handleValidate = async () => {
    setUiState("loading");
    setResult(null);
    setFetchError(null);
    try {
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(envelope);
      } catch {
        setFetchError("Invalid JSON envelope");
        setUiState("idle");
        return;
      }
      const res = await validatePiCoderDryRun({
        source_thread_id: String(payload.source_thread_id || ""),
        source_message_id: String(payload.source_message_id || ""),
        invocation_id: String(payload.invocation_id || ""),
        harness_id: String(payload.harness_id || ""),
        harness_version: String(payload.harness_version || ""),
        guardian_boundary: payload.guardian_boundary as Record<string, unknown> | undefined,
        provider_lane: payload.provider_lane as Record<string, unknown> | undefined,
        requested_permissions: payload.requested_permissions as Array<Record<string, unknown>> | undefined,
        granted_permissions: payload.granted_permissions as Array<Record<string, unknown>> | undefined,
        validation_metadata: payload.validation_metadata as Record<string, unknown> | undefined,
      });
      setResult(res);
      setUiState("result");
    } catch (err: unknown) {
      setFetchError("Dry-run validation is unavailable. No execution was performed.");
      setUiState("idle");
    }
  };

  return (
    <div data-testid="guardian-workspace-pi-coder-dry-run">
      <p className="text-sm mb-2 leading-5" style={{ color: "var(--muted)" }}>
        Validation-only Pi/Coder invocation dry-run.
        Accepted means accepted for dry-run validation only — no execution is
        performed, no data is persisted, and release support remains unsupported.
      </p>

      {/* Truth labels */}
      <div className="flex flex-wrap items-center gap-2 mb-2" data-testid="pi-coder-dry-run-labels">
        <Chip>Validation only</Chip>
        <Chip>Dry-run only</Chip>
        <Chip>No execution performed</Chip>
        <Chip>No persistence performed</Chip>
        <Chip>Release support: unsupported</Chip>
      </div>

      {/* Envelope input */}
      <div className="mb-2">
        <label className="text-xs font-medium block mb-1" style={{ color: "var(--muted)" }}>
          Dry-run envelope (JSON)
        </label>
        <textarea
          data-testid="pi-coder-dry-run-envelope"
          className="w-full rounded-[var(--tile-radius)] border p-2 text-xs font-mono"
          style={{
            background: "var(--surface-soft)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            minHeight: "8rem",
            resize: "vertical",
          }}
          value={envelope}
          onChange={(e) => setEnvelope(e.target.value)}
          spellCheck={false}
        />
      </div>

      {/* Validate button */}
      <button
        type="button"
        data-testid="pi-coder-dry-run-validate"
        className="text-xs rounded-[var(--tile-radius)] border px-3 py-1 mb-3"
        style={{
          background: "transparent",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
          cursor: "pointer",
        }}
        onClick={handleValidate}
        disabled={uiState === "loading"}
      >
        {uiState === "loading" ? "Validating…" : "Validate dry-run"}
      </button>

      {/* Loading */}
      {uiState === "loading" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} role="status" data-testid="pi-coder-dry-run-loading">
          Validating dry-run envelope…
        </p>
      )}

      {/* Error */}
      {fetchError && (
        <p className="text-sm" style={{ color: "var(--danger-text)" }} data-testid="pi-coder-dry-run-error">
          {fetchError}
        </p>
      )}

      {/* Result */}
      {uiState === "result" && result && (
        <div className="space-y-1.5 text-sm" data-testid="pi-coder-dry-run-result">
          <div className={result.accepted ? "" : "font-medium"} style={{ color: result.accepted ? "var(--text)" : "var(--danger-text)" }}>
            {result.accepted ? "Accepted for dry-run validation only" : "Rejected — validation failed"}
          </div>
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Validation status: </span>
            <span style={{ color: "var(--text)" }}>{result.validation_status}</span>
          </div>
          {result.errors.length > 0 && (
            <div>
              <span className="font-medium" style={{ color: "var(--muted)" }}>Errors: </span>
              <span style={{ color: "var(--danger-text)" }}>{result.errors.join(", ")}</span>
            </div>
          )}
          {result.warnings.length > 0 && (
            <div>
              <span className="font-medium" style={{ color: "var(--muted)" }}>Warnings: </span>
              <span style={{ color: "var(--text)" }}>{result.warnings.join(", ")}</span>
            </div>
          )}
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Dry run: </span>
            <span style={{ color: "var(--text)" }}>{String(result.dry_run)}</span>
          </div>
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Execution performed: </span>
            <span style={{ color: "var(--text)" }}>{String(result.execution_performed)}</span>
          </div>
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Persistence performed: </span>
            <span style={{ color: "var(--text)" }}>{String(result.persistence_performed)}</span>
          </div>

          {/* Operator evidence */}
          {result.operator_evidence && (
            <div data-testid="pi-coder-dry-run-operator-evidence" className="mt-2 rounded-[var(--tile-radius)] border p-2" style={{ borderColor: "var(--panel-border)", background: "var(--surface-soft)" }}>
              <div className="text-xs font-medium mb-1" style={{ color: "var(--muted)" }}>Operator evidence</div>
              <EvidenceField label="Evidence state" value={String((result.operator_evidence as Record<string, unknown>).evidence_state ?? "—")} />
              <EvidenceField label="Validation status" value={String((result.operator_evidence as Record<string, unknown>).validation_status ?? "—")} />
              <p className="text-[11px] leading-4 mt-1" style={{ color: "var(--muted)" }}>
                Evidence is read-only validation evidence only. It does not prove execution, receipt creation, artifact creation, or release support.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Acceptance note */}
      <p className="text-xs mt-2 leading-5" style={{ color: "var(--muted)" }}>
        Any accepted result means accepted for dry-run validation only.
        This does not prove autonomous delegation, Pi/Coder execution,
        recursive tool use, artifact creation, receipt creation, or work-order
        completion.
      </p>
    </div>
  );
}

function EvidenceField({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-xs">
      <span className="font-medium" style={{ color: "var(--muted)" }}>{label}: </span>
      <span style={{ color: "var(--text)" }}>{value}</span>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="text-[11px] font-medium rounded-[var(--tile-radius)] border px-2 py-0.5"
      style={{
        borderColor: "var(--panel-border)",
        color: "var(--muted)",
        background: "var(--surface-soft)",
      }}
    >
      {children}
    </span>
  );
}
