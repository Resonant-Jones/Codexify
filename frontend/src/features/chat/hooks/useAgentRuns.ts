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

      entry.data = res ?? [];

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
    void fetchAgentRunsForThread(threadKey);
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
