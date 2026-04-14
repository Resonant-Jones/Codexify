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

export type RuntimeStatusTone =
  | "active"
  | "attention"
  | "danger"
  | "info"
  | "neutral"
  | "subtle";

export interface RuntimeStatusPresentation {
  label: string;
  tone: RuntimeStatusTone;
  isFallback: boolean;
}

// Keep this registry explicit and bounded. Only operator-facing status tokens
// that we intentionally recognize should resolve here.
export const RUNTIME_STATUS_PRESENTATIONS = {
  healthy: { label: "healthy", tone: "active", isFallback: false },
  degraded: { label: "degraded", tone: "attention", isFallback: false },
  unknown: { label: "unknown", tone: "subtle", isFallback: false },
  active: { label: "active", tone: "active", isFallback: false },
  stale: { label: "stale", tone: "attention", isFallback: false },
  offline: { label: "offline", tone: "danger", isFallback: false },
  online: { label: "online", tone: "active", isFallback: false },
  running: { label: "running", tone: "info", isFallback: false },
  queued: { label: "queued", tone: "neutral", isFallback: false },
  open: { label: "open", tone: "active", isFallback: false },
  connecting: { label: "connecting", tone: "info", isFallback: false },
  closed: { label: "closed", tone: "subtle", isFallback: false },
  error: { label: "error", tone: "danger", isFallback: false },
  OK: { label: "OK", tone: "active", isFallback: false },
  FAIL: { label: "FAIL", tone: "danger", isFallback: false },
  UNKNOWN: { label: "UNKNOWN", tone: "subtle", isFallback: false },
  attention: { label: "attention", tone: "attention", isFallback: false },
  needs_attention: { label: "needs attention", tone: "attention", isFallback: false },
  succeeded: { label: "succeeded", tone: "active", isFallback: false },
  failed: { label: "failed", tone: "danger", isFallback: false },
  unauthorized: { label: "unauthorized", tone: "attention", isFallback: false },
} as const satisfies Record<string, RuntimeStatusPresentation>;

const RUNTIME_STATUS_FALLBACK_PRESENTATION: RuntimeStatusPresentation = {
  label: "unknown",
  tone: "subtle",
  isFallback: true,
};

function humanizeRuntimeStatus(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
}

function isRuntimeStatusPresentationKey(
  status: string
): status is keyof typeof RUNTIME_STATUS_PRESENTATIONS {
  return Object.prototype.hasOwnProperty.call(RUNTIME_STATUS_PRESENTATIONS, status);
}

export function describeRuntimeStatusPresentation(
  status: string | null | undefined
): RuntimeStatusPresentation {
  const normalized = typeof status === "string" ? status.trim() : "";
  if (!normalized) {
    return RUNTIME_STATUS_FALLBACK_PRESENTATION;
  }

  if (isRuntimeStatusPresentationKey(normalized)) {
    return RUNTIME_STATUS_PRESENTATIONS[normalized];
  }

  return {
    ...RUNTIME_STATUS_FALLBACK_PRESENTATION,
    label: humanizeRuntimeStatus(normalized),
  };
}

export const CHAT_REQUEST_STATES = {
  DISPATCHING: "dispatching",
  AWAITING_ACK: "awaiting_ack",
  AWAITING_MODEL: "awaiting_model",
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
    case CHAT_REQUEST_STATES.AWAITING_ACK:
    case CHAT_REQUEST_STATES.AWAITING_MODEL:
    case CHAT_REQUEST_STATES.STREAMING:
      return true;
    case CHAT_REQUEST_STATES.ORPHANED:
      return next !== CHAT_REQUEST_STATES.DISPATCHING;
    default:
      return false;
  }
}
