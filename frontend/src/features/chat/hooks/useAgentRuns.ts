import { useEffect, useState } from "react";

import {
  fetchAgentRuns,
  type AgentRunResponse,
} from "../api/actionCenter";

type AgentRunsStore = {
  data: AgentRunResponse[];
  inFlight: Promise<AgentRunResponse[]> | null;
  loading: boolean;
  subscribers: Set<() => void>;
};

const stores = new Map<number, AgentRunsStore>();

function getStore(threadId: number): AgentRunsStore {
  const existing = stores.get(threadId);
  if (existing) return existing;
  const next: AgentRunsStore = {
    data: [],
    inFlight: null,
    loading: false,
    subscribers: new Set(),
  };
  stores.set(threadId, next);
  return next;
}

function notify(threadId: number) {
  const store = stores.get(threadId);
  if (!store) return;
  for (const subscriber of store.subscribers) {
    subscriber();
  }
}

async function loadAgentRuns(threadId: number): Promise<AgentRunResponse[]> {
  const store = getStore(threadId);
  if (store.inFlight) return store.inFlight;

  store.loading = true;
  notify(threadId);

  console.debug("[chat-fetch]", {
    type: "agent-runs",
    threadId,
    source: "useAgentRuns",
    timestamp: Date.now(),
  });

  const request = fetchAgentRuns(threadId)
    .then((runs) => {
      store.data = Array.isArray(runs) ? runs : [];
      store.loading = false;
      store.inFlight = null;
      notify(threadId);
      return store.data;
    })
    .catch((error) => {
      store.loading = false;
      store.inFlight = null;
      notify(threadId);
      throw error;
    });

  store.inFlight = request;
  return request;
}

export function useAgentRuns(threadId: number | null) {
  const [data, setData] = useState<AgentRunResponse[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (threadId == null) {
      setData([]);
      setLoading(false);
      return;
    }

    const store = getStore(threadId);
    const onUpdate = () => {
      setData(store.data);
      setLoading(store.loading);
    };

    store.subscribers.add(onUpdate);
    onUpdate();

    return () => {
      store.subscribers.delete(onUpdate);
      if (store.subscribers.size === 0 && !store.loading) {
        stores.delete(threadId);
      }
    };
  }, [threadId]);

  useEffect(() => {
    if (threadId == null) return;
    if (typeof document !== "undefined" && document.hidden) return;
    void loadAgentRuns(threadId);
  }, [threadId]);

  return { data, loading };
}

export default useAgentRuns;
