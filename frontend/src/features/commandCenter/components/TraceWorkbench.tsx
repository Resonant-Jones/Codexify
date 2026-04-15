import * as React from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import useRagTrace from "@/features/commandCenter/hooks/useRagTrace";
import useRetrievalPosture from "@/features/commandCenter/hooks/useRetrievalPosture";
import {
  buildCommandCenterTraceListItem,
  buildCommandCenterTraceReportModel,
  describeCommandCenterTraceListSelection,
} from "@/features/commandCenter/commandCenterObservability";
import type {
  CommandCenterRun,
  CommandCenterTraceFilters,
} from "@/features/commandCenter/types";
import {
  COMMAND_CENTER_RUN_STATUSES,
  describeCommandCenterRunStatusPresentation,
  type CommandCenterRetrievalPosture,
  type CommandCenterStatusTone,
} from "@/features/commandCenter/types";

type TraceWorkbenchProps = {
  allRuns: CommandCenterRun[];
  filters: CommandCenterTraceFilters;
  onFiltersChange: (next: CommandCenterTraceFilters) => void;
  onSelectRun: (runKey: string | null) => void;
  selectedRun: CommandCenterRun | null;
  selectedRunKey: string | null;
  visibleRuns: CommandCenterRun[];
};

const STATUS_OPTIONS: Array<{ label: string; value: string }> = [
  { label: "Any status", value: "all" },
  { label: "Running", value: COMMAND_CENTER_RUN_STATUSES.RUNNING },
  { label: "Completed", value: COMMAND_CENTER_RUN_STATUSES.COMPLETED },
  { label: "Failed", value: COMMAND_CENTER_RUN_STATUSES.FAILED },
  { label: "Cancelled", value: COMMAND_CENTER_RUN_STATUSES.CANCELLED },
  { label: "Needs attention", value: COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION },
  { label: "Unknown", value: COMMAND_CENTER_RUN_STATUSES.UNKNOWN },
];

type TraceTab = "report" | "raw-trace" | "payload-summary";

