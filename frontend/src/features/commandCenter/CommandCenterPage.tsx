import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import EventConsole from "@/features/commandCenter/components/EventConsole";
import HealthOverview from "@/features/commandCenter/components/HealthOverview";
import TraceWorkbench, {
  diffRetrievalPosture,
  describeRetrievalPostureChange,
  RetrievalPosturePanel,
  RetrievalPostureSummaryRow,
  type RetrievalPostureDiff,
} from "@/features/commandCenter/components/TraceWorkbench";
import useCommandCenterEvents from "@/features/commandCenter/hooks/useCommandCenterEvents";
import useHealthSummary from "@/features/commandCenter/hooks/useHealthSummary";
import useRetrievalPostureHistory from "@/features/commandCenter/hooks/useRetrievalPostureHistory";
import {
  buildCommandCenterEventConsoleRows,
  countCommandCenterUnknownItems,
  countCommandCenterWarningSignals,
  filterCommandCenterRuns,
} from "@/features/commandCenter/commandCenterObservability";
import type {
  CommandCenterRetrievalPostureHistoryItem,
  CommandCenterRun,
  CommandCenterTraceFilters,
} from "@/features/commandCenter/types";
import {
  describeRuntimeStatusPresentation,
  type RuntimeStatusTone,
} from "@/contracts/runtimeTokens";

type CommandCenterPageProps = {
  enabled: boolean;
};

type BadgeTone = RuntimeStatusTone | "danger";

const filtersDefault: CommandCenterTraceFilters = {
  model: "",
  provider: "",
  retrieval: "",
  status: "all",
  threadId: "",
  warningsOnly: false,
};

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

function toneStyle(tone: BadgeTone): React.CSSProperties {
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

function BadgePill({
  ariaLabel,
  children,
  tone,
}: {
  ariaLabel?: string;
  children: React.ReactNode;
  tone: BadgeTone;
}) {
  return (
    <Badge
      aria-label={ariaLabel}
      className="border text-[11px] font-medium leading-none"
      style={toneStyle(tone)}
    >
      {children}
    </Badge>
  );
}

function SummaryTile({
  children,
  label,
  note,
}: {
  children: React.ReactNode;
  label: string;
  note: React.ReactNode;
}) {
  return (
    <div
      className="space-y-2 border p-[var(--card-pad)]"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        borderColor: "var(--panel-border)",
        borderRadius: "var(--tile-radius)",
      }}
    >
      <div
        className="text-[11px] font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--muted)" }}
      >
        {label}
      </div>
      <div className="flex min-h-10 items-start justify-between gap-3">{children}</div>
      <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
        {note}
      </div>
    </div>
  );
}

