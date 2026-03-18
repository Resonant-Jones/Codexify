import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import ApprovalsPanel from "@/features/commandCenter/components/ApprovalsPanel";
import RunDetailDrawer from "@/features/commandCenter/components/RunDetailDrawer";
import RunsPanel from "@/features/commandCenter/components/RunsPanel";
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
      <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {healthItems.map((item) => (
          <Card
            key={item.key}
            className="bezel-none rounded-xl border"
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <CardContent className="space-y-3 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  {item.label}
                </div>
                <Badge
                  className="border"
                  style={{
                    ...healthStyle(item.status),
                    color: "var(--text)",
                  }}
                >
                  {item.status}
                </Badge>
              </div>

              <div className="text-xs" style={{ color: "var(--muted)" }}>
                Endpoint: {item.endpoint}
              </div>

              {item.error ? (
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {item.error}
                </div>
              ) : null}

              {(item.raw || item.error) ? (
                <details className="text-xs" style={{ color: "var(--muted)" }}>
                  <summary className="cursor-pointer">Details</summary>
                  <pre
                    className="mt-2 overflow-x-auto rounded-lg border p-3"
                    style={{
                      borderColor: "var(--panel-border)",
                      background: "rgba(0, 0, 0, 0.12)",
                      color: "var(--text)",
                    }}
                  >
                    {item.raw ?? item.error}
                  </pre>
                </details>
              ) : null}
            </CardContent>
          </Card>
        ))}
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
          <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <div className="text-lg font-semibold">Agent Command Center</div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Read-only operational surface for service health, runs, approvals,
                and task event streams.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Badge
                className="border"
                style={{
                  ...connectionStyle(connectionState),
                  color: "var(--text)",
                }}
              >
                {unauthorized ? "unauthorized" : connectionState}
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

        <HealthStrip
          healthItems={healthItems}
          lastCheckedAt={lastCheckedAt}
          loading={loading}
          onRefresh={refresh}
        />

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <RunsPanel
            onSelectRun={(run) => setSelectedRunKey(run.key)}
            runs={runs}
            selectedRunKey={selectedRunKey}
          />
          <ApprovalsPanel
            approvals={approvals}
            onSelectRun={(runKey) => {
              if (runKey) setSelectedRunKey(runKey);
            }}
            selectedRunKey={selectedRunKey}
          />
        </div>
      </div>

      <RunDetailDrawer
        run={selectedRun}
        onClose={() => setSelectedRunKey(null)}
      />
    </main>
  );
}
