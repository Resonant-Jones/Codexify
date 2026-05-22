import * as React from "react";

import CommandCenterUtilityRail, {
  type CommandCenterLensId,
} from "@/features/commandCenter/components/CommandCenterUtilityRail";
import CommandCenterBottomDrawer from "@/features/commandCenter/components/CommandCenterBottomDrawer";
import CodingWorkOrdersPanel from "@/features/commandCenter/components/CodingWorkOrdersPanel";
import TraceWorkbench, {
  RetrievalPosturePanel,
  type PinnedRetrievalPostureState,
  type RetrievalPostureHistoryFilter,
  type RetrievalPostureHistoryWindowSize,
} from "@/features/commandCenter/components/TraceWorkbench";
import EventConsole from "@/features/commandCenter/components/EventConsole";
import HealthOverview from "@/features/commandCenter/components/HealthOverview";
import HeartbeatStatusPanel from "@/features/commandCenter/HeartbeatStatusPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import useRetrievalPostureHistory from "@/features/commandCenter/hooks/useRetrievalPostureHistory";
import useRetrievalPosture from "@/features/commandCenter/hooks/useRetrievalPosture";
import type {
  CommandCenterEvent,
  CommandCenterHealthItem,
  CommandCenterRetrievalPosture,
  CommandCenterRetrievalPostureHistoryItem,
  CommandCenterRun,
  CommandCenterTraceFilters,
} from "@/features/commandCenter/types";
import {
  diffRetrievalPosture,
  describeRetrievalPostureChange,
  RetrievalPostureSummaryRow,
} from "@/features/commandCenter/components/TraceWorkbench";

export type { CommandCenterLensId };

export interface CommandCenterShellProps {
  connectionDetail: string | null;
  connectionState: string;
  consoleRows: Array<{ key: string; raw: string; receivedAt: number; summary: string }>;
  healthItems: CommandCenterHealthItem[];
  heartbeatEnabled: boolean;
  lastCheckedAt: number | null;
  lastEventAt: number | null;
  loading: boolean;
  onRefresh: () => void;
  onPinCurrentRetrievalPosture: (posture: CommandCenterRetrievalPosture) => void;
  onPinHistoryRetrievalPosture: (item: CommandCenterRetrievalPostureHistoryItem) => void;
  pinnedRetrievalPosture: PinnedRetrievalPostureState;
  retrievalPostureHistoryFilter: RetrievalPostureHistoryFilter;
  retrievalPostureHistoryWindowSize: RetrievalPostureHistoryWindowSize;
  onClearPinnedPosture: () => void;
  onHistoryFilterChange: (next: RetrievalPostureHistoryFilter) => void;
  onHistoryWindowSizeChange: (next: RetrievalPostureHistoryWindowSize) => void;
  onSelectRun: (runKey: string | null) => void;
  onFiltersChange: (next: CommandCenterTraceFilters) => void;
  runs: CommandCenterRun[];
  selectedRun: CommandCenterRun | null;
  selectedRunKey: string | null;
  traceFilters: CommandCenterTraceFilters;
  visibleRuns: CommandCenterRun[];
  activeThreadId: number | null;
}

