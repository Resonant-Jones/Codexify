import * as React from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import useRagTrace from "@/features/commandCenter/hooks/useRagTrace";
import useRetrievalPosture from "@/features/commandCenter/hooks/useRetrievalPosture";
import {
  buildCommandCenterTraceListItem,
  buildCommandCenterTraceReportModel,
  describeCommandCenterTraceListSelection,
} from "@/features/commandCenter/commandCenterObservability";
import type {
  CommandCenterRun,
  CommandCenterTraceFilters,
} from "@/features/commandCenter/types";
import {
  COMMAND_CENTER_RUN_STATUSES,
  describeCommandCenterRunStatusPresentation,
  type CommandCenterStatusTone,
} from "@/features/commandCenter/types";

type TraceWorkbenchProps = {
  allRuns: CommandCenterRun[];
  filters: CommandCenterTraceFilters;
  onFiltersChange: (next: CommandCenterTraceFilters) => void;
  onSelectRun: (runKey: string | null) => void;
  selectedRun: CommandCenterRun | null;
  selectedRunKey: string | null;
  visibleRuns: CommandCenterRun[];
};

const STATUS_OPTIONS: Array<{ label: string; value: string }> = [
  { label: "Any status", value: "all" },
  { label: "Running", value: COMMAND_CENTER_RUN_STATUSES.RUNNING },
  { label: "Completed", value: COMMAND_CENTER_RUN_STATUSES.COMPLETED },
  { label: "Failed", value: COMMAND_CENTER_RUN_STATUSES.FAILED },
  { label: "Cancelled", value: COMMAND_CENTER_RUN_STATUSES.CANCELLED },
  { label: "Needs attention", value: COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION },
  { label: "Unknown", value: COMMAND_CENTER_RUN_STATUSES.UNKNOWN },
];

type TraceTab = "report" | "raw-trace" | "payload-summary";

function toneStyle(tone: CommandCenterStatusTone): React.CSSProperties {
  switch (tone) {
    case "active":
      return {
        background: "var(--accent-weak)",
        borderColor: "color-mix(in oklab, var(--accent-strong) 35%, var(--panel-border))",
        color: "var(--text-on-accent)",
      };
    case "attention":
      return {
        background: "color-mix(in oklab, var(--chip-bg) 82%, var(--accent-strong) 18%)",
        borderColor: "color-mix(in oklab, var(--accent-strong) 42%, var(--panel-border))",
        color: "var(--text)",
      };
    case "danger":
      return {
        background: "var(--danger-surface)",
        borderColor: "var(--danger-border)",
        color: "var(--danger-text)",
      };
    case "info":
      return {
        background: "var(--info-surface)",
        borderColor: "var(--panel-border)",
        color: "var(--info-text)",
      };
    case "neutral":
      return {
        background: "var(--chip-bg)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      };
    case "subtle":
    default:
      return {
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--muted)",
      };
  }
}

function StatusBadge({
  label,
  tone,
}: {
  label: string;
  tone: CommandCenterStatusTone;
}) {
  return (
    <Badge className="border text-[11px] font-medium leading-none" style={toneStyle(tone)}>
      {label}
    </Badge>
  );
}

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed) return trimmed;
  }
  return null;
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (!trimmed) continue;
      const parsed = Number(trimmed);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function resolveSelectedRunThreadId(run: CommandCenterRun): number | null {
  const payload = asRecord(run.lastEvent.json);
  const thread = asRecord(payload?.thread);
  const task = asRecord(payload?.task);
  const nestedRun = asRecord(payload?.run);
  const context = asRecord(payload?.context);
  const nestedPayload = asRecord(payload?.payload);

  return firstNumber(
    run.threadId,
    payload?.thread_id,
    payload?.threadId,
    thread?.id,
    thread?.thread_id,
    thread?.threadId,
    nestedRun?.thread_id,
    nestedRun?.threadId,
    task?.thread_id,
    task?.threadId,
    context?.thread_id,
    context?.threadId,
    nestedPayload?.thread_id,
    nestedPayload?.threadId
  );
}

