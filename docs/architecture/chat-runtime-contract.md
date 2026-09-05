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
- guardian/core/chat_completion_service.py
- guardian/db/models.py
- guardian/queue/task_events.py
- guardian/workers/chat_worker.py

## Scope

- Frontend and shared runtime-contract layer only.
- No speculative backend redesign in this first pass.

## Completion Acceptance Ownership

The ordinary HTTP completion route and the shared completion acceptance operation have separate responsibilities:

- `guardian/routes/chat.py` authenticates the request, validates and authorizes the thread/account/project, prepares retrieval/context and canonical task input, and serializes the existing HTTP response.
- `guardian/core/chat_completion_service.py::enqueue_chat_completion` owns the reusable acceptance control plane: canonical task identity, thread-scoped turn-lock acquisition and evidence-based stale-lock recovery, publication to `codexify:queue:chat`, `task.created` publication, `accepted` versus `accepted_degraded` calculation, and queue-failure reconciliation.
- `guardian/workers/chat_worker.py` owns dequeue, provider execution, terminal evidence, assistant-message persistence, and worker-side lock release.

Request identity, task identity, authored message identity, and turn-lock identity remain distinct. A new completion caller must reuse the shared acceptance operation and must not implement a parallel queue, lock, or task-event sequence. Hosted Room owner and guest invocation routes construct the bounded `ChatCompletionTask.hosted_room_invocation` context only after route-specific authority checks, then use the same shared acceptance operation. Ordinary tasks bypass Hosted Room validation and persistence provenance.

### Optional acceptance participant

`enqueue_chat_completion` may coordinate one optional typed acceptance
participant without transferring ownership of the acceptance transaction. No
current route opts into this participant, and the participant object is never
serialized into `ChatCompletionTask` or sent to a worker.

The canonical order is:

```text
turn lock acquired
-> canonical Persona selection captured
-> optional participant prepare
-> queue enqueue
-> optional participant commit
-> best-effort task.created
```

Preparation runs only after the service owns the turn lock and before task
serialization or enqueue. If preparation fails, the task is not enqueued, the
service releases the lock, and the failure remains pre-acceptance. If enqueue
fails after successful preparation, the participant receives one best-effort
rollback before the service performs its existing lock reconciliation. A
rollback failure is recorded separately and cannot replace the authoritative
enqueue failure.

Successful enqueue is irreversible acceptance from this service's perspective.
The participant commit attempt therefore runs after enqueue and before
`task.created`. Commit failure never rolls the participant back, releases the
accepted task's turn lock, retries enqueue, or masquerades as queue
non-acceptance. It reuses the existing `accepted_degraded` result and
content-free acceptance-warning mechanism while `task.created` is still
attempted independently. The warning is
`acceptance_participant_commit_failed`; participant-commit and task-event
visibility failures remain separately observable when both occur.

The participant may validate bounded feature-specific ephemeral state and may
mutate only the already-constructed in-memory task during preparation. It must
not enqueue, publish events, manipulate locks, execute providers, bypass route
authorization, or persist messages. This seam is orchestration capability only;
it does not implement a Browser Context reference, store, or Chrome-sidebar
binding.

### Accepted Persona selection

Every newly accepted `ChatCompletionTask` carries a service-owned
`persona_selection_snapshot` (`PersonaSelectionSnapshot`). After acquiring the
turn lock and before participant preparation or queue serialization, acceptance
reads canonical thread `active_profile_id` and `active_profile_revision` and
overwrites any caller-supplied snapshot. An unreadable or invalid pair prevents
enqueue and releases the lock; it cannot become a new unsnapshotted acceptance.

| Representation | Meaning |
| --- | --- |
| Snapshot `null` | Legacy task without an acceptance snapshot |
| `{profile_id: null, profile_revision: null}` | Explicit no-profile selection |
| Profile ID with null revision | Revisionless selection |
| Profile ID with positive integer revision | Exact persisted Persona selection |

The frozen typed pair rejects unknown/missing fields, invalid revisions, and
revision-without-profile. Historical payloads without the snapshot remain
readable as `None`; malformed present snapshots are rejected. The existing
participant authoritative-field guard protects the captured pair from
replacement during preparation, while the value itself rejects in-place edits.
No Persona-specific participant authority is introduced.

