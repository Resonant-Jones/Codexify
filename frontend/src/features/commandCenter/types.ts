export type CommandCenterConnectionState =
  | "connecting"
  | "open"
  | "error"
  | "closed";

export type CommandCenterRunStatus =
  | "running"
  | "succeeded"
  | "failed"
  | "needs_attention"
  | "unknown";

export type CommandCenterHealthStatus = "OK" | "FAIL" | "UNKNOWN";
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

export type CommandCenterRunLifecyclePath = string[];

export type CommandCenterRunTerminalOutcome =
  | "succeeded"
  | "failed"
  | "cancelled";

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
  latestTurnContentPresent: boolean;
  latestTurnTracePresent: boolean;
  retrievalQuery: string | null;
  retrievalQueryMatchesLatestTurn: boolean | null;
  retrievalQueryPresent: boolean;
  retrievalTarget: string | null;
  tracePresent: boolean;
  traceUrl: string | null;
}

export interface CommandCenterEvent {
  eventId: string | null;
  completedAt?: number | null;
  durationMs?: number | null;
  firstOutputAt?: number | null;
  firstTokenAt?: number | null;
  json: CommandCenterJson;
  kind: string | null;
  lifecycleState?: string | null;
  latestTurnContent?: string | null;
  raw: string;
  receivedAt: number;
  queuedAt?: number | null;
  requestId: string | null;
  runId: string | null;
  taskType: string | null;
  sseType: string | null;
  status: string | null;
  retrievalQuery?: string | null;
  retrievalQueryMatchesLatestTurn?: boolean | null;
  retrievalTarget?: string | null;
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
  raw: string | null;
  status: CommandCenterHealthStatus;
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
