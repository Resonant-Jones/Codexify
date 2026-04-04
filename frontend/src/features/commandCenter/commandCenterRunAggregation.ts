import type {
  CommandCenterApproval,
  CommandCenterCanonicalTaskEventType,
  CommandCenterEvent,
  CommandCenterRun,
  CommandCenterRunIdentityKind,
  CommandCenterRunKind,
  CommandCenterRunStatus,
  CommandCenterRunTerminalOutcome,
  CommandCenterRunStreamingEvidence,
  CommandCenterRunTimings,
  CommandCenterRunTraceEvidence,
} from "@/features/commandCenter/types";
import {
  COMMAND_CENTER_RUN_STATUSES,
  COMMAND_CENTER_RUN_KINDS,
  COMMAND_CENTER_RUN_TERMINAL_OUTCOMES,
  COMMAND_CENTER_TRACE_PRESENCE_STATES,
  normalizeCommandCenterTerminalOutcome,
} from "@/features/commandCenter/types";

const RUN_EVENT_LIMIT = 50;

type MutableRun = {
  eventCount: number;
  events: CommandCenterEvent[];
  identityKind: CommandCenterRunIdentityKind;
  key: string;
  lastEvent: CommandCenterEvent;
  lastEventAt: number;
  lastKind: string | null;
  lastType: string | null;
  latestTurnMessageId: string | null;
  requestId: string | null;
  runId: string | null;
  runKind: CommandCenterRunKind | null;
  runType: string | null;
  state: string | null;
  status: CommandCenterRunStatus;
  summary: string;
  taskId: string | null;
  terminalOutcome: CommandCenterRunTerminalOutcome | null;
  threadId: number | null;
  turnId: string | null;
};

type AggregationResult = {
  approvals: CommandCenterApproval[];
  runs: CommandCenterRun[];
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

function firstToken(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return String(value);
    }
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

function normalizeToken(value: string | null): string {
  return String(value ?? "")
    .trim()
    .toLowerCase();
}

function humanizeToken(value: string | null): string {
  const normalized = String(value ?? "")
    .trim()
    .replace(/[._-]+/g, " ")
    .replace(/\s+/g, " ");
  return normalized.toLowerCase();
}

function coerceRawPayload(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value ?? "");
  } catch {
    return String(value ?? "");
  }
}

function parseJson(raw: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed);
    return asRecord(parsed);
  } catch {
    return null;
  }
}

const NESTED_RECORD_KEYS = [
  "data",
  "event",
  "meta",
  "metadata",
  "payload",
  "response",
  "result",
  "run",
  "task",
  "trace",
  "context",
  "lifecycle",
  "runtime",
  "thread",
  "timings",
] as const;

function parseTimestamp(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (!trimmed) return null;

  const parsed = Number(trimmed);
  if (Number.isFinite(parsed) && /^(?:\d+)(?:\.\d+)?$/.test(trimmed)) {
    return parsed;
  }

  const parsedDate = Date.parse(trimmed);
  return Number.isFinite(parsedDate) ? parsedDate : null;
}

function parseBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (value === 1) return true;
    if (value === 0) return false;
    return null;
  }
  if (typeof value !== "string") return null;

  const normalized = normalizeToken(value);
  if (["true", "yes", "y", "1", "present", "available"].includes(normalized)) {
    return true;
  }
  if (["false", "no", "n", "0", "missing", "absent", "unavailable"].includes(normalized)) {
    return false;
  }
  return null;
}

function formatLifecycleStateToken(value: string): string {
  return value
    .trim()
    .replace(/[.\s-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toUpperCase();
}

function normalizeLifecycleStateToken(value: string | null): string | null {
  if (!value) return null;

  const normalized = normalizeToken(value).replace(/[.\s-]+/g, "_");
  switch (normalized) {
    case "accepted":
    case "accepted_degraded":
    case "created":
    case "queued":
      return "QUEUED";
    case "dispatching":
      return "DISPATCHING";
    case "awaiting_ack":
    case "waiting_for_ack":
    case "awaiting_confirmation":
      return "AWAITING_ACK";
    case "awaiting_model":
    case "running":
    case "model_warming":
      return "AWAITING_MODEL";
    case "awaiting_first_token":
    case "first_token_pending":
      return "AWAITING_FIRST_TOKEN";
    case "streaming":
    case "chunk":
    case "progress":
      return "STREAMING";
    case "completed":
    case "done":
    case "success":
    case "succeeded":
      return "COMPLETED";
    case "cancelled":
    case "canceled":
      return "CANCELLED";
    case "timed_out":
    case "timeout":
      return "TIMED_OUT";
    case "failed_retryable":
      return "FAILED_RETRYABLE";
    case "failed_fatal":
    case "failed":
    case "error":
      return "FAILED_FATAL";
    case "orphaned":
      return "ORPHANED";
    case "replayed":
      return "REPLAYED";
    default:
      return formatLifecycleStateToken(value);
  }
}

function collectRecords(json: Record<string, unknown> | null): Record<string, unknown>[] {
  const records: Record<string, unknown>[] = [];
  if (!json) return records;

  const queue: Record<string, unknown>[] = [];
  const seen = new Set<Record<string, unknown>>();

  const enqueue = (value: unknown): void => {
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        const parsed = parseJson(trimmed);
        if (parsed && !seen.has(parsed)) {
          seen.add(parsed);
          queue.push(parsed);
        }
      }
    }
    const record = asRecord(value);
    if (!record || seen.has(record)) return;
    seen.add(record);
    queue.push(record);
  };

  enqueue(json);

  while (queue.length > 0) {
    const record = queue.shift();
    if (!record) continue;
    records.push(record);
    for (const key of NESTED_RECORD_KEYS) {
      enqueue(record[key]);
    }
  }

  return records;
}

