# Chat Runtime Contract

Purpose: Define the normative frontend/shared-runtime contract for provider runtime state, request execution state, transport visibility state, message-versus-attempt identity, UI presentation, replay handling, and request-state transitions.
Last updated: 2026-07-28
Source anchors:
- docs/architecture/chat-runtime-gap-analysis.md
- docs/architecture/adr/038-chat-transport-visibility-and-adaptive-stream-recovery-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/adr/003-message-identity-vs-request-identity.md
- frontend/src/
- guardian/routes/chat.py
- guardian/db/models.py
- guardian/queue/task_events.py
- guardian/workers/chat_worker.py

## Scope

- Frontend and shared runtime-contract layer only.
- No speculative backend redesign in this first pass.

## Canonical Provider States

```ts
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
  (typeof ProviderRuntimeState)[keyof typeof ProviderRuntimeState];
```

## Canonical Transport Visibility States

```ts
export const ChatTransportVisibilityState = {
  CONNECTED: "connected",
  SUSPECTED_STALLED: "suspected_stalled",
  RECOVERING: "recovering",
  RECOVERED: "recovered",
  FAILED: "failed",
} as const;

export type ChatTransportVisibilityState =
  (typeof ChatTransportVisibilityState)[keyof typeof ChatTransportVisibilityState];
```

Transport visibility state describes whether the frontend can still observe the stream for a specific completion attempt. It is distinct from provider runtime state and request execution state.

A visible stream can become suspected stalled or recoverable even when the provider is still healthy and the request is still running. A later reconnect may surface the terminal event after the original visible stream path broke. That is a transport-observation problem, not automatically a provider or request failure.

## Canonical Request States

```ts
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
  (typeof ChatRequestState)[keyof typeof ChatRequestState];
```

## Message Identity vs Attempt Identity

```ts
export interface ChatTurnMessage {
  messageId: string; // stable authored turn identity
  threadId: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  logicalState: "submitted_unanswered" | "answered" | "abandoned" | "replayed";
}

export interface ChatTurnAttempt {
  requestId: string; // execution attempt identity
  messageId: string; // parent authored turn
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
```

## UI Status Mapping

This mapping matters because a reachable runtime that is still warming or delayed must not collapse into `offline`.

```ts
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
```

## Minimal State Transition Rules

These transition rules close the ghost-turn hole by making unresolved or replayed execution attempts explicit.

```ts
export function canTransitionRequestState(
  from: ChatRequestState,
  to: ChatRequestState
): boolean {
  const allowed: Record<ChatRequestState, ChatRequestState[]> = {
    queued: ["dispatching", "cancelled"],
    dispatching: [
      "awaiting_ack",
      "failed_retryable",
      "failed_fatal",
      "cancelled",
    ],
    awaiting_ack: [
      "awaiting_model",
      "awaiting_first_token",
      "orphaned",
      "timed_out",
      "failed_retryable",
    ],
    awaiting_model: [
      "awaiting_first_token",
      "timed_out",
      "cancelled",
      "orphaned",
    ],
    awaiting_first_token: ["streaming", "timed_out", "cancelled", "orphaned"],
    streaming: [
      "completed",
      "cancelled",
      "failed_retryable",
      "failed_fatal",
      "orphaned",
    ],
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
```

## Critical Behavioral Rules

1. Never silently replay.
   If a timed-out or orphaned turn is reissued, create a new attempt object with a new `requestId`, an incremented `attemptNumber`, `wasReplay = true`, and `replayOfRequestId = oldRequestId`.
1. Never map warmup to offline.
   Only use `offline` for transport-unreachable or repeated hard reachability failure.
1. Never mark a user turn `answered` until a specific attempt reaches `completed`.
   That preserves transcript integrity.
1. Never conflate transport stall with request failure.
   A stalled, recovering, or recovered visible stream does not by itself prove that the provider is offline or that the request failed.
1. Never let recovery mint a duplicate turn.
   Recovery may re-establish observation of the original attempt, but it must not create a second assistant message for the same message/request pair.
1. Keep timing policy out of the contract.
   Model/profile-specific TTFT windows, stall thresholds, and reconnect heuristics are future implementation concerns and belong in separate follow-up specs.

## What To Implement First

For beta shipping, implement this contract in three cuts:

1. Cut 1: frontend contract and UI truth.
   Add shared runtime tokens for provider and request states, change banner logic so warmup/degraded do not render as offline, and add explicit pending states in the per-thread run store.
1. Cut 2: request identity hardening.
   Introduce `messageId` versus `requestId` in frontend state, preserve unresolved attempts as `timed_out` or `orphaned`, and mark replay explicitly.
1. Cut 3: backend event enrichment.
   Emit enough task metadata to distinguish accepted, running, warming, first-token pending, completed, failed, and cancelled states while staying aligned with the canonical runtime token policy.

## Follow-up Implementation Specs

These are intentionally separate tasks. They are not implemented by this contract.

1. First-token expectation windows and model/profile-specific TTFT tuning.
2. Stream stall detection and heartbeat or keepalive policy.
3. Reconnect or resubscribe behavior for transport visibility recovery.
4. Duplicate suppression for late terminal events and recovered streams.
5. User-visible reconnecting or response-delayed banner policy.

## Hosted Room Message Authorship

`ChatMessage` now carries optional Hosted Room participant provenance:

- `hosted_room_participant_id` — nullable FK to `hosted_room_participants.id` (ON DELETE SET NULL)
- `sender_display_name_snapshot` — nullable, bounded (255 chars), immutable after creation

Key rules:

- Hosted Room human messages retain the canonical user/human role.
- Future agent messages retain the canonical assistant role.
- Participant authorship is separate from chat role — roles such as `member`, `owner`, or display names must not become chat roles.
- Message ID remains distinct from participant ID and request ID (ADR-003).
- Participant provenance is either both fields null (ordinary messages) or both non-null with a non-blank snapshot (room messages).
- Sender display name is a durable presentation snapshot, not global identity proof.
- Content remains semantically clean — participant identity is never embedded in message text.
- Participant-room-thread consistency is a future route proof obligation (routes not yet implemented).
- No message routes are implemented by this contract.
- No agent invocation behavior changes.

### Hosted Room message routes

Owner routes (authenticated account scope):
- `GET /api/hosted-rooms/{room_id}/messages` — list transcript with cursor pagination
- `POST /api/hosted-rooms/{room_id}/messages` — post human message

Guest routes (room-session cookie):
- `GET /api/hosted-room-session/messages` — list transcript with cursor pagination
- `POST /api/hosted-room-session/messages` — post human message

Message behavior:
- Human messages persist as canonical `ChatMessage` rows with role `user`.
- Participant provenance (`hosted_room_participant_id` + `sender_display_name_snapshot`) is mandatory for newly posted room human messages.
- Server resolves room, thread, and participant — clients cannot supply these values.
- Read projection excludes account IDs, `extra_meta` internals, and request/task IDs.
- Pagination: `after_id` (cursor) + `limit` (default 100, max 200), ascending ID order.
- Lifecycle validation: closed rooms, revoked/expired invitations, and removed participants block reads and writes.
- No completion side effect: mentions (`@Guardian`, `@Luna`) persist as text; no model is invoked.
