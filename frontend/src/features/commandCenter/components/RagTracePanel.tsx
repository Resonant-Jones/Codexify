import * as React from "react";

import { Card, CardContent } from "@/components/ui/card";

import useRagTrace from "@/features/commandCenter/hooks/useRagTrace";
import type {
  CommandCenterRagTraceItem,
  CommandCenterRagTracePayload,
  CommandCenterRagTraceUnavailableReason,
  CommandCenterRun,
} from "@/features/commandCenter/types";
import { describeCommandCenterTracePresencePresentation } from "@/features/commandCenter/types";

type RagTracePanelProps = {
  latestTurnMessageId?: string | null;
  run: CommandCenterRun | null;
  threadId?: number | null;
};

function itemChromeStyle(): React.CSSProperties {
  return {
    background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
    borderColor: "var(--panel-border)",
  };
}

function formatScore(score: number | null): string | null {
  if (score == null) return null;
  const rounded = score.toFixed(3);
  return rounded.replace(/0+$/, "").replace(/\.$/, "");
}

function clipInlineText(value: string, limit = 96): string {
  if (value.length <= limit) return value;
  return `${value.slice(0, Math.max(0, limit - 1))}…`;
}

function EmptyState({
  children,
  role,
}: {
  children: React.ReactNode;
  role?: "alert" | "status";
}) {
  return (
    <Card className="bezel-none rounded-xl border" style={itemChromeStyle()}>
      <CardContent
        className="p-4 text-sm"
        role={role}
        style={{ color: "var(--muted)" }}
      >
        {children}
      </CardContent>
    </Card>
  );
}