function readKey(records: Record<string, unknown>[], keys: string[]): string | null {
  for (const record of records) {
    for (const key of keys) {
      const value = firstString(record[key]);
      if (value) return value;
    }
  }
  return null;
}

function readToken(records: Record<string, unknown>[], keys: string[]): string | null {
  for (const record of records) {
    for (const key of keys) {
      const value = firstToken(record[key]);
      if (value) return value;
    }
  }
  return null;
}

function readNumber(records: Record<string, unknown>[], keys: string[]): number | null {
  for (const record of records) {
    for (const key of keys) {
      const value = firstNumber(record[key]);
      if (value != null) return value;
    }
  }
  return null;
}

function readThreadId(records: Record<string, unknown>[]): number | null {
  for (const record of records) {
    const thread = asRecord(record.thread);
    if (!thread) continue;
    const value = firstNumber(thread.thread_id, thread.threadId, thread.id);
    if (value != null) return value;
  }
  return readNumber(records, ["thread_id", "threadId"]);
}

function readTimestamp(records: Record<string, unknown>[], keys: string[]): number | null {
  for (const record of records) {
    for (const key of keys) {
      const value = parseTimestamp(record[key]);
      if (value != null) return value;
    }
  }
  return null;
}

function readBoolean(records: Record<string, unknown>[], keys: string[]): boolean | null {
  for (const record of records) {
    for (const key of keys) {
      const value = parseBoolean(record[key]);
      if (value != null) return value;
    }
  }
  return null;
}

function readTaskType(records: Record<string, unknown>[]): string | null {
  for (const record of records) {
    const value = firstToken(record.type, record.task_type, record.taskType);
    if (!value) continue;
    if (looksLikeEventType(value)) continue;
    return value;
  }
  return null;
}

function readTraceUrl(records: Record<string, unknown>[]): string | null {
  return readKey(records, ["trace_url", "traceUrl"]);
}

function readLatestTurnContent(records: Record<string, unknown>[]): string | null {
  return readKey(records, ["latest_turn_content", "latestTurnContent"]);
}

function normalizeSourceModeToken(value: string | null): string | null {
  if (!value) return null;

  const normalized = normalizeToken(value).replace(/[.\s-]+/g, "_");
  if (normalized === "project" || normalized === "personal_knowledge") {
    return normalized;
  }
  return normalized || null;
}

function readSourceMode(records: Record<string, unknown>[]): string | null {
  const explicit = readKey(records, ["source_mode", "sourceMode"]);
  if (explicit) {
    return normalizeSourceModeToken(explicit);
  }

  const origin = readKey(records, ["origin"]);
  if (origin) {
    const match = origin.match(/(?:^|\|)\s*source_mode=([^|]+)/i);
    if (match?.[1]) {
      return normalizeSourceModeToken(match[1]);
    }
  }

  return null;
}

function readWidenReason(records: Record<string, unknown>[]): string | null {
  const explicit = readKey(records, ["widen_reason", "widenReason"]);
  return explicit ? normalizeToken(explicit) : null;
}

function readNestedNumber(
  record: Record<string, unknown>,
  nestedKeys: string[],
  countKeys: string[]
): number | null {
  for (const nestedKey of nestedKeys) {
    const nested = asRecord(record[nestedKey]);
    if (!nested) continue;
    for (const countKey of countKeys) {
      const value = firstNumber(nested[countKey]);
      if (value != null) return value;
    }
  }
  return null;
}

function readCollectionCount(
  records: Record<string, unknown>[],
  {
    countKeys,
    nestedKeys,
    nestedCountKeys,
    arrayKeys,
  }: {
    countKeys: string[];
    nestedKeys?: string[];
    nestedCountKeys?: string[];
    arrayKeys?: string[];
  }
): number | null {
  for (const record of records) {
    for (const key of countKeys) {
      const value = firstNumber(record[key]);
      if (value != null) return value;
    }

    const nestedCount =
      nestedKeys && nestedKeys.length > 0
        ? readNestedNumber(record, nestedKeys, nestedCountKeys ?? countKeys)
        : null;
    if (nestedCount != null) {
      return nestedCount;
    }

    for (const key of arrayKeys ?? []) {
      const value = record[key];
      if (Array.isArray(value)) {
        return value.length;
      }
    }
  }
  return null;
}

