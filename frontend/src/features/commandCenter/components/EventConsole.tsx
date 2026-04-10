import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import type {
  CommandCenterEventConsoleRow,
  CommandCenterEventConsoleSeverity,
} from "@/features/commandCenter/commandCenterObservability";
import type { CommandCenterConnectionState } from "@/features/commandCenter/types";

type EventConsoleProps = {
  connectionDetail: string | null;
  connectionState: CommandCenterConnectionState;
  lastEventAt: number | null;
  rows: CommandCenterEventConsoleRow[];
};

const SEVERITY_OPTIONS: Array<{
  label: string;
  value: "all" | CommandCenterEventConsoleSeverity;
}> = [
  { label: "All severities", value: "all" },
  { label: "Error", value: "error" },
  { label: "Warning", value: "warn" },
  { label: "Info", value: "info" },
  { label: "Debug", value: "debug" },
  { label: "Neutral", value: "neutral" },
];

function toneStyle(severity: CommandCenterEventConsoleSeverity): React.CSSProperties {
  switch (severity) {
    case "error":
      return {
        background: "rgba(239, 68, 68, 0.14)",
        borderColor: "rgba(239, 68, 68, 0.35)",
        color: "rgb(254, 202, 202)",
      };
    case "warn":
      return {
        background: "rgba(250, 204, 21, 0.14)",
        borderColor: "rgba(250, 204, 21, 0.35)",
        color: "rgb(254, 240, 138)",
      };
    case "info":
      return {
        background: "rgba(59, 130, 246, 0.14)",
        borderColor: "rgba(59, 130, 246, 0.35)",
        color: "rgb(191, 219, 254)",
      };
    case "debug":
      return {
        background: "rgba(148, 163, 184, 0.14)",
        borderColor: "rgba(148, 163, 184, 0.35)",
        color: "rgb(226, 232, 240)",
      };
    case "neutral":
    default:
      return {
        background: "rgba(148, 163, 184, 0.1)",
        borderColor: "rgba(148, 163, 184, 0.28)",
        color: "rgb(226, 232, 240)",
      };
  }
}

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

function selectClassName(): string {
  return "h-9 w-full rounded-md border border-[var(--panel-border)] bg-[var(--panel-bg)]/80 px-3 py-1 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]";
}

