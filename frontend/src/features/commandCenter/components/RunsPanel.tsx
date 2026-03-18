import type { CSSProperties } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import type { CommandCenterRun } from "@/features/commandCenter/types";

type RunsPanelProps = {
  onSelectRun: (run: CommandCenterRun) => void;
  runs: CommandCenterRun[];
  selectedRunKey: string | null;
};

function formatTimestamp(value: number | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

function renderStatusStyle(status: CommandCenterRun["status"]): CSSProperties {
  switch (status) {
    case "running":
      return {
        background: "rgba(59, 130, 246, 0.12)",
        borderColor: "rgba(59, 130, 246, 0.35)",
      };
    case "succeeded":
      return {
        background: "rgba(34, 197, 94, 0.12)",
        borderColor: "rgba(34, 197, 94, 0.35)",
      };
    case "failed":
      return {
        background: "rgba(239, 68, 68, 0.12)",
        borderColor: "rgba(239, 68, 68, 0.35)",
      };
    case "needs_attention":
      return {
        background: "rgba(250, 204, 21, 0.12)",
        borderColor: "rgba(250, 204, 21, 0.35)",
      };
    default:
      return {
        background: "rgba(148, 163, 184, 0.12)",
        borderColor: "rgba(148, 163, 184, 0.28)",
      };
  }
}

function RunRow({
  onSelectRun,
  run,
  selected,
}: {
  onSelectRun: (run: CommandCenterRun) => void;
  run: CommandCenterRun;
  selected: boolean;
}) {
  const displayId = run.taskId ?? run.runId ?? run.key;

  return (
    <button
      type="button"
      onClick={() => onSelectRun(run)}
      className="w-full text-left"
    >
      <Card
        className={cn(
          "bezel-none rounded-xl border transition-colors",
          selected && "ring-1 ring-[var(--accent)]"
        )}
        style={{
          background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
          borderColor: selected ? "var(--accent)" : "var(--panel-border)",
        }}
      >
        <CardContent className="space-y-3 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                {displayId}
              </div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {run.summary}
              </div>
            </div>
            <Badge
              className="border"
              style={{
                ...renderStatusStyle(run.status),
                color: "var(--text)",
              }}
            >
              {run.status.replace(/_/g, " ")}
            </Badge>
          </div>

          <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Task: {run.taskId ?? "—"}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Run: {run.runId ?? "—"}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Events: {run.eventCount}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Last type: {run.lastType ?? run.lastKind ?? "unknown"}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Updated: {formatTimestamp(run.lastEventAt)}
            </span>
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

export default function RunsPanel({
  onSelectRun,
  runs,
  selectedRunKey,
}: RunsPanelProps) {
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
          Runs
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Derived from the global SSE stream using detected run and task IDs.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {runs.length === 0 ? (
          <div className="rounded-xl border px-4 py-5 text-sm" style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            Waiting for run-identifiable events.
          </div>
        ) : (
          runs.map((run) => (
            <RunRow
              key={run.key}
              onSelectRun={onSelectRun}
              run={run}
              selected={run.key === selectedRunKey}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}
