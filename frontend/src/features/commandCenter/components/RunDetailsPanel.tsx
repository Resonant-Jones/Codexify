import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

import type {
  CommandCenterEvent,
  CommandCenterRun,
} from "@/features/commandCenter/types";
import {
  describeCommandCenterRunKindLabel,
  describeCommandCenterRunStatusPresentation,
  describeCommandCenterRunTerminalOutcomePresentation,
  describeCommandCenterTracePresencePresentation,
  type CommandCenterStatusTone,
} from "@/features/commandCenter/types";

type RunDetailsPanelProps = {
  run: CommandCenterRun | null;
};

function formatTimestamp(value: number | null): string {
  if (value == null) return "—";
  return new Date(value).toLocaleString();
}

function formatDuration(value: number | null): string {
  if (value == null) return "—";
  if (value >= 1000) {
    const seconds = value / 1000;
    const rounded = seconds % 1 === 0 ? seconds.toFixed(0) : seconds.toFixed(2);
    return `${rounded}s`;
  }
  return `${value} ms`;
}

function formatSourceMode(value: string | null): string {
  switch (String(value ?? "").trim()) {
    case "project":
      return "Project";
    case "personal_knowledge":
      return "Personal Knowledge";
    default:
      return value ? value.replace(/[._-]+/g, " ") : "—";
  }
}

function clipInlineText(value: string, limit = 96): string {
  if (value.length <= limit) return value;
  return `${value.slice(0, Math.max(0, limit - 1))}…`;
}

function describeTracePanelExpectation(run: CommandCenterRun): string {
  const traceEvidence = run.traceEvidence ?? null;

  if (!traceEvidence) {
    return "No trace evidence exists for this run";
  }
  if (!traceEvidence.tracePresent) {
    return "Empty but expected";
  }
  if (run.threadId != null || run.traceUrl) {
    return "Aligned to this run/thread";
  }
  return "Unavailable";
}

function getEvents(run: CommandCenterRun): CommandCenterEvent[] {
  return run.events?.length ? run.events : [run.lastEvent];
}

function badgeToneStyle(tone: CommandCenterStatusTone): React.CSSProperties {
  switch (tone) {
    case "active":
      return {
        background: "rgba(34, 197, 94, 0.12)",
        borderColor: "rgba(34, 197, 94, 0.35)",
      };
    case "attention":
      return {
        background: "rgba(250, 204, 21, 0.12)",
        borderColor: "rgba(250, 204, 21, 0.35)",
      };
    case "danger":
      return {
        background: "rgba(239, 68, 68, 0.12)",
        borderColor: "rgba(239, 68, 68, 0.35)",
      };
    case "info":
      return {
        background: "rgba(59, 130, 246, 0.12)",
        borderColor: "rgba(59, 130, 246, 0.35)",
      };
    case "neutral":
      return {
        background: "rgba(148, 163, 184, 0.12)",
        borderColor: "rgba(148, 163, 184, 0.28)",
      };
    case "subtle":
    default:
      return {
        background: "rgba(148, 163, 184, 0.12)",
        borderColor: "rgba(148, 163, 184, 0.28)",
      };
  }
}