function inferLifecycleStateFromCanonicalType(
  canonicalType: string | null
): string | null {
  switch (normalizeToken(canonicalType)) {
    case "task.created":
      return "QUEUED";
    case "task.running":
      return "AWAITING_MODEL";
    case "task.state":
      return "STATE";
    case "task.chunk":
      return "STREAMING";
    case "task.completed":
      return "COMPLETED";
    case "task.failed":
      return "FAILED_FATAL";
    case "task.cancelled":
      return "CANCELLED";
    default:
      return null;
  }
}

function readLifecycleState(
  records: Record<string, unknown>[],
  canonicalType: string | null
): string | null {
  const explicit = readToken(records, [
    "lifecycle_state",
    "lifecycleState",
    "request_state",
    "requestState",
    "phase",
    "state",
  ]);
  if (explicit) {
    return normalizeLifecycleStateToken(explicit);
  }

  return inferLifecycleStateFromCanonicalType(canonicalType);
}

function isJsonLike(raw: string): boolean {
  const trimmed = raw.trim();
  return trimmed.startsWith("{") || trimmed.startsWith("[");
}

function isCanonicalTaskEventType(
  value: string | null
): value is CommandCenterCanonicalTaskEventType {
  switch (normalizeToken(value)) {
    case "task.created":
    case "task.running":
    case "task.state":
    case "task.chunk":
    case "task.completed":
    case "task.failed":
    case "task.cancelled":
      return true;
    default:
      return false;
  }
}

function looksLikeEventType(value: string | null): boolean {
  return /^(task|run|browser|message|thread|connector|completion)\./.test(
    normalizeToken(value)
  );
}

function normalizeCanonicalEventType(value: string | null): string | null {
  switch (normalizeToken(value)) {
    case "task.progress":
      return "task.chunk";
    case "task.updated":
      return "task.state";
    case "completion.error":
      return "task.failed";
    case "task.created":
    case "task.running":
    case "task.state":
    case "task.chunk":
    case "task.completed":
    case "task.failed":
    case "task.cancelled":
      return normalizeToken(value);
    default:
      return null;
  }
}

function deriveTaskState(
  canonicalType: string | null,
  records: Record<string, unknown>[]
): string | null {
  const explicitState = readToken(records, [
    "state",
    "lifecycle_state",
    "lifecycleState",
    "status",
  ]);
  const canonical = normalizeToken(canonicalType);

  if (canonical === "task.state") {
    return explicitState ? humanizeToken(explicitState) : "state";
  }

  if (explicitState) {
    return humanizeToken(explicitState);
  }

  switch (canonical) {
    case "task.created":
      return "created";
    case "task.running":
      return "running";
    case "task.chunk":
      return "chunk";
    case "task.completed":
      return "completed";
    case "task.failed":
      return "failed";
    case "task.cancelled":
      return "cancelled";
    default:
      return null;
  }
}

function deriveTerminalOutcome(
  canonicalType: string | null,
  records: Record<string, unknown>[]
): CommandCenterRun["terminalOutcome"] | null {
  const explicitOutcome = normalizeCommandCenterTerminalOutcome(
    readToken(records, ["terminal_outcome", "terminalOutcome", "outcome"])
  );
  if (explicitOutcome) return explicitOutcome;

  switch (normalizeToken(canonicalType)) {
    case "task.completed":
      return "completed";
    case "task.failed":
      return "failed";
    case "task.cancelled":
      return "cancelled";
    default:
      return null;
  }
}

function deriveRunType(
  canonicalType: string | null,
  taskType: string | null,
  sseType: string | null
): string | null {
  if (taskType) return humanizeToken(taskType);

  const canonical = normalizeToken(canonicalType);
  if (canonical && canonical.startsWith("task.")) {
    return "task";
  }

  const rawType = normalizeToken(sseType);
  if (!rawType || rawType === "message") {
    return null;
  }

  return humanizeToken(rawType);
}

function deriveRunKind(
  canonicalType: string | null,
  taskType: string | null,
  sseType: string | null
): CommandCenterRunKind {
  const normalizedTaskType = normalizeToken(taskType);
  if (normalizedTaskType === "chat.completion" || normalizedTaskType === "chat_completion") {
    return COMMAND_CENTER_RUN_KINDS.CHAT_COMPLETION;
  }

  const normalizedCanonical = normalizeToken(canonicalType);
  if (
    normalizedCanonical.startsWith("task.") &&
    normalizeToken(sseType) === "task.completed" &&
    normalizedTaskType === "chat.completion"
  ) {
    return COMMAND_CENTER_RUN_KINDS.CHAT_COMPLETION;
  }

  return COMMAND_CENTER_RUN_KINDS.UNKNOWN;
}