function matchesQuery(row: CommandCenterEventConsoleRow, query: string): boolean {
  if (!query.trim()) return true;
  const haystack = [
    row.visibleText,
    row.message,
    row.shortLabel,
    row.typeLabel,
    row.identityLabel ?? "",
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
}

function visibleRowsForState({
  filterText,
  severityFilter,
  typeFilter,
  rows,
}: {
  filterText: string;
  rows: CommandCenterEventConsoleRow[];
  severityFilter: "all" | CommandCenterEventConsoleSeverity;
  typeFilter: string;
}): CommandCenterEventConsoleRow[] {
  return rows.filter((row) => {
    if (severityFilter !== "all" && row.severity !== severityFilter) {
      return false;
    }
    if (typeFilter !== "all" && row.typeLabel !== typeFilter) {
      return false;
    }
    return matchesQuery(row, filterText);
  });
}

function ConsoleRow({
  expanded,
  onToggle,
  row,
  wrap,
}: {
  expanded: boolean;
  onToggle: () => void;
  row: CommandCenterEventConsoleRow;
  wrap: boolean;
}) {
  const codeStyle: React.CSSProperties = {
    whiteSpace: wrap ? "pre-wrap" : "nowrap",
  };

  return (
    <div className="border-b border-[var(--panel-border)] last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        className="grid w-full gap-3 px-3 py-2 text-left font-mono text-[12px] leading-5 transition-colors hover:bg-[var(--surface-soft)]/60"
        style={codeStyle}
      >
        <div className="grid gap-3 xl:grid-cols-[9rem_4.5rem_10rem_11rem_minmax(0,1fr)_11rem]">
          <div className="text-[11px] uppercase tracking-[0.14em]" style={{ color: "var(--muted)" }}>
            {row.timestampLabel}
          </div>
          <Badge className="border text-[11px] font-medium leading-none" style={toneStyle(row.severity)}>
            {row.severityLabel}
          </Badge>
          <div className="truncate text-[12px]" style={{ color: "var(--text)" }}>
            {row.typeLabel}
          </div>
          <div className="truncate font-semibold text-[12px]" style={{ color: "var(--text)" }}>
            {row.shortLabel}
          </div>
          <div className={wrap ? "break-words" : "truncate"} style={{ color: "var(--muted)" }}>
            {row.message}
          </div>
          <div className="truncate text-right text-[11px]" style={{ color: "var(--muted)" }}>
            {row.identityLabel ?? "raw"}
          </div>
        </div>
      </button>

      {expanded ? (
        <div className="border-t border-[var(--panel-border)] bg-[var(--surface-soft)] px-3 py-2">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
              Raw payload
            </div>
            <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
              {row.key}
            </Badge>
          </div>
          <pre className="overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-5" style={{ color: "var(--text)" }}>
            {row.payloadText}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

export default function EventConsole({
  connectionDetail,
  connectionState,
  lastEventAt,
  rows,
}: EventConsoleProps) {
  const [paused, setPaused] = React.useState(false);
  const [wrap, setWrap] = React.useState(false);
  const [autoScroll, setAutoScroll] = React.useState(true);
  const [filterText, setFilterText] = React.useState("");
  const [severityFilter, setSeverityFilter] =
    React.useState<"all" | CommandCenterEventConsoleSeverity>("all");
  const [typeFilter, setTypeFilter] = React.useState("all");
  const [expandedRowKey, setExpandedRowKey] = React.useState<string | null>(null);
  const [clearAfterAt, setClearAfterAt] = React.useState<number>(0);
  const [pausedSnapshot, setPausedSnapshot] = React.useState<CommandCenterEventConsoleRow[] | null>(
    null
  );
  const viewportRef = React.useRef<HTMLDivElement | null>(null);

  const filteredRows = React.useMemo(
    () =>
      visibleRowsForState({
        filterText,
        rows,
        severityFilter,
        typeFilter,
      }),
    [filterText, rows, severityFilter, typeFilter]
  );

  const visibleRows = React.useMemo(() => {
    const current = filteredRows.filter((row) => row.receivedAt >= clearAfterAt);
    if (paused) {
      return pausedSnapshot ?? current;
    }
    return current;
  }, [clearAfterAt, filteredRows, paused, pausedSnapshot]);

  const typeOptions = React.useMemo(() => {
    const values = new Set<string>();
    for (const row of rows) {
      values.add(row.typeLabel);
    }
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }, [rows]);

  const severityCounts = React.useMemo(() => {
    return rows.reduce(
      (counts, row) => {
        counts[row.severity] += 1;
        return counts;
      },
      {
        debug: 0,
        error: 0,
        info: 0,
        neutral: 0,
        warn: 0,
      } as Record<CommandCenterEventConsoleSeverity, number>
    );
  }, [rows]);

  React.useEffect(() => {
    if (!autoScroll || paused) return;
    const node = viewportRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [autoScroll, paused, visibleRows]);

  const handlePauseToggle = () => {
    if (paused) {
      setPaused(false);
      setPausedSnapshot(null);
      return;
    }
    setPaused(true);
    setPausedSnapshot(visibleRows);
  };

  const handleClear = () => {
    setClearAfterAt(Date.now());
    setExpandedRowKey(null);
    setPausedSnapshot([]);
  };

  const handleCopyVisible = async () => {
    const text = visibleRows.map((row) => row.visibleText).join("\n");
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Ignore clipboard failures in sandboxed browsers.
    }
  };

  const uniqueTypes = typeOptions.length;

  return (
    <Card
      className="bezel-none border flex h-full min-h-0 flex-col"
      role="region"
      aria-label="Embedded event console"
      data-testid="command-center-event-console"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="space-y-3 border-b border-[var(--panel-border)] pb-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base" style={{ color: "var(--text)" }}>
              Event console
            </CardTitle>
            <p className="max-w-3xl text-sm leading-6" style={{ color: "var(--muted)" }}>
              Raw SSE truth in an embedded machine-room view. {connectionDetail ?? "Live stream connected."}
            </p>
            <div className="flex flex-wrap gap-2 pt-1 text-xs">
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                {connectionState}
              </Badge>
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                Last event: {formatTimestamp(lastEventAt)}
              </Badge>
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                Visible: {visibleRows.length}
              </Badge>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant={paused ? "default" : "ghost"} size="sm" onClick={handlePauseToggle} className="border border-[var(--panel-border)]">
              {paused ? "Resume" : "Pause"}
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={handleClear} className="border border-[var(--panel-border)]">
              Clear
            </Button>
            <Button type="button" variant={wrap ? "default" : "ghost"} size="sm" onClick={() => setWrap((next) => !next)} className="border border-[var(--panel-border)]">
              Wrap
            </Button>
            <Button type="button" variant={autoScroll ? "default" : "ghost"} size="sm" onClick={() => setAutoScroll((next) => !next)} className="border border-[var(--panel-border)]">
              Auto-scroll
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => void handleCopyVisible()} className="border border-[var(--panel-border)]">
              Copy visible
            </Button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-1 text-xs">
            <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
              Filter
            </div>
            <Input value={filterText} onChange={(event) => setFilterText(event.target.value)} placeholder="Search messages, labels, ids" />
          </label>

          <label className="space-y-1 text-xs">
            <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
              Severity
            </div>
            <select className={selectClassName()} value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value as typeof severityFilter)}>
              {SEVERITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1 text-xs">
            <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
              Type
            </div>
            <select className={selectClassName()} value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <option value="all">All types</option>
              {typeOptions.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
              <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                Errors
              </div>
              <div className="mt-1 text-sm font-semibold" style={{ color: "var(--text)" }}>
                {severityCounts.error}
              </div>
            </div>
            <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
              <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                Warnings
              </div>
              <div className="mt-1 text-sm font-semibold" style={{ color: "var(--text)" }}>
                {severityCounts.warn}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
            Rows: {rows.length}
          </Badge>
          <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
            Types: {uniqueTypes}
          </Badge>
          <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
            Paused: {paused ? "yes" : "no"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 p-0">
        <div
          ref={viewportRef}
          className="h-full min-h-0 overflow-auto font-mono"
        >
          {visibleRows.length === 0 ? (
            <div className="p-4 text-sm" style={{ color: "var(--muted)" }}>
              No rows match the current filters.
            </div>
          ) : (
            <div>
              {visibleRows.map((row) => (
                <ConsoleRow
                  key={row.key}
                  expanded={expandedRowKey === row.key}
                  onToggle={() =>
                    setExpandedRowKey((current) => (current === row.key ? null : row.key))
                  }
                  row={row}
                  wrap={wrap}
                />
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
