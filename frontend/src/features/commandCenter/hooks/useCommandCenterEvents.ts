import * as React from "react";

import {
  checkAuthGate,
  markAuthUnauthenticatedFrom401,
  useAuthState,
} from "@/lib/authState";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { GuardianEventSource } from "@/lib/guardianEventSource";
import {
  getRuntimeConfigSync,
  resolveSseEndpoint,
} from "@/lib/runtimeConfig";

import type {
  CommandCenterApproval,
  CommandCenterConnectionState,
  CommandCenterEvent,
  CommandCenterRun,
  CommandCenterRunStatus,
} from "@/features/commandCenter/types";

const EVENT_BUFFER_LIMIT = 500;
const UUIDISH_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type UseCommandCenterEventsOptions = {
  enabled: boolean;
};

type UseCommandCenterEventsResult = {
  approvals: CommandCenterApproval[];
  connectionDetail: string | null;
  connectionState: CommandCenterConnectionState;
  events: CommandCenterEvent[];
  lastEventAt: number | null;
  runs: CommandCenterRun[];
  unauthorized: boolean;
};

type DerivationResult = {
  approvals: CommandCenterApproval[];
  runs: CommandCenterRun[];
};

type MutableRun = {
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

function looksLikeTaskIdentifier(value: string | null): boolean {
  if (!value) return false;
  const trimmed = value.trim();
  if (!trimmed) return false;
  return /^task[_:-]/i.test(trimmed) || UUIDISH_RE.test(trimmed);
}

function normalizeToken(value: string | null): string {
  return String(value ?? "")
    .trim()
    .toLowerCase();
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
    return asRecord(JSON.parse(trimmed));
  } catch {
    return null;
  }
}

function collectRecords(json: Record<string, unknown> | null): Array<Record<string, unknown>> {
  if (!json) return [];
  const nestedData = asRecord(json.data);
  const nestedRun = asRecord(json.run);
  const nestedDataRun = nestedData ? asRecord(nestedData.run) : null;
  return [json, nestedData, nestedRun, nestedDataRun].filter(
    (value): value is Record<string, unknown> => Boolean(value)
  );
}

function readKey(records: Array<Record<string, unknown>>, keys: string[]): string | null {
  for (const record of records) {
    for (const key of keys) {
      const value = firstString(record[key]);
      if (value) return value;
    }
  }
  return null;
}

function summarizeEvent(
  raw: string,
  json: Record<string, unknown> | null,
  sseType: string | null
): string {
  const records = collectRecords(json);
  const summary = readKey(records, [
    "summary",
    "message",
    "error",
    "reason",
    "status",
  ]);
  if (summary) return summary;
  const trimmedRaw = raw.trim();
  if (trimmedRaw) {
    return trimmedRaw.length > 160
      ? `${trimmedRaw.slice(0, 157)}...`
      : trimmedRaw;
  }
  return sseType ?? "Event received";
}

function normalizeEvent(message: MessageEvent<string>): CommandCenterEvent {
  const raw = coerceRawPayload(message.data);
  const json = parseJson(raw);
  const records = collectRecords(json);
  const fallbackTaskId = readKey(records, ["id"]);
  const sseType = firstString(message.type) ?? "message";

  return {
    eventId: firstString(message.lastEventId),
    json,
    kind: readKey(records, ["kind", "event_type", "eventType"]),
    raw,
    receivedAt: Date.now(),
    runId: readKey(records, ["run_id", "runId"]),
    sseType,
    status: readKey(records, ["status", "raw_status", "rawStatus"]),
    summary: summarizeEvent(raw, json, sseType),
    taskId:
      readKey(records, ["task_id", "taskId", "task"]) ||
      (looksLikeTaskIdentifier(fallbackTaskId) ? fallbackTaskId : null),
    type: readKey(records, ["type"]),
  };
}

