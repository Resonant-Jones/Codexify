import { useEffect, useState } from "react";

import {
  fetchAgentRuns,
  type AgentRunResponse,
} from "../api/actionCenter";

type AgentRunsEntry = {
  data: AgentRunResponse[];
  loading: boolean;
  error: unknown | null;
  listeners: Set<() => void>;
  inFlight?: Promise<void>;
};

const agentRunsStore = new Map<string, AgentRunsEntry>();

function normalizeText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function normalizeRunStatus(
  value: unknown,
  eventType: string | null
): string | null {
  const explicit = normalizeText(value);
  if (explicit) return explicit;

  switch (eventType) {
    case "task.created":
    case "task.updated":
    case "task.progress":
    case "task.running":
      return "running";
    case "task.completed":
      return "completed";
    case "task.failed":
    case "completion.error":
      return "failed";
    case "task.cancelled":
      return "canceled";
    default:
      return null;
  }
}

function normalizeAgentRunRecord(
  record: Record<string, unknown>,
  threadId: string
): AgentRunResponse | null {
  const runId = normalizeText(record.run_id ?? record.runId ?? record.id);
  const runtimeTarget = normalizeText(
    record.runtime_target ?? record.runtimeTarget
  );
  const worktreeId = normalizeText(record.worktree_id ?? record.worktreeId);
  const worktreePath = normalizeText(
    record.worktree_path ?? record.worktreePath
  );
  const eventType = normalizeText(record.event_type ?? record.eventType);

  const hasAgentRunShape =
    (runId && runId.startsWith("run_")) ||
    runtimeTarget ||
    worktreeId ||
    worktreePath;

  if (!hasAgentRunShape || !runId) {
    return null;
  }

  const rawThreadId = Number(
    record.thread_id ?? record.threadId ?? threadId
  );

  return {
    run_id: runId,
    runtime_target: runtimeTarget,
    status: normalizeRunStatus(record.status, eventType),
    thread_id: Number.isFinite(rawThreadId) ? rawThreadId : null,
    worktree_id: worktreeId,
    worktree_path: worktreePath,
  };
}

function normalizeIncomingAgentRuns(
  incoming: unknown,
  threadId: string
): AgentRunResponse[] {
  if (Array.isArray(incoming)) {
    return incoming.flatMap((item) => normalizeIncomingAgentRuns(item, threadId));
  }

  if (!incoming || typeof incoming !== "object") {
    return [];
  }

  const record = incoming as Record<string, unknown>;

  if (Array.isArray(record.runs)) {
    return normalizeIncomingAgentRuns(record.runs, threadId);
  }

  if (record.run && typeof record.run === "object" && !Array.isArray(record.run)) {
    const { run, ...rest } = record;
    return normalizeIncomingAgentRuns(
      {
        ...rest,
        ...(run as Record<string, unknown>),
      },
      threadId
    );
  }

  const normalized = normalizeAgentRunRecord(record, threadId);
  return normalized ? [normalized] : [];
}

function mergeAgentRuns(
  existing: AgentRunResponse[],
  incoming: unknown,
  threadId: string
): AgentRunResponse[] {
  const nextRuns = normalizeIncomingAgentRuns(incoming, threadId);

  if (nextRuns.length === 0) {
    return existing;
  }

  const map = new Map<string, AgentRunResponse>();
  const existingOrder: string[] = [];
  const nextIds = new Set<string>();

  for (const run of existing) {
    const runId = normalizeText(run.run_id);
    if (!runId) continue;
    map.set(runId, run);
    existingOrder.push(runId);
  }

  for (const run of nextRuns) {
    const runId = normalizeText(run.run_id);
    if (!runId) continue;
    if (!map.has(runId)) {
      nextIds.add(runId);
    }
    map.set(runId, {
      ...map.get(runId),
      ...run,
    });
  }

  return [
    ...Array.from(nextIds)
      .map((runId) => map.get(runId))
      .filter((run): run is AgentRunResponse => Boolean(run)),
    ...existingOrder
      .filter((runId) => !nextIds.has(runId))
      .map((runId) => map.get(runId))
      .filter((run): run is AgentRunResponse => Boolean(run)),
  ];
}

function getOrCreateEntry(threadId: string): AgentRunsEntry {
  let entry = agentRunsStore.get(threadId);

  if (!entry) {
    entry = {
      data: [],
      loading: false,
      error: null,
      listeners: new Set(),
    };
    agentRunsStore.set(threadId, entry);
  }

  return entry;
}

function broadcast(entry: AgentRunsEntry) {
  entry.listeners.forEach((listener) => listener());
}

export function applyAgentRunEvent(threadId: string, payload: unknown) {
  const entry = getOrCreateEntry(threadId);
  const updated = mergeAgentRuns(entry.data || [], payload, threadId);

  if (updated === entry.data) {
    return;
  }

  entry.data = updated;
  entry.error = null;
  broadcast(entry);
}

async function fetchAgentRunsForThread(threadId: string) {
  const entry = getOrCreateEntry(threadId);

  if (entry.inFlight) return entry.inFlight;

  entry.loading = true;
  entry.error = null;
  broadcast(entry);

  entry.inFlight = (async () => {
    try {
      console.debug("[chat-fetch] agent-runs:start", { threadId });

      const numericThreadId = Number(threadId);
      const res = await fetchAgentRuns(numericThreadId);

      entry.data = mergeAgentRuns(entry.data, res ?? [], threadId);

      console.debug("[chat-fetch] agent-runs:success", {
        threadId,
        count: entry.data.length,
      });
    } catch (err) {
      entry.error = err;

      console.error("[chat-fetch] agent-runs:error", {
        threadId,
        err,
      });
    } finally {
      entry.loading = false;
      entry.inFlight = undefined;
      broadcast(entry);
    }
  })();

  return entry.inFlight;
}

export function useAgentRuns(threadId: number | null) {
  const [, forceRender] = useState(0);
  const threadKey = threadId == null ? null : String(threadId);

  useEffect(() => {
    if (!threadKey) return;

    const entry = getOrCreateEntry(threadKey);
    const listener = () => forceRender((value) => value + 1);

    entry.listeners.add(listener);

    return () => {
      entry.listeners.delete(listener);
    };
  }, [threadKey]);

  useEffect(() => {
    if (!threadKey) return;
    if (typeof document !== "undefined" && document.hidden) return;
    const entry = getOrCreateEntry(threadKey);
    if (!entry.data.length) {
      void fetchAgentRunsForThread(threadKey);
    }
  }, [threadKey]);

  const entry = threadKey ? getOrCreateEntry(threadKey) : null;

  return {
    data: entry?.data ?? [],
    loading: entry?.loading ?? false,
    error: entry?.error ?? null,
    refetch: () => (threadKey ? fetchAgentRunsForThread(threadKey) : undefined),
  };
}

export default useAgentRuns;

export function __resetAgentRunsStoreForTests() {
  agentRunsStore.clear();
}
