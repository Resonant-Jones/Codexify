import type { CSSProperties } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { describeRuntimeStatusPresentation } from "@/contracts/runtimeTokens";

import type { CommandCenterEvent, CommandCenterRun } from "@/features/commandCenter/types";

type RunSummaryCardProps = {
  onOpen: (run: CommandCenterRun) => void;
  run: CommandCenterRun;
  selected?: boolean;
};

function formatTimestamp(value: number | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

function runStateStyle(status: CommandCenterRun["status"]): CSSProperties {
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

function runOutcomeStyle(
  outcome: CommandCenterRun["terminalOutcome"] | null | undefined
): CSSProperties {
  switch (outcome) {
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
    case "cancelled":
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

function RunIdentityChips({ run }: { run: CommandCenterRun }) {
  const chips: Array<{ label: string; value: string | number }> = [];

  if (run.taskId) {
    chips.push({ label: "Task", value: run.taskId });
  } else if (run.requestId || run.runId) {
    chips.push({ label: "Target", value: run.requestId ?? run.runId ?? "—" });
  }

  if (run.threadId != null) {
    chips.push({ label: "Thread", value: run.threadId });
  }

  if (run.turnId) {
    chips.push({ label: "Turn", value: run.turnId });
  }

  if (run.latestTurnMessageId) {
    chips.push({ label: "Latest turn message", value: run.latestTurnMessageId });
  }

  if (run.streamingEvidence?.chunkCount) {
    chips.push({ label: "Chunks", value: run.streamingEvidence.chunkCount });
  }

  if (chips.length === 0) {
    return (
      <span style={{ color: "var(--muted)" }}>
        No stable task identity available.
      </span>
    );
  }

  return (
    <>
      {chips.map((chip) => (
        <span
          key={`${chip.label}:${String(chip.value)}`}
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)" }}
        >
          {chip.label}: {chip.value}
        </span>
      ))}
    </>
  );
}

function getRunTitle(run: CommandCenterRun): string {
  if (run.runType) return run.runType;
  if (run.identityKind === "synthetic" || run.status === "unknown") {
    return "Unknown run";
  }
  return "task";
}

function getRunSubtitle(run: CommandCenterRun, title: string): string | null {
  if (!run.summary) return null;
  if (run.summary === title) return null;
  return run.summary;
}

function getEvents(run: CommandCenterRun): CommandCenterEvent[] {
  return run.events?.length ? run.events : [run.lastEvent];
}

export default function RunSummaryCard({
  onOpen,
  run,
  selected = false,
}: RunSummaryCardProps) {
  const title = getRunTitle(run);
  const subtitle = getRunSubtitle(run, title);
  const events = getEvents(run);
  const statusPresentation = describeRuntimeStatusPresentation(run.status);

  return (
    <Card
      className={cn(
        "bezel-none rounded-xl border transition-colors",
        selected && "ring-1 ring-[var(--accent)]"
      )}
      data-testid={`command-center-run-${run.key}`}
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
        borderColor: selected ? "var(--accent)" : "var(--panel-border)",
      }}
    >
      <CardContent className="space-y-4 p-[var(--card-pad)]">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1.5">
            <div className="text-sm font-semibold leading-5" style={{ color: "var(--text)" }}>
              {title}
            </div>
            {subtitle ? (
              <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                {subtitle}
              </div>
            ) : null}
          </div>

          <div className="flex shrink-0 items-start gap-2">
            <Badge
              className="border text-[11px] font-medium leading-none"
              style={{
                ...runStateStyle(run.status),
                color: "var(--text)",
              }}
            >
              {run.state ?? run.status}
            </Badge>
            {run.terminalOutcome ? (
              <Badge
                className="border text-[11px] font-medium leading-none"
                style={{
                  ...runOutcomeStyle(run.terminalOutcome),
                  color: "var(--text)",
                }}
              >
                {run.terminalOutcome}
              </Badge>
            ) : null}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onOpen(run)}
              aria-label={`Open details for ${title}`}
            >
              Open
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
          <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
            Type: {title}
          </span>
          <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
            Events: {run.eventCount}
          </span>
          <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
            Updated: {formatTimestamp(run.lastEventAt)}
          </span>
          <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
            Status: {statusPresentation.label}
          </span>
        </div>

        <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
          <RunIdentityChips run={run} />
        </div>

        <details className="text-xs" style={{ color: "var(--muted)" }}>
          <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.16em]">
            Inspect raw events
          </summary>
          <div className="mt-3 space-y-3">
            {events.map((event, index) => (
              <div
                key={`${event.eventId ?? event.receivedAt}-${index}`}
                className="space-y-2 rounded-[var(--tile-radius)] border p-3"
                style={{
                  background: "var(--surface-soft)",
                  borderColor: "var(--panel-border)",
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div
                    className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                    style={{ color: "var(--muted)" }}
                  >
                    {event.type ?? event.sseType ?? "event"}
                  </div>
                  <div className="text-[11px]" style={{ color: "var(--muted)" }}>
                    {formatTimestamp(event.receivedAt)}
                  </div>
                </div>
                <div className="text-xs leading-5" style={{ color: "var(--text)" }}>
                  {event.summary}
                </div>
                <pre
                  className="overflow-x-auto rounded-[var(--tile-radius)] border p-3 text-[11px] leading-5"
                  style={{
                    background: "var(--panel-bg)",
                    borderColor: "var(--panel-border)",
                    color: "var(--muted)",
                  }}
                >
                  {event.raw || "No raw payload available."}
                </pre>
              </div>
            ))}
          </div>
        </details>
      </CardContent>
    </Card>
  );
}
