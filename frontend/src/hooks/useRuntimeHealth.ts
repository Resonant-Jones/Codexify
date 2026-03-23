import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { ConnectionStatus, useLiveEvents } from "@/hooks/useLiveEvents";

const POLL_INTERVAL_MS = 15000;
const STALE_THRESHOLD_MS = 45000;

export type RuntimeFailureKind =
  | "backend_unreachable"
  | "health_endpoint_missing"
  | "chat_unhealthy"
  | "llm_unhealthy"
  | "live_events_disconnected"
  | "stale";

export type RuntimeHealthStatus = {
  status: "healthy" | "degraded";
  failureKind: RuntimeFailureKind | null;
  backendReachable: boolean | null;
  chatHealthy: boolean | null;
  llmHealthy: boolean | null;
  liveEventsStatus: ConnectionStatus;
  lastSuccessAt: number | null;
  lastCheckedAt: number | null;
  stale: boolean;
};

type HealthSnapshot = {
  backendReachable: boolean | null;
  healthEndpointMissing: boolean | null;
  chatHealthy: boolean | null;
  llmHealthy: boolean | null;
  lastSuccessAt: number | null;
  lastCheckedAt: number | null;
};

const INITIAL_SNAPSHOT: HealthSnapshot = {
  backendReachable: null,
  healthEndpointMissing: null,
  chatHealthy: null,
  llmHealthy: null,
  lastSuccessAt: null,
  lastCheckedAt: null,
};

function isHealthOk(payload: unknown): boolean {
  if (!payload || typeof payload !== "object") return false;
  const candidate = payload as { ok?: unknown; status?: unknown };
  if (typeof candidate.ok === "boolean") return candidate.ok;
  return String(candidate.status ?? "").toLowerCase() === "ok";
}

type HealthResult = {
  reachable: boolean;
  ok: boolean | null;
  missing: boolean;
};

function responseStatusFromResult(
  result: PromiseSettledResult<{ data?: unknown }>
): number | null {
  if (result.status !== "rejected") return null;
  const reason = result.reason as { response?: { status?: number } } | null;
  const status = reason?.response?.status;
  return typeof status === "number" ? status : null;
}

function parseHealthResult(
  result: PromiseSettledResult<{ data?: unknown }>
): HealthResult {
  if (result.status === "fulfilled") {
    return {
      reachable: true,
      ok: isHealthOk(result.value?.data),
      missing: false,
    };
  }
  const status = responseStatusFromResult(result);
  if (status === 404) {
    return { reachable: true, ok: null, missing: true };
  }
  if (status != null) {
    return { reachable: true, ok: false, missing: false };
  }
  return { reachable: false, ok: null, missing: false };
}

export function useRuntimeHealth(): RuntimeHealthStatus {
  const liveEvents = useLiveEvents({ passive: true });
  const connectionStatus =
    liveEvents.connectionStatus ?? "disconnected";
  const statusUpdatedAt = liveEvents.statusUpdatedAt ?? null;
  const [snapshot, setSnapshot] = useState<HealthSnapshot>(INITIAL_SNAPSHOT);
  const inFlightRef = useRef(false);
  const firstCheckAtRef = useRef<number | null>(null);

  const poll = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    const startedAt = Date.now();
    if (!firstCheckAtRef.current) {
      firstCheckAtRef.current = startedAt;
    }
    try {
      const [backendResult, chatResult, llmResult] =
        await Promise.allSettled([
          api.get("/health"),
          api.get("/health/chat"),
          api.get("/health/llm"),
        ]);

      const backendHealth = parseHealthResult(backendResult);
      const chatHealth = parseHealthResult(chatResult);
      const llmHealth = parseHealthResult(llmResult);
      const backendReachable = backendHealth.reachable;
      const chatHealthy = chatHealth.ok;
      const llmHealthy = llmHealth.ok;
      const healthEndpointMissing =
        backendHealth.missing || chatHealth.missing || llmHealth.missing;
      const success = backendReachable && chatHealthy && llmHealthy;

      setSnapshot((prev) => ({
        backendReachable,
        healthEndpointMissing,
        chatHealthy,
        llmHealthy,
        lastCheckedAt: startedAt,
        lastSuccessAt: success ? startedAt : prev.lastSuccessAt,
      }));
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    void poll();
    const timer = setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [poll]);

  const now = Date.now();
  const hasChecked = snapshot.lastCheckedAt != null;
  const lastSuccessAt = snapshot.lastSuccessAt;
  const firstCheckAt = firstCheckAtRef.current;
  const stale =
    lastSuccessAt != null
      ? now - lastSuccessAt > STALE_THRESHOLD_MS
      : firstCheckAt != null
        ? now - firstCheckAt > STALE_THRESHOLD_MS
        : false;
  const liveEventsDisconnected =
    connectionStatus === "disconnected" &&
    typeof statusUpdatedAt === "number" &&
    now - statusUpdatedAt > STALE_THRESHOLD_MS;

  let failureKind: RuntimeFailureKind | null = null;
  if (hasChecked && snapshot.backendReachable === false) {
    failureKind = "backend_unreachable";
  } else if (hasChecked && snapshot.healthEndpointMissing) {
    failureKind = "health_endpoint_missing";
  } else if (hasChecked && snapshot.chatHealthy === false) {
    failureKind = "chat_unhealthy";
  } else if (hasChecked && snapshot.llmHealthy === false) {
    failureKind = "llm_unhealthy";
  } else if (liveEventsDisconnected) {
    failureKind = "live_events_disconnected";
  } else if (stale) {
    failureKind = "stale";
  }

  return {
    status: failureKind ? "degraded" : "healthy",
    failureKind,
    backendReachable: snapshot.backendReachable,
    chatHealthy: snapshot.chatHealthy,
    llmHealthy: snapshot.llmHealthy,
    liveEventsStatus: connectionStatus,
    lastSuccessAt,
    lastCheckedAt: snapshot.lastCheckedAt,
    stale,
  };
}

export default useRuntimeHealth;
