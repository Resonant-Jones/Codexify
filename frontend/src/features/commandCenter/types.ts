export type CommandCenterConnectionState =
  | "connecting"
  | "open"
  | "error"
  | "closed";

export type CommandCenterStatusTone =
  | "active"
  | "attention"
  | "danger"
  | "info"
  | "neutral"
  | "subtle";

export interface CommandCenterStatusPresentation {
  isFallback: boolean;
  label: string;
  tone: CommandCenterStatusTone;
}

export const COMMAND_CENTER_HEALTH_STATES = {
  OK: "ok",
  DEGRADED: "degraded",
  DOWN: "down",
  UNKNOWN: "unknown",
} as const;

export type CommandCenterHealthState =
  (typeof COMMAND_CENTER_HEALTH_STATES)[keyof typeof COMMAND_CENTER_HEALTH_STATES];

export const COMMAND_CENTER_HEALTH_STATE_PRESENTATIONS = {
  [COMMAND_CENTER_HEALTH_STATES.OK]: {
    isFallback: false,
    label: "OK",
    tone: "active",
  },
  [COMMAND_CENTER_HEALTH_STATES.DEGRADED]: {
    isFallback: false,
    label: "Degraded",
    tone: "attention",
  },
  [COMMAND_CENTER_HEALTH_STATES.DOWN]: {
    isFallback: false,
    label: "Down",
    tone: "danger",
  },
  [COMMAND_CENTER_HEALTH_STATES.UNKNOWN]: {
    isFallback: false,
    label: "Unknown",
    tone: "subtle",
  },
} as const satisfies Record<CommandCenterHealthState, CommandCenterStatusPresentation>;

export const COMMAND_CENTER_RUN_STATUSES = {
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
  NEEDS_ATTENTION: "needs_attention",
  UNKNOWN: "unknown",
} as const;

export type CommandCenterRunStatus =
  (typeof COMMAND_CENTER_RUN_STATUSES)[keyof typeof COMMAND_CENTER_RUN_STATUSES];

export const COMMAND_CENTER_RUN_STATUS_PRESENTATIONS = {
  [COMMAND_CENTER_RUN_STATUSES.RUNNING]: {
    isFallback: false,
    label: "Running",
    tone: "info",
  },
  [COMMAND_CENTER_RUN_STATUSES.COMPLETED]: {
    isFallback: false,
    label: "Completed",
    tone: "active",
  },
  [COMMAND_CENTER_RUN_STATUSES.FAILED]: {
    isFallback: false,
    label: "Failed",
    tone: "danger",
  },
  [COMMAND_CENTER_RUN_STATUSES.CANCELLED]: {
    isFallback: false,
    label: "Cancelled",
    tone: "attention",
  },
  [COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION]: {
    isFallback: false,
    label: "Needs attention",
    tone: "attention",
  },
  [COMMAND_CENTER_RUN_STATUSES.UNKNOWN]: {
    isFallback: false,
    label: "Unknown",
    tone: "subtle",
  },
} as const satisfies Record<CommandCenterRunStatus, CommandCenterStatusPresentation>;