function SectionCard({
  children,
  title,
  note,
}: {
  children: React.ReactNode;
  note?: string;
  title: string;
}) {
  return (
    <Card
      className="bezel-none rounded-xl border"
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardContent className="space-y-3 p-4">
        <div className="space-y-1">
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            {title}
          </div>
          {note ? (
            <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              {note}
            </div>
          ) : null}
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function Chip({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <span
      className="rounded-full border px-2 py-1"
      style={{ borderColor: "var(--panel-border)" }}
    >
      {label}: {value}
    </span>
  );
}

function EventCard({ event }: { event: CommandCenterEvent }) {
  return (
    <div
      className="space-y-2 rounded-[var(--tile-radius)] border p-3"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="space-y-1">
          <div
            className="text-[11px] font-semibold uppercase tracking-[0.16em]"
            style={{ color: "var(--muted)" }}
          >
            {event.type ?? event.sseType ?? "event"}
          </div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            {event.lifecycleState ?? event.state ?? "unclassified"}
          </div>
        </div>
        <div className="text-[11px]" style={{ color: "var(--muted)" }}>
          {formatTimestamp(event.receivedAt)}
        </div>
      </div>
      <div className="text-sm leading-5" style={{ color: "var(--text)" }}>
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
        {event.json ? JSON.stringify(event.json, null, 2) : event.raw}
      </pre>
    </div>
  );
}

export default function RunDetailsPanel({ run }: RunDetailsPanelProps) {
  const [showRawEvents, setShowRawEvents] = React.useState(false);

  if (!run) return null;

  const statusPresentation = describeCommandCenterRunStatusPresentation(run.status);
  const terminalOutcomePresentation = describeCommandCenterRunTerminalOutcomePresentation(
    run.terminalOutcome
  );
  const lifecycleStates = run.lifecycleStates ?? [];
  const timings = run.timings ?? null;
  const streamingEvidence = run.streamingEvidence ?? null;
  const traceEvidence = run.traceEvidence ?? null;
  const tracePanelExpectation = describeTracePanelExpectation(run);
  const events = getEvents(run);
  const timingFields = [
    ["Queued", timings?.queuedAt ?? null],
    ["Warmup", timings?.warmupAt ?? null],
    ["First token", timings?.firstTokenAt ?? null],
    ["First output", timings?.firstOutputAt ?? null],
    ["Completed", timings?.completedAt ?? null],
  ] as const;
  const visibleTimingFields = timingFields.filter(([, value]) => value != null);
  const hasTimingEvidence =
    visibleTimingFields.length > 0 || timings?.totalDurationMs != null;

  return (
    <div data-testid="run-details-panel" className="space-y-3">
      <Card
        className="bezel-none rounded-xl border"
        style={{
          background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
          borderColor: "var(--panel-border)",
        }}
      >
        <CardContent className="space-y-3 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1">
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Run details
              </div>
              <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                {describeCommandCenterRunKindLabel(run.runKind) ?? run.runType ?? "task"} ·{" "}
                {run.summary}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge
                className="border text-[11px] font-medium leading-none"
                style={{
                  ...badgeToneStyle(statusPresentation.tone),
                  color: "var(--text)",
                }}
              >
                {statusPresentation.label}
              </Badge>
              {terminalOutcomePresentation ? (
                <Badge
                  className="border text-[11px] font-medium leading-none"
                  style={{
                    ...badgeToneStyle(terminalOutcomePresentation.tone),
                    color: "var(--text)",
                  }}
                >
                  {terminalOutcomePresentation.label}
                </Badge>
              ) : null}
              <Badge
                className="border text-[11px] font-medium leading-none"
                style={{
                  background: "rgba(148, 163, 184, 0.12)",
                  borderColor: "rgba(148, 163, 184, 0.28)",
                  color: "var(--text)",
                }}
              >
                {statusPresentation.label}
              </Badge>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
            <Chip label="Events" value={run.eventCount} />
            <Chip label="Updated" value={formatTimestamp(run.lastEventAt)} />
          </div>
        </CardContent>
      </Card>

      <SectionCard title="Identity" note="Stable run identity and target fields when available.">
        <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
          <Chip label="Grouping key" value={run.key} />
          <Chip label="Task" value={run.taskId ?? "—"} />
          <Chip label="Thread" value={run.threadId ?? "—"} />
          <Chip label="Latest turn message" value={run.latestTurnMessageId ?? "—"} />
          <Chip label="Run" value={run.runId ?? "—"} />
          <Chip label="Request" value={run.requestId ?? "—"} />
        </div>
      </SectionCard>

      <SectionCard title="Lifecycle" note="Ordered states and terminal outcome from the aggregated run record.">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
            <Chip label="Current state" value={statusPresentation.label} />
            <Chip
              label="Terminal result"
              value={terminalOutcomePresentation?.label ?? "not reached"}
            />
            <Chip
              label="Streaming"
              value={
                streamingEvidence
                  ? `${streamingEvidence.chunkCount} chunks`
                  : "No chunk evidence"
              }
            />
          </div>
          <div className="rounded-[var(--tile-radius)] border p-3 text-sm leading-6" style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}>
            {lifecycleStates.length > 0 ? lifecycleStates.join(" → ") : "No structured lifecycle path recorded."}
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Timing" note="Only recorded timestamps and durations are shown.">
        {hasTimingEvidence ? (
          <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
            {visibleTimingFields.map(([label, value]) => (
              <Chip key={label} label={label} value={formatTimestamp(value)} />
            ))}
            {timings?.totalDurationMs != null ? (
              <Chip label="Total" value={formatDuration(timings.totalDurationMs)} />
            ) : null}
          </div>
        ) : (
          <div className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs" style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            No structured timing evidence recorded.
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="Trace / Retrieval"
        note="Compact retrieval context and trace presence. Raw trace details stay secondary."
      >
        {traceEvidence ? (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
              {traceEvidence.sourceMode ? (
                <Chip label="Source" value={formatSourceMode(traceEvidence.sourceMode)} />
              ) : null}
              {traceEvidence.widenReason != null ? (
                <Chip label="Widen reason" value={traceEvidence.widenReason} />
              ) : null}
              <Chip
                label="Trace status"
                value={describeCommandCenterTracePresencePresentation(
                  traceEvidence.tracePresenceState
                ).label}
              />
              {traceEvidence.latestTurnMessageId ?? run.latestTurnMessageId ? (
                <Chip
                  label="Latest turn message"
                  value={traceEvidence.latestTurnMessageId ?? run.latestTurnMessageId}
                />
              ) : null}
            </div>

            <div
              className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5"
              style={{
                background: "var(--surface-soft)",
                borderColor: "var(--panel-border)",
                color: "var(--muted)",
              }}
            >
              <span className="font-semibold" style={{ color: "var(--text)" }}>
                Trace panel:
              </span>{" "}
              {tracePanelExpectation}
              {tracePanelExpectation === "Aligned to this run/thread" ? (
                <span> Use the RAG Trace tab for the scoped payload.</span>
              ) : null}
            </div>

            {traceEvidence.retrievalQuery ? (
              <div
                className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5"
                style={{
                  background: "var(--surface-soft)",
                  borderColor: "var(--panel-border)",
                  color: "var(--muted)",
                }}
              >
                <span className="font-semibold" style={{ color: "var(--text)" }}>
                  Retrieval query:
                </span>{" "}
                <span title={traceEvidence.retrievalQuery}>
                  {clipInlineText(traceEvidence.retrievalQuery)}
                </span>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
              {traceEvidence.documentCount != null ? (
                <Chip label="Documents" value={traceEvidence.documentCount} />
              ) : null}
              {traceEvidence.memoryCount != null ? (
                <Chip label="Memory" value={traceEvidence.memoryCount} />
              ) : null}
              {traceEvidence.graphCount != null ? (
                <Chip label="Graph" value={traceEvidence.graphCount} />
              ) : null}
            </div>

            {!traceEvidence.tracePresent ? (
              <div
                className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs"
                style={{
                  borderColor: "var(--panel-border)",
                  color: "var(--muted)",
                }}
              >
                No detailed trace payload is currently available.
              </div>
            ) : null}
          </div>
        ) : (
          <div
            className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs"
            style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          >
            No trace evidence exists for this run.
          </div>
        )}
      </SectionCard>

      <div className="text-xs" style={{ color: "var(--muted)" }}>
        <button
          type="button"
          className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.16em]"
          aria-expanded={showRawEvents}
          aria-controls="run-details-raw-events"
          onClick={() => setShowRawEvents((current) => !current)}
        >
          {showRawEvents ? "Hide raw events" : "Raw events"}
        </button>
        {showRawEvents ? (
          <div
            className="mt-3 space-y-3"
            id="run-details-raw-events"
          >
            {events.map((event, index) => (
              <EventCard
                key={`${event.eventId ?? event.receivedAt}-${index}`}
                event={event}
              />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