function DashboardHeader({
  connectionDetail,
  lastEventAt,
  transportLabel,
  transportTone,
}: {
  connectionDetail: string | null;
  lastEventAt: number | null;
  transportLabel: string;
  transportTone: BadgeTone;
}) {
  return (
    <Card
      className="bezel-none border"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardContent className="flex flex-col gap-4 p-[var(--card-pad)] sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div
            className="text-[11px] font-semibold uppercase tracking-[0.18em]"
            style={{ color: "var(--muted)" }}
          >
            Command Center
          </div>
          <h1 className="text-2xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>
            Agent Command Center
          </h1>
          <p className="max-w-3xl text-sm leading-6" style={{ color: "var(--muted)" }}>
            Split observability surface for health, RAG diagnostics, and raw transport truth.
          </p>
          {connectionDetail ? (
            <div className="text-xs" style={{ color: "var(--muted)" }}>
              {connectionDetail}
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          <BadgePill ariaLabel={`Transport state ${transportLabel}`} tone={transportTone}>
            {transportLabel}
          </BadgePill>
          <BadgePill tone="subtle">Last event: {formatTimestamp(lastEventAt)}</BadgePill>
        </div>
      </CardContent>
    </Card>
  );
}

function DashboardSummary({
  healthCount,
  unknownCount,
  visibleRunCount,
  warningCount,
  transportLabel,
  transportTone,
  lastEventAt,
}: {
  healthCount: number;
  lastEventAt: number | null;
  transportLabel: string;
  transportTone: BadgeTone;
  unknownCount: number;
  visibleRunCount: number;
  warningCount: number;
}) {
  return (
    <Card
      className="bezel-none border"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="pb-3">
        <CardTitle className="text-base" style={{ color: "var(--text)" }}>
          Runtime summary
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Compact high-value state only. Raw payloads remain in the trace report and console panes.
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <SummaryTile
          label="Transport state"
          note="Current SSE connection state."
        >
          <BadgePill tone={transportTone} ariaLabel={`Transport state ${transportLabel}`}>
            {transportLabel}
          </BadgePill>
        </SummaryTile>

        <SummaryTile label="Last event" note="Most recent event timestamp.">
          <div className="text-lg font-semibold leading-tight" style={{ color: "var(--text)" }}>
            {formatTimestamp(lastEventAt)}
          </div>
        </SummaryTile>

        <SummaryTile label="Health surfaces" note="Visible service checks.">
          <div className="text-2xl font-semibold leading-none" style={{ color: "var(--text)" }}>
            {healthCount}
          </div>
        </SummaryTile>

        <SummaryTile label="Visible runs" note="Runs after current trace filters.">
          <div className="text-2xl font-semibold leading-none" style={{ color: "var(--text)" }}>
            {visibleRunCount}
          </div>
        </SummaryTile>

        <SummaryTile label="Unknown items" note="Promoted unknowns are suppressed; raw noise stays in the console.">
          <div
            className="text-2xl font-semibold leading-none"
            aria-label={`Unknown items ${unknownCount}`}
            style={{ color: "var(--text)" }}
          >
            {unknownCount}
          </div>
        </SummaryTile>

        <SummaryTile label="Warnings / failures" note="Health failures + trace warnings + console warnings.">
          <div className="text-2xl font-semibold leading-none" style={{ color: "var(--text)" }}>
            {warningCount}
          </div>
        </SummaryTile>
      </CardContent>
    </Card>
  );
}

function latestRetrievalPostureComparison(
  items: CommandCenterRetrievalPostureHistoryItem[]
): {
  comparison: RetrievalPostureDiff | null;
  explanationLines: string[] | null;
  label: string | null;
  changedFields: string[] | null;
  state: "changed" | "unchanged" | "no-previous" | "none";
} {
  const current = items[0] ?? null;
  if (!current) {
    return {
      comparison: null,
      explanationLines: null,
      changedFields: null,
      label: null,
      state: "none",
    };
  }

  const previous = items[1] ?? null;
  if (!previous) {
    return {
      comparison: { changed: false, changedFields: [] },
      explanationLines: null,
      changedFields: null,
      label: "No previous posture to compare",
      state: "no-previous",
    };
  }

  const comparison = diffRetrievalPosture(current.retrieval_posture, previous.retrieval_posture);
  const explanation = describeRetrievalPostureChange(
    comparison,
    current.retrieval_posture,
    previous.retrieval_posture
  );
  return {
    comparison,
    explanationLines: comparison.changed ? explanation.lines : null,
    changedFields: comparison.changed ? comparison.changedFields : null,
    label: comparison.changed
      ? "Posture changed since previous run"
      : "Posture unchanged since previous run",
    state: comparison.changed ? "changed" : "unchanged",
  };
}

function RecentRetrievalPosturePanel({
  threadId,
}: {
  threadId: number | null;
}) {
  const { error, items, loading, status } = useRetrievalPostureHistory(threadId);
  const comparison = React.useMemo(() => latestRetrievalPostureComparison(items), [items]);

  if (threadId === null) return null;

  return (
    <Card
      className="bezel-none border"
      data-testid="command-center-retrieval-posture-history-panel"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="pb-3">
        <CardTitle className="text-base" style={{ color: "var(--text)" }}>
          Recent retrieval posture
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Newest-first thread history from completed debug evidence only.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="rounded-[var(--tile-radius)] border p-3 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            Loading recent retrieval posture history…
          </div>
        ) : error ? (
          <div className="rounded-[var(--tile-radius)] border p-3 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--danger-border)", color: "var(--danger-text)" }}>
            {error}
          </div>
        ) : status === "empty" || items.length === 0 ? (
          <div className="rounded-[var(--tile-radius)] border p-3 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            No recent retrieval posture history for this thread.
          </div>
        ) : (
          <div className="space-y-2">
            {comparison.label ? (
              <div
                className="flex flex-wrap items-center gap-2 rounded-[var(--tile-radius)] border px-3 py-2 text-xs"
                style={{
                  background: "var(--surface-soft)",
                  borderColor: "var(--panel-border)",
                  color: "var(--muted)",
                }}
              >
                <BadgePill
                  tone={comparison.state === "changed" ? "attention" : "subtle"}
                  ariaLabel={comparison.label}
                >
                  {comparison.label}
                </BadgePill>
                {comparison.changedFields ? (
                  <div className="space-y-1">
                    <span>Changed: {comparison.changedFields.join(", ")}</span>
                    {comparison.explanationLines ? (
                      <div className="space-y-0.5 leading-5" style={{ color: "var(--text)" }}>
                        {comparison.explanationLines.map((line) => (
                          <p key={line}>{line}</p>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}
            {items.map((item) => (
              <RetrievalPostureSummaryRow
                key={`${item.task_id}:${item.created_at}`}
                createdAt={item.created_at}
                posture={item.retrieval_posture}
                taskId={item.task_id}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function CommandCenterPage({ enabled }: CommandCenterPageProps) {
  const {
    connectionDetail,
    connectionState,
    events,
    lastEventAt,
    runs,
    unauthorized,
  } = useCommandCenterEvents({ enabled });
  const { healthItems, lastCheckedAt, loading, refresh } = useHealthSummary({
    enabled,
  });
  const [selectedRunKey, setSelectedRunKey] = React.useState<string | null>(null);
  const [traceFilters, setTraceFilters] =
    React.useState<CommandCenterTraceFilters>(filtersDefault);

  const consoleRows = React.useMemo(() => buildCommandCenterEventConsoleRows(events), [events]);
  const visibleRuns = React.useMemo(
    () => filterCommandCenterRuns(runs, traceFilters),
    [runs, traceFilters]
  );

  const selectedRun = React.useMemo<CommandCenterRun | null>(() => {
    if (!selectedRunKey) return null;
    return visibleRuns.find((candidate) => candidate.key === selectedRunKey) ?? null;
  }, [selectedRunKey, visibleRuns]);

  const activeThreadId = React.useMemo<number | null>(() => {
    return selectedRun?.threadId ?? visibleRuns[0]?.threadId ?? null;
  }, [selectedRun, visibleRuns]);

  React.useEffect(() => {
    if (visibleRuns.length === 0) {
      if (selectedRunKey !== null) {
        setSelectedRunKey(null);
      }
      return;
    }

    if (!selectedRunKey || !visibleRuns.some((run) => run.key === selectedRunKey)) {
      setSelectedRunKey(visibleRuns[0]?.key ?? null);
    }
  }, [selectedRunKey, visibleRuns]);

  const transportPresentation = React.useMemo(() => {
    if (unauthorized) {
      return { label: "Unauthorized", tone: "danger" as BadgeTone };
    }
    const presentation = describeRuntimeStatusPresentation(connectionState);
    return { label: presentation.label, tone: presentation.tone as BadgeTone };
  }, [connectionState, unauthorized]);

  const unknownCount = React.useMemo(
    () =>
      countCommandCenterUnknownItems({
        healthItems,
        runs: visibleRuns,
        consoleRows,
      }),
    [consoleRows, healthItems, visibleRuns]
  );

  const warningCount = React.useMemo(
    () =>
      countCommandCenterWarningSignals({
        healthItems,
        runs: visibleRuns,
        consoleRows,
      }),
    [consoleRows, healthItems, visibleRuns]
  );

  if (!enabled) {
    return (
      <main
        className="min-h-screen px-6 py-10"
        style={{ background: "var(--panel-bg)", color: "var(--text)" }}
      >
        <div className="mx-auto flex max-w-2xl items-center justify-center">
          <Card
            className="bezel-none w-full border"
            style={{
              background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <CardContent className="space-y-3 p-6">
              <div className="text-lg font-semibold">Command Center not enabled</div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Set <code>VITE_ENABLE_COMMAND_CENTER=true</code> to expose this route outside development.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main
      className="flex min-h-0 flex-1 flex-col overflow-hidden p-[var(--card-pad)]"
      style={{ background: "var(--panel-bg)", color: "var(--text)" }}
    >
      <div className="mx-auto flex min-h-0 flex-1 flex-col gap-4 w-full max-w-7xl overflow-hidden">
        <DashboardHeader
          connectionDetail={connectionDetail}
          lastEventAt={lastEventAt}
          transportLabel={transportPresentation.label}
          transportTone={transportPresentation.tone}
        />

        <DashboardSummary
          healthCount={healthItems.length}
          lastEventAt={lastEventAt}
          transportLabel={transportPresentation.label}
          transportTone={transportPresentation.tone}
          unknownCount={unknownCount}
          visibleRunCount={visibleRuns.length}
          warningCount={warningCount}
        />

        <HealthOverview
          healthItems={healthItems}
          lastCheckedAt={lastCheckedAt}
          loading={loading}
          onRefresh={refresh}
        />

        <div
          className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden rounded-[var(--tile-radius)] border"
          data-testid="command-center-root"
          style={{
            background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
            borderColor: "var(--panel-border)",
            padding: "var(--card-pad)",
          }}
        >
          {activeThreadId !== null ? (
            <div className="space-y-4">
              <RecentRetrievalPosturePanel threadId={activeThreadId} />
              <RetrievalPosturePanel
                compact
                testId="command-center-thread-posture-panel"
                threadId={activeThreadId}
                title="Thread retrieval posture"
              />
            </div>
          ) : null}
          <div className="min-h-0 flex-1 overflow-hidden">
            <TraceWorkbench
              allRuns={runs}
              filters={traceFilters}
              onFiltersChange={setTraceFilters}
              onSelectRun={setSelectedRunKey}
              selectedRun={selectedRun}
              selectedRunKey={selectedRunKey}
              visibleRuns={visibleRuns}
            />
          </div>

          <div className="h-64 min-h-0 overflow-hidden rounded-[var(--tile-radius)] border" style={{ borderColor: "var(--panel-border)" }}>
            <EventConsole
              connectionDetail={connectionDetail}
              connectionState={connectionState}
              lastEventAt={lastEventAt}
              rows={consoleRows}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