function deriveRunStatus(
  state: string | null,
  terminalOutcome: CommandCenterRun["terminalOutcome"] | null,
  rawStatus: string | null,
  canonicalType: string | null
): CommandCenterRunStatus {
  if (terminalOutcome === COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED) {
    return COMMAND_CENTER_RUN_STATUSES.COMPLETED;
  }
  if (terminalOutcome === COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.FAILED) {
    return COMMAND_CENTER_RUN_STATUSES.FAILED;
  }
  if (terminalOutcome === COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.CANCELLED) {
    return COMMAND_CENTER_RUN_STATUSES.CANCELLED;
  }

  const normalizedState = normalizeToken(state);
  if (normalizedState) {
    if (/(failed|error)/.test(normalizedState)) {
      return COMMAND_CENTER_RUN_STATUSES.FAILED;
    }
    if (/(cancelled|canceled)/.test(normalizedState)) {
      return COMMAND_CENTER_RUN_STATUSES.CANCELLED;
    }
    if (
      /(blocked|waiting|approval|clarification|pending|needs attention)/.test(
        normalizedState
      )
    ) {
      return COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION;
    }
    if (
      /(completed|succeeded|success|done)/.test(normalizedState)
    ) {
      return COMMAND_CENTER_RUN_STATUSES.COMPLETED;
    }
    if (
      /(created|running|chunk|state|streaming|processing|started)/.test(
        normalizedState
      )
    ) {
      return COMMAND_CENTER_RUN_STATUSES.RUNNING;
    }
  }

  const normalizedStatus = normalizeToken(rawStatus);
  if (normalizedStatus) {
    if (/(failed|error)/.test(normalizedStatus)) {
      return COMMAND_CENTER_RUN_STATUSES.FAILED;
    }
    if (
      /(blocked|waiting|approval|clarification|pending|attention)/.test(
        normalizedStatus
      )
    ) {
      return COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION;
    }
    if (
      /(running|created|chunk|streaming|processing|started)/.test(normalizedStatus)
    ) {
      return COMMAND_CENTER_RUN_STATUSES.RUNNING;
    }
    if (/(complete|completed|succeeded|success|done)/.test(normalizedStatus)) {
      return COMMAND_CENTER_RUN_STATUSES.COMPLETED;
    }
    if (/(cancelled|canceled)/.test(normalizedStatus)) {
      return COMMAND_CENTER_RUN_STATUSES.CANCELLED;
    }
  }

  if (isCanonicalTaskEventType(canonicalType)) {
    return COMMAND_CENTER_RUN_STATUSES.RUNNING;
  }

  return COMMAND_CENTER_RUN_STATUSES.UNKNOWN;
}

function summarizeEvent(
  raw: string,
  canonicalType: string | null,
  taskType: string | null,
  state: string | null,
  terminalOutcome: CommandCenterRun["terminalOutcome"] | null,
  records: Record<string, unknown>[]
): string {
  const summary = readKey(records, [
    "summary",
    "message",
    "error",
    "reason",
    "details",
  ]);
  if (summary) return summary;

  const canonical = normalizeToken(canonicalType);
  if (taskType || (canonical && canonical.startsWith("task."))) {
    const runTypeLabel = taskType ? humanizeToken(taskType) : "task";
    const stateLabel = state ? humanizeToken(state) : null;
    if (stateLabel) {
      return `${runTypeLabel} ${stateLabel}`;
    }
    return runTypeLabel;
  }

  const rawStatus = readKey(records, ["status", "raw_status", "rawStatus"]);
  if (rawStatus) return rawStatus;

  if (state) return humanizeToken(state);

  const trimmedRaw = raw.trim();
  if (trimmedRaw && !isJsonLike(trimmedRaw)) {
    return trimmedRaw.length > 160
      ? `${trimmedRaw.slice(0, 157)}...`
      : trimmedRaw;
  }

  return canonicalType ?? "Event received";
}

function buildRunSummary(
  runType: string | null,
  state: string | null,
  terminalOutcome: CommandCenterRun["terminalOutcome"] | null,
  status: CommandCenterRunStatus
): string {
  const typeLabel =
    runType ?? (status !== "unknown" ? "task" : null) ?? "unclassified event";
  const stateLabel = state ? humanizeToken(state) : null;

  if (!stateLabel || stateLabel === typeLabel) {
    return typeLabel;
  }

  return `${typeLabel} · ${stateLabel}`;
}

function firstDefined<T>(
  items: T[],
  selector: (item: T) => unknown
): unknown | null {
  for (const item of items) {
    const value = selector(item);
    if (value != null) return value;
  }
  return null;
}

function lastDefined<T>(
  items: T[],
  selector: (item: T) => unknown
): unknown | null {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const value = selector(items[index]);
    if (value != null) return value;
  }
  return null;
}

function deriveLifecycleStates(events: CommandCenterEvent[]): string[] {
  const states: string[] = [];
  let previous: string | null = null;

  for (const event of events) {
    const state = event.lifecycleState;
    if (!state) continue;
    if (state === previous) continue;
    states.push(state);
    previous = state;
  }

  return states;
}

