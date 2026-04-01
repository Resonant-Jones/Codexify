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

export const PROVIDER_RUNTIME_STATES = {
  ONLINE: "online",
  DEGRADED: "degraded",
  OFFLINE: "offline",
} as const;

export type ProviderRuntimeState =
  (typeof PROVIDER_RUNTIME_STATES)[keyof typeof PROVIDER_RUNTIME_STATES];

export function describeProviderState(state: ProviderRuntimeState): {
  title: string;
  detail: string;
} {
  switch (state) {
    case PROVIDER_RUNTIME_STATES.OFFLINE:
      return {
        title: "Provider offline",
        detail: "The runtime provider is unreachable or not responding.",
      };
    case PROVIDER_RUNTIME_STATES.DEGRADED:
      return {
        title: "Provider degraded",
        detail: "The runtime provider is available, but one or more checks are failing.",
      };
    case PROVIDER_RUNTIME_STATES.ONLINE:
    default:
      return {
        title: "Provider online",
        detail: "The runtime provider is healthy.",
      };
  }
}

export const CHAT_REQUEST_STATES = {
  DISPATCHING: "dispatching",
  STREAMING: "streaming",
  COMPLETED: "completed",
  FAILED_RETRYABLE: "failed_retryable",
  FAILED_FATAL: "failed_fatal",
  CANCELLED: "cancelled",
  ORPHANED: "orphaned",
} as const;

export type ChatRequestState =
  (typeof CHAT_REQUEST_STATES)[keyof typeof CHAT_REQUEST_STATES];

const TERMINAL_CHAT_REQUEST_STATES = new Set<ChatRequestState>([
  CHAT_REQUEST_STATES.COMPLETED,
  CHAT_REQUEST_STATES.FAILED_RETRYABLE,
  CHAT_REQUEST_STATES.FAILED_FATAL,
  CHAT_REQUEST_STATES.CANCELLED,
]);

export function canTransitionRequestState(
  current: ChatRequestState | null | undefined,
  next: ChatRequestState
): boolean {
  if (!current) return true;
  if (current === next) return false;
  if (TERMINAL_CHAT_REQUEST_STATES.has(current)) return false;

  switch (current) {
    case CHAT_REQUEST_STATES.DISPATCHING:
      return true;
    case CHAT_REQUEST_STATES.STREAMING:
      return true;
    case CHAT_REQUEST_STATES.ORPHANED:
      return next !== CHAT_REQUEST_STATES.DISPATCHING;
    default:
      return false;
  }
}
