import * as React from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

import useHeartbeatStatus from "@/features/commandCenter/hooks/useHeartbeatStatus";
import type { HeartbeatStatusResponse } from "@/features/commandCenter/api";

type HeartbeatStatusPanelProps = {
  enabled: boolean;
};

function statusTone(s: string): "active" | "attention" | "danger" | "info" | "neutral" | "subtle" {
  switch (s) {
    case "passed": return "active";
    case "warning": return "attention";
    case "failed": return "danger";
    case "missing": return "subtle";
    default: return "neutral";
  }
}

function statusLabel(s: string): string {
  switch (s) {
    case "passed": return "Passed";
    case "warning": return "Warning";
    case "failed": return "Failed";
    case "missing": return "Missing";
    default: return s;
  }
}

export default function HeartbeatStatusPanel({ enabled }: HeartbeatStatusPanelProps) {
  const { status, loading, error, lastCheckedAt, refresh } = useHeartbeatStatus({ enabled });

  if (!enabled) {
    return (
      <Card className="bezel-none w-full border" style={{ borderColor: "var(--panel-border)" }}>
        <CardHeader>
          <CardTitle className="text-base">Heartbeat Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Heartbeat status not enabled.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (loading && !status) {
    return (
      <Card className="bezel-none w-full border" style={{ borderColor: "var(--panel-border)" }}>
        <CardHeader>
          <CardTitle className="text-base">Heartbeat Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm" style={{ color: "var(--muted)" }}>Loading…</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bezel-none w-full border" style={{ borderColor: "var(--panel-border)" }}>
        <CardHeader>
          <CardTitle className="text-base">Heartbeat Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm" style={{ color: "var(--danger)" }}>Error: {error}</p>
          <button onClick={refresh} className="mt-2 text-xs underline" style={{ color: "var(--accent)" }}>
            Retry
          </button>
        </CardContent>
      </Card>
    );
  }

  const s = status as HeartbeatStatusResponse;

  return (
    <Card className="bezel-none w-full border" style={{ borderColor: "var(--panel-border)" }}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Heartbeat Status</CardTitle>
          <div className="flex gap-1.5">
            <Badge tone="subtle" size="sm">Read-only</Badge>
            <Badge tone="subtle" size="sm">Manual-only</Badge>
            <Badge tone="subtle" size="sm">Publishing disabled</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Latest date */}
        <div className="flex items-center justify-between text-sm">
          <span style={{ color: "var(--muted)" }}>Latest run</span>
          <span className="font-mono">{s.latest_date ?? "—"}</span>
        </div>

        {/* Review status */}
        <div className="flex items-center justify-between text-sm">
          <span style={{ color: "var(--muted)" }}>Review</span>
          <Badge tone={statusTone(s.review_status)} size="sm">
            {statusLabel(s.review_status)}
          </Badge>
        </div>

        {/* Outbox status */}
        <div className="flex items-center justify-between text-sm">
          <span style={{ color: "var(--muted)" }}>Outbox</span>
          <Badge tone={statusTone(s.outbox_status)} size="sm">
            {statusLabel(s.outbox_status)}
          </Badge>
        </div>

        {/* Publication */}
        <div className="flex items-center justify-between text-sm">
          <span style={{ color: "var(--muted)" }}>Publication</span>
          <Badge tone="subtle" size="sm">
            {s.publication_enabled ? "Enabled" : "Disabled"}
          </Badge>
        </div>

        {/* Generated files count */}
        <div className="flex items-center justify-between text-sm">
          <span style={{ color: "var(--muted)" }}>Staged files</span>
          <span className="font-mono">{s.generated_files?.length ?? 0}</span>
        </div>

        {/* Report path */}
        {s.heartbeat_report_path && (
          <div className="text-xs font-mono truncate" style={{ color: "var(--muted)" }}>
            {s.heartbeat_report_path}
          </div>
        )}

        {/* Warnings */}
        {s.warnings && s.warnings.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs font-semibold" style={{ color: "var(--attention)" }}>
              Warnings
            </div>
            {s.warnings.map((w, i) => (
              <div key={i} className="text-xs" style={{ color: "var(--muted)" }}>
                • {w}
              </div>
            ))}
          </div>
        )}

        {/* Failures */}
        {s.failures && s.failures.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs font-semibold" style={{ color: "var(--danger)" }}>
              Failures
            </div>
            {s.failures.map((f, i) => (
              <div key={i} className="text-xs" style={{ color: "var(--muted)" }}>
                • {f}
              </div>
            ))}
          </div>
        )}

        {/* Manual command hint */}
        <div className="pt-2 border-t" style={{ borderColor: "var(--panel-border)" }}>
          <div className="text-xs font-semibold mb-1" style={{ color: "var(--muted)" }}>
            Manual command
          </div>
          <code className="block text-xs p-1.5 rounded" style={{
            background: "color-mix(in oklab, var(--panel-bg) 90%, transparent)",
            fontFamily: "monospace",
            wordBreak: "break-all",
          }}>
            {s.manual_commands?.[0] ?? "make heartbeat-full FORCE=1"}
          </code>
        </div>

        {/* Last checked */}
        {lastCheckedAt && (
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            Last checked: {new Date(lastCheckedAt).toLocaleTimeString()}
          </div>
        )}

        {/* Deferred notes */}
        <div className="pt-1">
          <Badge tone="subtle" size="sm">Future: Agent Command Center execution deferred</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