function deriveRunTimings(
  events: CommandCenterEvent[]
): CommandCenterRunTimings | null {
  const queuedAt = firstDefined(events, (event) => event.queuedAt) as number | null;
  const warmupAt = firstDefined(events, (event) => event.warmupAt) as number | null;
  const firstTokenAt = firstDefined(events, (event) => event.firstTokenAt) as number | null;
  const firstOutputAt = firstDefined(events, (event) => event.firstOutputAt) as number | null;
  const completedAt = lastDefined(events, (event) => event.completedAt) as number | null;
  let totalDurationMs = lastDefined(events, (event) => event.durationMs) as number | null;

  if (
    totalDurationMs == null &&
    queuedAt != null &&
    completedAt != null &&
    completedAt >= queuedAt
  ) {
    totalDurationMs = completedAt - queuedAt;
  }

  if (
    queuedAt == null &&
    warmupAt == null &&
    firstTokenAt == null &&
    firstOutputAt == null &&
    completedAt == null &&
    totalDurationMs == null
  ) {
    return null;
  }

  return {
    completedAt,
    firstOutputAt,
    firstTokenAt,
    queuedAt,
    totalDurationMs,
    warmupAt,
  };
}

function deriveRunStreamingEvidence(
  events: CommandCenterEvent[]
): CommandCenterRunStreamingEvidence | null {
  const chunkEvents = events.filter((event) => normalizeToken(event.type) === "task.chunk");
  if (chunkEvents.length === 0) return null;

  return {
    chunkCount: chunkEvents.length,
    firstChunkAt: chunkEvents[0]?.receivedAt ?? null,
    hasStreamedContent: true,
  };
}

function deriveRunTraceEvidence(
  events: CommandCenterEvent[],
  latestTurnMessageId: string | null
): CommandCenterRunTraceEvidence | null {
  const sourceMode = lastDefined(events, (event) => event.sourceMode) as string | null;
  const widenReason = lastDefined(events, (event) => event.widenReason) as string | null;
  const traceUrl = lastDefined(events, (event) => event.traceUrl) as string | null;
  const retrievalQuery = lastDefined(events, (event) => event.retrievalQuery) as string | null;
  const retrievalTarget = lastDefined(events, (event) => event.retrievalTarget) as string | null;
  const retrievalQueryMatchesLatestTurn = lastDefined(
    events,
    (event) => event.retrievalQueryMatchesLatestTurn
  ) as boolean | null;
  const latestTurnContent = lastDefined(events, (event) => event.latestTurnContent) as string | null;
  const documentCount = lastDefined(events, (event) => event.documentCount) as number | null;
  const memoryCount = lastDefined(events, (event) => event.memoryCount) as number | null;
  const graphCount = lastDefined(events, (event) => event.graphCount) as number | null;

  const hasRetrievalSummary = Boolean(
    sourceMode ||
      widenReason != null ||
      traceUrl ||
      retrievalQuery ||
      retrievalTarget ||
      retrievalQueryMatchesLatestTurn != null ||
      latestTurnContent ||
      documentCount != null ||
      memoryCount != null ||
      graphCount != null
  );
  const tracePresent = Boolean(
    widenReason != null ||
      traceUrl ||
      retrievalQuery ||
      retrievalTarget ||
      retrievalQueryMatchesLatestTurn != null ||
      latestTurnContent ||
      documentCount != null ||
      memoryCount != null ||
      graphCount != null
  );
  const latestTurnTracePresent = Boolean(
    latestTurnMessageId && tracePresent
  );
  const tracePresenceState: CommandCenterRunTraceEvidence["tracePresenceState"] =
    latestTurnTracePresent
      ? COMMAND_CENTER_TRACE_PRESENCE_STATES.LATEST_TURN_TRACE_PRESENT
      : tracePresent
        ? COMMAND_CENTER_TRACE_PRESENCE_STATES.TRACE_PRESENT
        : COMMAND_CENTER_TRACE_PRESENCE_STATES.NONE;
  const retrievalQueryPresent = Boolean(retrievalQuery);
  const latestTurnContentPresent = Boolean(latestTurnContent);

  if (!hasRetrievalSummary) {
    return null;
  }

  return {
    documentCount,
    graphCount,
    latestTurnContentPresent,
    latestTurnMessageId,
    latestTurnTracePresent,
    memoryCount,
    retrievalQuery,
    retrievalQueryMatchesLatestTurn,
    retrievalQueryPresent,
    retrievalTarget,
    sourceMode,
    tracePresenceState,
    tracePresent,
    traceUrl,
    widenReason,
  };
}

function finalizeRun(run: MutableRun): CommandCenterRun {
  const lifecycleStates = deriveLifecycleStates(run.events);
  const timings = deriveRunTimings(run.events);
  const streamingEvidence = deriveRunStreamingEvidence(run.events);
  const traceEvidence = deriveRunTraceEvidence(run.events, run.latestTurnMessageId);
  const traceUrl = traceEvidence?.traceUrl ?? null;

  return {
    eventCount: run.eventCount,
    events: run.events,
    identityKind: run.identityKind,
    key: run.key,
    lifecycleStates: lifecycleStates.length > 0 ? lifecycleStates : undefined,
    lastEvent: run.lastEvent,
    lastEventAt: run.lastEventAt,
    lastKind: run.lastKind,
    lastType: run.lastType,
    latestTurnMessageId: run.latestTurnMessageId,
    requestId: run.requestId,
    runId: run.runId,
    runKind: run.runKind,
    runType: run.runType,
    state: run.state,
    status: run.status,
    streamingEvidence,
    summary: run.summary,
    taskId: run.taskId,
    terminalOutcome: run.terminalOutcome,
    timings,
    traceEvidence,
    traceUrl,
    turnId: run.turnId,
    threadId: run.threadId,
  };
}