function resolveSelectedRunTraceUrl(run: CommandCenterRun): string | null {
  const payload = asRecord(run.lastEvent.json);
  const nestedRun = asRecord(payload?.run);
  const response = asRecord(payload?.response);
  const result = asRecord(payload?.result);

  return firstString(
    run.traceUrl,
    payload?.trace_url,
    payload?.traceUrl,
    nestedRun?.trace_url,
    nestedRun?.traceUrl,
    response?.trace_url,
    response?.traceUrl,
    result?.trace_url,
    result?.traceUrl
  );
}

function selectClassName(active: boolean): string {
  return [
    "h-9 w-full rounded-md border bg-[var(--panel-bg)]/80 px-3 py-1 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]",
    active ? "border-[var(--accent)]" : "border-[var(--panel-border)]",
  ].join(" ");
}

function updateFilter(
  filters: CommandCenterTraceFilters,
  onFiltersChange: (next: CommandCenterTraceFilters) => void,
  key: keyof CommandCenterTraceFilters,
  value: string | boolean
): void {
  onFiltersChange({
    ...filters,
    [key]: value,
  });
}

function MarkdownBody({ markdown }: { markdown: string }) {
  const components = {
    h2: ({ children }: { children?: React.ReactNode }) => (
      <h2 className="mt-4 text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
        {children}
      </h2>
    ),
    p: ({ children }: { children?: React.ReactNode }) => (
      <p className="text-sm leading-6" style={{ color: "var(--text)" }}>
        {children}
      </p>
    ),
    ul: ({ children }: { children?: React.ReactNode }) => (
      <ul className="space-y-1 pl-5 text-sm leading-6" style={{ color: "var(--text)" }}>
        {children}
      </ul>
    ),
    li: ({ children }: { children?: React.ReactNode }) => <li>{children}</li>,
    blockquote: ({ children }: { children?: React.ReactNode }) => (
      <blockquote
        className="rounded-[var(--tile-radius)] border-l-4 border-[var(--accent)] bg-[var(--surface-soft)] px-4 py-3"
        style={{ color: "var(--text)" }}
      >
        {children}
      </blockquote>
    ),
    code: ({
      inline,
      children,
    }: {
      inline?: boolean;
      children?: React.ReactNode;
    }) =>
      inline ? (
        <code
          className="rounded bg-[var(--chip-bg)] px-1 py-0.5 text-[11px]"
          style={{ color: "var(--text)" }}
        >
          {children}
        </code>
      ) : (
        <code className="text-xs leading-5" style={{ color: "var(--text)" }}>
          {children}
        </code>
      ),
  } as const;

  return (
    <div className="space-y-3">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components as any}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

function TraceListItem({
  item,
  onSelectRun,
  selected,
}: {
  item: ReturnType<typeof buildCommandCenterTraceListItem>;
  onSelectRun: (runKey: string) => void;
  selected: boolean;
}) {
  return (
    <button
      type="button"
      className="w-full text-left"
      onClick={() => onSelectRun(item.key)}
    >
      <Card
        className="bezel-none border transition-colors hover:border-[var(--accent)]"
        style={{
          background: "color-mix(in oklab, var(--panel-bg) 93%, transparent)",
          borderColor: selected ? "var(--accent)" : "var(--panel-border)",
        }}
      >
        <CardContent className="space-y-3 p-[var(--card-pad)]">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <div className="text-sm font-semibold leading-5" style={{ color: "var(--text)" }}>
                {item.label}
              </div>
              <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                {item.verdict}
              </div>
            </div>
            <StatusBadge label={item.statusLabel} tone={item.statusTone} />
          </div>

          <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              {item.timestampLabel}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Thread: {item.threadIdLabel ?? "—"}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              {item.taskOrTurnLabel ?? "No stable task id"}
            </span>
          </div>

          <div className="flex flex-wrap gap-2 text-xs">
            {item.providerBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                {item.providerBadge}
              </Badge>
            ) : null}
            {item.modelBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                {item.modelBadge}
              </Badge>
            ) : null}
            {item.retrievalBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                {item.retrievalBadge}
              </Badge>
            ) : null}
            {item.warningBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--danger-surface)", borderColor: "var(--danger-border)", color: "var(--danger-text)" }}>
                {item.warningBadge}
              </Badge>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

