import type {
  CommandCenterApproval,
  CommandCenterCanonicalTaskEventType,
  CommandCenterEvent,
  CommandCenterRun,
  CommandCenterRunIdentityKind,
  CommandCenterRunStatus,
  CommandCenterRunTerminalOutcome,
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

function pushRecord(
  records: Record<string, unknown>[],
  value: unknown
): void {
  const record = asRecord(value);
  if (!record) return;
  if (!records.includes(record)) {
    records.push(record);
  }
}

function collectRecords(json: Record<string, unknown> | null): Record<string, unknown>[] {
  const records: Record<string, unknown>[] = [];
  if (!json) return records;

  pushRecord(records, json);
  pushRecord(records, json.data);
  pushRecord(records, json.run);
  pushRecord(records, json.payload);
  pushRecord(records, json.task);
  pushRecord(records, json.event);
  pushRecord(records, json.thread);
  pushRecord(records, json.context);

  for (const record of [...records]) {
    pushRecord(records, record.data);
    pushRecord(records, record.run);
    pushRecord(records, record.payload);
    pushRecord(records, record.task);
    pushRecord(records, record.event);
    pushRecord(records, record.thread);
    pushRecord(records, record.context);
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
  const explicitOutcome = normalizeToken(
    readToken(records, ["terminal_outcome", "terminalOutcome", "outcome"])
  );
  switch (explicitOutcome) {
    case "succeeded":
    case "failed":
    case "cancelled":
      return explicitOutcome;
    default:
      break;
  }

  switch (normalizeToken(canonicalType)) {
    case "task.completed":
      return "succeeded";
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

function deriveRunStatus(
  state: string | null,
  terminalOutcome: CommandCenterRun["terminalOutcome"] | null,
  rawStatus: string | null,
  canonicalType: string | null
): CommandCenterRunStatus {
  if (terminalOutcome === "succeeded") return "succeeded";
  if (terminalOutcome === "failed") return "failed";
  if (terminalOutcome === "cancelled") return "needs_attention";

  const normalizedState = normalizeToken(state);
  if (normalizedState) {
    if (/(failed|error)/.test(normalizedState)) return "failed";
    if (/(cancelled|canceled)/.test(normalizedState)) return "needs_attention";
    if (
      /(blocked|waiting|approval|clarification|pending|needs attention)/.test(
        normalizedState
      )
    ) {
      return "needs_attention";
    }
    if (
      /(completed|succeeded|success|done)/.test(normalizedState)
    ) {
      return "succeeded";
    }
    if (
      /(created|running|chunk|state|streaming|processing|started)/.test(
        normalizedState
      )
    ) {
      return "running";
    }
  }

  const normalizedStatus = normalizeToken(rawStatus);
  if (normalizedStatus) {
    if (/(failed|error)/.test(normalizedStatus)) return "failed";
    if (
      /(blocked|waiting|approval|clarification|pending|attention)/.test(
        normalizedStatus
      )
    ) {
      return "needs_attention";
    }
    if (/(running|created|chunk|streaming|processing|started)/.test(normalizedStatus)) {
      return "running";
    }
    if (/(complete|completed|succeeded|success|done)/.test(normalizedStatus)) {
      return "succeeded";
    }
  }

  if (isCanonicalTaskEventType(canonicalType)) {
    return "running";
  }

  return "unknown";
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
    if (stateLabel && terminalOutcome === "succeeded") {
      return `${runTypeLabel} ${stateLabel}`;
    }
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

  if (terminalOutcome === "succeeded") {
    return `${typeLabel} · ${stateLabel}`;
  }

  return `${typeLabel} · ${stateLabel}`;
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
    runType: latest.runType ?? older.runType,
    state: latest.state ?? older.state,
    status:
      latest.status !== "unknown"
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
  const taskType = readToken(records, ["type", "task_type", "taskType"]);
  const state = deriveTaskState(canonicalType, records);
  const terminalOutcome = deriveTerminalOutcome(canonicalType, records);
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
    latestTurnMessageId: ids.latestTurnMessageId,
    raw,
    receivedAt: Date.now(),
    requestId: ids.requestId,
    runId: ids.runId,
    sseType: rawEventType ?? payloadEventType ?? "message",
    state,
    status: readToken(records, ["status", "raw_status", "rawStatus"]),
    summary,
    taskId: ids.taskId,
    taskType,
    terminalOutcome,
    threadId: ids.threadId,
    turnId: ids.turnId,
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
      runType: null,
      state: event.state,
      status: "unknown",
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
    const nextRunType = runType ?? run.runType;
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
    run.runType = nextRunType;
    run.state = nextState;
    run.status =
      summaryStatus !== "unknown" || run.status === "unknown"
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

  return {
    approvals: approvals.sort((left, right) => right.receivedAt - left.receivedAt),
    runs: Array.from(runs.values()).sort(
      (left, right) => right.lastEventAt - left.lastEventAt
    ),
  };
}

export function deriveCommandCenterRunIdentity(
  event: CommandCenterEvent
): { identityKind: CommandCenterRunIdentityKind; key: string } {
  return getEventIdentity(event);
}