function normalizeEventIds(
  records: Record<string, unknown>[]
): {
  latestTurnMessageId: string | null;
  requestId: string | null;
  runId: string | null;
  taskId: string | null;
  threadId: number | null;
  turnId: string | null;
} {
  const latestTurnMessageId =
    readToken(records, [
      "latest_turn_message_id",
      "latestTurnMessageId",
      "message_id",
      "messageId",
      "id",
    ]) ?? null;

  return {
    latestTurnMessageId,
    requestId: readToken(records, ["request_id", "requestId"]),
    runId: readToken(records, ["run_id", "runId"]),
    taskId: readToken(records, ["task_id", "taskId"]),
    threadId: readThreadId(records),
    turnId: readToken(records, ["turn_id", "turnId"]),
  };
}

function getEventIdentity(
  event: CommandCenterEvent
): { identityKind: CommandCenterRunIdentityKind; key: string } {
  if (event.taskId) {
    return { identityKind: "task", key: event.taskId };
  }
  if (event.requestId) {
    return { identityKind: "request", key: event.requestId };
  }
  if (event.runId) {
    return { identityKind: "run", key: event.runId };
  }
  if (event.eventId) {
    return { identityKind: "synthetic", key: `event:${event.eventId}` };
  }
  return {
    identityKind: "synthetic",
    key: `event:${event.type ?? "unknown"}:${event.receivedAt}`,
  };
}

function resolveAlias(aliases: Map<string, string>, key: string): string {
  let current = key;
  let next = aliases.get(current);
  while (next && next !== current) {
    current = next;
    next = aliases.get(current);
  }
  return current;
}

function appendBoundedEvents(
  previous: CommandCenterEvent[],
  next: CommandCenterEvent
): CommandCenterEvent[] {
  const appended = [...previous, next];
  if (appended.length <= RUN_EVENT_LIMIT) return appended;
  return appended.slice(appended.length - RUN_EVENT_LIMIT);
}

function mergeEventLists(
  left: CommandCenterEvent[],
  right: CommandCenterEvent[]
): CommandCenterEvent[] {
  const combined = [...left, ...right];
  combined.sort((a, b) => {
    if (a.receivedAt !== b.receivedAt) {
      return a.receivedAt - b.receivedAt;
    }
    return (a.eventId ?? "").localeCompare(b.eventId ?? "");
  });
  if (combined.length <= RUN_EVENT_LIMIT) return combined;
  return combined.slice(combined.length - RUN_EVENT_LIMIT);
}

function mergeRuns(target: MutableRun, source: MutableRun): MutableRun {
  const keepTarget = target.lastEventAt >= source.lastEventAt;
  const latest = keepTarget ? target : source;
  const older = keepTarget ? source : target;

  return {
    ...latest,
    eventCount: target.eventCount + source.eventCount,
    events: mergeEventLists(target.events, source.events),
    identityKind:
      latest.identityKind === "synthetic" ? older.identityKind : latest.identityKind,
    key: latest.key,
    lastEvent: latest.lastEvent,
    lastEventAt: latest.lastEventAt,
    lastKind: latest.lastKind ?? older.lastKind,
    lastType: latest.lastType ?? older.lastType,
    latestTurnMessageId: latest.latestTurnMessageId ?? older.latestTurnMessageId,
    requestId: latest.requestId ?? older.requestId,
    runId: latest.runId ?? older.runId,
    runKind: latest.runKind ?? older.runKind,
    runType: latest.runType ?? older.runType,
    state: latest.state ?? older.state,
    status:
      latest.status !== COMMAND_CENTER_RUN_STATUSES.UNKNOWN
        ? latest.status
        : older.status,
    summary: latest.summary ?? older.summary,
    taskId: latest.taskId ?? older.taskId,
    terminalOutcome: latest.terminalOutcome ?? older.terminalOutcome,
    threadId: latest.threadId ?? older.threadId,
    turnId: latest.turnId ?? older.turnId,
  };
}

function isApprovalEvent(event: CommandCenterEvent): boolean {
  const haystack = [
    event.kind,
    event.type,
    event.sseType,
    event.state,
    event.status,
  ]
    .map((value) => normalizeToken(value))
    .filter(Boolean)
    .join(" ");

  if (!haystack) return false;

  return (
    haystack.includes("approval") ||
    haystack.includes("approval_required") ||
    haystack.includes("clarification_required") ||
    haystack.includes("blocked_waiting_for_user") ||
    haystack.includes("run.blocked") ||
    /\bblocked\b/.test(haystack)
  );
}

