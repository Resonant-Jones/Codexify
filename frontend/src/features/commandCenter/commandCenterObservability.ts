import type {
  CommandCenterEvent,
  CommandCenterHealthItem,
  CommandCenterRagTracePayload,
  CommandCenterRun,
  CommandCenterStatusTone,
} from "@/features/commandCenter/types";
import {
  COMMAND_CENTER_HEALTH_STATES,
  COMMAND_CENTER_RUN_STATUSES,
  describeCommandCenterHealthStatePresentation,
  describeCommandCenterRunKindLabel,
  describeCommandCenterRunStatusPresentation,
} from "@/features/commandCenter/types";

export type CommandCenterTraceFilters = {
  model: string;
  provider: string;
  retrieval: string;
  status: string;
  threadId: string;
  warningsOnly: boolean;
};

export type CommandCenterHealthViewModel = {
  action: string;
  diagnosis: string;
  label: string;
  lastCheckedLabel: string;
  statusLabel: string;
  statusTone: CommandCenterStatusTone;
};

export type CommandCenterTraceListItemViewModel = {
  key: string;
  label: string;
  modelBadge: string | null;
  providerBadge: string | null;
  retrievalBadge: string | null;
  statusLabel: string;
  statusTone: CommandCenterStatusTone;
  taskOrTurnLabel: string | null;
  threadIdLabel: string | null;
  timestampLabel: string;
  verdict: string;
  warningBadge: string | null;
};

export type CommandCenterEventConsoleSeverity =
  | "error"
  | "warn"
  | "info"
  | "debug"
  | "neutral";

export type CommandCenterEventConsoleRow = {
  identityLabel: string | null;
  isPromoted: boolean;
  key: string;
  message: string;
  payloadText: string;
  receivedAt: number;
  severity: CommandCenterEventConsoleSeverity;
  severityLabel: string;
  shortLabel: string;
  timestampLabel: string;
  typeLabel: string;
  visibleText: string;
};

export type CommandCenterTraceReportSection = {
  label: string;
  value: string;
};

export type CommandCenterTraceReportModel = {
  markdown: string;
  payloadSummaryRows: CommandCenterTraceReportSection[];
  rawTraceText: string;
  verdict: string;
  warnings: string[];
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asArray(value: unknown): unknown[] | null {
  return Array.isArray(value) ? value : null;
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

function firstBoolean(...values: unknown[]): boolean | null {
  for (const value of values) {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") {
      if (value === 1) return true;
      if (value === 0) return false;
      continue;
    }
    if (typeof value === "string") {
      const normalized = value.trim().toLowerCase();
      if (["true", "yes", "1", "on"].includes(normalized)) return true;
      if (["false", "no", "0", "off"].includes(normalized)) return false;
    }
  }
  return null;
}

function normalizeToken(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[.\s-]+/g, "_")
    .replace(/_+/g, "_");
}