export const COMMAND_CENTER_RUN_TERMINAL_OUTCOMES = {
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const;

export type CommandCenterRunTerminalOutcome =
  (typeof COMMAND_CENTER_RUN_TERMINAL_OUTCOMES)[keyof typeof COMMAND_CENTER_RUN_TERMINAL_OUTCOMES];

export const COMMAND_CENTER_RUN_TERMINAL_OUTCOME_PRESENTATIONS = {
  [COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED]: {
    isFallback: false,
    label: "Completed",
    tone: "active",
  },
  [COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.FAILED]: {
    isFallback: false,
    label: "Failed",
    tone: "danger",
  },
  [COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.CANCELLED]: {
    isFallback: false,
    label: "Cancelled",
    tone: "attention",
  },
} as const satisfies Record<CommandCenterRunTerminalOutcome, CommandCenterStatusPresentation>;

export const COMMAND_CENTER_TRACE_PRESENCE_STATES = {
  NONE: "none",
  TRACE_PRESENT: "trace_present",
  LATEST_TURN_TRACE_PRESENT: "latest_turn_trace_present",
} as const;

export type CommandCenterRunTracePresenceState =
  (typeof COMMAND_CENTER_TRACE_PRESENCE_STATES)[keyof typeof COMMAND_CENTER_TRACE_PRESENCE_STATES];

export const COMMAND_CENTER_TRACE_PRESENCE_PRESENTATIONS = {
  [COMMAND_CENTER_TRACE_PRESENCE_STATES.NONE]: {
    isFallback: false,
    label: "No trace",
    tone: "subtle",
  },
  [COMMAND_CENTER_TRACE_PRESENCE_STATES.TRACE_PRESENT]: {
    isFallback: false,
    label: "Trace present",
    tone: "info",
  },
  [COMMAND_CENTER_TRACE_PRESENCE_STATES.LATEST_TURN_TRACE_PRESENT]: {
    isFallback: false,
    label: "Latest turn trace present",
    tone: "active",
  },
} as const satisfies Record<CommandCenterRunTracePresenceState, CommandCenterStatusPresentation>;

export const COMMAND_CENTER_RUN_KINDS = {
  CHAT_COMPLETION: "chat_completion",
  UNKNOWN: "unknown",
} as const;

export type CommandCenterRunKind =
  (typeof COMMAND_CENTER_RUN_KINDS)[keyof typeof COMMAND_CENTER_RUN_KINDS];

export type CommandCenterRunIdentityKind =
  | "task"
  | "request"
  | "run"
  | "synthetic";

export type CommandCenterRunLifecycleState =
  | "created"
  | "running"
  | "state"
  | "chunk"
  | "completed"
  | "failed"
  | "cancelled"
  | "unknown";

export type CommandCenterHealthStatus =
  | "OK"
  | "DEGRADED"
  | "DOWN"
  | "UNKNOWN";

export type CommandCenterRunLifecyclePath = string[];

export type CommandCenterCanonicalTaskEventType =
  | "task.created"
  | "task.running"
  | "task.state"
  | "task.chunk"
  | "task.completed"
  | "task.failed"
  | "task.cancelled";

export type CommandCenterJson = Record<string, unknown> | null;
export type CommandCenterRagTraceUnavailableReason =
  | "no_run"
  | "no_thread"
  | "no_trace";

export interface CommandCenterRunTimings {
  completedAt: number | null;
  firstOutputAt: number | null;
  firstTokenAt: number | null;
  queuedAt: number | null;
  totalDurationMs: number | null;
  warmupAt: number | null;
}

export interface CommandCenterRunStreamingEvidence {
  chunkCount: number;
  firstChunkAt: number | null;
  hasStreamedContent: boolean;
}

export interface CommandCenterRunTraceEvidence {
  documentCount: number | null;
  graphCount: number | null;
  latestTurnContentPresent: boolean;
  latestTurnMessageId: string | null;
  latestTurnTracePresent: boolean;
  memoryCount: number | null;
  retrievalQuery: string | null;
  retrievalQueryMatchesLatestTurn: boolean | null;
  retrievalQueryPresent: boolean;
  retrievalTarget: string | null;
  sourceMode: string | null;
  tracePresenceState: CommandCenterRunTracePresenceState;
  tracePresent: boolean;
  traceUrl: string | null;
  widenReason: string | null;
}

export interface CommandCenterEvent {
  eventId: string | null;
  completedAt?: number | null;
  durationMs?: number | null;
  firstOutputAt?: number | null;
  firstTokenAt?: number | null;
  graphCount?: number | null;
  json: CommandCenterJson;
  kind: string | null;
  lifecycleState?: string | null;
  latestTurnContent?: string | null;
  memoryCount?: number | null;
  raw: string;
  receivedAt: number;
  queuedAt?: number | null;
  requestId: string | null;
  runId: string | null;
  runKind?: CommandCenterRunKind | null;
  sourceMode?: string | null;
  taskType: string | null;
  sseType: string | null;
  status: string | null;
  retrievalQuery?: string | null;
  retrievalQueryMatchesLatestTurn?: boolean | null;
  retrievalTarget?: string | null;
  documentCount?: number | null;
  widenReason?: string | null;
  summary: string;
  taskId: string | null;
  latestTurnMessageId: string | null;
  state: string | null;
  terminalOutcome: CommandCenterRunTerminalOutcome | null;
  threadId: number | null;
  turnId: string | null;
  traceUrl?: string | null;
  warmupAt?: number | null;
  type: string | null;
}

export interface CommandCenterRun {
  eventCount: number;
  events?: CommandCenterEvent[];
  identityKind?: CommandCenterRunIdentityKind;
  key: string;
  lifecycleStates?: CommandCenterRunLifecyclePath;
  lastEvent: CommandCenterEvent;
  lastEventAt: number;
  lastKind: string | null;
  lastType: string | null;
  latestTurnMessageId?: string | null;
  requestId?: string | null;
  runId: string | null;
  runKind?: CommandCenterRunKind | null;
  runType?: string | null;
  state?: CommandCenterRunLifecycleState | string | null;
  status: CommandCenterRunStatus;
  streamingEvidence?: CommandCenterRunStreamingEvidence | null;
  summary: string;
  taskId: string | null;
  terminalOutcome?: CommandCenterRunTerminalOutcome | null;
  timings?: CommandCenterRunTimings | null;
  turnId?: string | null;
  threadId?: number | null;
  traceEvidence?: CommandCenterRunTraceEvidence | null;
  traceUrl?: string | null;
}

export interface CommandCenterApproval {
  event: CommandCenterEvent;
  key: string;
  label: string;
  receivedAt: number;
  runId: string | null;
  runKey: string | null;
  status: string | null;
  summary: string;
  taskId: string | null;
}

export interface CommandCenterHealthItem {
  checkedAt: number | null;
  endpoint: string;
  error: string | null;
  httpStatus: number | null;
  key: "core" | "llm" | "deps" | "vector" | "memory";
  label: string;
  details?: Record<string, unknown> | null;
  raw: string | null;
  status: CommandCenterHealthState;
}

export interface CommandCenterTaskEvent {
  eventId: string | null;
  eventType: string | null;
  json: CommandCenterJson;
  raw: string;
  receivedAt: number;
  summary: string;
}

export interface CommandCenterRagTraceItem {
  depthUsed: string | null;
  id: string;
  origin: string | null;
  raw: Record<string, unknown> | null;
  score: number | null;
  silo: string | null;
  source: string | null;
  text: string;
  threadId: string | null;
  timestamp: string | null;
}

export interface CommandCenterRagTracePayload {
  memory: CommandCenterRagTraceItem[];
  resolvedThreadId: number;
  semantic: CommandCenterRagTraceItem[];
}

function normalizeCommandCenterToken(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[.\s-]+/g, "_")
    .replace(/_+/g, "_");
}

