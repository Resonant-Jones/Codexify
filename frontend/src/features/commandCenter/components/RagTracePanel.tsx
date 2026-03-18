import * as React from "react";

import { Card, CardContent } from "@/components/ui/card";

import useRagTrace from "@/features/commandCenter/hooks/useRagTrace";
import type {
  CommandCenterRagTraceItem,
  CommandCenterRun,
} from "@/features/commandCenter/types";

type RagTracePanelProps = {
  run: CommandCenterRun | null;
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
          <div className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--muted)" }}>
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

export default function RagTracePanel({ run }: RagTracePanelProps) {
  const {
    error,
    loading,
    resolvedThreadId,
    trace,
    unavailable,
    unavailableReason,
  } = useRagTrace(run);

  if (loading) {
    return <EmptyState role="status">Loading retrieval trace…</EmptyState>;
  }

  if (error) {
    return <EmptyState role="alert">{error}</EmptyState>;
  }

  if (unavailable) {
    if (unavailableReason === "no_run") {
      return (
        <EmptyState>
          Select a run to inspect retrieval evidence.
        </EmptyState>
      );
    }
    if (unavailableReason === "no_thread") {
      return (
        <EmptyState>
          No resolvable thread available for this run.
        </EmptyState>
      );
    }
    return (
      <EmptyState>
        No retrieval evidence available for this thread yet.
      </EmptyState>
    );
  }

  if (!trace) {
    return null;
  }

  return (
    <div className="space-y-4">
      <Card className="bezel-none rounded-xl border" style={itemChromeStyle()}>
        <CardContent className="space-y-3 p-4">
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Retrieval Trace
          </div>
          <div className="flex flex-wrap gap-2">
            <span
              className="rounded-full border px-2 py-1 text-xs"
              style={{
                borderColor: "var(--panel-border)",
                color: "var(--muted)",
              }}
            >
              Resolved thread: {resolvedThreadId ?? trace.resolvedThreadId}
            </span>
          </div>
        </CardContent>
      </Card>

      <EvidenceSection items={trace.semantic} title="Semantic Results" />
      <EvidenceSection items={trace.memory} title="Memory Results" />
    </div>
  );
}