function humanizeToken(value: string | null | undefined): string {
  const text = String(value ?? "").trim();
  if (!text) return "—";
  const normalized = text.replace(/[._-]+/g, " ").replace(/\s+/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatTimestamp(value: number | null): string {
  if (value == null) return "—";
  return new Date(value).toLocaleString();
}

function formatDuration(value: number | null): string {
  if (value == null) return "—";
  if (value >= 1000) {
    const seconds = value / 1000;
    const rounded = seconds % 1 === 0 ? seconds.toFixed(0) : seconds.toFixed(2);
    return `${rounded}s`;
  }
  return `${value} ms`;
}

function clipText(value: string | null | undefined, limit = 96): string {
  const text = String(value ?? "").trim();
  if (!text) return "—";
  if (text.length <= limit) return text;
  return `${text.slice(0, Math.max(0, limit - 1))}…`;
}

function stringify(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || "—";
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function renderBoolean(value: boolean | null): string {
  if (value == null) return "—";
  return value ? "yes" : "no";
}

function renderList(value: unknown): string {
  const items = asArray(value);
  if (!items) return stringify(value);
  return items.length > 0 ? items.map((entry) => stringify(entry)).join(" → ") : "—";
}

function renderMaybeNumber(value: number | null | undefined): string {
  return value == null ? "—" : String(value);
}

function renderMaybeString(value: string | null | undefined): string {
  return value == null || !String(value).trim() ? "—" : String(value).trim();
}

function getRunWarnings(run: CommandCenterRun): string[] {
  const warnings: string[] = [];

  if (run.fallbackTriggered) {
    warnings.push(
      run.fallbackReason
        ? `Fallback triggered: ${humanizeToken(run.fallbackReason)}`
        : "Fallback triggered"
    );
  }

  if (run.traceEvidence?.widenReason && run.traceEvidence.widenReason !== "none") {
    warnings.push(`Retrieval widened: ${humanizeToken(run.traceEvidence.widenReason)}`);
  }

  if (run.persistenceOutcome && normalizeToken(run.persistenceOutcome) !== "persisted") {
    warnings.push(`Persistence outcome: ${humanizeToken(run.persistenceOutcome)}`);
  }

  if (run.status === COMMAND_CENTER_RUN_STATUSES.FAILED) {
    warnings.push("Run status is failed");
  }
  if (run.status === COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION) {
    warnings.push("Run needs attention");
  }

  return warnings;
}

function hasRunWarnings(run: CommandCenterRun): boolean {
  return getRunWarnings(run).length > 0;
}

export function shouldPromoteCommandCenterEvent(event: CommandCenterEvent): boolean {
  if (event.taskId || event.requestId || event.runId) {
    return true;
  }

  if (event.traceUrl && (event.threadId != null || event.turnId != null || event.latestTurnMessageId != null)) {
    return true;
  }

  const hasStructuredTask =
    event.threadId != null &&
    Boolean(
      event.turnId ||
        event.taskType ||
        event.retrievalQuery ||
        event.retrievalDepth ||
        event.retrievalIntent ||
        event.documentCount != null ||
        event.memoryCount != null ||
        event.graphCount != null ||
        event.finalProvider ||
        event.finalModel ||
        event.attemptedProvider ||
        event.attemptedModel
    );
  if (hasStructuredTask) {
    return true;
  }

  const lifecycleToken = normalizeToken(event.status ?? event.state ?? event.lifecycleState);
  if (
    lifecycleToken &&
    ["failed", "error", "completed", "running", "cancelled", "needs_attention"].includes(lifecycleToken)
  ) {
    return Boolean(event.threadId != null && event.turnId != null);
  }

  return false;
}

function deriveConsoleSeverity(event: CommandCenterEvent): CommandCenterEventConsoleSeverity {
  const haystack = [
    event.type,
    event.sseType,
    event.kind,
    event.status,
    event.state,
    event.lifecycleState,
    event.summary,
    event.fallbackReason,
    event.persistenceOutcome,
  ]
    .map((value) => normalizeToken(value))
    .filter(Boolean)
    .join(" ");

  if (
    haystack.includes("failed") ||
    haystack.includes("error") ||
    haystack.includes("offline") ||
    haystack.includes("down") ||
    haystack.includes("unreachable")
  ) {
    return "error";
  }

  if (
    haystack.includes("degraded") ||
    haystack.includes("warning") ||
    haystack.includes("needs_attention") ||
    haystack.includes("blocked") ||
    haystack.includes("clarification") ||
    haystack.includes("fallback") ||
    haystack.includes("cancelled")
  ) {
    return "warn";
  }

  if (
    haystack.includes("running") ||
    haystack.includes("completed") ||
    haystack.includes("created") ||
    haystack.includes("connected") ||
    haystack.includes("open")
  ) {
    return "info";
  }

  if (shouldPromoteCommandCenterEvent(event)) {
    return "debug";
  }

  return "neutral";
}

function severityLabel(severity: CommandCenterEventConsoleSeverity): string {
  switch (severity) {
    case "error":
      return "error";
    case "warn":
      return "warning";
    case "info":
      return "info";
    case "debug":
      return "debug";
    case "neutral":
    default:
      return "neutral";
  }
}

function summarizeEventMessage(event: CommandCenterEvent): string {
  const summary = firstString(
    event.summary,
    event.latestTurnContent,
    event.retrievalQuery,
    event.retrievalTarget,
    event.finalModel,
    event.attemptedModel,
    event.finalProvider,
    event.attemptedProvider
  );
  if (summary) {
    return clipText(summary, 180);
  }

  const raw = String(event.raw ?? "").trim();
  if (!raw) return "Event received";
  return clipText(raw, 180);
}

function summarizeEventLabel(event: CommandCenterEvent): string {
  const label =
    firstString(event.kind, event.type, event.sseType, event.lifecycleState, event.status, event.state) ??
    "event";
  return clipText(humanizeToken(label), 72);
}

function payloadText(event: CommandCenterEvent): string {
  if (event.json != null) {
    return stringify(event.json);
  }
  return event.raw || "No raw payload available.";
}

function identityLabel(event: CommandCenterEvent): string | null {
  if (event.taskId) return `task ${event.taskId}`;
  if (event.turnId) return `turn ${event.turnId}`;
  if (event.requestId) return `request ${event.requestId}`;
  if (event.runId) return `run ${event.runId}`;
  if (event.threadId != null) return `thread ${event.threadId}`;
  return null;
}

function textForRow(
  timestamp: number,
  severity: CommandCenterEventConsoleSeverity,
  typeLabel: string,
  shortLabel: string,
  message: string,
  identity: string | null
): string {
  return [
    formatTimestamp(timestamp),
    severityLabel(severity),
    typeLabel,
    shortLabel,
    message,
    identity ?? "raw",
  ].join(" | ");
}

export function buildCommandCenterEventConsoleRows(
  events: CommandCenterEvent[]
): CommandCenterEventConsoleRow[] {
  return [...events]
    .sort((left, right) => {
      if (left.receivedAt !== right.receivedAt) {
        return left.receivedAt - right.receivedAt;
      }
      return (left.eventId ?? "").localeCompare(right.eventId ?? "");
    })
    .map((event, index) => {
      const severity = deriveConsoleSeverity(event);
      const promoted = shouldPromoteCommandCenterEvent(event);
      const typeLabel = clipText(
        humanizeToken(firstString(event.type, event.sseType, event.kind) ?? "event"),
        72
      );
      const shortLabel = summarizeEventLabel(event);
      const message = summarizeEventMessage(event);
      const identity = identityLabel(event);

      return {
        identityLabel: identity,
        isPromoted: promoted,
        key: `${event.eventId ?? event.requestId ?? event.runId ?? event.taskId ?? event.receivedAt}-${index}`,
        message,
        payloadText: payloadText(event),
        receivedAt: event.receivedAt,
        severity,
        severityLabel: severityLabel(severity),
        shortLabel,
        timestampLabel: formatTimestamp(event.receivedAt),
        typeLabel,
        visibleText: textForRow(event.receivedAt, severity, typeLabel, shortLabel, message, identity),
      };
    });
}

export function buildCommandCenterHealthViewModel(
  item: CommandCenterHealthItem
): CommandCenterHealthViewModel {
  const presentation = describeCommandCenterHealthStatePresentation(item.status);
  const details = item.details;

  let diagnosis = item.error ?? "Healthy response";
  if (!item.error && details) {
    diagnosis =
      firstString(
        details.detail,
        details.reason,
        details.message,
        details.status,
        details.error
      ) ?? diagnosis;
  }

  if (item.status === COMMAND_CENTER_HEALTH_STATES.DEGRADED && diagnosis === "Healthy response") {
    diagnosis = "Service returned a degraded status";
  }
  if (item.status === COMMAND_CENTER_HEALTH_STATES.DOWN && diagnosis === "Healthy response") {
    diagnosis = "Service did not report a healthy response";
  }
  if (item.status === COMMAND_CENTER_HEALTH_STATES.UNKNOWN && diagnosis === "Healthy response") {
    diagnosis = "Health status could not be interpreted";
  }

  let action = "Inspect endpoint";
  switch (item.status) {
    case COMMAND_CENTER_HEALTH_STATES.OK:
      action = "No action required";
      break;
    case COMMAND_CENTER_HEALTH_STATES.DEGRADED:
      action = "Inspect latency and dependency drift";
      break;
    case COMMAND_CENTER_HEALTH_STATES.DOWN:
      action = "Check the endpoint, credentials, and backing service";
      break;
    case COMMAND_CENTER_HEALTH_STATES.UNKNOWN:
    default:
      action = "Verify the response contract and auth path";
      break;
  }

  return {
    action,
    diagnosis,
    label: item.label,
    lastCheckedLabel: formatTimestamp(item.checkedAt),
    statusLabel: presentation.label,
    statusTone: presentation.tone,
  };
}

export function buildCommandCenterTraceListItem(
  run: CommandCenterRun
): CommandCenterTraceListItemViewModel {
  const statusPresentation = describeCommandCenterRunStatusPresentation(run.status);
  const warningLabels = getRunWarnings(run);
  const runLabel =
    describeCommandCenterRunKindLabel(run.runKind) ??
    run.runType ??
    (run.identityKind === "synthetic" || run.status === COMMAND_CENTER_RUN_STATUSES.UNKNOWN
      ? "Unknown run"
      : "Task");

  const verdict = hasRunWarnings(run)
    ? warningLabels[0] ?? statusPresentation.label
    : run.status === COMMAND_CENTER_RUN_STATUSES.COMPLETED
      ? "Completed cleanly"
      : run.status === COMMAND_CENTER_RUN_STATUSES.RUNNING
        ? "In progress"
        : run.status === COMMAND_CENTER_RUN_STATUSES.FAILED
          ? "Failed"
          : run.status === COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION
            ? "Needs attention"
            : statusPresentation.label;

  return {
    key: run.key,
    label: runLabel,
    modelBadge: run.finalModel ?? run.attemptedModel ?? null,
    providerBadge: run.finalProvider ?? run.attemptedProvider ?? null,
    retrievalBadge:
      run.retrievalIntent ??
      run.retrievalDepth ??
      run.traceEvidence?.sourceMode ??
      run.traceEvidence?.widenReason ??
      null,
    statusLabel: statusPresentation.label,
    statusTone: statusPresentation.tone,
    taskOrTurnLabel: run.taskId ?? run.turnId ?? run.requestId ?? run.runId ?? null,
    threadIdLabel: run.threadId != null ? String(run.threadId) : null,
    timestampLabel: formatTimestamp(run.lastEventAt),
    verdict,
    warningBadge: warningLabels[0] ?? null,
  };
}

export function filterCommandCenterRuns(
  runs: CommandCenterRun[],
  filters: CommandCenterTraceFilters
): CommandCenterRun[] {
  const statusFilter = normalizeToken(filters.status);
  const providerFilter = normalizeToken(filters.provider);
  const modelFilter = normalizeToken(filters.model);
  const retrievalFilter = normalizeToken(filters.retrieval);
  const threadFilter = normalizeToken(filters.threadId);

  return [...runs]
    .filter((run) => {
      if (statusFilter && statusFilter !== "all") {
        if (normalizeToken(run.status) !== statusFilter) {
          return false;
        }
      }

      if (filters.warningsOnly && !hasRunWarnings(run)) {
        return false;
      }

      if (threadFilter && !normalizeToken(String(run.threadId ?? "")).includes(threadFilter)) {
        return false;
      }

      if (providerFilter) {
        const providerValue = normalizeToken(
          run.finalProvider ?? run.attemptedProvider ?? run.lastEvent.finalProvider ?? run.lastEvent.attemptedProvider
        );
        if (!providerValue.includes(providerFilter)) {
          return false;
        }
      }

      if (modelFilter) {
        const modelValue = normalizeToken(
          run.finalModel ?? run.attemptedModel ?? run.lastEvent.finalModel ?? run.lastEvent.attemptedModel
        );
        if (!modelValue.includes(modelFilter)) {
          return false;
        }
      }

      if (retrievalFilter) {
        const retrievalValue = normalizeToken(
          [
            run.retrievalIntent,
            run.retrievalDepth,
            run.traceEvidence?.sourceMode,
            run.traceEvidence?.widenReason,
          ]
            .filter(Boolean)
            .join(" ")
        );
        if (!retrievalValue.includes(retrievalFilter)) {
          return false;
        }
      }

      return true;
    })
    .sort((left, right) => right.lastEventAt - left.lastEventAt);
}

function countHealthUnknownItems(items: CommandCenterHealthItem[]): number {
  return items.filter((item) => item.status === COMMAND_CENTER_HEALTH_STATES.UNKNOWN).length;
}

function countHealthWarnings(items: CommandCenterHealthItem[]): number {
  return items.filter(
    (item) =>
      item.status === COMMAND_CENTER_HEALTH_STATES.DEGRADED ||
      item.status === COMMAND_CENTER_HEALTH_STATES.DOWN
  ).length;
}

function countRunUnknownItems(runs: CommandCenterRun[]): number {
  return runs.filter((run) => run.status === COMMAND_CENTER_RUN_STATUSES.UNKNOWN).length;
}

function countRunWarnings(runs: CommandCenterRun[]): number {
  return runs.filter((run) => hasRunWarnings(run)).length;
}

function countConsoleUnknownItems(rows: CommandCenterEventConsoleRow[]): number {
  return rows.filter((row) => !row.isPromoted && row.severity === "neutral").length;
}

function countConsoleWarnings(rows: CommandCenterEventConsoleRow[]): number {
  return rows.filter((row) => row.severity === "warn" || row.severity === "error").length;
}

export function countCommandCenterUnknownItems(args: {
  healthItems: CommandCenterHealthItem[];
  runs: CommandCenterRun[];
  consoleRows: CommandCenterEventConsoleRow[];
}): number {
  return (
    countHealthUnknownItems(args.healthItems) +
    countRunUnknownItems(args.runs) +
    countConsoleUnknownItems(args.consoleRows)
  );
}

export function countCommandCenterWarningSignals(args: {
  healthItems: CommandCenterHealthItem[];
  runs: CommandCenterRun[];
  consoleRows: CommandCenterEventConsoleRow[];
}): number {
  return (
    countHealthWarnings(args.healthItems) +
    countRunWarnings(args.runs) +
    countConsoleWarnings(args.consoleRows)
  );
}

function buildListSection(title: string, rows: Array<[string, string]>): string {
  return [title, ...rows.map(([label, value]) => `- **${label}:** ${value}`)].join("\n");
}

function buildRequestRows(run: CommandCenterRun | null, rawTrace: Record<string, unknown>): Array<[string, string]> {
  const retrievalPlan = asRecord(rawTrace.retrieval_plan);
  return [
    ["Intent", firstString(retrievalPlan?.intent) ?? "—"],
    ["Query", run?.traceEvidence?.retrievalQuery ?? firstString(rawTrace.retrieval_query) ?? "—"],
    ["Thread / project", `${renderMaybeNumber(run?.threadId ?? null)} / ${renderMaybeNumber(firstNumber(rawTrace.project_id))}`],
    ["Source mode", firstString(rawTrace.source_mode, run?.traceEvidence?.sourceMode) ?? "—"],
    ["Depth mode", firstString(rawTrace.depth_mode, run?.retrievalDepth) ?? "—"],
    [
      "Retrieval needed",
      renderBoolean(firstBoolean(retrievalPlan?.retrieval_needed, asRecord(rawTrace.payload_summary)?.retrieval_injected)),
    ],
  ];
}

function buildRetrievalPlanRows(rawTrace: Record<string, unknown>): Array<[string, string]> {
  const retrievalPlan = asRecord(rawTrace.retrieval_plan);
  if (!retrievalPlan) {
    return [["Retrieval plan", "Not reported"]];
  }

  return [
    ["Intent", firstString(retrievalPlan.intent) ?? "—"],
    ["User depth", firstString(retrievalPlan.user_depth) ?? "—"],
    ["Resolved depth", firstString(retrievalPlan.resolved_depth) ?? "—"],
    ["Primary scope", firstString(retrievalPlan.primary_scope) ?? "—"],
    ["Time mode", firstString(retrievalPlan.time_mode) ?? "—"],
    ["Graph allowance", firstString(retrievalPlan.graph_allowance) ?? "—"],
    ["Retrieval needed", renderBoolean(firstBoolean(retrievalPlan.retrieval_needed))],
    ["Global fallback", renderBoolean(firstBoolean(retrievalPlan.allow_global_fallback))],
    ["Escalation order", renderList(retrievalPlan.escalation_order)],
    ["Reasons", renderList(retrievalPlan.reasons)],
  ];
}

function buildOutcomeRows(
  run: CommandCenterRun | null,
  normalizedTrace: CommandCenterRagTracePayload | null,
  rawTrace: Record<string, unknown>
): Array<[string, string]> {
  const payloadSummary = asRecord(rawTrace.payload_summary);
  const semanticCount =
    normalizedTrace?.semantic.length ??
    firstNumber(payloadSummary?.semantic_count, asArray(rawTrace.documents)?.length, run?.traceEvidence?.documentCount);
  const memoryCount =
    normalizedTrace?.memory.length ??
    firstNumber(payloadSummary?.memory_count, asArray(rawTrace.memory)?.length, run?.traceEvidence?.memoryCount);
  const graphCount =
    normalizedTrace?.graph.length ??
    firstNumber(payloadSummary?.graph_count, asArray(rawTrace.graph)?.length, run?.traceEvidence?.graphCount);

  return [
    ["Trace presence", run?.traceEvidence?.tracePresenceState ?? "—"],
    ["Semantic contributions", renderMaybeNumber(semanticCount)],
    ["Memory contributions", renderMaybeNumber(memoryCount)],
    ["Graph contributions", renderMaybeNumber(graphCount)],
    ["Linked documents", renderMaybeNumber(run?.traceEvidence?.documentCount ?? null)],
    ["Widen reason", run?.traceEvidence?.widenReason ?? firstString(rawTrace.widen_reason) ?? "—"],
    [
      "Query matched latest turn",
      renderBoolean(run?.traceEvidence?.retrievalQueryMatchesLatestTurn ?? null),
    ],
  ];
}

function buildExecutionRows(run: CommandCenterRun | null): Array<[string, string]> {
  const timings = run?.timings ?? null;
  const firstTokenDelay =
    timings?.queuedAt != null && timings.firstTokenAt != null && timings.firstTokenAt >= timings.queuedAt
      ? timings.firstTokenAt - timings.queuedAt
      : null;
  const firstOutputDelay =
    timings?.queuedAt != null && timings.firstOutputAt != null && timings.firstOutputAt >= timings.queuedAt
      ? timings.firstOutputAt - timings.queuedAt
      : null;

  return [
    ["Attempted provider / model", `${run?.attemptedProvider ?? "—"} / ${run?.attemptedModel ?? "—"}`],
    ["Final provider / model", `${run?.finalProvider ?? "—"} / ${run?.finalModel ?? "—"}`],
    ["Fallback triggered", renderBoolean(run?.fallbackTriggered ?? null)],
    ["Fallback reason", run?.fallbackReason ?? "—"],
    ["Selection source", run?.selectionSource ?? "—"],
    ["Duration", formatDuration(timings?.totalDurationMs ?? null)],
    ["First token delay", formatDuration(firstTokenDelay)],
    ["First output delay", formatDuration(firstOutputDelay)],
    ["Persistence outcome", run?.persistenceOutcome ?? "—"],
  ];
}

function buildPayloadSummaryRows(
  run: CommandCenterRun | null,
  rawTrace: Record<string, unknown>
): Array<[string, string]> {
  const payloadSummary = asRecord(rawTrace.payload_summary);

  const semanticCount =
    firstNumber(payloadSummary?.semantic_count, asArray(rawTrace.documents)?.length, run?.traceEvidence?.documentCount) ??
    null;
  const memoryCount =
    firstNumber(payloadSummary?.memory_count, asArray(rawTrace.memory)?.length, run?.traceEvidence?.memoryCount) ??
    null;
  const graphCount =
    firstNumber(payloadSummary?.graph_count, asArray(rawTrace.graph)?.length, run?.traceEvidence?.graphCount) ??
    null;
  const linkedDocumentCount = firstNumber(payloadSummary?.linked_document_count);
  const fallbackTriggered = run?.fallbackTriggered ?? firstBoolean(rawTrace.fallback_triggered);

  return [
    ["Provider", run?.finalProvider ?? firstString(rawTrace.final_provider, payloadSummary?.final_provider, payloadSummary?.resolved_provider) ?? "—"],
    ["Model", run?.finalModel ?? firstString(rawTrace.final_model, payloadSummary?.final_model, payloadSummary?.resolved_model) ?? "—"],
    ["Attempted provider", run?.attemptedProvider ?? firstString(rawTrace.attempted_provider, payloadSummary?.attempted_provider) ?? "—"],
    ["Attempted model", run?.attemptedModel ?? firstString(rawTrace.attempted_model, payloadSummary?.attempted_model) ?? "—"],
    ["Fallback triggered", renderBoolean(fallbackTriggered)],
    ["Fallback reason", run?.fallbackReason ?? firstString(rawTrace.fallback_reason) ?? "—"],
    ["Selection source", run?.selectionSource ?? firstString(rawTrace.selection_source) ?? "—"],
    ["Persistence outcome", run?.persistenceOutcome ?? firstString(rawTrace.persistence_outcome) ?? "—"],
    ["Message count", renderMaybeNumber(firstNumber(payloadSummary?.message_count, rawTrace.message_count))],
    ["Payload chars", renderMaybeNumber(firstNumber(payloadSummary?.payload_char_count, rawTrace.payload_char_count))],
    ["Payload tokens", renderMaybeNumber(firstNumber(payloadSummary?.payload_estimated_tokens, rawTrace.payload_estimated_tokens))],
    ["Semantic count", renderMaybeNumber(semanticCount)],
    ["Memory count", renderMaybeNumber(memoryCount)],
    ["Graph count", renderMaybeNumber(graphCount)],
    ["Linked document count", renderMaybeNumber(linkedDocumentCount)],
    [
      "Retrieval injected",
      renderBoolean(firstBoolean(payloadSummary?.retrieval_injected, rawTrace.retrieval_injected)),
    ],
    [
      "Persona / imprint present",
      renderBoolean(firstBoolean(payloadSummary?.persona_or_imprint_present, rawTrace.persona_or_imprint_present)),
    ],
    ["Active profile", firstString(rawTrace.active_profile_id) ?? "—"],
    ["Provider override", firstString(rawTrace.provider_override) ?? "—"],
    ["Model override", firstString(rawTrace.model_override) ?? "—"],
    ["Retrieval mode", firstString(rawTrace.retrieval_mode) ?? "—"],
    ["Model mode", firstString(rawTrace.model_mode) ?? "—"],
  ];
}

function buildNotes(
  run: CommandCenterRun | null,
  rawTrace: Record<string, unknown>,
  normalizedTrace: CommandCenterRagTracePayload | null
): string[] {
  const notes: string[] = [];

  if (run?.fallbackTriggered) {
    notes.push(
      run.fallbackReason
        ? `Fallback was triggered (${humanizeToken(run.fallbackReason)}).`
        : "Fallback was triggered."
    );
  }

  if (run?.traceEvidence?.widenReason && run.traceEvidence.widenReason !== "none") {
    notes.push(`Retrieval widened because ${humanizeToken(run.traceEvidence.widenReason)}.`);
  }

  if (run?.persistenceOutcome && normalizeToken(run.persistenceOutcome) !== "persisted") {
    notes.push(`Persistence outcome was ${humanizeToken(run.persistenceOutcome)}.`);
  }

  const payloadSummary = asRecord(rawTrace.payload_summary);
  if (payloadSummary && firstBoolean(payloadSummary.retrieval_injected) === false) {
    notes.push("Retrieval was assembled but not injected into the provider payload.");
  }

  if (
    normalizedTrace &&
    normalizedTrace.semantic.length === 0 &&
    normalizedTrace.memory.length === 0 &&
    (run?.traceEvidence?.tracePresent || asArray(rawTrace.documents)?.length || asArray(rawTrace.graph)?.length)
  ) {
    notes.push("Trace metadata was returned, but no semantic or memory items were normalized.");
  }

  if (notes.length === 0) {
    notes.push("No warnings reported.");
  }

  return notes;
}

function buildMarkdownReport(
  verdict: string,
  requestRows: Array<[string, string]>,
  retrievalPlanRows: Array<[string, string]>,
  outcomeRows: Array<[string, string]>,
  executionRows: Array<[string, string]>,
  payloadSummaryRows: Array<[string, string]>,
  notes: string[]
): string {
  return [
    "## Verdict",
    `> ${verdict}`,
    "",
    buildListSection("## Request", requestRows),
    "",
    buildListSection("## Retrieval Plan", retrievalPlanRows),
    "",
    buildListSection("## Retrieval Outcome", outcomeRows),
    "",
    buildListSection("## Execution", executionRows),
    "",
    buildListSection("## Payload Summary", payloadSummaryRows),
    "",
    "## Notes / Warnings",
    ...notes.map((note) => `- ${note}`),
  ].join("\n");
}

export function buildCommandCenterTraceReportModel(args: {
  normalizedTrace: CommandCenterRagTracePayload | null;
  rawTrace: Record<string, unknown> | null;
  run: CommandCenterRun | null;
  unavailableReason?: string | null;
}): CommandCenterTraceReportModel {
  const rawTrace = args.rawTrace ?? {};
  const requestRows = buildRequestRows(args.run, rawTrace);
  const retrievalPlanRows = buildRetrievalPlanRows(rawTrace);
  const outcomeRows = buildOutcomeRows(args.run, args.normalizedTrace, rawTrace);
  const executionRows = buildExecutionRows(args.run);
  const payloadSummaryRows = buildPayloadSummaryRows(args.run, rawTrace);
  const notes = buildNotes(args.run, rawTrace, args.normalizedTrace);

  let verdict = "Trace available for inspection.";
  if (args.unavailableReason === "no_run") {
    verdict = "Select a run to inspect its trace.";
  } else if (args.unavailableReason === "no_thread") {
    verdict = "This run has no stable thread identity, so the trace cannot be resolved.";
  } else if (args.unavailableReason === "no_trace") {
    verdict = "Trace metadata was resolved, but no detailed payload was returned.";
  } else if (args.run?.status === COMMAND_CENTER_RUN_STATUSES.FAILED) {
    verdict = "The run failed and should be inspected for the failure path.";
  } else if (args.run?.fallbackTriggered) {
    verdict = "The run completed, but provider fallback was triggered.";
  } else if (args.run?.status === COMMAND_CENTER_RUN_STATUSES.COMPLETED) {
    verdict = "The run completed cleanly with an attached trace.";
  } else if (args.run?.status === COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION) {
    verdict = "The run completed with an attention signal.";
  }

  return {
    markdown: buildMarkdownReport(
      verdict,
      requestRows,
      retrievalPlanRows,
      outcomeRows,
      executionRows,
      payloadSummaryRows,
      notes
    ),
    payloadSummaryRows: payloadSummaryRows.map(([label, value]) => ({ label, value })),
    rawTraceText: stringify(args.rawTrace ?? {}),
    verdict,
    warnings: notes.filter((note) => note !== "No warnings reported."),
  };
}

export function describeCommandCenterTraceListSelection(
  run: CommandCenterRun | null,
  filters: CommandCenterTraceFilters
): string {
  if (!run) return "No run selected";

  const status = describeCommandCenterRunStatusPresentation(run.status).label;
  const kind = describeCommandCenterRunKindLabel(run.runKind) ?? run.runType ?? "task";
  const provider = run.finalProvider ?? run.attemptedProvider ?? "—";
  const model = run.finalModel ?? run.attemptedModel ?? "—";
  const retrieval =
    run.retrievalIntent ?? run.retrievalDepth ?? run.traceEvidence?.sourceMode ?? "—";
  const thread = run.threadId != null ? String(run.threadId) : "—";

  const filterBits = [
    filters.status && filters.status !== "all" ? `status ${filters.status}` : null,
    filters.provider ? `provider ${filters.provider}` : null,
    filters.model ? `model ${filters.model}` : null,
    filters.retrieval ? `retrieval ${filters.retrieval}` : null,
    filters.threadId ? `thread ${filters.threadId}` : null,
    filters.warningsOnly ? "warnings only" : null,
  ].filter(Boolean);

  return [
    `${kind} · ${status}`,
    `thread ${thread}`,
    `provider ${provider}`,
    `model ${model}`,
    `retrieval ${retrieval}`,
    filterBits.length > 0 ? `filters: ${filterBits.join(", ")}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}
