import * as React from "react";

import useCodingWorkOrders from "@/features/commandCenter/hooks/useCodingWorkOrders";

/** Read-only standalone receipt evidence card for Guardian Operator Workspace.
 *
 * Uses existing work-order `latest_receipt_id` pointers from `useCodingWorkOrders`.
 * Richer receipt readback and receipt linkage remain deferred (C05).
 * Does NOT:
 *  - fabricate receipt IDs
 *  - create receipts, artifacts, or completions
 *  - call command invocation or tool execution routes
 *  - expose raw args, secrets, prompts, result_json, or stack traces
 */
export default function GuardianWorkspaceReceiptEvidenceCard() {
  const { error, items, loading, refresh } = useCodingWorkOrders({
    enabled: true,
    limit: 10,
  });

  const withReceipt = React.useMemo(
    () => items.filter((wo) => wo.latest_receipt_id),
    [items]
  );

  const state = React.useMemo((): "available" | "loading" | "error" | "empty" | "no-pointer" => {
    if (loading) return "loading";
    if (error) return "error";
    if (items.length === 0) return "empty";
    if (withReceipt.length === 0) return "no-pointer";
    return "available";
  }, [loading, error, items, withReceipt]);

  return (
    <div data-testid="guardian-workspace-receipt-card">
      <p className="text-sm mb-2 leading-5" style={{ color: "var(--muted)" }}>
        Read-only receipt pointers from existing workspace evidence.
        Receipt evidence does not prove work-order completion, artifact creation,
        Pi/Coder execution, autonomous delegation, recursive tool use, or successful merge.
      </p>

      <p className="text-xs mb-2" style={{ color: "var(--muted)" }} data-testid="rc-deferred">
        Receipt linkage and standalone receipt readback remain deferred.
      </p>

      {/* Loading */}
      {state === "loading" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} role="status" data-testid="rc-loading">
          Loading receipt evidence…
        </p>
      )}

      {/* Error */}
      {state === "error" && (
        <p className="text-sm" style={{ color: "var(--danger-text)" }} data-testid="rc-error">
          Receipt evidence is unavailable from the current workspace source.
        </p>
      )}

      {/* Empty — no work orders at all */}
      {state === "empty" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} data-testid="rc-empty">
          No receipt evidence is available from current work-order pointers.
        </p>
      )}

      {/* No pointer — work orders exist but no latest_receipt_id */}
      {state === "no-pointer" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} data-testid="rc-no-pointer">
          Receipt evidence is unavailable because no explicit receipt pointer is
          present in current workspace evidence.
        </p>
      )}

      {/* Available — show safe fields */}
      {state === "available" && (
        <div className="space-y-2">
          {withReceipt.map((wo) => (
            <div
              key={wo.work_order_id}
              data-testid={`rc-wo-${wo.work_order_id}`}
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
                <span
                  className="text-[11px] font-medium rounded-[var(--tile-radius)] border px-2 py-0.5"
                  style={{
                    borderColor: "var(--panel-border)",
                    color: "var(--muted)",
                    background: "var(--surface-soft)",
                  }}
                >
                  {wo.status}
                </span>
              </div>
              <div className="text-xs space-y-0.5" style={{ color: "var(--muted)" }}>
                {wo.latest_receipt_id && (
                  <div>
                    <span className="font-medium">latest receipt: </span>
                    {wo.latest_receipt_id}
                  </div>
                )}
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
          data-testid="rc-refresh"
          style={{
            background: "transparent",
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
            cursor: "pointer",
          }}
          onClick={() => { void refresh(); }}
        >
          Refresh receipt evidence
        </button>
      </div>
    </div>
  );
}
