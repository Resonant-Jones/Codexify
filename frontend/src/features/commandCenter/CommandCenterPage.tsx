import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import ApprovalsPanel from "@/features/commandCenter/components/ApprovalsPanel";
import RunDetailDrawer from "@/features/commandCenter/components/RunDetailDrawer";
import useCommandCenterEvents from "@/features/commandCenter/hooks/useCommandCenterEvents";
import useHealthSummary from "@/features/commandCenter/hooks/useHealthSummary";
import type {
  CommandCenterConnectionState,
  CommandCenterHealthItem,
  CommandCenterRun,
} from "@/features/commandCenter/types";

type CommandCenterPageProps = {
  enabled: boolean;
};

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

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
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

function connectionStyle(state: CommandCenterConnectionState): React.CSSProperties {
  switch (state) {
    case "open":
      return {
        background: "rgba(34, 197, 94, 0.12)",
        borderColor: "rgba(34, 197, 94, 0.35)",
      };
    case "connecting":
      return {
        background: "rgba(59, 130, 246, 0.12)",
        borderColor: "rgba(59, 130, 246, 0.35)",
      };
    case "error":
      return {
        background: "rgba(239, 68, 68, 0.12)",
        borderColor: "rgba(239, 68, 68, 0.35)",
      };
    default:
      return {
        background: "rgba(148, 163, 184, 0.12)",
        borderColor: "rgba(148, 163, 184, 0.28)",
      };
  }
}

function healthStyle(status: CommandCenterHealthItem["status"]): React.CSSProperties {
  switch (status) {
    case "OK":
      return {
        background: "rgba(34, 197, 94, 0.12)",
        borderColor: "rgba(34, 197, 94, 0.35)",
      };
    case "FAIL":
      return {
        background: "rgba(239, 68, 68, 0.12)",
        borderColor: "rgba(239, 68, 68, 0.35)",
      };
    default:
      return {
        background: "rgba(148, 163, 184, 0.12)",
        borderColor: "rgba(148, 163, 184, 0.28)",
      };
  }
}

