import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

import CommandCenterShell from "@/features/commandCenter/components/CommandCenterShell";
import type {
  CommandCenterRetrievalPosture,
  CommandCenterRetrievalPostureHistoryItem,
  CommandCenterRun,
  CommandCenterTraceFilters,
} from "@/features/commandCenter/types";
import type { PinnedRetrievalPostureState } from "@/features/commandCenter/components/TraceWorkbench";
import type {
  RetrievalPostureHistoryFilter,
  RetrievalPostureHistoryWindowSize,
} from "@/features/commandCenter/components/TraceWorkbench";
import useCommandCenterEvents from "@/features/commandCenter/hooks/useCommandCenterEvents";
import useHealthSummary from "@/features/commandCenter/hooks/useHealthSummary";
import {
  buildCommandCenterEventConsoleRows,
  countCommandCenterUnknownItems,
  countCommandCenterWarningSignals,
  filterCommandCenterRuns,
} from "@/features/commandCenter/commandCenterObservability";
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
  const [retrievalPostureHistoryFilter, setRetrievalPostureHistoryFilter] =
    React.useState<RetrievalPostureHistoryFilter>("all");
  const [retrievalPostureHistoryWindowSize, setRetrievalPostureHistoryWindowSize] =
    React.useState<RetrievalPostureHistoryWindowSize>(5);
  const [pinnedRetrievalPosture, setPinnedRetrievalPosture] =
    React.useState<PinnedRetrievalPostureState>(null);

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
    setPinnedRetrievalPosture(null);
  }, [activeThreadId]);

  const onPinCurrentRetrievalPosture = React.useCallback((posture: CommandCenterRetrievalPosture) => {
    setPinnedRetrievalPosture({
      createdAt: null,
      posture: { ...posture },
      source: "current",
      taskId: null,
    });
  }, []);

  const onPinHistoryRetrievalPosture = React.useCallback(
    (item: CommandCenterRetrievalPostureHistoryItem) => {
      setPinnedRetrievalPosture({
        createdAt: item.created_at,
        posture: { ...item.retrieval_posture },
        source: "history",
        taskId: item.task_id,
      });
    },
    []
  );

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
    <CommandCenterShell
      connectionDetail={connectionDetail}
      connectionState={connectionState}
      consoleRows={consoleRows}
      healthItems={healthItems}
      lastCheckedAt={lastCheckedAt}
      lastEventAt={lastEventAt}
      loading={loading}
      onRefresh={refresh}
      onPinCurrentRetrievalPosture={onPinCurrentRetrievalPosture}
      onPinHistoryRetrievalPosture={onPinHistoryRetrievalPosture}
      pinnedRetrievalPosture={pinnedRetrievalPosture}
      onClearPinnedPosture={() => setPinnedRetrievalPosture(null)}
      retrievalPostureHistoryFilter={retrievalPostureHistoryFilter}
      retrievalPostureHistoryWindowSize={retrievalPostureHistoryWindowSize}
      onHistoryFilterChange={setRetrievalPostureHistoryFilter}
      onHistoryWindowSizeChange={setRetrievalPostureHistoryWindowSize}
      onSelectRun={setSelectedRunKey}
      onFiltersChange={setTraceFilters}
      runs={runs}
      selectedRun={selectedRun}
      selectedRunKey={selectedRunKey}
      traceFilters={traceFilters}
      visibleRuns={visibleRuns}
      activeThreadId={activeThreadId}
    />
  );
}
