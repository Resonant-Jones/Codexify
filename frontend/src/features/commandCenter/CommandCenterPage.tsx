import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import RunDetailDrawer from "@/features/commandCenter/components/RunDetailDrawer";
import RunSummaryCard from "@/features/commandCenter/components/RunSummaryCard";
import useCommandCenterEvents from "@/features/commandCenter/hooks/useCommandCenterEvents";
import useHealthSummary from "@/features/commandCenter/hooks/useHealthSummary";
import type {
  CommandCenterHealthItem,
  CommandCenterRun,
} from "@/features/commandCenter/types";
import {
  describeRuntimeStatusPresentation,
  type RuntimeStatusTone,
} from "@/contracts/runtimeTokens";

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

type BadgeTone = RuntimeStatusTone;

const sectionSurfaceStyle: React.CSSProperties = {
  background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
  borderColor: "var(--panel-border)",
  borderRadius: "var(--tile-radius)",
};

const tileSurfaceStyle: React.CSSProperties = {
  background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
  borderColor: "var(--panel-border)",
  borderRadius: "var(--tile-radius)",
};

const rawSurfaceStyle: React.CSSProperties = {
  background: "var(--surface-soft)",
  borderColor: "var(--panel-border)",
  borderRadius: "var(--tile-radius)",
};

function badgeToneStyle(tone: BadgeTone): React.CSSProperties {
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
  className,
  tone,
}: {
  ariaLabel?: string;
  children: React.ReactNode;
  className?: string;
  tone: BadgeTone;
}) {
  return (
    <Badge
      aria-label={ariaLabel}
      className={`border text-[11px] font-medium leading-none ${className ?? ""}`.trim()}
      style={badgeToneStyle(tone)}
    >
      {children}
    </Badge>
  );
}

function StatusPill({
  ariaLabelPrefix,
  fallbackStatus,
  status,
}: {
  ariaLabelPrefix?: string;
  fallbackStatus?: string;
  status: string | null | undefined;
}) {
  const presentation = describeRuntimeStatusPresentation(
    firstString(status, fallbackStatus)
  );

  return (
    <BadgePill
      ariaLabel={
        ariaLabelPrefix ? `${ariaLabelPrefix} ${presentation.label}` : presentation.label
      }
      tone={presentation.tone}
    >
      {presentation.label}
    </BadgePill>
  );
}