function toneStyle(tone: CommandCenterStatusTone): React.CSSProperties {
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

function StatusBadge({
  label,
  tone,
}: {
  label: string;
  tone: CommandCenterStatusTone;
}) {
  return (
    <Badge className="border text-[11px] font-medium leading-none" style={toneStyle(tone)}>
      {label}
    </Badge>
  );
}

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

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

export const RETRIEVAL_POSTURE_DIFF_FIELDS = [
  "source_mode",
  "boundary_label",
  "retrieval_override_mode",
  "widen_reason",
  "conversation_only",
] as const;

export type RetrievalPostureDiffField =
  (typeof RETRIEVAL_POSTURE_DIFF_FIELDS)[number];

export type RetrievalPostureDiff = {
  changed: boolean;
  changedFields: RetrievalPostureDiffField[];
};

export function diffRetrievalPosture(
  current: CommandCenterRetrievalPosture,
  previous: CommandCenterRetrievalPosture | null
): RetrievalPostureDiff {
  if (!previous) {
    return { changed: false, changedFields: [] };
  }

  const changedFields = RETRIEVAL_POSTURE_DIFF_FIELDS.filter(
    (field) => current[field] !== previous[field]
  );

  return {
    changed: changedFields.length > 0,
    changedFields,
  };
}

export type RetrievalPostureChangeExplanation = {
  lines: string[];
};

type RetrievalPostureHistoryItem = {
  retrieval_posture: CommandCenterRetrievalPosture | null;
};

export type RetrievalPostureTrend =
  | "stable"
  | "stabilizing"
  | "flapping"
  | "insufficient_history";

export type RetrievalPostureHistoryFilter = "all" | "changed_only";
export type RetrievalPostureHistoryWindowSize = 3 | 5 | 10;

const RETRIEVAL_POSTURE_HISTORY_WINDOW_OPTIONS: RetrievalPostureHistoryWindowSize[] = [3, 5, 10];

const RETRIEVAL_POSTURE_CHANGE_EXPLANATIONS: Record<
  RetrievalPostureDiffField,
  string
> = {
  source_mode: "The retrieval scope changed.",
  boundary_label: "The retrieval boundary changed.",
  retrieval_override_mode: "An explicit retrieval override changed the posture.",
  widen_reason: "The reason for widening changed.",
  conversation_only: "Conversation-only retrieval changed.",
};

const RETRIEVAL_POSTURE_CHANGE_FALLBACK =
  "Retrieval posture changed, but this combination does not yet have a tailored explanation.";

export function describeRetrievalPostureChange(
  diff: RetrievalPostureDiff,
  current: CommandCenterRetrievalPosture | null,
  previous: CommandCenterRetrievalPosture | null
): RetrievalPostureChangeExplanation {
  if (!diff.changed || !current || !previous) {
    return { lines: [] };
  }

  if (diff.changedFields.length === 0 || diff.changedFields.length > 2) {
    return { lines: [RETRIEVAL_POSTURE_CHANGE_FALLBACK] };
  }

  const lines = diff.changedFields.map(
    (field) => RETRIEVAL_POSTURE_CHANGE_EXPLANATIONS[field]
  );

  return lines.length > 0 ? { lines } : { lines: [RETRIEVAL_POSTURE_CHANGE_FALLBACK] };
}

function formatRetrievalPostureHistoryTimestampLegacy(value: string | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

function renderRetrievalPostureBadgesLegacy(posture: CommandCenterRetrievalPosture): React.ReactNode[] {
  return [
    <Badge
      key="source"
      className="border text-[11px] font-medium leading-none"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      source: {posture.source_mode}
    </Badge>,
    <Badge
      key="boundary"
      className="border text-[11px] font-medium leading-none"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      boundary: {posture.boundary_label}
    </Badge>,
    posture.retrieval_override_mode ? (
      <Badge
        key="override"
        className="border text-[11px] font-medium leading-none"
        style={{
          background: "var(--surface-soft)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        override: {posture.retrieval_override_mode}
      </Badge>
    ) : null,
    <Badge
      key="widen"
      className="border text-[11px] font-medium leading-none"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      widen: {posture.widen_reason}
    </Badge>,
    posture.conversation_only ? (
      <Badge
        key="conversation-only"
        className="border text-[11px] font-medium leading-none"
        style={{
          background: "color-mix(in oklab, var(--accent-weak) 60%, transparent)",
          borderColor: "var(--panel-border)",
          color: "var(--text-on-accent)",
        }}
      >
        conversation-only
      </Badge>
    ) : null,
  ].filter((node): node is React.ReactNode => node !== null);
}

function postureSignature(posture: CommandCenterRetrievalPosture | null): string | null {
  if (!posture) return null;

  const {
    source_mode,
    boundary_label,
    retrieval_override_mode,
    widen_reason,
    conversation_only,
  } = posture;

  if (
    typeof source_mode !== "string" ||
    typeof boundary_label !== "string" ||
    (retrieval_override_mode !== null && typeof retrieval_override_mode !== "string") ||
    typeof widen_reason !== "string" ||
    typeof conversation_only !== "boolean"
  ) {
    return null;
  }

  return [
    source_mode,
    boundary_label,
    retrieval_override_mode ?? "null",
    widen_reason,
    String(conversation_only),
  ].join("\u241f");
}

function isRetrievalPostureHistoryItem(
  item: RetrievalPostureHistoryItem
): item is RetrievalPostureHistoryItem & {
  retrieval_posture: CommandCenterRetrievalPosture;
} {
  return postureSignature(item.retrieval_posture) !== null;
}

/**
 * Keep a bounded newest-first history view while dropping repeated identical entries.
 * The comparison is chronological: oldest to newest, retaining only change points.
 */
export function filterRetrievalPostureHistory(
  items: Array<RetrievalPostureHistoryItem>,
  mode: RetrievalPostureHistoryFilter
): Array<RetrievalPostureHistoryItem> {
  const validItems = items.filter(isRetrievalPostureHistoryItem);

  if (mode === "all") {
    return validItems.slice();
  }

  const chronologicalItems = validItems.slice().reverse();
  const changedChronologicalItems: Array<RetrievalPostureHistoryItem> = [];
  let previousPosture: CommandCenterRetrievalPosture | null = null;

  for (const item of chronologicalItems) {
    const currentPosture = item.retrieval_posture;

    if (!currentPosture) {
      continue;
    }

    if (previousPosture === null) {
      previousPosture = currentPosture;
      continue;
    }

    if (diffRetrievalPosture(currentPosture, previousPosture).changed) {
      changedChronologicalItems.push(item);
    }

    previousPosture = currentPosture;
  }

  return changedChronologicalItems.reverse();
}

/**
 * Keep only the newest-first slice the operator chose. The input is already bounded
 * history, so this helper is a pure presentation filter rather than a data source.
 */
export function limitRetrievalPostureHistory(
  items: Array<RetrievalPostureHistoryItem>,
  windowSize: RetrievalPostureHistoryWindowSize
): Array<RetrievalPostureHistoryItem> {
  return items.slice(0, windowSize);
}

/**
 * Classify a bounded newest-first posture window using only canonical posture fields.
 * The window is capped at five items and the rule stays explicit: stable if the
 * newest three match, stabilizing if the newest two match but an older one differs,
 * flapping if the recent window contains repeated transitions, otherwise insufficient.
 */
export function classifyRetrievalPostureTrend(
  items: Array<RetrievalPostureHistoryItem>
): RetrievalPostureTrend {
  const signatures = items
    .slice(0, 5)
    .map((item) => postureSignature(item.retrieval_posture))
    .filter((signature): signature is string => Boolean(signature));

  if (signatures.length < 2) {
    return "insufficient_history";
  }

  if (
    signatures.length >= 3 &&
    signatures[0] === signatures[1] &&
    signatures[1] === signatures[2]
  ) {
    return "stable";
  }

  if (
    signatures.length >= 3 &&
    signatures[0] === signatures[1] &&
    signatures.some((signature) => signature !== signatures[0])
  ) {
    return "stabilizing";
  }

  let transitions = 0;
  for (let index = 1; index < signatures.length; index += 1) {
    if (signatures[index] !== signatures[index - 1]) {
      transitions += 1;
    }
  }

  return transitions >= 2 ? "flapping" : "insufficient_history";
}

const RETRIEVAL_POSTURE_TREND_PRESENTATIONS: Record<
  RetrievalPostureTrend,
  { explanation: string; label: string }
> = {
  stable: {
    explanation: "Recent runs used the same retrieval posture.",
    label: "Stable",
  },
  stabilizing: {
    explanation: "The newest posture matches the previous run, but differs from older recent runs.",
    label: "Stabilizing",
  },
  flapping: {
    explanation: "Recent runs changed posture multiple times.",
    label: "Flapping",
  },
  insufficient_history: {
    explanation: "Not enough completed posture history is available yet.",
    label: "Insufficient history",
  },
};

/**
 * Derives a brief human-readable explanation of the retrieval posture from
 * canonical backend fields. Presentation-only — does not infer or classify.
 */
export function describeRetrievalPosture(posture: CommandCenterRetrievalPosture): string[] {
  const {
    source_mode,
    boundary_label,
    retrieval_override_mode,
    widen_reason,
    conversation_only,
  } = posture;

  const genericFallback = [
    "Retrieval posture metadata is present, but this combination does not yet have a tailored explanation.",
  ];

  if (retrieval_override_mode !== null && retrieval_override_mode !== source_mode) {
    return genericFallback;
  }

  if (
    source_mode === "conversation" &&
    boundary_label === "active_conversation_only" &&
    widen_reason === "none" &&
    conversation_only
  ) {
    return [
      "This run stayed inside the active conversation.",
      "Evidence was constrained to the active conversation.",
      "No widening occurred.",
    ];
  }

  if (
    source_mode === "project" &&
    boundary_label === "same_user_same_project" &&
    widen_reason === "insufficient_thread_hits" &&
    !conversation_only
  ) {
    return [
      "This run operated within the current project scope.",
      "Evidence was drawn from the current project.",
      "This run widened within the current project when thread-local evidence was insufficient.",
    ];
  }

  if (
    source_mode === "personal_knowledge" &&
    boundary_label === "same_user_only" &&
    widen_reason === "explicit_personal_knowledge" &&
    !conversation_only
  ) {
    return [
      "This run was allowed to use the user's personal knowledge scope.",
      "Evidence was drawn from the same user's broader knowledge.",
      "This run was allowed to widen across the same user's knowledge scope.",
    ];
  }

  return genericFallback;
}

type RetrievalPostureTokenField =
  | "source_mode"
  | "boundary_label"
  | "retrieval_override_mode"
  | "widen_reason";

const GENERIC_GLOSSARY_LINE =
  "This token is present but does not yet have a tailored glossary entry.";

function describeRetrievalPostureToken(
  field: RetrievalPostureTokenField,
  value: string | null
): string {
  switch (field) {
    case "source_mode":
      switch (value) {
        case "conversation":
          return "Retrieval began inside the active conversation.";
        case "project":
          return "Retrieval began in the current project scope.";
        case "personal_knowledge":
          return "Retrieval began in the same user's personal knowledge scope.";
        default:
          return GENERIC_GLOSSARY_LINE;
      }
    case "boundary_label":
      switch (value) {
        case "active_conversation_only":
          return "Retrieval stayed inside the active conversation.";
        case "same_user_same_project":
          return "Retrieval could move within the current project.";
        case "same_user_only":
          return "Retrieval could move within the same user's broader knowledge.";
        default:
          return GENERIC_GLOSSARY_LINE;
      }
    case "retrieval_override_mode":
      if (value === null) {
        return "No explicit override was applied.";
      }
      switch (value) {
        case "conversation":
          return "Explicit command intent kept retrieval in conversation scope.";
        case "project":
          return "Explicit command intent kept retrieval in project scope.";
        case "personal_knowledge":
          return "Explicit command intent widened retrieval into personal knowledge.";
        default:
          return GENERIC_GLOSSARY_LINE;
      }
    case "widen_reason":
      switch (value) {
        case "none":
          return "Retrieval did not widen.";
        case "insufficient_thread_hits":
          return "Thread-local evidence was thin, so retrieval widened within the project.";
        case "explicit_personal_knowledge":
          return "Explicit personal-knowledge intent allowed retrieval to widen.";
        default:
          return GENERIC_GLOSSARY_LINE;
      }
    default:
      return GENERIC_GLOSSARY_LINE;
  }
}

function serializeRetrievalPosture(posture: CommandCenterRetrievalPosture): string {
  const snapshot: {
    boundary_label: string;
    conversation_only?: boolean;
    retrieval_override_mode: string | null;
    source_mode: string;
    widen_reason: string;
  } = {
    source_mode: posture.source_mode,
    boundary_label: posture.boundary_label,
    retrieval_override_mode: posture.retrieval_override_mode,
    widen_reason: posture.widen_reason,
  };

  if (typeof posture.conversation_only === "boolean") {
    snapshot.conversation_only = posture.conversation_only;
  }

  return JSON.stringify(snapshot, null, 2);
}

function formatRetrievalPostureAuditNote(posture: CommandCenterRetrievalPosture): string {
  const summaryLines = describeRetrievalPosture(posture);
  const compactSummaryLines =
    summaryLines.length > 1 ? [summaryLines[0], summaryLines[summaryLines.length - 1]] : summaryLines;

  const lines = [
    "Retrieval posture",
    `- source_mode: ${posture.source_mode}`,
    `- boundary_label: ${posture.boundary_label}`,
    `- retrieval_override_mode: ${posture.retrieval_override_mode ?? "null"}`,
    `- widen_reason: ${posture.widen_reason}`,
  ];

  if (typeof posture.conversation_only === "boolean") {
    lines.push(`- conversation_only: ${posture.conversation_only}`);
  }

  lines.push("", "Summary");
  compactSummaryLines.forEach((line) => {
    lines.push(`- ${line}`);
  });

  return lines.join("\n");
}

function formatRetrievalPostureBundle(posture: CommandCenterRetrievalPosture): string {
  return [
    "Retrieval posture JSON",
    serializeRetrievalPosture(posture),
    "",
    "Audit note",
    formatRetrievalPostureAuditNote(posture),
  ].join("\n");
}

type RetrievalPostureCopyFeedback =
  | { action: "posture"; status: "copied" | "failed" }
  | { action: "audit-note"; status: "copied" | "failed" }
  | { action: "bundle"; status: "copied" | "failed" }
  | null;

function renderRetrievalPostureBadges(
  posture: CommandCenterRetrievalPosture
): React.ReactNode[] {
  return [
    <Badge
      key="source_mode"
      className="border text-[11px] font-medium leading-none"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      source: {posture.source_mode}
    </Badge>,
    <Badge
      key="boundary_label"
      className="border text-[11px] font-medium leading-none"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      boundary: {posture.boundary_label}
    </Badge>,
    posture.retrieval_override_mode ? (
    <Badge
      key="retrieval_override_mode"
      className="border text-[11px] font-medium leading-none"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
        override: {posture.retrieval_override_mode}
      </Badge>
    ) : null,
    <Badge
      key="widen_reason"
      className="border text-[11px] font-medium leading-none"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      widen: {posture.widen_reason}
    </Badge>,
    posture.conversation_only ? (
      <Badge
        key="conversation_only"
        className="border text-[11px] font-medium leading-none"
        style={{
          background: "color-mix(in oklab, var(--accent-weak) 60%, transparent)",
          borderColor: "var(--panel-border)",
          color: "var(--text-on-accent)",
        }}
      >
        conversation-only
      </Badge>
    ) : null,
  ].filter((value): value is React.ReactNode => Boolean(value));
}

function formatRetrievalPostureHistoryTimestamp(value: string | null): string {
  if (!value) return "Not yet";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return value;
  return new Date(parsed).toLocaleString();
}

type RetrievalPostureComparisonState = "changed" | "unchanged" | "no-previous" | "none";

type RetrievalPostureComparison = {
  changedFields: RetrievalPostureDiffField[] | null;
  explanationLines: string[] | null;
  label: string | null;
  state: RetrievalPostureComparisonState;
};

function latestRetrievalPostureComparison(
  items: Array<RetrievalPostureHistoryItem>
): RetrievalPostureComparison {
  const current = items[0]?.retrieval_posture ?? null;
  const previous = items[1]?.retrieval_posture ?? null;

  if (!current) {
    return {
      changedFields: null,
      explanationLines: null,
      label: null,
      state: "none",
    };
  }

  if (!previous) {
    return {
      changedFields: null,
      explanationLines: null,
      label: "No previous posture to compare",
      state: "no-previous",
    };
  }

  const comparison = diffRetrievalPosture(current, previous);
  const explanation = describeRetrievalPostureChange(comparison, current, previous);

  return {
    changedFields: comparison.changed ? comparison.changedFields : null,
    explanationLines: comparison.changed ? explanation.lines : null,
    label: comparison.changed
      ? "Posture changed since previous run"
      : "Posture unchanged since previous run",
    state: comparison.changed ? "changed" : "unchanged",
  };
}

function RetrievalPostureDetails({
  comparison,
  historyFilter,
  historyItems,
  historyWindowSize,
  onHistoryFilterChange,
  onHistoryWindowSizeChange,
  retrievalPosture,
  trend,
  showHistorySection,
  showComparisonStrip,
  showTrendBadge,
}: {
  comparison: RetrievalPostureComparison | null;
  historyFilter: RetrievalPostureHistoryFilter;
  historyItems: Array<RetrievalPostureHistoryItem>;
  historyWindowSize: RetrievalPostureHistoryWindowSize;
  onHistoryFilterChange?: (next: RetrievalPostureHistoryFilter) => void;
  onHistoryWindowSizeChange?: (next: RetrievalPostureHistoryWindowSize) => void;
  retrievalPosture: CommandCenterRetrievalPosture;
  trend: RetrievalPostureTrend;
  showHistorySection: boolean;
  showTrendBadge: boolean;
  showComparisonStrip: boolean;
}) {
  const limitedHistoryItems = showHistorySection
    ? limitRetrievalPostureHistory(historyItems, historyWindowSize)
    : [];
  const visibleHistoryItems = showHistorySection
    ? filterRetrievalPostureHistory(limitedHistoryItems, historyFilter)
    : [];

  const glossaryRows: Array<{
    field: RetrievalPostureTokenField;
    label: string;
    value: string | null;
  }> = [
    {
      field: "source_mode",
      label: "source_mode",
      value: retrievalPosture.source_mode,
    },
    {
      field: "boundary_label",
      label: "boundary_label",
      value: retrievalPosture.boundary_label,
    },
    {
      field: "retrieval_override_mode",
      label: "retrieval_override_mode",
      value: retrievalPosture.retrieval_override_mode,
    },
    {
      field: "widen_reason",
      label: "widen_reason",
      value: retrievalPosture.widen_reason,
    },
  ];

  type CopyAction = "posture" | "audit-note" | "bundle";
  type CopyFeedback = { action: CopyAction; status: "copied" | "failed" } | null;

  const [copyFeedback, setCopyFeedback] = React.useState<CopyFeedback>(null);

  async function writeClipboardText(action: CopyAction, text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback({ action, status: "copied" });
    } catch {
      setCopyFeedback({ action, status: "failed" });
    }
  }

  function buildRetrievalPostureJson(): string {
    return JSON.stringify(
      {
        source_mode: retrievalPosture.source_mode,
        boundary_label: retrievalPosture.boundary_label,
        retrieval_override_mode: retrievalPosture.retrieval_override_mode,
        widen_reason: retrievalPosture.widen_reason,
        conversation_only: retrievalPosture.conversation_only,
      },
      null,
      2
    );
  }

  function buildRetrievalPostureAuditNote(): string {
    const summaryLines = describeRetrievalPosture(retrievalPosture);
    return [
      "Retrieval posture",
      `- source_mode: ${retrievalPosture.source_mode}`,
      `- boundary_label: ${retrievalPosture.boundary_label}`,
      `- retrieval_override_mode: ${retrievalPosture.retrieval_override_mode ?? "null"}`,
      `- widen_reason: ${retrievalPosture.widen_reason}`,
      `- conversation_only: ${String(retrievalPosture.conversation_only)}`,
      "",
      "Summary",
      ...summaryLines.map((line) => `- ${line}`),
    ].join("\n");
  }

  function buildRetrievalPostureBundle(): string {
    return [
      "Retrieval posture JSON",
      buildRetrievalPostureJson(),
      "",
      "Audit note",
      buildRetrievalPostureAuditNote(),
    ].join("\n");
  }

  function onCopyPosture(): void {
    void writeClipboardText("posture", buildRetrievalPostureJson());
  }

  function onCopyAuditNote(): void {
    void writeClipboardText("audit-note", buildRetrievalPostureAuditNote());
  }

  function onCopyBundle(): void {
    void writeClipboardText("bundle", buildRetrievalPostureBundle());
  }

  return (
    <>
      {showTrendBadge ? (
        <div
          className="mt-2 rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5"
          style={{
            background: "color-mix(in oklab, var(--surface-soft) 88%, transparent)",
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
          }}
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              className="border text-[11px] font-medium leading-none"
              style={{
                background: "var(--surface-soft)",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
            >
              Posture trend: {RETRIEVAL_POSTURE_TREND_PRESENTATIONS[trend].label}
            </Badge>
          </div>
          <p className="mt-1">{RETRIEVAL_POSTURE_TREND_PRESENTATIONS[trend].explanation}</p>
        </div>
      ) : null}
      {showComparisonStrip && comparison?.label ? (
        <div
          className="mt-2 rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5"
          style={{
            background: "var(--surface-soft)",
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
          }}
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              className="border text-[11px] font-medium leading-none"
              style={{
                background: "var(--surface-soft)",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
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
        </div>
      ) : null}
      {showHistorySection ? (
        <div
          className="mt-2 rounded-[var(--tile-radius)] border px-3 py-3 text-xs leading-5"
          style={{
            background: "color-mix(in oklab, var(--surface-soft) 88%, transparent)",
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em]">
              Recent posture history
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div
                aria-label="Recent posture history window size"
                className="inline-flex rounded-md border p-0.5"
                role="group"
                style={{
                  background: "var(--surface-soft)",
                  borderColor: "var(--panel-border)",
                }}
              >
                {RETRIEVAL_POSTURE_HISTORY_WINDOW_OPTIONS.map((option) => (
                  <Button
                    key={option}
                    type="button"
                    variant={historyWindowSize === option ? "default" : "ghost"}
                    size="sm"
                    onClick={() => onHistoryWindowSizeChange?.(option)}
                    className="h-7 min-w-7 px-2.5 text-[11px]"
                  >
                    {option}
                  </Button>
                ))}
              </div>
              <div
                aria-label="Recent posture history filter"
                className="inline-flex rounded-md border p-0.5"
                role="group"
                style={{
                  background: "var(--surface-soft)",
                  borderColor: "var(--panel-border)",
                }}
              >
                <Button
                  type="button"
                  variant={historyFilter === "all" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => onHistoryFilterChange?.("all")}
                  className="h-7 px-2.5 text-[11px]"
                >
                  All entries
                </Button>
                <Button
                  type="button"
                  variant={historyFilter === "changed_only" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => onHistoryFilterChange?.("changed_only")}
                  className="h-7 px-2.5 text-[11px]"
                >
                  Changed only
                </Button>
              </div>
            </div>
          </div>

          {visibleHistoryItems.length === 0 ? (
            <div
              className="mt-2 rounded-[var(--tile-radius)] border px-3 py-2 text-sm"
              style={{
                background: "var(--surface-soft)",
                borderColor: "var(--panel-border)",
                color: "var(--muted)",
              }}
            >
              No posture changes in the recent history window.
            </div>
          ) : (
            <ul aria-label="Recent posture history" className="mt-2 space-y-2">
              {visibleHistoryItems.map((item, index) => {
                const posture = item.retrieval_posture;

                if (!posture) {
                  return null;
                }

                return (
                  <li
                    key={`${posture.source_mode}-${posture.boundary_label}-${posture.retrieval_override_mode ?? "null"}-${posture.widen_reason}-${String(posture.conversation_only)}-${index}`}
                  >
                    <div
                      className="rounded-[var(--tile-radius)] border px-3 py-2"
                      style={{
                        background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
                        borderColor: "var(--panel-border)",
                      }}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          className="border text-[11px] font-medium leading-none"
                          style={{
                            background: "var(--surface-soft)",
                            borderColor: "var(--panel-border)",
                            color: "var(--text)",
                          }}
                        >
                          {index === 0 ? "Newest" : `Earlier ${index + 1}`}
                        </Badge>
                        <span style={{ color: "var(--text)" }}>Posture snapshot</span>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge
                          className="border text-[11px] font-medium leading-none"
                          style={{
                            background: "var(--surface-soft)",
                            borderColor: "var(--panel-border)",
                            color: "var(--text)",
                          }}
                        >
                          scope {posture.source_mode}
                        </Badge>
                        <Badge
                          className="border text-[11px] font-medium leading-none"
                          style={{
                            background: "var(--surface-soft)",
                            borderColor: "var(--panel-border)",
                            color: "var(--text)",
                          }}
                        >
                          limit {posture.boundary_label}
                        </Badge>
                        {posture.retrieval_override_mode ? (
                          <Badge
                            className="border text-[11px] font-medium leading-none"
                            style={{
                              background: "var(--surface-soft)",
                              borderColor: "var(--panel-border)",
                              color: "var(--text)",
                            }}
                          >
                            override {posture.retrieval_override_mode}
                          </Badge>
                        ) : null}
                        <Badge
                          className="border text-[11px] font-medium leading-none"
                          style={{
                            background: "var(--surface-soft)",
                            borderColor: "var(--panel-border)",
                            color: "var(--text)",
                          }}
                        >
                          widen {posture.widen_reason}
                        </Badge>
                        {posture.conversation_only ? (
                          <Badge
                            className="border text-[11px] font-medium leading-none"
                            style={{
                              background: "color-mix(in oklab, var(--accent-weak) 60%, transparent)",
                              borderColor: "var(--panel-border)",
                              color: "var(--text-on-accent)",
                            }}
                          >
                            conv only yes
                          </Badge>
                        ) : (
                          <Badge
                            className="border text-[11px] font-medium leading-none"
                            style={{
                              background: "var(--surface-soft)",
                              borderColor: "var(--panel-border)",
                              color: "var(--text)",
                            }}
                          >
                            conv only no
                          </Badge>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-2">
        <Badge
          className="border text-[11px] font-medium leading-none"
          style={{
            background: "var(--surface-soft)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
          }}
        >
          source: {retrievalPosture.source_mode}
        </Badge>
        <Badge
          className="border text-[11px] font-medium leading-none"
          style={{
            background: "var(--surface-soft)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
          }}
        >
          boundary: {retrievalPosture.boundary_label}
        </Badge>
        {retrievalPosture.retrieval_override_mode ? (
          <Badge
            className="border text-[11px] font-medium leading-none"
            style={{
              background: "var(--surface-soft)",
              borderColor: "var(--panel-border)",
              color: "var(--text)",
            }}
          >
            override: {retrievalPosture.retrieval_override_mode}
          </Badge>
        ) : null}
        <Badge
          className="border text-[11px] font-medium leading-none"
          style={{
            background: "var(--surface-soft)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
          }}
        >
          widen: {retrievalPosture.widen_reason}
        </Badge>
        {retrievalPosture.conversation_only && (
          <Badge
            className="border text-[11px] font-medium leading-none"
            style={{
              background: "color-mix(in oklab, var(--accent-weak) 60%, transparent)",
              borderColor: "var(--panel-border)",
              color: "var(--text-on-accent)",
            }}
          >
            conversation-only
          </Badge>
        )}
      </div>
      <div
        className="mt-2 rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5"
        style={{
          background: "var(--surface-soft)",
          borderColor: "var(--panel-border)",
          color: "var(--muted)",
        }}
      >
        {describeRetrievalPosture(retrievalPosture).map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
      <div
        className="mt-2 rounded-[var(--tile-radius)] border px-3 py-2"
        style={{
          background: "color-mix(in oklab, var(--surface-soft) 84%, transparent)",
          borderColor: "var(--panel-border)",
        }}
      >
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          What these fields mean
        </div>
        <dl className="mt-2 grid gap-2 md:grid-cols-2">
          {glossaryRows.map((row) => (
            <div key={row.field} className="space-y-0.5">
              <dt className="text-[11px] font-semibold tracking-[0.12em]" style={{ color: "var(--text)" }}>
                {row.label}
              </dt>
              <dd className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                {describeRetrievalPostureToken(row.field, row.value)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="border border-[var(--panel-border)]"
          onClick={onCopyPosture}
        >
          Copy posture
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="border border-[var(--panel-border)]"
          onClick={onCopyAuditNote}
        >
          Copy audit note
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="border border-[var(--panel-border)]"
          onClick={onCopyBundle}
        >
          Copy posture bundle
        </Button>
        {copyFeedback?.action === "posture" && copyFeedback.status === "copied" ? (
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            Copied posture
          </span>
        ) : copyFeedback?.action === "posture" && copyFeedback.status === "failed" ? (
          <span className="text-xs" style={{ color: "var(--danger-text)" }}>
            Copy failed
          </span>
        ) : copyFeedback?.action === "audit-note" && copyFeedback.status === "copied" ? (
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            Copied audit note
          </span>
        ) : copyFeedback?.action === "audit-note" && copyFeedback.status === "failed" ? (
          <span className="text-xs" style={{ color: "var(--danger-text)" }}>
            Audit note copy failed
          </span>
        ) : copyFeedback?.action === "bundle" && copyFeedback.status === "copied" ? (
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            Copied posture bundle
          </span>
        ) : copyFeedback?.action === "bundle" && copyFeedback.status === "failed" ? (
          <span className="text-xs" style={{ color: "var(--danger-text)" }}>
            Posture bundle copy failed
          </span>
        ) : null}
      </div>
    </>
  );
}

export function RetrievalPostureSummaryRow({
  createdAt,
  posture,
  taskId,
}: {
  createdAt: string | null;
  posture: CommandCenterRetrievalPosture;
  taskId: string;
}) {
  const summaryLines = describeRetrievalPosture(posture);
  const summary = summaryLines[0] ?? "Retrieval posture metadata is present.";

  return (
    <div
      className="space-y-2 rounded-[var(--tile-radius)] border px-3 py-2"
      data-testid="command-center-retrieval-posture-history-item"
      style={{
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
      }}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
        >
          {formatRetrievalPostureHistoryTimestamp(createdAt)}
        </span>
        <span
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
        >
          Task: {taskId}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">{renderRetrievalPostureBadges(posture)}</div>

      <div className="text-sm leading-5" style={{ color: "var(--text)" }}>
        {summary}
      </div>
    </div>
  );
}

export function RetrievalPosturePanel({
  className,
  compact = false,
  historyFilter = "all",
  historyWindowSize = 5,
  onHistoryFilterChange,
  onHistoryWindowSizeChange,
  showHistorySection = false,
  threadId,
  title = "Retrieval posture",
  testId,
  showComparisonStrip = false,
  showTrendBadge = false,
}: {
  className?: string;
  compact?: boolean;
  historyFilter?: RetrievalPostureHistoryFilter;
  historyWindowSize?: RetrievalPostureHistoryWindowSize;
  onHistoryFilterChange?: (next: RetrievalPostureHistoryFilter) => void;
  onHistoryWindowSizeChange?: (next: RetrievalPostureHistoryWindowSize) => void;
  showHistorySection?: boolean;
  threadId: number | null;
  title?: string;
  testId?: string;
  showComparisonStrip?: boolean;
  showTrendBadge?: boolean;
}) {
  const { error: postureError, loading: postureLoading, retrievalPosture, status: postureStatus } =
    useRetrievalPosture(threadId);
  const recentHistoryByThreadRef = React.useRef(new Map<number, RetrievalPostureHistoryItem[]>());
  const [trend, setTrend] = React.useState<RetrievalPostureTrend>("insufficient_history");
  const [comparison, setComparison] = React.useState<RetrievalPostureComparison>({
    changedFields: null,
    explanationLines: null,
    label: null,
    state: "none",
  });

  React.useEffect(() => {
    setCopyFeedback(null);
  }, [threadId, retrievalPosture]);

  const writeRetrievalPostureToClipboard = React.useCallback(async (payload: string) => {
    if (!navigator.clipboard?.writeText) {
      throw new Error("Clipboard unavailable");
    }

    await navigator.clipboard.writeText(payload);
  }, []);

  const handleCopyPosture = React.useCallback(async () => {
    if (!retrievalPosture) return;

    try {
      await writeRetrievalPostureToClipboard(serializeRetrievalPosture(retrievalPosture));
      setCopyFeedback({ action: "posture", status: "copied" });
    } catch {
      setCopyFeedback({ action: "posture", status: "failed" });
    }
  }, [retrievalPosture, writeRetrievalPostureToClipboard]);

  const handleCopyAuditNote = React.useCallback(async () => {
    if (!retrievalPosture) return;

    try {
      await writeRetrievalPostureToClipboard(formatRetrievalPostureAuditNote(retrievalPosture));
      setCopyFeedback({ action: "audit-note", status: "copied" });
    } catch {
      setCopyFeedback({ action: "audit-note", status: "failed" });
    }
  }, [retrievalPosture, writeRetrievalPostureToClipboard]);

  const handleCopyBundle = React.useCallback(async () => {
    if (!retrievalPosture) return;

    try {
      await writeRetrievalPostureToClipboard(formatRetrievalPostureBundle(retrievalPosture));
      setCopyFeedback({ action: "bundle", status: "copied" });
    } catch {
      setCopyFeedback({ action: "bundle", status: "failed" });
    }
  }, [retrievalPosture, writeRetrievalPostureToClipboard]);

  const comparisonSnapshot = retrievalPosture
    ? [
        retrievalPosture.source_mode,
        retrievalPosture.boundary_label,
        retrievalPosture.retrieval_override_mode ?? "null",
        retrievalPosture.widen_reason,
        String(retrievalPosture.conversation_only),
      ].join("\u241f")
    : null;

  React.useEffect(() => {
    if (postureLoading || postureError || postureStatus !== "ok" || !retrievalPosture) {
      return;
    }

    if (threadId !== null) {
      const nextHistory = [
        { retrieval_posture: retrievalPosture },
        ...(recentHistoryByThreadRef.current.get(threadId) ?? []),
      ].slice(0, 10);
      recentHistoryByThreadRef.current.set(threadId, nextHistory);

      const boundedHistory = limitRetrievalPostureHistory(nextHistory, historyWindowSize);
      setTrend(classifyRetrievalPostureTrend(boundedHistory));
      setComparison(latestRetrievalPostureComparison(boundedHistory));
    }
  }, [comparisonSnapshot, postureError, postureLoading, postureStatus, threadId]);

  const historyItems = threadId !== null ? recentHistoryByThreadRef.current.get(threadId) ?? [] : [];

  React.useEffect(() => {
    if (threadId === null) {
      setTrend("insufficient_history");
      setComparison({
        changedFields: null,
        explanationLines: null,
        label: null,
        state: "none",
      });
      return;
    }

    const boundedHistory = limitRetrievalPostureHistory(
      recentHistoryByThreadRef.current.get(threadId) ?? [],
      historyWindowSize
    );

    setTrend(classifyRetrievalPostureTrend(boundedHistory));
    setComparison(latestRetrievalPostureComparison(boundedHistory));
  }, [historyWindowSize, threadId]);

  const rootClassName = [
    compact ? "rounded-[var(--tile-radius)] border p-2.5" : "rounded-[var(--tile-radius)] border p-3",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      data-testid={testId}
      className={rootClassName}
      style={{
        background: "color-mix(in oklab, var(--surface-soft) 60%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <div
        className={compact ? "text-[10px] font-semibold uppercase tracking-[0.16em]" : "text-[11px] font-semibold uppercase tracking-[0.18em]"}
        style={{ color: "var(--muted)" }}
      >
        {title}
      </div>
      {postureLoading ? (
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          Loading retrieval posture…
        </div>
      ) : postureError ? (
        <div className="mt-2 text-sm" style={{ color: "var(--danger-text)" }}>
          {postureError}
        </div>
      ) : postureStatus === "empty" ? (
        <div className="mt-2 text-sm" style={{ color: "var(--muted)" }}>
          No retrieval posture evidence for this thread.
        </div>
      ) : retrievalPosture ? (
          <RetrievalPostureDetails
            comparison={comparison}
            historyFilter={historyFilter}
            historyItems={historyItems}
            historyWindowSize={historyWindowSize}
            onHistoryFilterChange={onHistoryFilterChange}
            onHistoryWindowSizeChange={onHistoryWindowSizeChange}
            retrievalPosture={retrievalPosture}
            showHistorySection={showHistorySection}
            showComparisonStrip={showComparisonStrip}
            showTrendBadge={showTrendBadge}
          trend={trend}
        />
      ) : null}
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

function selectClassName(active: boolean): string {
  return [
    "h-9 w-full rounded-md border bg-[var(--panel-bg)]/80 px-3 py-1 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]",
    active ? "border-[var(--accent)]" : "border-[var(--panel-border)]",
  ].join(" ");
}

function updateFilter(
  filters: CommandCenterTraceFilters,
  onFiltersChange: (next: CommandCenterTraceFilters) => void,
  key: keyof CommandCenterTraceFilters,
  value: string | boolean
): void {
  onFiltersChange({
    ...filters,
    [key]: value,
  });
}

function MarkdownBody({ markdown }: { markdown: string }) {
  const components = {
    h2: ({ children }: { children?: React.ReactNode }) => (
      <h2 className="mt-4 text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
        {children}
      </h2>
    ),
    p: ({ children }: { children?: React.ReactNode }) => (
      <p className="text-sm leading-6" style={{ color: "var(--text)" }}>
        {children}
      </p>
    ),
    ul: ({ children }: { children?: React.ReactNode }) => (
      <ul className="space-y-1 pl-5 text-sm leading-6" style={{ color: "var(--text)" }}>
        {children}
      </ul>
    ),
    li: ({ children }: { children?: React.ReactNode }) => <li>{children}</li>,
    blockquote: ({ children }: { children?: React.ReactNode }) => (
      <blockquote
        className="rounded-[var(--tile-radius)] border-l-4 border-[var(--accent)] bg-[var(--surface-soft)] px-4 py-3"
        style={{ color: "var(--text)" }}
      >
        {children}
      </blockquote>
    ),
    code: ({
      inline,
      children,
    }: {
      inline?: boolean;
      children?: React.ReactNode;
    }) =>
      inline ? (
        <code
          className="rounded bg-[var(--chip-bg)] px-1 py-0.5 text-[11px]"
          style={{ color: "var(--text)" }}
        >
          {children}
        </code>
      ) : (
        <code className="text-xs leading-5" style={{ color: "var(--text)" }}>
          {children}
        </code>
      ),
  } as const;

  return (
    <div className="space-y-3">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components as any}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

function TraceListItem({
  item,
  onSelectRun,
  selected,
}: {
  item: ReturnType<typeof buildCommandCenterTraceListItem>;
  onSelectRun: (runKey: string) => void;
  selected: boolean;
}) {
  return (
    <button
      type="button"
      className="w-full text-left"
      onClick={() => onSelectRun(item.key)}
    >
      <Card
        className="bezel-none border transition-colors hover:border-[var(--accent)]"
        style={{
          background: "color-mix(in oklab, var(--panel-bg) 93%, transparent)",
          borderColor: selected ? "var(--accent)" : "var(--panel-border)",
        }}
      >
        <CardContent className="space-y-3 p-[var(--card-pad)]">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <div className="text-sm font-semibold leading-5" style={{ color: "var(--text)" }}>
                {item.label}
              </div>
              <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                {item.verdict}
              </div>
            </div>
            <StatusBadge label={item.statusLabel} tone={item.statusTone} />
          </div>

          <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              {item.timestampLabel}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Thread: {item.threadIdLabel ?? "—"}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              {item.taskOrTurnLabel ?? "No stable task id"}
            </span>
          </div>

          <div className="flex flex-wrap gap-2 text-xs">
            {item.providerBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                {item.providerBadge}
              </Badge>
            ) : null}
            {item.modelBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                {item.modelBadge}
              </Badge>
            ) : null}
            {item.retrievalBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                {item.retrievalBadge}
              </Badge>
            ) : null}
            {item.warningBadge ? (
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--danger-surface)", borderColor: "var(--danger-border)", color: "var(--danger-text)" }}>
                {item.warningBadge}
              </Badge>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

function TraceListPane({
  onSelectRun,
  runs,
  selectedRunKey,
}: {
  onSelectRun: (runKey: string) => void;
  runs: CommandCenterRun[];
  selectedRunKey: string | null;
}) {
  return (
    <section
      data-testid="command-center-trace-list-pane"
      className="flex min-h-0 flex-col overflow-hidden rounded-[var(--tile-radius)] border"
      style={{ background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)", borderColor: "var(--panel-border)" }}
    >
      <div className="border-b border-[var(--panel-border)] p-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Trace list
            </div>
            <div className="text-xs" style={{ color: "var(--muted)" }}>
              Newest first, with filtered runs only.
            </div>
          </div>
          <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
            {runs.length} visible
          </Badge>
        </div>
      </div>
      <div data-testid="command-center-trace-list-scroll" className="min-h-0 flex-1 overflow-auto p-2">
        {runs.length === 0 ? (
          <div className="rounded-[var(--tile-radius)] border p-4 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            No runs match the current filters.
          </div>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => {
              const item = buildCommandCenterTraceListItem(run);
              return (
                <TraceListItem
                  key={item.key}
                  item={item}
                  onSelectRun={onSelectRun}
                  selected={item.key === selectedRunKey}
                />
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      variant={active ? "default" : "ghost"}
      size="sm"
      onClick={onClick}
      className={active ? "" : "border border-[var(--panel-border)]"}
    >
      {children}
    </Button>
  );
}

function TraceViewerPane({
  filters,
  selectedRun,
}: {
  filters: CommandCenterTraceFilters;
  selectedRun: CommandCenterRun | null;
}) {
  const effectiveRun = React.useMemo(() => {
    if (!selectedRun) return null;
    return {
      ...selectedRun,
      threadId: resolveSelectedRunThreadId(selectedRun),
      traceUrl: resolveSelectedRunTraceUrl(selectedRun),
    };
  }, [selectedRun]);

  const { error, loading, rawTrace, trace, unavailable, unavailableReason } =
    useRagTrace(effectiveRun);
  const [tab, setTab] = React.useState<TraceTab>("report");

  React.useEffect(() => {
    setTab("report");
  }, [selectedRun?.key]);

  const reportModel = React.useMemo(
    () =>
      buildCommandCenterTraceReportModel({
        normalizedTrace: trace,
        rawTrace,
        run: effectiveRun,
        unavailableReason,
      }),
    [effectiveRun, rawTrace, trace, unavailableReason]
  );

  const selectionLabel = describeCommandCenterTraceListSelection(effectiveRun, filters);
  const statusPresentation = describeCommandCenterRunStatusPresentation(
    effectiveRun?.status ?? null
  );

  const rawTraceText = React.useMemo(() => {
    if (!rawTrace) {
      return "No raw trace payload available.";
    }
    try {
      return JSON.stringify(rawTrace, null, 2);
    } catch {
      return String(rawTrace);
    }
  }, [rawTrace]);

  const retrievalPostureThreadId = effectiveRun?.threadId ?? null;

  return (
    <section
      data-testid="command-center-trace-viewer-pane"
      className="flex min-h-0 flex-col overflow-hidden rounded-[var(--tile-radius)] border"
      style={{ background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)", borderColor: "var(--panel-border)" }}
    >
      <div className="border-b border-[var(--panel-border)] p-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Trace viewer
            </div>
            <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              {selectionLabel}
            </div>
            <div className="flex flex-wrap gap-2 pt-1 text-xs">
              <StatusBadge label={statusPresentation.label} tone={statusPresentation.tone} />
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                Thread: {effectiveRun?.threadId ?? "—"}
              </Badge>
              <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                Trace: {loading ? "loading" : unavailable ? "unavailable" : "ready"}
              </Badge>
              {error ? (
                <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--danger-surface)", borderColor: "var(--danger-border)", color: "var(--danger-text)" }}>
                  {error}
                </Badge>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <TabButton active={tab === "report"} onClick={() => setTab("report")}>
              Report
            </TabButton>
            <TabButton active={tab === "raw-trace"} onClick={() => setTab("raw-trace")}>
              Raw Trace
            </TabButton>
            <TabButton active={tab === "payload-summary"} onClick={() => setTab("payload-summary")}>
              Payload Summary
            </TabButton>
          </div>
        </div>
      </div>
      <div data-testid="command-center-trace-viewer-scroll" className="min-h-0 flex-1 overflow-auto p-4">
        {!effectiveRun ? (
          <div className="rounded-[var(--tile-radius)] border p-4 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
            Select a run to inspect its trace report.
          </div>
        ) : tab === "report" ? (
          <div className="space-y-4">
            <div className="rounded-[var(--tile-radius)] border p-4" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                Verdict
              </div>
              <div className="mt-1 text-sm leading-6" style={{ color: "var(--text)" }}>
                {reportModel.verdict}
              </div>
            </div>
            <MarkdownBody markdown={reportModel.markdown} />
          </div>
        ) : tab === "raw-trace" ? (
          <pre className="overflow-auto rounded-[var(--tile-radius)] border p-4 text-xs leading-5" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
            {rawTraceText}
          </pre>
        ) : (
          <div className="space-y-3">
            {reportModel.payloadSummaryRows.length === 0 ? (
              <div className="rounded-[var(--tile-radius)] border p-4 text-sm" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--muted)" }}>
                No payload summary fields were available.
              </div>
            ) : (
              <div className="grid gap-2">
                {reportModel.payloadSummaryRows.map((row) => (
                  <div
                    key={row.label}
                    className="grid gap-2 rounded-[var(--tile-radius)] border px-3 py-2 text-sm md:grid-cols-[12rem_minmax(0,1fr)]"
                    style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}
                  >
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                      {row.label}
                    </div>
                    <div className="min-w-0 break-words" style={{ color: "var(--text)" }}>
                      {row.value}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {reportModel.warnings.length > 0 ? (
              <div className="rounded-[var(--tile-radius)] border p-4" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                  Notes / warnings
                </div>
                <ul className="mt-2 space-y-1 pl-5 text-sm leading-6" style={{ color: "var(--text)" }}>
                  {reportModel.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
        {effectiveRun ? <RetrievalPosturePanel threadId={retrievalPostureThreadId} /> : null}
      </div>
    </section>
  );
}

function TraceFilterBar({
  filters,
  onFiltersChange,
}: {
  filters: CommandCenterTraceFilters;
  onFiltersChange: (next: CommandCenterTraceFilters) => void;
}) {
  return (
    <div className="grid gap-3 rounded-[var(--tile-radius)] border p-3 md:grid-cols-2 xl:grid-cols-6" style={{ background: "color-mix(in oklab, var(--surface-soft) 85%, transparent)", borderColor: "var(--panel-border)" }}>
      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Status
        </div>
        <select
          className={selectClassName(filters.status !== "all")}
          value={filters.status}
          onChange={(event) => updateFilter(filters, onFiltersChange, "status", event.target.value)}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Provider
        </div>
        <Input
          value={filters.provider}
          onChange={(event) => updateFilter(filters, onFiltersChange, "provider", event.target.value)}
          placeholder="openai, local, anthropic"
          list="command-center-provider-options"
        />
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Model
        </div>
        <Input
          value={filters.model}
          onChange={(event) => updateFilter(filters, onFiltersChange, "model", event.target.value)}
          placeholder="gpt-5, claude, llama"
          list="command-center-model-options"
        />
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Retrieval
        </div>
        <Input
          value={filters.retrieval}
          onChange={(event) => updateFilter(filters, onFiltersChange, "retrieval", event.target.value)}
          placeholder="personal_knowledge, graph, widen"
        />
      </label>

      <label className="space-y-1 text-xs">
        <div className="font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
          Thread id
        </div>
        <Input
          value={filters.threadId}
          onChange={(event) => updateFilter(filters, onFiltersChange, "threadId", event.target.value)}
          placeholder="42"
        />
      </label>

      <label className="flex items-end">
        <Button
          type="button"
          variant={filters.warningsOnly ? "default" : "ghost"}
          size="sm"
          onClick={() => updateFilter(filters, onFiltersChange, "warningsOnly", !filters.warningsOnly)}
          className="w-full border border-[var(--panel-border)]"
        >
          {filters.warningsOnly ? "Warnings only" : "Show all runs"}
        </Button>
      </label>
    </div>
  );
}

export default function TraceWorkbench({
  allRuns,
  filters,
  onFiltersChange,
  onSelectRun,
  selectedRun,
  selectedRunKey,
  visibleRuns,
}: TraceWorkbenchProps) {
  const selectionSummary = describeCommandCenterTraceListSelection(selectedRun, filters);

  const providerOptions = React.useMemo(() => {
    const values = new Set<string>();
    for (const run of allRuns) {
      const value = firstString(run.finalProvider, run.attemptedProvider);
      if (value) values.add(value);
    }
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }, [allRuns]);

  const modelOptions = React.useMemo(() => {
    const values = new Set<string>();
    for (const run of allRuns) {
      const value = firstString(run.finalModel, run.attemptedModel);
      if (value) values.add(value);
    }
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }, [allRuns]);

  return (
    <Card
      className="bezel-none border flex h-full min-h-0 flex-col overflow-hidden"
      role="region"
      aria-label="Command Center trace workbench"
      data-testid="command-center-trace-workbench"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="space-y-2 border-b border-[var(--panel-border)] pb-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base" style={{ color: "var(--text)" }}>
              RAG trace workbench
            </CardTitle>
            <p className="max-w-3xl text-sm leading-6" style={{ color: "var(--muted)" }}>
              Interpreted diagnostic reports on the right, filtered run identities on the left.
            </p>
            <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              {selectionSummary}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
              {visibleRuns.length} visible
            </Badge>
            <Badge className="border text-[11px] font-medium leading-none" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
              Selected: {selectedRunKey ?? "none"}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-[var(--card-pad)]">
        <TraceFilterBar filters={filters} onFiltersChange={onFiltersChange} />

        <div className="grid min-h-0 flex-1 gap-4 overflow-hidden xl:grid-cols-[minmax(18rem,0.36fr)_minmax(0,0.64fr)]">
          <TraceListPane onSelectRun={onSelectRun} runs={visibleRuns} selectedRunKey={selectedRunKey} />
          <TraceViewerPane filters={filters} selectedRun={selectedRun} />
        </div>

        <datalist id="command-center-provider-options">
          {providerOptions.map((provider) => (
            <option key={provider} value={provider} />
          ))}
        </datalist>
        <datalist id="command-center-model-options">
          {modelOptions.map((model) => (
            <option key={model} value={model} />
          ))}
        </datalist>
      </CardContent>
    </Card>
  );
}