function TraceListPane({
  onSelectRun,
  runs,
  selectedRunKey,
}: {
  onSelectRun: (runKey: string) => void;
  runs: CommandCenterRun[];
  selectedRunKey: string | null;
}) {
  return (
    <section className="flex min-h-0 flex-col rounded-[var(--tile-radius)] border" style={{ background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)", borderColor: "var(--panel-border)" }}>
      <div className="border-b border-[var(--panel-border)] p-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Trace list
            </div>
            <div className="text-xs" style={{ color: "var(--muted)" }}>
              Newest first, with filtered runs only.
            </div>
          </div>
          <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
            {runs.length} visible
          </Badge>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-2">
        {runs.length === 0 ? (
          <div className="rounded-[var(--tile-radius)] border p-4 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            No runs match the current filters.
          </div>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => {
              const item = buildCommandCenterTraceListItem(run);
              return (
                <TraceListItem
                  key={item.key}
                  item={item}
                  onSelectRun={onSelectRun}
                  selected={item.key === selectedRunKey}
                />
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      variant={active ? "default" : "ghost"}
      size="sm"
      onClick={onClick}
      className={active ? "" : "border border-[var(--panel-border)]"}
    >
      {children}
    </Button>
  );
}

function TraceViewerPane({
  filters,
  selectedRun,
}: {
  filters: CommandCenterTraceFilters;
  selectedRun: CommandCenterRun | null;
}) {
  const effectiveRun = React.useMemo(() => {
    if (!selectedRun) return null;
    return {
      ...selectedRun,
      threadId: resolveSelectedRunThreadId(selectedRun),
      traceUrl: resolveSelectedRunTraceUrl(selectedRun),
    };
  }, [selectedRun]);

  const { error, loading, rawTrace, trace, unavailable, unavailableReason } =
    useRagTrace(effectiveRun);
  const [tab, setTab] = React.useState<TraceTab>("report");

  React.useEffect(() => {
    setTab("report");
  }, [selectedRun?.key]);

  const reportModel = React.useMemo(
    () =>
      buildCommandCenterTraceReportModel({
        normalizedTrace: trace,
        rawTrace,
        run: effectiveRun,
        unavailableReason,
      }),
    [effectiveRun, rawTrace, trace, unavailableReason]
  );

  const selectionLabel = describeCommandCenterTraceListSelection(effectiveRun, filters);
  const statusPresentation = describeCommandCenterRunStatusPresentation(
    effectiveRun?.status ?? null
  );

  const rawTraceText = React.useMemo(() => {
    if (!rawTrace) {
      return "No raw trace payload available.";
    }
    try {
      return JSON.stringify(rawTrace, null, 2);
    } catch {
      return String(rawTrace);
    }
  }, [rawTrace]);

  const retrievalPostureThreadId = effectiveRun?.threadId ?? null;
  const { error: postureError, loading: postureLoading, retrievalPosture, status: postureStatus } =
    useRetrievalPosture(retrievalPostureThreadId);

  return (
    <section className="flex min-h-0 flex-col rounded-[var(--tile-radius)] border" style={{ background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)", borderColor: "var(--panel-border)" }}>
      <div className="border-b border-[var(--panel-border)] p-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Trace viewer
            </div>
            <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              {selectionLabel}
            </div>
            <div className="flex flex-wrap gap-2 pt-1 text-xs">
              <StatusBadge label={statusPresentation.label} tone={statusPresentation.tone} />
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                Thread: {effectiveRun?.threadId ?? "—"}
              </Badge>
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                Trace: {loading ? "loading" : unavailable ? "unavailable" : "ready"}
              </Badge>
              {error ? (
                <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--danger-surface)", borderColor: "var(--danger-border)", color: "var(--danger-text)" }}>
                  {error}
                </Badge>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <TabButton active={tab === "report"} onClick={() => setTab("report")}>
              Report
            </TabButton>
            <TabButton active={tab === "raw-trace"} onClick={() => setTab("raw-trace")}>
              Raw Trace
            </TabButton>
            <TabButton active={tab === "payload-summary"} onClick={() => setTab("payload-summary")}>
              Payload Summary
            </TabButton>
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {!effectiveRun ? (
          <div className="rounded-[var(--tile-radius)] border p-4 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            Select a run to inspect its trace report.
          </div>
        ) : tab === "report" ? (
          <div className="space-y-4">
            <div className="rounded-[var(--tile-radius)] border p-4" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                Verdict
              </div>
              <div className="mt-1 text-sm leading-6" style={{ color: "var(--text)" }}>
                {reportModel.verdict}
              </div>
            </div>
            <MarkdownBody markdown={reportModel.markdown} />
          </div>
        ) : tab === "raw-trace" ? (
          <pre className="overflow-auto rounded-[var(--tile-radius)] border p-4 text-xs leading-5" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
            {rawTraceText}
          </pre>
        ) : (
          <div className="space-y-3">
            {reportModel.payloadSummaryRows.length === 0 ? (
              <div className="rounded-[var(--tile-radius)] border p-4 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
                No payload summary fields were available.
              </div>
            ) : (
              <div className="grid gap-2">
                {reportModel.payloadSummaryRows.map((row) => (
                  <div
                    key={row.label}
                    className="grid gap-2 rounded-[var(--tile-radius)] border px-3 py-2 text-sm md:grid-cols-[12rem_minmax(0,1fr)]"
                    style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}
                  >
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                      {row.label}
                    </div>
                    <div className="min-w-0 break-words" style={{ color: "var(--text)" }}>
                      {row.value}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {reportModel.warnings.length > 0 ? (
              <div className="rounded-[var(--tile-radius)] border p-4" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                  Notes / warnings
                </div>
                <ul className="mt-2 space-y-1 pl-5 text-sm leading-6" style={{ color: "var(--text)" }}>
                  {reportModel.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
        {effectiveRun && (
          <div className="mt-4 rounded-[var(--tile-radius)] border p-3" style={{ background: "color-mix(in oklab, var(--surface-soft) 60%, transparent)", borderColor: "var(--panel-border)" }}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
              Retrieval posture
            </div>
            {postureLoading ? (
              <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
                Loading retrieval posture…
              </div>
            ) : postureError ? (
              <div className="mt-2 text-sm" style={{ color: "var(--danger-text)" }}>
                {postureError}
              </div>
            ) : postureStatus === "empty" ? (
              <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
                No retrieval posture evidence for this thread.
              </div>
            ) : retrievalPosture ? (
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                  source: {retrievalPosture.source_mode}
                </Badge>
                <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                  boundary: {retrievalPosture.boundary_label}
                </Badge>
                {retrievalPosture.retrieval_override_mode ? (
                  <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                    override: {retrievalPosture.retrieval_override_mode}
                  </Badge>
                ) : null}
                <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                  widen: {retrievalPosture.widen_reason}
                </Badge>
                {retrievalPosture.conversation_only && (
                  <Badge className="border text-[11px] font-medium leading-none" style={{ background: "color-mix(in oklab, var(--accent-weak) 60%, transparent)", borderColor: "var(--panel-border)", color: "var(--text-on-accent)" }}>
                    conversation-only
                  </Badge>
                )}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </section>
  );
}

function TraceFilterBar({
  filters,
  onFiltersChange,
}: {
  filters: CommandCenterTraceFilters;
  onFiltersChange: (next: CommandCenterTraceFilters) => void;
}) {
  return (
    <div className="grid gap-3 rounded-[var(--tile-radius)] border p-3 md:grid-cols-2 xl:grid-cols-6" style={{ background: "color-mix(in oklab, var(--surface-soft) 85%, transparent)", borderColor: "var(--panel-border)" }}>
      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Status
        </div>
        <select
          className={selectClassName(filters.status !== "all")}
          value={filters.status}
          onChange={(event) => updateFilter(filters, onFiltersChange, "status", event.target.value)}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Provider
        </div>
        <Input
          value={filters.provider}
          onChange={(event) => updateFilter(filters, onFiltersChange, "provider", event.target.value)}
          placeholder="openai, local, anthropic"
          list="command-center-provider-options"
        />
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Model
        </div>
        <Input
          value={filters.model}
          onChange={(event) => updateFilter(filters, onFiltersChange, "model", event.target.value)}
          placeholder="gpt-5, claude, llama"
          list="command-center-model-options"
        />
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Retrieval
        </div>
        <Input
          value={filters.retrieval}
          onChange={(event) => updateFilter(filters, onFiltersChange, "retrieval", event.target.value)}
          placeholder="personal_knowledge, graph, widen"
        />
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Thread id
        </div>
        <Input
          value={filters.threadId}
          onChange={(event) => updateFilter(filters, onFiltersChange, "threadId", event.target.value)}
          placeholder="42"
        />
      </label>

      <label className="flex items-end">
        <Button
          type="button"
          variant={filters.warningsOnly ? "default" : "ghost"}
          size="sm"
          onClick={() => updateFilter(filters, onFiltersChange, "warningsOnly", !filters.warningsOnly)}
          className="w-full border border-[var(--panel-border)]"
        >
          {filters.warningsOnly ? "Warnings only" : "Show all runs"}
        </Button>
      </label>
    </div>
  );
}

export default function TraceWorkbench({
  allRuns,
  filters,
  onFiltersChange,
  onSelectRun,
  selectedRun,
  selectedRunKey,
  visibleRuns,
}: TraceWorkbenchProps) {
  const selectionSummary = describeCommandCenterTraceListSelection(selectedRun, filters);

  const providerOptions = React.useMemo(() => {
    const values = new Set<string>();
    for (const run of allRuns) {
      const value = firstString(run.finalProvider, run.attemptedProvider);
      if (value) values.add(value);
    }
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }, [allRuns]);

  const modelOptions = React.useMemo(() => {
    const values = new Set<string>();
    for (const run of allRuns) {
      const value = firstString(run.finalModel, run.attemptedModel);
      if (value) values.add(value);
    }
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }, [allRuns]);

  return (
    <Card
      className="bezel-none border h-full min-h-0"
      role="region"
      aria-label="Command Center trace workbench"
      data-testid="command-center-trace-workbench"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="space-y-2 border-b border-[var(--panel-border)] pb-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base" style={{ color: "var(--text)" }}>
              RAG trace workbench
            </CardTitle>
            <p className="max-w-3xl text-sm leading-6" style={{ color: "var(--muted)" }}>
              Interpreted diagnostic reports on the right, filtered run identities on the left.
            </p>
            <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              {selectionSummary}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
              {visibleRuns.length} visible
            </Badge>
            <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
              Selected: {selectedRunKey ?? "none"}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col gap-4 p-[var(--card-pad)]">
        <TraceFilterBar filters={filters} onFiltersChange={onFiltersChange} />

      <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[minmax(18rem,0.36fr)_minmax(0,0.64fr)]">
        <TraceListPane onSelectRun={onSelectRun} runs={visibleRuns} selectedRunKey={selectedRunKey} />
        <TraceViewerPane filters={filters} selectedRun={selectedRun} />
      </div>

      <datalist id="command-center-provider-options">
        {providerOptions.map((provider) => (
          <option key={provider} value={provider} />
        ))}
      </datalist>
      <datalist id="command-center-model-options">
        {modelOptions.map((model) => (
          <option key={model} value={model} />
        ))}
      </datalist>
      </CardContent>
    </Card>
  );
}