function runStatusStyle(status: CommandCenterRun["status"]): React.CSSProperties {
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

function getRunLabel(run: CommandCenterRun): string {
  return firstString(run.taskId, run.runId, run.key) ?? "Unknown run";
}

function getRunEventType(run: CommandCenterRun): string {
  return (
    firstString(
      run.lastType,
      run.lastKind,
      run.lastEvent.type,
      run.lastEvent.kind,
      run.lastEvent.sseType,
      run.lastEvent.status
    ) ?? "unknown"
  );
}

function formatStatusLabel(value: string): string {
  return value.replace(/_/g, " ");
}

function getServiceStatusLabel(
  connectionState: CommandCenterConnectionState,
  unauthorized: boolean
): string {
  return unauthorized ? "unauthorized" : connectionState;
}

function countUnknownItems(
  healthItems: CommandCenterHealthItem[],
  runs: CommandCenterRun[]
): number {
  const healthUnknownCount = healthItems.filter((item) => item.status === "UNKNOWN").length;
  const runUnknownCount = runs.filter((run) => run.status === "unknown").length;
  return healthUnknownCount + runUnknownCount;
}

function SummaryStrip({
  connectionState,
  lastEventAt,
  healthItems,
  runs,
  unauthorized,
}: {
  connectionState: CommandCenterConnectionState;
  lastEventAt: number | null;
  healthItems: CommandCenterHealthItem[];
  runs: CommandCenterRun[];
  unauthorized: boolean;
}) {
  const serviceStatus = getServiceStatusLabel(connectionState, unauthorized);
  const unknownCount = countUnknownItems(healthItems, runs);

  return (
    <Card
      className="bezel-none rounded-2xl border"
      role="region"
      aria-label="Command Center summary strip"
      data-testid="command-center-summary-strip"
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="space-y-1 pb-3">
        <CardTitle className="text-base" style={{ color: "var(--text)" }}>
          Current runtime summary
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Presentation-only snapshot derived from the active connection, visible
          health surfaces, and run records on this page.
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div
          className="space-y-2 rounded-xl border px-4 py-3"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
          }}
          data-testid="command-center-summary-service"
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
            Service status
          </div>
          <Badge
            className="border"
            aria-label={`Service status ${serviceStatus}`}
            style={{
              ...connectionStyle(connectionState),
              color: "var(--text)",
            }}
          >
            {serviceStatus}
          </Badge>
          {unauthorized ? (
            <div className="text-xs" style={{ color: "var(--muted)" }}>
              Authentication is required for live surfaces.
            </div>
          ) : null}
        </div>

        <div
          className="space-y-2 rounded-xl border px-4 py-3"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
          }}
          data-testid="command-center-summary-last-event"
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
            Last event
          </div>
          <div className="text-sm font-medium" data-testid="command-center-summary-last-event-value">
            {formatTimestamp(lastEventAt)}
          </div>
        </div>

        <div
          className="space-y-2 rounded-xl border px-4 py-3"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
          }}
          data-testid="command-center-summary-health-count"
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
            Health surfaces
          </div>
          <div className="text-2xl font-semibold leading-none">{healthItems.length}</div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            Health probes currently shown
          </div>
        </div>

        <div
          className="space-y-2 rounded-xl border px-4 py-3"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
          }}
          data-testid="command-center-summary-run-count"
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
            Visible runs
          </div>
          <div className="text-2xl font-semibold leading-none">{runs.length}</div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            Run records currently visible
          </div>
        </div>

        <div
          className="space-y-2 rounded-xl border px-4 py-3"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
          }}
          data-testid="command-center-summary-unknown-count"
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
            Unknown items
          </div>
          <Badge
            className="border"
            aria-label={`Unknown items ${unknownCount > 0 ? `yes ${unknownCount}` : "no"}`}
            style={{
              ...healthStyle(unknownCount > 0 ? "UNKNOWN" : "OK"),
              color: "var(--text)",
            }}
          >
            {unknownCount > 0 ? `Yes (${unknownCount})` : "No"}
          </Badge>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            {unknownCount > 0
              ? "One or more items are still unresolved."
              : "No unknown statuses are currently visible."}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthStrip({
  healthItems,
  lastCheckedAt,
  loading,
  onRefresh,
}: {
  healthItems: CommandCenterHealthItem[];
  lastCheckedAt: number | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
}) {
  return (
    <Card
      className="bezel-none rounded-2xl border"
      role="region"
      aria-label="Command Center health strip"
      data-testid="command-center-health-strip"
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-base" style={{ color: "var(--text)" }}>
            Health Strip
          </CardTitle>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Minimal snapshots of the existing health endpoints. Last checked:{" "}
            {formatTimestamp(lastCheckedAt)}
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={() => void onRefresh()}>
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {healthItems.map((item) => (
          <Card
            key={item.key}
            className="bezel-none rounded-xl border"
            data-testid={`command-center-health-${item.key}`}
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <CardContent className="space-y-3 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    {item.label}
                  </div>
                  <div className="text-xs font-mono break-all" style={{ color: "var(--muted)" }}>
                    Endpoint: {item.endpoint}
                  </div>
                </div>
                <Badge
                  className="border"
                  aria-label={`${item.label} status ${item.status}`}
                  style={{
                    ...healthStyle(item.status),
                    color: "var(--text)",
                  }}
                >
                  {item.status}
                </Badge>
              </div>

              {item.error ? (
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {item.error}
                </div>
              ) : null}

              {(item.raw || item.error) ? (
                <details className="text-xs" style={{ color: "var(--muted)" }}>
                  <summary className="cursor-pointer">Details</summary>
                  <div className="mt-2 space-y-2">
                    <div className="rounded-lg border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                        Checked
                      </div>
                      <div className="text-xs" style={{ color: "var(--text)" }}>
                        {formatTimestamp(item.checkedAt)}
                      </div>
                    </div>
                    <pre
                      className="overflow-x-auto rounded-lg border p-3"
                      style={{
                        borderColor: "var(--panel-border)",
                        background: "rgba(0, 0, 0, 0.12)",
                        color: "var(--text)",
                      }}
                    >
                      {item.raw ?? item.error}
                    </pre>
                  </div>
                </details>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </CardContent>
    </Card>
  );
}

function RunFeed({
  onSelectRun,
  runs,
  selectedRunKey,
}: {
  onSelectRun: (run: CommandCenterRun) => void;
  runs: CommandCenterRun[];
  selectedRunKey: string | null;
}) {
  return (
    <Card
      className="bezel-none rounded-2xl border"
      role="region"
      aria-label="Command Center runs feed"
      data-testid="command-center-runs-feed"
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
          Compact feed derived from the global SSE stream. Raw payload details stay
          collapsed unless needed.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {runs.length === 0 ? (
          <div
            className="rounded-xl border px-4 py-5 text-sm"
            style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          >
            Waiting for run-identifiable events.
          </div>
        ) : (
          runs.map((run) => {
            const selected = run.key === selectedRunKey;
            const runLabel = getRunLabel(run);
            const eventType = getRunEventType(run);
            const eventIds = [
              run.lastEvent.eventId ? `Event: ${run.lastEvent.eventId}` : null,
              run.runId ? `Run: ${run.runId}` : null,
              run.taskId ? `Task: ${run.taskId}` : null,
            ].filter((value): value is string => Boolean(value));

            return (
              <Card
                key={run.key}
                className="bezel-none rounded-xl border"
                data-testid={`command-center-run-${run.key}`}
                style={{
                  background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
                  borderColor: selected ? "var(--accent)" : "var(--panel-border)",
                }}
              >
                <CardContent className="space-y-3 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                          {runLabel}
                        </div>
                        <Badge
                          className="border"
                          aria-label={`${runLabel} status ${run.status}`}
                          style={{
                            ...runStatusStyle(run.status),
                            color: "var(--text)",
                          }}
                        >
                          {formatStatusLabel(run.status)}
                        </Badge>
                      </div>
                      <div className="text-xs" style={{ color: "var(--muted)" }}>
                        Last event type: {eventType}
                      </div>
                      <div className="text-xs" style={{ color: "var(--muted)" }}>
                        Timestamp: {formatTimestamp(run.lastEventAt)}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => onSelectRun(run)}
                      aria-label={`Open details for ${runLabel}`}
                    >
                      Open
                    </Button>
                  </div>

                  {run.summary ? (
                    <div className="text-sm" style={{ color: "var(--muted)" }}>
                      {run.summary}
                    </div>
                  ) : null}

                  <details className="text-xs" style={{ color: "var(--muted)" }}>
                    <summary className="cursor-pointer">Details</summary>
                    <div className="mt-2 space-y-3">
                      <div className="rounded-lg border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                          Event IDs
                        </div>
                        <div className="mt-1 flex flex-wrap gap-2">
                          {eventIds.length > 0 ? (
                            eventIds.map((value) => (
                              <Badge
                                key={value}
                                variant="outline"
                                className="px-2 py-1 text-[10px]"
                                style={{ borderColor: "var(--panel-border)" }}
                              >
                                {value}
                              </Badge>
                            ))
                          ) : (
                            <span style={{ color: "var(--muted)" }}>
                              No raw event identifiers available.
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="rounded-lg border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                          Raw message
                        </div>
                        <pre
                          className="mt-2 overflow-x-auto rounded-lg border p-3"
                          style={{
                            borderColor: "var(--panel-border)",
                            background: "rgba(0, 0, 0, 0.12)",
                            color: "var(--text)",
                          }}
                        >
                          {run.lastEvent.raw || "No raw message available."}
                        </pre>
                      </div>
                    </div>
                  </details>
                </CardContent>
              </Card>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

export default function CommandCenterPage({
  enabled,
}: CommandCenterPageProps) {
  const {
    approvals,
    connectionDetail,
    connectionState,
    lastEventAt,
    runs,
    unauthorized,
  } = useCommandCenterEvents({ enabled });
  const { healthItems, lastCheckedAt, loading, refresh } = useHealthSummary({
    enabled,
  });
  const [selectedRunKey, setSelectedRunKey] = React.useState<string | null>(null);
  const serviceStatus = getServiceStatusLabel(connectionState, unauthorized);

  const selectedRun = React.useMemo<CommandCenterRun | null>(
    () => {
      const run = runs.find((candidate) => candidate.key === selectedRunKey) ?? null;
      if (!run) return null;
      return {
        ...run,
        threadId: resolveSelectedRunThreadId(run),
        traceUrl: resolveSelectedRunTraceUrl(run),
      };
    },
    [runs, selectedRunKey]
  );

  React.useEffect(() => {
    if (!selectedRunKey) return;
    if (runs.some((run) => run.key === selectedRunKey)) return;
    setSelectedRunKey(null);
  }, [runs, selectedRunKey]);

  if (!enabled) {
    return (
      <main
        className="min-h-screen px-6 py-10"
        style={{ background: "var(--panel-bg)", color: "var(--text)" }}
      >
        <div className="mx-auto flex max-w-2xl items-center justify-center">
          <Card
            className="bezel-none w-full rounded-2xl border"
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <CardContent className="space-y-3 p-6">
              <div className="text-lg font-semibold">Command Center not enabled</div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Set <code>VITE_ENABLE_COMMAND_CENTER=true</code> to expose this
                route outside development.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main
      className="min-h-screen px-4 py-5 sm:px-6 sm:py-8"
      style={{ background: "var(--panel-bg)", color: "var(--text)" }}
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <Card
          className="bezel-none rounded-2xl border"
          style={{
            background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
            borderColor: "var(--panel-border)",
          }}
        >
          <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-tight">Agent Command Center</h1>
              <p className="max-w-3xl text-sm leading-6" style={{ color: "var(--muted)" }}>
                Read-only operational surface for service health, runs, approvals,
                and task event streams.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Badge
                className="border"
                aria-label={`Service status ${serviceStatus}`}
                style={{
                  ...connectionStyle(connectionState),
                  color: "var(--text)",
                }}
              >
                {serviceStatus}
              </Badge>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                Last event: {formatTimestamp(lastEventAt)}
              </div>
              {connectionDetail ? (
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {connectionDetail}
                </div>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <SummaryStrip
          connectionState={connectionState}
          healthItems={healthItems}
          lastEventAt={lastEventAt}
          runs={runs}
          unauthorized={unauthorized}
        />

        <HealthStrip
          healthItems={healthItems}
          lastCheckedAt={lastCheckedAt}
          loading={loading}
          onRefresh={refresh}
        />

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.75fr)]">
          <RunFeed
            onSelectRun={(run) => setSelectedRunKey(run.key)}
            runs={runs}
            selectedRunKey={selectedRunKey}
          />
          <div className="space-y-5 self-start">
            <ApprovalsPanel
              approvals={approvals}
              onSelectRun={(runKey) => {
                if (runKey) setSelectedRunKey(runKey);
              }}
              selectedRunKey={selectedRunKey}
            />
          </div>
        </div>
      </div>

      <RunDetailDrawer
        run={selectedRun}
        onClose={() => setSelectedRunKey(null)}
      />
    </main>
  );
}
