export const LIVE_EVENT_CONNECTION_STATES = {
  CONNECTING: "connecting",
  CONNECTED: "connected",
  RECONNECTING: "reconnecting",
  DISCONNECTED: "disconnected",
} as const;

export type LiveEventConnectionState =
  (typeof LIVE_EVENT_CONNECTION_STATES)[keyof typeof LIVE_EVENT_CONNECTION_STATES];

export const RUNTIME_HEALTH_STATUSES = {
  HEALTHY: "healthy",
  DEGRADED: "degraded",
} as const;

export type RuntimeHealthStatusToken =
  (typeof RUNTIME_HEALTH_STATUSES)[keyof typeof RUNTIME_HEALTH_STATUSES];

export const RUNTIME_HEALTH_FAILURE_KINDS = {
  BACKEND_UNREACHABLE: "backend_unreachable",
  HEALTH_ENDPOINT_MISSING: "health_endpoint_missing",
  CHAT_UNHEALTHY: "chat_unhealthy",
  LLM_UNHEALTHY: "llm_unhealthy",
  LIVE_EVENTS_DISCONNECTED: "live_events_disconnected",
  STALE: "stale",
} as const;

export type RuntimeHealthFailureKindToken =
  (typeof RUNTIME_HEALTH_FAILURE_KINDS)[keyof typeof RUNTIME_HEALTH_FAILURE_KINDS];
