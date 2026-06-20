import * as React from "react";

import useCodingWorkOrders from "@/features/commandCenter/hooks/useCodingWorkOrders";
import api from "@/lib/api";

/** Read-only standalone tool-turn evidence card for Guardian Operator Workspace.
 *
 * Uses existing C05 tool-turn observability route only when a stable
 * explicit assistant_message_id is available from work-order data.
 * Does NOT:
 *  - fabricate or infer assistant message IDs
 *  - call command invocation or tool execution routes
 *  - create artifacts or receipts
 *  - expose raw args, secrets, prompts, result_json, or stack traces
 */

interface ToolTurnFields {
  tool_turn_id?: string | null;
  tool_turn_state?: string | null;
  loop_stop_reason?: string | null;
  command_run_id?: string | null;
  command_id?: string | null;
  command_status?: string | null;
  command_result_summary?: string | null;
  command_error_summary?: string | null;
  command_blocked_reason?: string | null;
  evidence_durability?: string | null;
}

export default function GuardianWorkspaceToolTurnEvidenceCard() {
  const { error: woError, items, loading: woLoading } = useCodingWorkOrders({
    enabled: true,
    limit: 10,
  });

  const [fetching, setFetching] = React.useState(false);
  const [fetchError, setFetchError] = React.useState<string | null>(null);
  const [data, setData] = React.useState<ToolTurnFields | null>(null);

  // Only accept explicit assistant_message_id from work-order data.
  // Do NOT infer from work_order_id, run_id, receipt_id, or lease_id.
  const assistantMessageId = React.useMemo((): string | null => {
    for (const wo of items) {
      if (wo.assistant_message_id) return wo.assistant_message_id;
    }
    return null;
  }, [items]);

  const state = React.useMemo((): "unavailable" | "loading" | "error" | "empty" | "available" => {
    if (woLoading || fetching) return "loading";
    if (woError || fetchError) return "error";
    if (!assistantMessageId) return "unavailable";
    if (!data) return "loading"; // initial load in progress
    if (data.tool_turn_id == null) return "empty";
    return "available";
  }, [woLoading, fetching, woError, fetchError, assistantMessageId, data]);

  // Fetch tool-turn observability when assistant_message_id is available
  React.useEffect(() => {
    if (!assistantMessageId) return;
    let cancelled = false;
    setFetching(true);
    setFetchError(null);
    api
      .get<Record<string, unknown>>(
        `/api/guardian/commands/tool-turns/${encodeURIComponent(assistantMessageId)}/observability`
      )
      .then((resp) => {
        if (cancelled) return;
        setData(resp.data as unknown as ToolTurnFields);
        setFetching(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFetchError("Tool-turn evidence is unavailable from the current workspace source.");
        setFetching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [assistantMessageId]);

  const handleRefresh = () => {
    if (!assistantMessageId) return;
    setFetching(true);
    setFetchError(null);
    api
      .get<Record<string, unknown>>(
        `/api/guardian/commands/tool-turns/${encodeURIComponent(assistantMessageId)}/observability`
      )
      .then((resp) => {
        setData(resp.data as unknown as ToolTurnFields);
        setFetching(false);
      })
      .catch(() => {
        setFetchError("Tool-turn evidence is unavailable from the current workspace source.");
        setFetching(false);
      });
  };

  return (
    <div data-testid="guardian-workspace-tool-turn-card">
      <p className="text-sm mb-2 leading-5" style={{ color: "var(--muted)" }}>
        Read-only bounded tool-turn evidence from existing C05 observability.
        Tool-turn evidence does not prove autonomous delegation, Pi/Coder execution,
        recursive tool use, artifact creation, receipt creation, or work-order completion.
      </p>

      {/* Loading */}
      {state === "loading" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} role="status" data-testid="tt-loading">
          Loading tool-turn evidence…
        </p>
      )}

      {/* Unavailable — no explicit assistant_message_id */}
      {state === "unavailable" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} data-testid="tt-unavailable">
          Tool-turn evidence is unavailable because no explicit assistant message id
          is present in current workspace evidence.
        </p>
      )}

      {/* Error */}
      {state === "error" && (
        <p className="text-sm" style={{ color: "var(--danger-text)" }} data-testid="tt-error">
          {fetchError || "Tool-turn evidence is unavailable from the current workspace source."}
        </p>
      )}

      {/* Empty — ID present but no tool-turn evidence */}
      {state === "empty" && (
        <p className="text-sm" style={{ color: "var(--muted)" }} data-testid="tt-empty">
          No bounded tool-turn evidence is recorded for this assistant message.
        </p>
      )}

      {/* Available */}
      {state === "available" && data && (
        <div className="space-y-1.5 text-sm" data-testid="tt-available">
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Assistant message: </span>
            <span style={{ color: "var(--text)" }}>{assistantMessageId}</span>
          </div>
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Tool turn: </span>
            <span style={{ color: "var(--text)" }}>{data.tool_turn_id ?? "—"}</span>
          </div>
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>State: </span>
            <span style={{ color: "var(--text)" }}>{data.tool_turn_state ?? "—"}</span>
          </div>
          {data.loop_stop_reason && (
            <div>
              <span className="font-medium" style={{ color: "var(--muted)" }}>Stop reason: </span>
              <span style={{ color: "var(--text)" }}>{data.loop_stop_reason}</span>
            </div>
          )}
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Command run: </span>
            <span style={{ color: "var(--text)" }}>{data.command_run_id ?? "—"}</span>
          </div>
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Command: </span>
            <span style={{ color: "var(--text)" }}>{data.command_id ?? "—"}</span>
          </div>
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Status: </span>
            <span style={{ color: "var(--text)" }}>{data.command_status ?? "—"}</span>
          </div>
          {data.command_result_summary && (
            <div>
              <span className="font-medium" style={{ color: "var(--muted)" }}>Result: </span>
              <span style={{ color: "var(--text)" }}>{data.command_result_summary}</span>
            </div>
          )}
          {data.command_error_summary && (
            <div>
              <span className="font-medium" style={{ color: "var(--muted)" }}>Error: </span>
              <span style={{ color: "var(--danger-text)" }}>{data.command_error_summary}</span>
            </div>
          )}
          <div>
            <span className="font-medium" style={{ color: "var(--muted)" }}>Durability: </span>
            <span style={{ color: "var(--text)" }}>{data.evidence_durability ?? "—"}</span>
          </div>
        </div>
      )}

      {/* Refresh */}
      {assistantMessageId && (
        <div className="mt-3">
          <button
            type="button"
            className="text-xs rounded-[var(--tile-radius)] border px-3 py-1"
            data-testid="tt-refresh"
            style={{
              background: "transparent",
              borderColor: "var(--panel-border)",
              color: "var(--muted)",
              cursor: "pointer",
            }}
            onClick={handleRefresh}
          >
            Refresh tool-turn evidence
          </button>
        </div>
      )}
    </div>
  );
}
