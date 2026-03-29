Scope

Frontend and shared runtime-contract layer only.
No speculative backend redesign in this first pass.

Canonical provider states
export const ProviderRuntimeState = {
  OFFLINE: "offline",
  CONNECTING: "connecting",
  RUNTIME_AVAILABLE: "runtime_available",
  MODEL_WARMING: "model_warming",
  READY: "ready",
  GENERATING: "generating",
  DEGRADED: "degraded",
  ERROR: "error",
} as const;

export type ProviderRuntimeState =
  [typeof ProviderRuntimeState](keyof typeof ProviderRuntimeState);
Canonical request states
export const ChatRequestState = {
  QUEUED: "queued",
  DISPATCHING: "dispatching",
  AWAITING_ACK: "awaiting_ack",
  AWAITING_MODEL: "awaiting_model",
  AWAITING_FIRST_TOKEN: "awaiting_first_token",
  STREAMING: "streaming",
  COMPLETED: "completed",
  CANCELLED: "cancelled",
  TIMED_OUT: "timed_out",
  FAILED_RETRYABLE: "failed_retryable",
  FAILED_FATAL: "failed_fatal",
  ORPHANED: "orphaned",
  REPLAYED: "replayed",
} as const;

export type ChatRequestState =
  [typeof ChatRequestState](keyof typeof ChatRequestState);
Message identity vs attempt identity
export interface ChatTurnMessage {
  messageId: string;          // stable authored turn identity
  threadId: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  logicalState: "submitted_unanswered" | "answered" | "abandoned" | "replayed";
}

export interface ChatTurnAttempt {
  requestId: string;          // execution attempt identity
  messageId: string;          // parent authored turn
  threadId: string;
  attemptNumber: number;

  provider: string;
  model: string;

  state: ChatRequestState;
  providerRuntimeState?: ProviderRuntimeState;

  queuedAt?: string;
  dispatchedAt?: string;
  ackAt?: string;
  modelAcceptedAt?: string;
  firstTokenAt?: string;
  completedAt?: string;
  cancelledAt?: string;
  timedOutAt?: string;
  failedAt?: string;

  backendTaskId?: string;
  streamId?: string;

  wasReplay: boolean;
  replayOfRequestId?: string;

  errorCode?: string;
  errorMessage?: string;
}
UI status mapping

This matters because your current banner likely jumps too early to “offline.”

export interface RuntimeStatusPresentation {
  tone: "neutral" | "info" | "warning" | "error";
  title: string;
  detail: string;
}

export function describeProviderState(
  state: ProviderRuntimeState
): RuntimeStatusPresentation {
  switch (state) {
    case "connecting":
      return {
        tone: "info",
        title: "Checking runtime",
        detail: "Codexify is checking the selected model runtime.",
      };
    case "runtime_available":
      return {
        tone: "info",
        title: "Runtime reachable",
        detail: "The provider is reachable.",
      };
    case "model_warming":
      return {
        tone: "warning",
        title: "Loading model",
        detail: "The selected model is loading into memory.",
      };
    case "ready":
      return {
        tone: "neutral",
        title: "Ready",
        detail: "The selected model is ready.",
      };
    case "generating":
      return {
        tone: "neutral",
        title: "Generating",
        detail: "The model is preparing or streaming a response.",
      };
    case "degraded":
      return {
        tone: "warning",
        title: "Response delayed",
        detail: "The runtime is reachable, but slower than expected.",
      };
    case "error":
      return {
        tone: "error",
        title: "Provider error",
        detail: "The runtime responded with an internal error.",
      };
    case "offline":
    default:
      return {
        tone: "error",
        title: "Runtime offline",
        detail: "Codexify cannot reach the selected provider.",
      };
  }
}
Minimal state transition rules

These are the ones that close the ghost-turn hole:

export function canTransitionRequestState(
  from: ChatRequestState,
  to: ChatRequestState
): boolean {
  const allowed: Record<ChatRequestState, ChatRequestState[]> = {
    queued: ["dispatching", "cancelled"],
    dispatching: ["awaiting_ack", "failed_retryable", "failed_fatal", "cancelled"],
    awaiting_ack: ["awaiting_model", "awaiting_first_token", "orphaned", "timed_out", "failed_retryable"],
    awaiting_model: ["awaiting_first_token", "timed_out", "cancelled", "orphaned"],
    awaiting_first_token: ["streaming", "timed_out", "cancelled", "orphaned"],
    streaming: ["completed", "cancelled", "failed_retryable", "failed_fatal", "orphaned"],
    completed: [],
    cancelled: [],
    timed_out: ["replayed", "completed", "orphaned"],
    failed_retryable: ["replayed"],
    failed_fatal: [],
    orphaned: ["replayed", "completed"],
    replayed: [],
  };

  return allowed[from].includes(to);
}
Critical behavioral rules

1. Never silently replay

If a timed-out or orphaned turn is reissued, create a new attempt object with:

new requestId
incremented attemptNumber
wasReplay = true
replayOfRequestId = oldRequestId

That aligns with the project’s protocol-token discipline and existing acceptance-vs-completion caution.

1. Never map warmup to offline

Only use offline for transport-unreachable or repeated hard reachability failure.

1. Never mark a user turn “answered” until a specific attempt reaches completed

That preserves transcript integrity.