export function normalizeCommandCenterEvent(
  message: MessageEvent<string>
): CommandCenterEvent {
  const raw = coerceRawPayload(message.data);
  const json = parseJson(raw);
  const records = collectRecords(json);
  const rawEventType = firstString(message.type);
  const payloadEventType = readToken(records, ["event_type", "eventType"]);
  const candidateEventType =
    rawEventType && rawEventType !== "message"
      ? rawEventType
      : payloadEventType && looksLikeEventType(payloadEventType)
        ? payloadEventType
        : null;
  const canonicalType =
    normalizeCanonicalEventType(candidateEventType) ??
    firstToken(candidateEventType);
  const ids = normalizeEventIds(records);
  const taskType = readTaskType(records);
  const state = deriveTaskState(canonicalType, records);
  const terminalOutcome = deriveTerminalOutcome(canonicalType, records);
  const runKind = deriveRunKind(canonicalType, taskType, rawEventType);
  const lifecycleState = readLifecycleState(records, canonicalType);
  const queuedAt = readTimestamp(records, [
    "queued_at",
    "queuedAt",
    "created_at",
    "createdAt",
    "started_at",
    "startedAt",
  ]);
  const warmupAt = readTimestamp(records, ["warmup_at", "warmupAt"]);
  const firstTokenAt = readTimestamp(records, [
    "first_token_at",
    "firstTokenAt",
  ]);
  const firstOutputAt = readTimestamp(records, [
    "first_output_at",
    "firstOutputAt",
  ]);
  const completedAt = readTimestamp(records, [
    "completed_at",
    "completedAt",
    "finished_at",
    "finishedAt",
  ]);
  const durationMs = readNumber(records, [
    "duration_ms",
    "durationMs",
    "total_duration_ms",
    "totalDurationMs",
    "elapsed_ms",
    "elapsedMs",
  ]);
  const retrievalQuery = readKey(records, [
    "retrieval_query",
    "retrievalQuery",
  ]);
  const retrievalTarget = readKey(records, [
    "retrieval_target",
    "retrievalTarget",
  ]);
  const retrievalQueryMatchesLatestTurn = readBoolean(records, [
    "retrieval_query_matches_latest_turn",
    "retrievalQueryMatchesLatestTurn",
  ]);
  const latestTurnContent = readLatestTurnContent(records);
  const traceUrl = readTraceUrl(records);
  const sourceMode = readSourceMode(records);
  const widenReason = readWidenReason(records);
  const documentCount = readCollectionCount(records, {
    countKeys: [
      "semantic_count",
      "document_count",
      "documents_count",
      "linked_document_count",
    ],
    nestedKeys: ["payload_summary"],
    nestedCountKeys: [
      "semantic_count",
      "document_count",
      "documents_count",
      "linked_document_count",
    ],
    arrayKeys: ["documents"],
  });
  const memoryCount = readCollectionCount(records, {
    countKeys: ["memory_count"],
    nestedKeys: ["payload_summary", "memory_context"],
    nestedCountKeys: ["memory_count", "count"],
    arrayKeys: ["memory"],
  });
  const graphCount = readCollectionCount(records, {
    countKeys: ["graph_count"],
    nestedKeys: ["payload_summary", "graph_context"],
    nestedCountKeys: ["graph_count", "count"],
    arrayKeys: ["graph"],
  });
  const summary = summarizeEvent(
    raw,
    canonicalType,
    taskType,
    state,
    terminalOutcome,
    records
  );

  return {
    eventId: firstString(message.lastEventId),
    json,
    kind: readToken(records, ["kind"]),
    completedAt,
    durationMs,
    firstOutputAt,
    firstTokenAt,
    latestTurnMessageId: ids.latestTurnMessageId,
    latestTurnContent,
    sourceMode,
    widenReason,
    documentCount,
    memoryCount,
    graphCount,
    lifecycleState,
    raw,
    receivedAt: Date.now(),
    queuedAt,
    requestId: ids.requestId,
    runId: ids.runId,
    runKind,
    retrievalQuery,
    retrievalQueryMatchesLatestTurn,
    retrievalTarget,
    sseType: rawEventType ?? payloadEventType ?? "message",
    state,
    status: readToken(records, ["status", "raw_status", "rawStatus"]),
    summary,
    taskId: ids.taskId,
    taskType,
    terminalOutcome,
    threadId: ids.threadId,
    turnId: ids.turnId,
    traceUrl,
    warmupAt,
    type: canonicalType,
  };
}