function deriveRunStatus(event: CommandCenterEvent): CommandCenterRunStatus {
  const signal = normalizeToken(event.kind ?? event.type ?? event.sseType);
  if (!signal) return "unknown";
  if (/(fail|error)/.test(signal)) return "failed";
  if (/(complete|done|success|succeeded)/.test(signal)) return "succeeded";
  if (/(start|running|progress)/.test(signal)) return "running";
  if (/(approval|blocked|clarification)/.test(signal)) return "needs_attention";
  return "unknown";
}

function isApprovalEvent(event: CommandCenterEvent): boolean {
  const haystack = [
    event.kind,
    event.type,
    event.sseType,
    event.status,
  ]
    .map(normalizeToken)
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

function humanizeLabel(value: string | null): string {
  const normalized = firstString(value) ?? "needs_attention";
  return normalized
    .replace(/[._]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function appendBoundedEvent(
  previous: CommandCenterEvent[],
  next: CommandCenterEvent
): CommandCenterEvent[] {
  const appended = [...previous, next];
  if (appended.length <= EVENT_BUFFER_LIMIT) return appended;
  return appended.slice(appended.length - EVENT_BUFFER_LIMIT);
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

function mergeRuns(target: MutableRun, source: MutableRun): MutableRun {
  return {
    ...target,
    eventCount: target.eventCount + source.eventCount,
    lastEvent:
      target.lastEventAt >= source.lastEventAt ? target.lastEvent : source.lastEvent,
    lastEventAt: Math.max(target.lastEventAt, source.lastEventAt),
    lastKind:
      target.lastEventAt >= source.lastEventAt ? target.lastKind : source.lastKind,
    lastType:
      target.lastEventAt >= source.lastEventAt ? target.lastType : source.lastType,
    runId: target.runId ?? source.runId,
    status:
      target.status !== "unknown"
        ? target.status
        : source.status,
    summary:
      target.lastEventAt >= source.lastEventAt ? target.summary : source.summary,
    taskId: target.taskId ?? source.taskId,
  };
}

function deriveEvents(events: CommandCenterEvent[]): DerivationResult {
  const aliases = new Map<string, string>();
  const runs = new Map<string, MutableRun>();
  const approvals: CommandCenterApproval[] = [];

  const ensureRun = (key: string, event: CommandCenterEvent): MutableRun => {
    const existing = runs.get(key);
    if (existing) return existing;
    const created: MutableRun = {
      eventCount: 0,
      key,
      lastEvent: event,
      lastEventAt: event.receivedAt,
      lastKind: null,
      lastType: null,
      runId: null,
      status: "unknown",
      summary: event.summary,
      taskId: null,
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

  const resolveRunKey = (event: CommandCenterEvent): string | null => {
    if (event.taskId) {
      let primary = resolveAlias(aliases, event.taskId);
      if (event.runId) {
        primary = collapse(primary, event.runId);
      }
      aliases.set(event.taskId, primary);
      if (event.runId) aliases.set(event.runId, primary);
      return primary;
    }

    if (event.runId) {
      const primary = resolveAlias(aliases, event.runId);
      aliases.set(event.runId, primary);
      return primary;
    }

    return event.eventId ? resolveAlias(aliases, event.eventId) : null;
  };

  events.forEach((event, index) => {
    const key = resolveRunKey(event) ?? `event:${index}:${event.receivedAt}`;
    const run = ensureRun(key, event);
    const nextStatus = deriveRunStatus(event);

    run.eventCount += 1;
    run.lastEvent = event;
    run.lastEventAt = event.receivedAt;
    run.lastKind = event.kind;
    run.lastType = event.type ?? event.sseType;
    run.runId = event.runId ?? run.runId;
    run.summary = event.summary;
    run.taskId = event.taskId ?? run.taskId;
    if (nextStatus !== "unknown" || run.status === "unknown") {
      run.status = nextStatus;
    }
    runs.set(key, run);

    if (isApprovalEvent(event)) {
      approvals.push({
        event,
        key: `${key}:${index}:${event.receivedAt}`,
        label: humanizeLabel(event.kind ?? event.type ?? event.sseType ?? event.status),
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

function tapMessageEvents(
  source: GuardianEventSource,
  onMessage: (event: MessageEvent<string>) => void
): () => void {
  const originalDispatchEvent = source.dispatchEvent.bind(source);
  (source as any).dispatchEvent = (event: Event) => {
    if (event instanceof MessageEvent) {
      onMessage(event as MessageEvent<string>);
    }
    return originalDispatchEvent(event);
  };
  return () => {
    (source as any).dispatchEvent = originalDispatchEvent;
  };
}

function closeSource(ref: React.MutableRefObject<GuardianEventSource | null>): void {
  ref.current?.close();
  ref.current = null;
}

export function useCommandCenterEvents(
  options: UseCommandCenterEventsOptions
): UseCommandCenterEventsResult {
  const { enabled } = options;
  const auth = useAuthState();
  const [events, setEvents] = React.useState<CommandCenterEvent[]>([]);
  const [connectionState, setConnectionState] =
    React.useState<CommandCenterConnectionState>("closed");
  const [lastEventAt, setLastEventAt] = React.useState<number | null>(null);
  const [unauthorized, setUnauthorized] = React.useState(false);
  const [connectionDetail, setConnectionDetail] = React.useState<string | null>(
    null
  );
  const sourceRef = React.useRef<GuardianEventSource | null>(null);

  React.useEffect(() => {
    if (!enabled) {
      closeSource(sourceRef);
      setConnectionState("closed");
      setConnectionDetail("Command Center not enabled.");
      setUnauthorized(false);
      return;
    }

    if (!checkAuthGate(auth, "command center SSE")) {
      closeSource(sourceRef);
      setConnectionState("closed");
      const blocked = auth.ready && auth.status !== "authenticated";
      setUnauthorized(blocked);
      setConnectionDetail(blocked ? "Unauthorized" : "Waiting for authentication");
      return;
    }

    const authInit = buildAuthenticatedFetchInit({
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
    const headers = ((authInit.headers as Record<string, string>) ?? {}) as Record<
      string,
      string
    >;
    const source = new GuardianEventSource(
      resolveSseEndpoint(getRuntimeConfigSync()),
      {
        autoReconnect: true,
        headers,
        retryInterval: 3000,
        withCredentials: authInit.credentials === "include",
        onUnauthorized: () => {
          markAuthUnauthenticatedFrom401();
        },
      }
    );

    closeSource(sourceRef);
    sourceRef.current = source;
    setConnectionState("connecting");
    setConnectionDetail("Connecting to live events...");
    setUnauthorized(false);

    const restoreDispatch = tapMessageEvents(source, (message) => {
      const normalized = normalizeEvent(message);
      setEvents((previous) => appendBoundedEvent(previous, normalized));
      setLastEventAt(normalized.receivedAt);
    });

    const handleOpen = () => {
      setConnectionState("open");
      setConnectionDetail(null);
      setUnauthorized(false);
    };

    const handleError = () => {
      setConnectionState("error");
      setConnectionDetail("Disconnected from live events.");
    };

    const handleUnauthorized = () => {
      setConnectionState("closed");
      setConnectionDetail("Unauthorized");
      setUnauthorized(true);
    };

    source.addEventListener("open", handleOpen as EventListener);
    source.addEventListener("error", handleError as EventListener);
    source.addEventListener("unauthorized", handleUnauthorized as EventListener);

    return () => {
      restoreDispatch();
      source.removeEventListener("open", handleOpen as EventListener);
      source.removeEventListener("error", handleError as EventListener);
      source.removeEventListener(
        "unauthorized",
        handleUnauthorized as EventListener
      );
      if (sourceRef.current === source) {
        closeSource(sourceRef);
      } else {
        source.close();
      }
    };
  }, [auth.ready, auth.status, auth.token, enabled]);

  const derived = React.useMemo(() => deriveEvents(events), [events]);

  return {
    approvals: derived.approvals,
    connectionDetail,
    connectionState,
    events,
    lastEventAt,
    runs: derived.runs,
    unauthorized,
  };
}

export default useCommandCenterEvents;