The serialized queue payload retains the pair. The existing best-effort
`task.created` payload includes it as acceptance evidence, without becoming a
second acceptance or execution authority. Capture does not resolve the manifest,
grant account access, or change message/request/task identity (ADR-001,
ADR-003, ADR-082).

Worker/runtime consumption is deferred. Runtime still resolves later thread
selection; this capture slice alone does not make execution reproducible across
a subsequent thread switch. Revisionless selections capture an ID only, not
built-in/environment/flow configuration content. No release claim changes.

### Completion task identity context

The optional bounded task context keeps these identities distinct for future
authorization and revalidation:

- `room_id` — Hosted Room identity
- `thread_id` — backing chat thread identity
- `source_message_id` — authored source-message identity
- `actor_participant_id` — resident actor participant identity
- `requester_participant_id` — guest requester participant identity, when present
- `request_id` — completion attempt/request identity
- `task_id` — queued execution identity
- future assistant `message_id` — durable generated-message identity

The context records authority information but grants no authority by itself.
Owner requests omit `requester_participant_id`; guest requests require it.
Routes and the route-neutral preparation service remain responsible for
authentication, authorization, and task construction. The worker revalidates
room, source-message, actor, requester, invitation, and lifecycle state before
model execution and again immediately before assistant persistence. Public
invocation routes expose acceptance only; they do not imply execution or
assistant persistence.

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
- Participant-room-thread consistency is a worker/service proof obligation for
  metadata-bearing tasks; routes and task producers remain responsible for
  authorization before task construction.
- No message routes are implemented by this contract.
- No mention-triggered agent invocation behavior changes; explicit Guardian
  invocation is defined by the dedicated routes below.

### Canonical message-persistence seam

The canonical `create_message` persistence interface accepts optional structured
Hosted Room provenance through `hosted_room_participant_id` and
`sender_display_name_snapshot`. Ordinary callers omit both parameters and retain
paired NULL provenance. When supplied, both values are validated and inserted
atomically with the message row; provenance is never added through a later
message update.

Participant identity remains separate from the message role and content, and the
persistence layer does not grant or validate room authority. Worker and service
layers remain responsible for participant, room, requester, and lifecycle
authorization before using the seam. When a bounded Hosted Room task is present,
the chat worker passes the validated Guardian participant ID and the canonical
`Guardian` display snapshot in the same assistant insert. The worker does not
change model, prompt, retrieval, retry, queue, or task-schema behavior. Explicit
Hosted Room invocation routes prepare the bounded task context and delegate to
canonical acceptance; no later provenance update is used.

### Hosted Room message routes

Owner routes (authenticated account scope):
- `GET /api/hosted-rooms/{room_id}/messages` — list transcript with cursor pagination
- `POST /api/hosted-rooms/{room_id}/messages` — post human message

Guest routes (room-session cookie):
- `GET /api/hosted-room-session/messages` — list transcript with cursor pagination
- `POST /api/hosted-room-session/messages` — post human message

Explicit Guardian invocation routes:
- `POST /api/hosted-rooms/{room_id}/actors/{participant_id}/invoke` — owner-authorized asynchronous invocation
- `POST /api/hosted-room-session/actors/{participant_id}/invoke` — guest-session-authorized asynchronous invocation

Message behavior:
- Human messages persist as canonical `ChatMessage` rows with role `user`.
- Participant provenance (`hosted_room_participant_id` + `sender_display_name_snapshot`) is mandatory for newly posted room human messages.
- Server resolves room, thread, and participant — clients cannot supply these values.
- Read projection excludes account IDs, `extra_meta` internals, and request/task IDs.
- Pagination: `after_id` (cursor) + `limit` (default 100, max 200), ascending ID order.
- Lifecycle validation: closed rooms, revoked/expired invitations, and removed participants block reads and writes.
- No completion side effect from posting a message: mentions (`@Guardian`, `@Luna`) persist as text; explicit invocation requires one of the two routes above and a source `message_id`.