function humanizeCommandCenterToken(value: string | null | undefined): string {
  const normalized = String(value ?? "")
    .trim()
    .replace(/[._-]+/g, " ")
    .replace(/\s+/g, " ");
  if (!normalized) return "unknown";
  if (normalized.toLowerCase() === "ok") return "OK";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function fallbackPresentation(value: string | null | undefined): CommandCenterStatusPresentation {
  const label = humanizeCommandCenterToken(value);
  return {
    isFallback: true,
    label,
    tone: "subtle",
  };
}

export function describeCommandCenterHealthStatePresentation(
  state: string | null | undefined
): CommandCenterStatusPresentation {
  const normalized = normalizeCommandCenterToken(state);
  switch (normalized) {
    case COMMAND_CENTER_HEALTH_STATES.OK:
    case "healthy":
    case "online":
      return COMMAND_CENTER_HEALTH_STATE_PRESENTATIONS[COMMAND_CENTER_HEALTH_STATES.OK];
    case COMMAND_CENTER_HEALTH_STATES.DEGRADED:
    case "warning":
    case "warn":
      return COMMAND_CENTER_HEALTH_STATE_PRESENTATIONS[COMMAND_CENTER_HEALTH_STATES.DEGRADED];
    case COMMAND_CENTER_HEALTH_STATES.DOWN:
    case "fail":
    case "failed":
    case "error":
    case "offline":
    case "misconfigured":
      return COMMAND_CENTER_HEALTH_STATE_PRESENTATIONS[COMMAND_CENTER_HEALTH_STATES.DOWN];
    case COMMAND_CENTER_HEALTH_STATES.UNKNOWN:
    case "":
      return COMMAND_CENTER_HEALTH_STATE_PRESENTATIONS[COMMAND_CENTER_HEALTH_STATES.UNKNOWN];
    default:
      return fallbackPresentation(state);
  }
}

export function normalizeCommandCenterRunStatus(
  status: string | null | undefined
): CommandCenterRunStatus {
  const normalized = normalizeCommandCenterToken(status);
  switch (normalized) {
    case COMMAND_CENTER_RUN_STATUSES.RUNNING:
    case "created":
    case "chunk":
    case "streaming":
    case "processing":
    case "started":
      return COMMAND_CENTER_RUN_STATUSES.RUNNING;
    case COMMAND_CENTER_RUN_STATUSES.COMPLETED:
    case "succeeded":
    case "success":
    case "done":
      return COMMAND_CENTER_RUN_STATUSES.COMPLETED;
    case COMMAND_CENTER_RUN_STATUSES.FAILED:
    case "error":
    case "failure":
      return COMMAND_CENTER_RUN_STATUSES.FAILED;
    case COMMAND_CENTER_RUN_STATUSES.CANCELLED:
    case "canceled":
      return COMMAND_CENTER_RUN_STATUSES.CANCELLED;
    case COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION:
    case "attention":
    case "blocked":
    case "waiting":
    case "approval":
    case "clarification":
    case "pending":
      return COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION;
    case COMMAND_CENTER_RUN_STATUSES.UNKNOWN:
    default:
      return COMMAND_CENTER_RUN_STATUSES.UNKNOWN;
  }
}

export function describeCommandCenterRunStatusPresentation(
  status: string | null | undefined
): CommandCenterStatusPresentation {
  const normalized = normalizeCommandCenterRunStatus(status);
  return COMMAND_CENTER_RUN_STATUS_PRESENTATIONS[normalized];
}

export function normalizeCommandCenterTerminalOutcome(
  outcome: string | null | undefined
): CommandCenterRunTerminalOutcome | null {
  const normalized = normalizeCommandCenterToken(outcome);
  switch (normalized) {
    case COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED:
    case "succeeded":
    case "success":
    case "done":
      return COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED;
    case COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.FAILED:
      return COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.FAILED;
    case COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.CANCELLED:
    case "canceled":
      return COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.CANCELLED;
    default:
      return null;
  }
}

export function describeCommandCenterRunTerminalOutcomePresentation(
  outcome: string | null | undefined
): CommandCenterStatusPresentation | null {
  const normalized = normalizeCommandCenterTerminalOutcome(outcome);
  if (!normalized) return null;
  return COMMAND_CENTER_RUN_TERMINAL_OUTCOME_PRESENTATIONS[normalized];
}

export function normalizeCommandCenterTracePresenceState(
  state: string | null | undefined
): CommandCenterRunTracePresenceState {
  const normalized = normalizeCommandCenterToken(state);
  switch (normalized) {
    case COMMAND_CENTER_TRACE_PRESENCE_STATES.NONE:
    case "no_trace":
      return COMMAND_CENTER_TRACE_PRESENCE_STATES.NONE;
    case COMMAND_CENTER_TRACE_PRESENCE_STATES.TRACE_PRESENT:
    case "tracepresent":
    case "trace":
      return COMMAND_CENTER_TRACE_PRESENCE_STATES.TRACE_PRESENT;
    case COMMAND_CENTER_TRACE_PRESENCE_STATES.LATEST_TURN_TRACE_PRESENT:
    case "latestturntracepresent":
    case "latest_turn_trace":
      return COMMAND_CENTER_TRACE_PRESENCE_STATES.LATEST_TURN_TRACE_PRESENT;
    case "":
    default:
      return COMMAND_CENTER_TRACE_PRESENCE_STATES.NONE;
  }
}

export function describeCommandCenterTracePresencePresentation(
  state: string | null | undefined
): CommandCenterStatusPresentation {
  const normalized = normalizeCommandCenterTracePresenceState(state);
  return COMMAND_CENTER_TRACE_PRESENCE_PRESENTATIONS[normalized];
}

export function normalizeCommandCenterRunKind(
  kind: string | null | undefined
): CommandCenterRunKind {
  const normalized = normalizeCommandCenterToken(kind);
  if (
    normalized === COMMAND_CENTER_RUN_KINDS.CHAT_COMPLETION ||
    normalized === "chatcompletion" ||
    normalized === "chat_completion" ||
    normalized === "chat.completion" ||
    normalized === "chat" ||
    normalized === "completion"
  ) {
    return COMMAND_CENTER_RUN_KINDS.CHAT_COMPLETION;
  }
  return COMMAND_CENTER_RUN_KINDS.UNKNOWN;
}

export function describeCommandCenterRunKindLabel(
  kind: string | null | undefined
): string | null {
  const normalized = normalizeCommandCenterRunKind(kind);
  if (normalized === COMMAND_CENTER_RUN_KINDS.CHAT_COMPLETION) {
    return "chat completion";
  }
  return null;
}