type RetrievalPostureDiff = {
  changed: boolean;
  changedFields: string[];
};

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
  onPinHistoryPosture,
  threadId,
}: {
  onPinHistoryPosture?: (item: CommandCenterRetrievalPostureHistoryItem) => void;
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
                <Badge
                  className="border text-[11px] font-medium leading-none"
                  style={{
                    background:
                      comparison.state === "changed"
                        ? "color-mix(in oklab, var(--chip-bg) 82%, var(--accent-strong) 18%)"
                        : "var(--surface-soft)",
                    borderColor:
                      comparison.state === "changed"
                        ? "color-mix(in oklab, var(--accent-strong) 42%, var(--panel-border))"
                        : "var(--panel-border)",
                    color: comparison.state === "changed" ? "var(--text)" : "var(--muted)",
                  }}
                >
                  {comparison.label}
                </Badge>
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
                onPinPosture={onPinHistoryPosture ? () => onPinHistoryPosture(item) : undefined}
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

export default function CommandCenterShell(props: CommandCenterShellProps) {
  const {
    connectionDetail,
    connectionState,
    consoleRows,
    healthItems,
    heartbeatEnabled,
    lastCheckedAt,
    lastEventAt,
    loading,
    onRefresh,
    onPinCurrentRetrievalPosture,
    onPinHistoryRetrievalPosture,
    pinnedRetrievalPosture,
    retrievalPostureHistoryFilter,
    retrievalPostureHistoryWindowSize,
    onClearPinnedPosture,
    onHistoryFilterChange,
    onHistoryWindowSizeChange,
    onSelectRun,
    onFiltersChange,
    runs,
    selectedRun,
    selectedRunKey,
    traceFilters,
    visibleRuns,
    activeThreadId,
  } = props;

  const [activeLens, setActiveLens] = React.useState<CommandCenterLensId>("agent-command");
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const lensContent = React.useMemo((): React.ReactNode => {
    switch (activeLens) {
      case "agent-command":
        return <CodingWorkOrdersPanel />;

      case "observability":
        return (
          <div className="flex min-h-0 flex-col gap-4 overflow-visible">
            {activeThreadId !== null ? (
              <div>
                <RetrievalPosturePanel
                  compact
                  historyFilter={retrievalPostureHistoryFilter}
                  historyWindowSize={retrievalPostureHistoryWindowSize}
                  onClearPinnedPosture={onClearPinnedPosture}
                  onHistoryFilterChange={onHistoryFilterChange}
                  onHistoryWindowSizeChange={onHistoryWindowSizeChange}
                  onPinCurrentPosture={onPinCurrentRetrievalPosture}
                  onPinHistoryPosture={onPinHistoryRetrievalPosture}
                  pinnedRetrievalPosture={pinnedRetrievalPosture}
                  showHistorySection
                  showComparisonStrip
                  showTrendBadge
                  testId="command-center-thread-posture-panel"
                  threadId={activeThreadId}
                  title="Thread retrieval posture"
                />
              </div>
            ) : null}
            <TraceWorkbench
              allRuns={runs}
              filters={traceFilters}
              onFiltersChange={onFiltersChange}
              onSelectRun={onSelectRun}
              selectedRun={selectedRun}
              selectedRunKey={selectedRunKey}
              visibleRuns={visibleRuns}
            />
            <RecentRetrievalPosturePanel
              onPinHistoryPosture={onPinHistoryRetrievalPosture}
              threadId={activeThreadId}
            />
            <div
              className="h-64 min-h-0 overflow-hidden"
              style={{
                borderRadius: "var(--tile-radius)",
                border: "1px solid var(--panel-border)",
              }}
            >
              <EventConsole
                connectionDetail={connectionDetail}
                connectionState={connectionState}
                lastEventAt={lastEventAt}
                rows={consoleRows}
              />
            </div>
          </div>
        );

      case "heartbeat":
        return <HeartbeatStatusPanel enabled={heartbeatEnabled} />;

      case "runtime-health":
        return (
          <HealthOverview
            healthItems={healthItems}
            lastCheckedAt={lastCheckedAt}
            loading={loading}
            onRefresh={onRefresh}
          />
        );

      case "event-console":
        return (
          <div
            className="h-96 min-h-0 overflow-hidden"
            style={{
              borderRadius: "var(--tile-radius)",
              border: "1px solid var(--panel-border)",
            }}
          >
            <EventConsole
              connectionDetail={connectionDetail}
              connectionState={connectionState}
              lastEventAt={lastEventAt}
              rows={consoleRows}
            />
          </div>
        );

      case "deep-settings":
        return (
          <div
            className="space-y-4"
            style={{
              padding: "var(--card-pad)",
              borderRadius: "var(--tile-radius)",
              border: "1px solid var(--panel-border)",
              background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
            }}
          >
            <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Deep Settings
            </h2>
            <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
              Configuration surfaces for full-app, plugin, and MCP settings will appear here
              once available. This lens is a placeholder for future settings governance.
            </p>
            <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              No backend configuration behavior is implemented through this panel.
            </p>
          </div>
        );

      case "extensions":
        return (
          <div
            className="space-y-4"
            style={{
              padding: "var(--card-pad)",
              borderRadius: "var(--tile-radius)",
              border: "1px solid var(--panel-border)",
              background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
            }}
          >
            <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Extensions
            </h2>
            <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
              Plugin and overlay runtime is governed by the Self-Extending Agent Plugin System
              architecture. Extension proposal persistence and manual install-gate decisions
              exist on the backend, but sandbox execution, autonomous retries, recursive loops,
              worker orchestration, autonomous runtime execution, and plugin execution do not.
            </p>
            <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              This lens is a future/governed placeholder. No plugin registration, install gate,
              sandbox execution, or runtime activation occurs through this panel.
            </p>
          </div>
        );

      default:
        return null;
    }
  }, [
    activeLens,
    activeThreadId,
    connectionDetail,
    connectionState,
    consoleRows,
    healthItems,
    lastCheckedAt,
    lastEventAt,
    loading,
    onClearPinnedPosture,
    onFiltersChange,
    onHistoryFilterChange,
    onHistoryWindowSizeChange,
    onPinCurrentRetrievalPosture,
    onPinHistoryRetrievalPosture,
    onRefresh,
    onSelectRun,
    pinnedRetrievalPosture,
    retrievalPostureHistoryFilter,
    retrievalPostureHistoryWindowSize,
    runs,
    selectedRun,
    selectedRunKey,
    traceFilters,
    visibleRuns,
  ]);

  return (
    <main
      className="min-h-screen overflow-y-auto"
      data-testid="command-center-scroll-shell"
      style={{
        background: "var(--panel-bg)",
        color: "var(--text)",
        padding: "var(--card-pad)",
      }}
    >
      <div
        className="mx-auto flex w-full max-w-7xl gap-0 pb-8"
        data-testid="command-center-shell"
        style={{
          borderRadius: "var(--radius)",
          border: "1px solid var(--panel-border)",
          background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
          minHeight: "calc(100vh - 4rem)",
        }}
      >
        <CommandCenterUtilityRail
          activeLens={activeLens}
          onLensChange={setActiveLens}
          onToggleDrawer={() => setDrawerOpen((current) => !current)}
        />

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto" style={{ padding: "var(--card-pad)" }}>
            {lensContent}
          </div>

          <CommandCenterBottomDrawer
            open={drawerOpen}
            onToggle={() => setDrawerOpen((current) => !current)}
          />
        </div>
      </div>
    </main>
  );
}
