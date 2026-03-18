import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import type { CommandCenterApproval } from "@/features/commandCenter/types";

type ApprovalsPanelProps = {
  approvals: CommandCenterApproval[];
  onSelectRun: (runKey: string | null) => void;
  selectedRunKey: string | null;
};

function formatTimestamp(value: number): string {
  return new Date(value).toLocaleString();
}

export default function ApprovalsPanel({
  approvals,
  onSelectRun,
  selectedRunKey,
}: ApprovalsPanelProps) {
  return (
    <Card
      className="bezel-none rounded-2xl border"
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="space-y-1">
        <CardTitle className="text-base" style={{ color: "var(--text)" }}>
          Approvals
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Escalation-facing events filtered from the same global SSE stream.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {approvals.length === 0 ? (
          <div className="rounded-xl border px-4 py-5 text-sm" style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            No approval or clarification events detected yet.
          </div>
        ) : (
          approvals.map((approval) => {
            const selectable = Boolean(approval.runKey);
            const selected =
              selectable && approval.runKey != null && approval.runKey === selectedRunKey;

            return (
              <button
                key={approval.key}
                type="button"
                className="w-full text-left"
                onClick={() => onSelectRun(approval.runKey)}
                disabled={!selectable}
              >
                <Card
                  className={cn(
                    "bezel-none rounded-xl border transition-colors",
                    selected && "ring-1 ring-[var(--accent)]"
                  )}
                  style={{
                    background:
                      "color-mix(in srgb, rgba(250, 204, 21, 0.08) 80%, var(--panel-bg))",
                    borderColor: selected ? "var(--accent)" : "var(--panel-border)",
                    opacity: selectable ? 1 : 0.72,
                  }}
                >
                  <CardContent className="space-y-3 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                          {approval.label}
                        </div>
                        <div className="text-xs" style={{ color: "var(--muted)" }}>
                          {approval.summary}
                        </div>
                      </div>
                      <Badge
                        className="border"
                        style={{
                          background: "rgba(250, 204, 21, 0.14)",
                          borderColor: "rgba(250, 204, 21, 0.35)",
                          color: "var(--text)",
                        }}
                      >
                        {approval.status ?? "attention"}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
                      <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                        Task: {approval.taskId ?? "—"}
                      </span>
                      <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                        Run: {approval.runId ?? "—"}
                      </span>
                      <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                        Seen: {formatTimestamp(approval.receivedAt)}
                      </span>
                      <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                        {selectable ? "Selectable" : "No run selection available"}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </button>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
