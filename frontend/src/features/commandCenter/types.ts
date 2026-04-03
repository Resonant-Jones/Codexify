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

export type CommandCenterHealthStatus =
  | "OK"
  | "DEGRADED"
  | "DOWN"
  | "UNKNOWN";

export type CommandCenterJson = Record<string, unknown> | null;
export type CommandCenterRagTraceUnavailableReason =
  | "no_run"
  | "no_thread"
  | "no_trace";

export interface CommandCenterEvent {
  eventId: string | null;
  json: CommandCenterJson;
  kind: string | null;
  raw: string;
  receivedAt: number;
  runId: string | null;
  sseType: string | null;
  status: string | null;
  summary: string;
  taskId: string | null;
  type: string | null;
}

export interface CommandCenterRun {
  eventCount: number;
  key: string;
  lastEvent: CommandCenterEvent;
  lastEventAt: number;
  lastKind: string | null;
  lastType: string | null;
  runId: string | null;
  status: CommandCenterRunStatus;
  summary: string;
  taskId: string | null;
  threadId?: number | null;
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