function SummaryTile({
  children,
  dataTestId,
  label,
  note,
}: {
  children: React.ReactNode;
  dataTestId?: string;
  label: string;
  note: React.ReactNode;
}) {
  return (
    <div
      className="space-y-2 border p-[var(--card-pad)]"
      data-testid={dataTestId}
      style={tileSurfaceStyle}
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
  const unknownCount = countUnknownItems(healthItems, runs);

  return (
    <Card
      className="bezel-none border"
      role="region"
      aria-label="Command Center summary strip"
      data-testid="command-center-summary-strip"
      style={{
        ...sectionSurfaceStyle,
      }}
    >
      <CardHeader className="space-y-2 pb-3">
        <CardTitle className="text-base" style={{ color: "var(--text)" }}>
          Runtime snapshot
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Live counts from the current connection, visible health surfaces, and
          run records on this page.
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryTile
          dataTestId="command-center-summary-service"
          label="Service status"
          note={
            unauthorized
              ? "Authentication is required for live surfaces."
              : "Current transport state from the live stream."
          }
        >
          <StatusPill
            ariaLabelPrefix="Service status"
            status={unauthorized ? "unauthorized" : connectionState}
          />
        </SummaryTile>

        <SummaryTile
          dataTestId="command-center-summary-last-event"
          label="Last event"
          note="Most recent page-level event timestamp."
        >
          <div
            className="text-lg font-semibold leading-tight"
            data-testid="command-center-summary-last-event-value"
          >
            {formatTimestamp(lastEventAt)}
          </div>
        </SummaryTile>

        <SummaryTile
          dataTestId="command-center-summary-health-count"
          label="Health surfaces"
          note="Health probes currently shown."
        >
          <div className="text-2xl font-semibold leading-none">{healthItems.length}</div>
        </SummaryTile>

        <SummaryTile
          dataTestId="command-center-summary-run-count"
          label="Visible runs"
          note="Run records currently visible."
        >
          <div className="text-2xl font-semibold leading-none">{runs.length}</div>
        </SummaryTile>

        <SummaryTile
          dataTestId="command-center-summary-unknown-count"
          label="Unknown items"
          note={
            unknownCount > 0
              ? "Unresolved items remain visible."
              : "No unknown statuses are currently visible."
          }
        >
          <div
            className="text-2xl font-semibold leading-none"
            aria-label={`Unknown items ${unknownCount}`}
          >
            {unknownCount}
          </div>
        </SummaryTile>
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
      className="bezel-none border"
      role="region"
      aria-label="Command Center health strip"
      data-testid="command-center-health-strip"
      style={{
        ...sectionSurfaceStyle,
      }}
    >
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-base" style={{ color: "var(--text)" }}>
            Health
          </CardTitle>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Per-endpoint snapshots from the current health checks. Last checked:{" "}
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
            className="bezel-none border"
            data-testid={`command-center-health-${item.key}`}
            style={{
              ...tileSurfaceStyle,
            }}
          >
            <CardContent className="space-y-3 p-[var(--card-pad)]">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="text-sm font-semibold leading-5" style={{ color: "var(--text)" }}>
                    {item.label}
                  </div>
                  <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                    {item.endpoint}
                  </div>
                </div>
                <StatusPill
                  ariaLabelPrefix={`${item.label} status`}
                  status={item.status}
                />
              </div>

              <details className="text-xs" style={{ color: "var(--muted)" }}>
                <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.16em]">
                  Inspect raw details
                </summary>
                <div className="mt-3 space-y-2">
                  <div className="rounded-[var(--tile-radius)] border p-3" style={rawSurfaceStyle}>
                    <div
                      className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Checked
                    </div>
                    <div className="text-xs leading-5" style={{ color: "var(--text)" }}>
                      {formatTimestamp(item.checkedAt)}
                    </div>
                  </div>
                  {item.httpStatus != null ? (
                    <div className="rounded-[var(--tile-radius)] border p-3" style={rawSurfaceStyle}>
                      <div
                        className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                        style={{ color: "var(--muted)" }}
                      >
                        HTTP status
                      </div>
                      <div className="text-xs leading-5" style={{ color: "var(--text)" }}>
                        {item.httpStatus}
                      </div>
                    </div>
                  ) : null}
                  {item.error ? (
                    <div className="rounded-[var(--tile-radius)] border p-3" style={rawSurfaceStyle}>
                      <div
                        className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                        style={{ color: "var(--muted)" }}
                      >
                        Error
                      </div>
                      <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                        {item.error}
                      </div>
                    </div>
                  ) : null}
                  <pre
                    className="overflow-x-auto rounded-[var(--tile-radius)] border p-3 text-[11px] leading-5"
                    style={{
                      ...rawSurfaceStyle,
                      color: "var(--muted)",
                    }}
                  >
                    {item.raw ?? "No raw payload available."}
                  </pre>
                </div>
              </details>
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
      className="bezel-none border"
      role="region"
      aria-label="Command Center runs feed"
      data-testid="command-center-runs-feed"
      style={{
        ...sectionSurfaceStyle,
      }}
    >
      <CardHeader className="space-y-2">
        <CardTitle className="text-base" style={{ color: "var(--text)" }}>
          Runs
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Summary-first cards derived from the global SSE stream. Raw identifiers
          and payload text stay collapsed unless needed.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {runs.length === 0 ? (
          <div
            className="rounded-[var(--tile-radius)] border px-[var(--card-pad)] py-5 text-sm"
            style={{ ...tileSurfaceStyle, color: "var(--muted)" }}
          >
            Waiting for run-identifiable events.
          </div>
        ) : (
          runs.map((run) => {
            const selected = run.key === selectedRunKey;
            return (
              <RunSummaryCard
                key={run.key}
                onOpen={onSelectRun}
                run={run}
                selected={selected}
              />
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

function ApprovalsPanelSection({
  approvals,
  onSelectRun,
  selectedRunKey,
}: {
  approvals: Array<{
    key: string;
    label: string;
    receivedAt: number;
    runId: string | null;
    runKey: string | null;
    status: string | null;
    summary: string;
    taskId: string | null;
  }>;
  onSelectRun: (runKey: string | null) => void;
  selectedRunKey: string | null;
}) {
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
          Approvals
        </CardTitle>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Escalation-facing events filtered from the same global SSE stream.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {approvals.length === 0 ? (
          <div
            className="rounded-xl border px-4 py-5 text-sm"
            style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          >
            No approval or clarification events detected yet.
          </div>
        ) : (
          approvals.map((approval) => {
            const selectable = Boolean(approval.runKey);
            const selected =
              selectable && approval.runKey != null && approval.runKey === selectedRunKey;
            const status = approval.status ?? "attention";

            return (
              <button
                key={approval.key}
                type="button"
                className="w-full text-left"
                onClick={() => onSelectRun(approval.runKey)}
                disabled={!selectable}
              >
                <Card
                  className={`bezel-none rounded-xl border transition-colors ${
                    selected ? "ring-1 ring-[var(--accent)]" : ""
                  }`}
                  style={{
                    background:
                      "color-mix(in srgb, rgba(250, 204, 21, 0.08) 80%, var(--panel-bg))",
                    borderColor: selected ? "var(--accent)" : "var(--panel-border)",
                    opacity: selectable ? 1 : 0.72,
                  }}
                >
                  <CardContent className="space-y-3 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                          {approval.label}
                        </div>
                        <div className="text-xs" style={{ color: "var(--muted)" }}>
                          {approval.summary}
                        </div>
                      </div>
                      <StatusPill
                        ariaLabelPrefix={`${approval.label} status`}
                        status={status}
                      />
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
                      <span
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Task: {approval.taskId ?? "—"}
                      </span>
                      <span
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Run: {approval.runId ?? "—"}
                      </span>
                      <span
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Seen: {new Date(approval.receivedAt).toLocaleString()}
                      </span>
                      <span
                        className="rounded-full border px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        {selectable ? "Selectable" : "No run selection available"}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </button>
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
            className="bezel-none w-full border"
            style={{
              ...sectionSurfaceStyle,
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
      className="min-h-screen overflow-auto p-[var(--card-pad)]"
      style={{ background: "var(--panel-bg)", color: "var(--text)" }}
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-[var(--shell-gap)]">
        <Card
          className="bezel-none border"
          style={{
            ...sectionSurfaceStyle,
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
              <h1 className="text-2xl font-semibold tracking-tight">Agent Command Center</h1>
              <p className="max-w-3xl text-sm leading-6" style={{ color: "var(--muted)" }}>
                Read-only operational surface for service health, runs, approvals,
                and task event streams.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 sm:justify-end">
              <StatusPill
                ariaLabelPrefix="Service status"
                status={unauthorized ? "unauthorized" : connectionState}
              />
              <BadgePill tone="subtle">Last event: {formatTimestamp(lastEventAt)}</BadgePill>
              {connectionDetail ? <BadgePill tone="subtle">{connectionDetail}</BadgePill> : null}
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
            <ApprovalsPanelSection
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
