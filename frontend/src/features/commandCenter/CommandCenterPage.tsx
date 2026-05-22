import * as React from "react";

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
  filterCommandCenterRuns,
} from "@/features/commandCenter/commandCenterObservability";

type CommandCenterPageProps = {
  enabled: boolean;
  heartbeatEnabled: boolean;
};

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

export default function CommandCenterPage({ enabled, heartbeatEnabled }: CommandCenterPageProps) {
  const {
    connectionDetail,
    connectionState,
    events,
    lastEventAt,
    runs,
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
      heartbeatEnabled={heartbeatEnabled}
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