export function aggregateCommandCenterEvents(
  events: CommandCenterEvent[]
): AggregationResult {
  const aliases = new Map<string, string>();
  const runs = new Map<string, MutableRun>();
  const approvals: CommandCenterApproval[] = [];

  const ensureRun = (
    key: string,
    identityKind: CommandCenterRunIdentityKind,
    event: CommandCenterEvent
  ): MutableRun => {
    const existing = runs.get(key);
    if (existing) {
      return existing;
    }

    const created: MutableRun = {
      eventCount: 0,
      events: [],
      identityKind,
      key,
      lastEvent: event,
      lastEventAt: event.receivedAt,
      lastKind: event.kind,
      lastType: event.type,
      latestTurnMessageId: event.latestTurnMessageId,
      requestId: event.requestId,
      runId: event.runId,
      runKind: null,
      runType: null,
      state: event.state,
      status: COMMAND_CENTER_RUN_STATUSES.UNKNOWN,
      summary: event.summary,
      taskId: event.taskId,
      terminalOutcome: event.terminalOutcome,
      threadId: event.threadId,
      turnId: event.turnId,
    };
    runs.set(key, created);
    return created;
  };

  const collapse = (primary: string, secondary: string): string => {
    const resolvedPrimary = resolveAlias(aliases, primary);
    const resolvedSecondary = resolveAlias(aliases, secondary);
    if (resolvedPrimary === resolvedSecondary) return resolvedPrimary;

    const primaryRun = runs.get(resolvedPrimary);
    const secondaryRun = runs.get(resolvedSecondary);
    if (secondaryRun) {
      if (primaryRun) {
        runs.set(resolvedPrimary, mergeRuns(primaryRun, secondaryRun));
      } else {
        runs.set(resolvedPrimary, { ...secondaryRun, key: resolvedPrimary });
      }
      runs.delete(resolvedSecondary);
    }

    aliases.set(resolvedSecondary, resolvedPrimary);
    return resolvedPrimary;
  };

  const registerAliases = (
    primaryKey: string,
    identityKind: CommandCenterRunIdentityKind,
    event: CommandCenterEvent
  ): string => {
    const aliasesToRegister = [event.taskId, event.requestId, event.runId]
      .filter((value): value is string => Boolean(value))
      .filter((value) => value !== primaryKey);

    let nextKey = primaryKey;
    for (const aliasKey of aliasesToRegister) {
      nextKey = collapse(nextKey, aliasKey);
    }

    aliases.set(primaryKey, nextKey);
    if (identityKind === "task" && event.requestId) {
      aliases.set(event.requestId, nextKey);
    }
    if (identityKind === "task" && event.runId) {
      aliases.set(event.runId, nextKey);
    }
    if (identityKind === "request" && event.runId) {
      aliases.set(event.runId, nextKey);
    }
    return resolveAlias(aliases, nextKey);
  };

  events.forEach((event, index) => {
    const { identityKind, key: rawKey } = getEventIdentity(event);
    const resolvedKey = resolveAlias(aliases, rawKey) || rawKey;
    const key = resolvedKey || `event:${index}:${event.receivedAt}`;
    const run = ensureRun(key, identityKind, event);
    const runType = deriveRunType(event.type, event.taskType, event.sseType);
    const runKind = deriveRunKind(event.type, event.taskType, event.sseType);
    const nextRunType = runType ?? run.runType;
    const nextRunKind =
      runKind !== COMMAND_CENTER_RUN_KINDS.UNKNOWN ? runKind : run.runKind;
    const nextState = event.state ?? run.state;
    const nextOutcome = event.terminalOutcome ?? run.terminalOutcome;
    const summaryStatus = deriveRunStatus(
      nextState,
      nextOutcome,
      event.status,
      event.type
    );
    const summary = buildRunSummary(
      nextRunType,
      nextState,
      nextOutcome,
      summaryStatus
    );

    run.eventCount += 1;
    run.events = appendBoundedEvents(run.events, event);
    run.lastEvent = event;
    run.lastEventAt = event.receivedAt;
    run.lastKind = event.kind;
    run.lastType = event.type;
    run.latestTurnMessageId = event.latestTurnMessageId ?? run.latestTurnMessageId;
    run.requestId = event.requestId ?? run.requestId;
    run.runId = event.runId ?? run.runId;
    run.runKind = nextRunKind;
    run.runType = nextRunType;
    run.state = nextState;
    run.status =
      summaryStatus !== COMMAND_CENTER_RUN_STATUSES.UNKNOWN ||
      run.status === COMMAND_CENTER_RUN_STATUSES.UNKNOWN
        ? summaryStatus
        : run.status;
    run.summary = summary;
    run.taskId = event.taskId ?? run.taskId;
    run.terminalOutcome = nextOutcome;
    run.threadId = event.threadId ?? run.threadId;
    run.turnId = event.turnId ?? run.turnId;
    runs.set(key, run);

    const collapsedKey = registerAliases(key, identityKind, event);
    if (collapsedKey !== key) {
      const collapsedRun = runs.get(collapsedKey);
      if (collapsedRun) {
        runs.set(collapsedKey, mergeRuns(collapsedRun, run));
      } else {
        runs.set(collapsedKey, { ...run, key: collapsedKey });
      }
      runs.delete(key);
    }

    if (isApprovalEvent(event)) {
      approvals.push({
        event,
        key: `${key}:${index}:${event.receivedAt}`,
        label: humanizeToken(event.kind ?? event.type ?? event.sseType ?? event.status),
        receivedAt: event.receivedAt,
        runId: event.runId,
        runKey: key,
        status: event.status,
        summary: event.summary,
        taskId: event.taskId,
      });
    }
  });

  const finalizedRuns = Array.from(runs.values())
    .map((run) => finalizeRun(run))
    .sort((left, right) => right.lastEventAt - left.lastEventAt);

  return {
    approvals: approvals.sort((left, right) => right.receivedAt - left.receivedAt),
    runs: finalizedRuns,
  };
}

export function deriveCommandCenterRunIdentity(
  event: CommandCenterEvent
): { identityKind: CommandCenterRunIdentityKind; key: string } {
  return getEventIdentity(event);
}