function MetadataChip({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  if (!value) return null;
  return (
    <span
      className="rounded-full border px-2 py-1 text-xs"
      style={{
        borderColor: "var(--panel-border)",
        color: "var(--muted)",
      }}
    >
      {label}: {value}
    </span>
  );
}

function EvidenceCard({ item }: { item: CommandCenterRagTraceItem }) {
  const score = formatScore(item.score);

  return (
    <Card className="bezel-none rounded-xl border" style={itemChromeStyle()}>
      <CardContent className="space-y-3 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div
            className="text-xs font-semibold uppercase tracking-[0.12em]"
            style={{ color: "var(--muted)" }}
          >
            Evidence {item.id}
          </div>
          {score ? (
            <span
              className="rounded-full border px-2 py-1 text-xs"
              style={{
                borderColor: "var(--panel-border)",
                color: "var(--muted)",
              }}
            >
              Score: {score}
            </span>
          ) : null}
        </div>

        <div
          className="whitespace-pre-wrap break-words text-sm leading-6"
          style={{ color: "var(--text)" }}
        >
          {item.text}
        </div>

        <div className="flex flex-wrap gap-2">
          <MetadataChip label="Source" value={item.source} />
          <MetadataChip label="Silo" value={item.silo} />
          <MetadataChip label="Origin" value={item.origin} />
          <MetadataChip label="Depth used" value={item.depthUsed} />
          <MetadataChip label="Timestamp" value={item.timestamp} />
          <MetadataChip label="Thread" value={item.threadId} />
        </div>
      </CardContent>
    </Card>
  );
}

function EvidenceSection({
  items,
  title,
}: {
  items: CommandCenterRagTraceItem[];
  title: string;
}) {
  if (items.length === 0) return null;

  return (
    <section className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          {title}
        </h3>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <EvidenceCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}

function TraceScopeCard({
  liveTraceLabel,
  latestTurnMessageId,
  resolvedThreadId,
  run,
}: {
  liveTraceLabel: string;
  latestTurnMessageId: string | null;
  resolvedThreadId: number | null;
  run: CommandCenterRun;
}) {
  const traceEvidence = run.traceEvidence ?? null;
  const traceSummaryLabel = traceEvidence
    ? describeCommandCenterTracePresencePresentation(
        traceEvidence.tracePresenceState
      ).label
    : "No trace evidence exists for this run";

  return (
    <Card className="bezel-none rounded-xl border" style={itemChromeStyle()}>
      <CardContent className="space-y-3 p-4">
        <div className="space-y-1">
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Retrieval Trace
          </div>
          <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
            The same thread and latest-turn identity are carried from the run
            detail into this trace view.
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <MetadataChip
            label="Thread"
            value={resolvedThreadId != null ? String(resolvedThreadId) : null}
          />
          <MetadataChip
            label="Latest turn message"
            value={latestTurnMessageId}
          />
          {traceEvidence?.retrievalQuery ? (
            <MetadataChip
              label="Retrieval query"
              value={clipInlineText(traceEvidence.retrievalQuery, 72)}
            />
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <MetadataChip label="Trace summary" value={traceSummaryLabel} />
          <MetadataChip label="Live trace" value={liveTraceLabel} />
        </div>
      </CardContent>
    </Card>
  );
}

function describeLiveTraceLabel({
  error,
  loading,
  run,
  trace,
  unavailable,
  unavailableReason,
}: {
  error: string | null;
  loading: boolean;
  run: CommandCenterRun;
  trace: CommandCenterRagTracePayload | null;
  unavailable: boolean;
  unavailableReason: CommandCenterRagTraceUnavailableReason | null;
}): string {
  if (loading) {
    return "Loading scoped trace";
  }
  if (error) {
    return "Trace unavailable";
  }
  if (trace) {
    return "Aligned to this run/thread";
  }
  if (!unavailable) {
    return "Trace unavailable";
  }

  switch (unavailableReason) {
    case "no_thread":
      return "Trace panel unavailable";
    case "no_trace":
      if (run.traceEvidence?.tracePresent) {
        return "Trace summary present, live trace unavailable";
      }
      if (run.traceEvidence) {
        return "Empty but expected";
      }
      return "No trace evidence exists for this run";
    default:
      return "Trace panel unavailable";
  }
}

function describeUnavailableState({
  run,
  unavailableReason,
}: {
  run: CommandCenterRun;
  unavailableReason: CommandCenterRagTraceUnavailableReason | null;
}): string {
  if (unavailableReason === "no_thread") {
    return "No thread identity available for this run.";
  }
  if (unavailableReason === "no_trace") {
    if (run.traceEvidence?.tracePresent) {
      return "Trace summary present, live trace unavailable.";
    }
    if (run.traceEvidence) {
      return "Empty but expected.";
    }
    return "No trace evidence exists for this run.";
  }
  return "Trace panel unavailable.";
}

export default function RagTracePanel({
  latestTurnMessageId,
  run,
  threadId,
}: RagTracePanelProps) {
  const effectiveRun = React.useMemo(() => {
    if (!run) return run;

    const resolvedThreadId = threadId ?? run.threadId ?? null;
    const resolvedLatestTurnMessageId =
      latestTurnMessageId ?? run.latestTurnMessageId ?? run.traceEvidence?.latestTurnMessageId ?? null;

    if (
      resolvedThreadId === run.threadId &&
      resolvedLatestTurnMessageId === run.latestTurnMessageId
    ) {
      return run;
    }

    return {
      ...run,
      latestTurnMessageId: resolvedLatestTurnMessageId,
      threadId: resolvedThreadId,
    };
  }, [latestTurnMessageId, run, threadId]);

  const {
    error,
    loading,
    resolvedThreadId,
    trace,
    unavailable,
    unavailableReason,
  } = useRagTrace(effectiveRun);

  const scopeThreadId = resolvedThreadId ?? threadId ?? run?.threadId ?? null;
  const scopeLatestTurnMessageId =
    latestTurnMessageId ?? run?.latestTurnMessageId ?? run?.traceEvidence?.latestTurnMessageId ?? null;
  const liveTraceLabel = run
    ? describeLiveTraceLabel({
        error,
        loading,
        run,
        trace,
        unavailable,
        unavailableReason,
      })
    : "No run selected";

  if (loading) {
    return (
      <div className="space-y-3">
        {run ? (
          <TraceScopeCard
            latestTurnMessageId={scopeLatestTurnMessageId}
            liveTraceLabel={liveTraceLabel}
            resolvedThreadId={scopeThreadId}
            run={run}
          />
        ) : null}
        <EmptyState role="status">Loading retrieval trace…</EmptyState>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3">
        {run ? (
          <TraceScopeCard
            latestTurnMessageId={scopeLatestTurnMessageId}
            liveTraceLabel={liveTraceLabel}
            resolvedThreadId={scopeThreadId}
            run={run}
          />
        ) : null}
        <EmptyState role="alert">{error}</EmptyState>
      </div>
    );
  }

  if (unavailable) {
    if (unavailableReason === "no_run") {
      return (
        <EmptyState>
          Select a run to inspect retrieval evidence.
        </EmptyState>
      );
    }

    return (
      <div className="space-y-3">
        {run ? (
          <TraceScopeCard
            latestTurnMessageId={scopeLatestTurnMessageId}
            liveTraceLabel={liveTraceLabel}
            resolvedThreadId={scopeThreadId}
            run={run}
          />
        ) : null}
        <EmptyState>
          {run
            ? describeUnavailableState({ run, unavailableReason })
            : "Trace panel unavailable."}
        </EmptyState>
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="space-y-3">
        {run ? (
          <TraceScopeCard
            latestTurnMessageId={scopeLatestTurnMessageId}
            liveTraceLabel={liveTraceLabel}
            resolvedThreadId={scopeThreadId}
            run={run}
          />
        ) : null}
        <EmptyState>No detailed trace payload is currently available.</EmptyState>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {run ? (
        <TraceScopeCard
          latestTurnMessageId={scopeLatestTurnMessageId}
          liveTraceLabel={liveTraceLabel}
          resolvedThreadId={scopeThreadId}
          run={run}
        />
      ) : null}

      <EvidenceSection items={trace.semantic} title="Semantic Results" />
      <EvidenceSection items={trace.memory} title="Memory Results" />
    </div>
  );
}
