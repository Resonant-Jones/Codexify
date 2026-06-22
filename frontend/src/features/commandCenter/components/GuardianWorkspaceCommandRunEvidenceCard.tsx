import * as React from "react";

import useCodingWorkOrders from "@/features/commandCenter/hooks/useCodingWorkOrders";

/** Read-only command-run evidence card for Guardian Operator Workspace.
 *
 * Derives command-run evidence from existing work-order `latest_run_id` pointers.
 * Does NOT:
 *  - call backend routes beyond existing work-order endpoint
 *  - invoke commands, dispatch, execute, retry, or replay
 *  - create artifacts or receipts
 *  - expose raw args, secrets, prompts, or stack traces
 */
export default function GuardianWorkspaceCommandRunEvidenceCard() {
  const { error, items, loading, refresh } = useCodingWorkOrders({
    enabled: true,
    limit: 10,
  });

  const withRun = React.useMemo(
    () => items.filter((wo) => wo.latest_run_id),
    [items]
  );

  const state = React.useMemo((): "available" | "loading" | "error" | "empty" | "no-pointer" => {
    if (loading) return "loading";
    if (error) return "error";
    if (items.length === 0) return "empty";
    if (withRun.length === 0) return "no-pointer";
    return "available";
  }, [loading, error, items, withRun]);

  return (
    <div data-testid="guardian-workspace-command-run-evidence">
      <p className="text-sm mb-2 leading-5" style={{ color: "var(--muted)" }}>
        Read-only command-run pointers from existing workspace evidence.
        A run pointer does not prove artifact creation, receipt creation,
        Pi/Coder execution, autonomous delegation, or work-order completion.
      </p>

      {/* Loading */}
      {state === "loading" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} role="status">
          Loading command-run evidence…
        </p>
      )}

      {/* Error */}
      {state === "error" && (
        <p className="text-sm" style={{ color: "var(--danger-text)" }} data-testid="cmd-run-error">
          Command-run evidence is unavailable from the current workspace source.
        </p>
      )}

      {/* Empty — no work orders at all */}
      {state === "empty" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} data-testid="cmd-run-empty">
          No command-run evidence is available from current work-order pointers.
        </p>
      )}

      {/* No pointer — work orders exist but no latest_run_id */}
      {state === "no-pointer" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} data-testid="cmd-run-no-pointer">
          Work orders are present, but no latest command-run pointer is recorded.
        </p>
      )}

      {/* Available — show safe fields */}
      {state === "available" && (
        <div className="space-y-2">
          {withRun.map((wo) => (
            <div
              key={wo.work_order_id}
              data-testid={`cmd-run-wo-${wo.work_order_id}`}
              className="text-sm rounded-[var(--tile-radius)] border p-3"
              style={{
                background: "var(--surface-soft)",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
            >
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-1">
                <span className="font-medium">{wo.work_order_id}</span>
                <span className="text-xs" style={{ color: "var(--muted)" }}>
                  {wo.title}
                </span>
                <StateChip status={wo.status} />
              </div>
              <div className="text-xs space-y-0.5" style={{ color: "var(--muted)" }}>
                {wo.latest_run_id && (
                  <div>
                    <span className="font-medium">latest run: </span>
                    {wo.latest_run_id}
                  </div>
                )}
                {wo.latest_lease_id && (
                  <div>
                    <span className="font-medium">latest lease: </span>
                    {wo.latest_lease_id}
                  </div>
                )}
                {wo.latest_receipt_id && (
                  <div>
                    <span className="font-medium">latest receipt: </span>
                    {wo.latest_receipt_id}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Refresh */}
      <div className="mt-3">
        <button
          type="button"
          className="text-xs rounded-[var(--tile-radius)] border px-3 py-1"
          data-testid="cmd-run-refresh"
          style={{
            background: "transparent",
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
            cursor: "pointer",
          }}
          onClick={() => { void refresh(); }}
        >
          Refresh command-run evidence
        </button>
      </div>
    </div>
  );
}

function StateChip({ status }: { status: string }) {
  return (
    <span
      className="text-[11px] font-medium rounded-[var(--tile-radius)] border px-2 py-0.5"
      style={{
        borderColor: "var(--panel-border)",
        color: "var(--muted)",
        background: "var(--surface-soft)",
      }}
    >
      {status}
    </span>
  );
}
