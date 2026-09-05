# Completion Request Pipeline (Current Runtime)

## Goal and Non-Goals

- Goal: describe the queue-backed chat completion path as it exists on `main`.
- Non-goals: aspirational architecture, UI guarantees the backend cannot prove, or a line-by-line code walkthrough.

## Actors and Responsibilities

- API routes: `guardian/routes/chat.py`
  - persist user messages
  - resolve depth/provider inputs
  - authorize the thread/account/project and prepare validated task input
  - map typed acceptance results into the existing HTTP response contract
- Shared completion acceptance operation: `guardian/core/chat_completion_service.py::enqueue_chat_completion`
  - construct and normalize the canonical task acceptance identity
  - acquire and reconcile the per-thread turn lock, including evidence-based stale-lock recovery
  - coordinate an optional typed participant after lock acquisition and around queue acceptance
  - enqueue onto the canonical chat queue
  - emit the best-effort `task.created` breadcrumb
  - calculate `accepted` versus `accepted_degraded` and reconcile queue failures
- `ChatCompletionTask` carries one optional `HostedRoomInvocationMetadata` value. Explicit Hosted Room owner and guest routes are the current public producers of this bounded field.
  - It is a bounded identity-and-authority context for an already-authorized
    caller; it is not an authority grant. Current Hosted Room routes construct
    it only after their owner or guest checks pass.
  - Ordinary completion tasks remain valid without it. Because task serialization
    uses the dataclass shape, ordinary task payloads carry
    `hosted_room_invocation: null`; legacy payloads without the key remain readable.
  - Malformed nested metadata is not partially trusted: task deserialization drops
    it to `None`, while direct typed construction raises a bounded `ValueError`.
- Shared completion service: `guardian/core/chat_completion_service.py`
  - load thread messages
  - assemble retrieval context
  - build provider-ready message lists
  - normalize provider completion into content-free terminal evidence
- Queue and coordination layer: `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`, `guardian/queue/turn_lock.py`
  - chat queue transport
  - task-event streams
  - cancellation set
  - turn locks
- Chat worker: `guardian/workers/chat_worker.py`
  - dequeue and execute tasks
  - publish progress and terminal task events
  - persist assistant messages
  - release turn locks in `finally`
- Provider routing: `guardian/core/ai_router.py`
  - local inference path
  - cloud-provider execution
  - transport and provider failure classification

## Runtime Shape

```text
UI
  -> POST /api/chat/{thread_id}/messages
     -> Postgres message row
     -> best-effort domain event + chat-embed enqueue
  -> POST /api/chat/{thread_id}/complete
     -> route authorization and task preparation
     -> enqueue_chat_completion
        -> Redis turn lock / stale-lock recovery
        -> canonical Persona selection capture
        -> optional participant prepare
        -> Redis chat queue
        -> optional participant commit
        -> best-effort task.created breadcrumb
        -> accepted or accepted_degraded result
     -> worker dequeues
        -> shared completion service builds messages/context
        -> provider execution
        -> optional pre-output cloud-to-local rescue
        -> accepted provider terminal evidence
        -> Postgres assistant row
        -> task.completed / task.failed / task.cancelled
        -> turn lock release
```

## Step-by-Step Flow

1. User message is persisted.
   - `POST /api/chat/{thread_id}/messages` writes the user message to Postgres and emits best-effort side effects such as domain events and chat-embed enqueue.
   - The user message is durable before completion is requested.

2. Completion route validates and prepares the canonical task input.
   - `POST /api/chat/{thread_id}/complete` validates the thread and resolves effective depth mode.
   - The route retains HTTP authentication, request parsing, thread/account/project authorization, retrieval/context preparation, and response serialization.
   - It delegates the complete acceptance control plane to `enqueue_chat_completion`; no other completion caller should implement a parallel lock/queue/event sequence.

3. Stale-lock recovery is evidence-based, not lease-age-only.
   - Recovery only runs when the existing lock is stale by TTL.
   - The shared acceptance operation then inspects two evidence sources:
     - task-event stream terminal evidence via `guardian/queue/task_events.py::describe_terminal_state`
     - worker-heartbeat evidence via the shared service's canonical heartbeat probe and `guardian/routes/health.py` classifier
   - Recovery is allowed only when:
     - the old task has a terminal task event, or
     - the old task is nonterminal and the worker heartbeat is `stale`, `dead`, or `missing`
   - Recovery does not run when either evidence source is `unknown`.
   - This is fail-closed behavior: uncertainty blocks recovery rather than pretending confidence.

4. Shared acceptance is queue acceptance, not completion success.
   - `enqueue_chat_completion` enqueues a `ChatCompletionTask` onto `codexify:queue:chat` after the lock is held.
   - After lock acquisition, the service reads the canonical thread Persona ID/revision pair into a strict `PersonaSelectionSnapshot`, replacing caller-supplied values before participant preparation or serialization. Read or validation failure releases the lock and prevents enqueue.
   - Every new accepted task includes the snapshot: null/null explicitly records no selection, ID/null records revisionless selection, and ID/positive revision records a persisted Persona. A null snapshot is reserved for legacy payloads. Unknown fields and invalid pairs are rejected.
   - The frozen value and existing authoritative-field guard prevent acceptance participants from changing the captured selection. The actual queue serializer retains it; later thread switches cannot rewrite the queued pair.
   - When a typed participant is supplied, its preparation runs after lock acquisition and before task serialization/enqueue. No current route supplies a participant.
   - Preparation failure prevents enqueue and causes the service to release the lock through a bounded pre-acceptance failure.
   - Enqueue or synchronous serialization failure after successful preparation invokes one best-effort participant rollback before the existing lock reconciliation. Rollback failure is recorded separately and never replaces the authoritative enqueue failure.
   - If enqueue fails, the operation reconciles the lock and returns a safe typed failure; the route maps it to the existing `503 queue_unavailable` response.
   - After enqueue succeeds, the participant commit attempt runs before `task.created`. Commit failure cannot undo queue acceptance, release the accepted task's turn lock, or trigger automatic re-enqueue.
   - If enqueue succeeds, the route returns success with `task_id`, `turn_id`, and discovery URLs.
   - What this proves:
     - the task was accepted into the Redis-backed execution lane
     - the thread lock was acquired for this task
   - What this does not prove:
     - the worker has already dequeued the task
     - the UI will receive progress events
     - the task will complete successfully

5. `task.created` is an important breadcrumb, but best-effort.
   - The shared acceptance operation attempts to publish `task.created` after enqueue and after any participant commit attempt.
   - Its existing payload includes `persona_selection_snapshot` as captured acceptance evidence. This adds no independent truth surface.
   - This breadcrumb is useful because it gives operators and clients evidence that lifecycle publication started.
   - It is not authoritative acceptance proof by itself because enqueue success is the stronger signal; the `task.created` publish can fail without causing the route to fail.
   - Participant-commit failure and `task.created` failure are independent degradations and remain separately represented when both occur.

The accepted snapshot now supplies Persona selection to the shared resolver in
both worker pre-resolution and shared completion assembly. The canonical thread
owner remains the account-authority anchor. Exact persisted revisions never
fall forward; missing accepted history fails before inference. Explicit
no-profile and revisionless selections retain their accepted identity despite
later thread switches. Legacy snapshot `None` retains live-thread behavior.
Same-task retries/copies retain the snapshot; only a new acceptance captures a
new selection. Existing routing precedence and provider rescue policy remain
unchanged. Revisionless built-in/env definitions and flow contents remain
mutable and outside this guarantee. See
[Chat Runtime Contract](./chat-runtime-contract.md#accepted-persona-selection).

6. Worker execution starts with explicit running state.
   - The chat worker dequeues from `codexify:queue:chat`.
   - It publishes `task.running` and then calls the shared completion service path to build messages, retrieval context, and prompt state.

7. Provider execution can rescue from cloud failure to local before output.
   - When the resolved execution provider is non-local, the worker first tries that provider/model pair.
   - If that cloud attempt fails, the worker may rescue once to local inference when:
     - the selection was not explicit, or
     - explicit local fallback is enabled and the provider was not pinned
   - The worker records:
     - attempted provider/model
     - final provider/model
     - `fallback_reason="cloud_failure_local_rescue"` when rescue occurs
   - This is execution degradation, not silent success. The terminal payload carries the fallback evidence.
   - Rescue is forbidden once any user-visible token, chunk, or response body has
     been emitted. A failure after visible output terminates the attempt without
     restarting generation or trying another provider.

8. Progress visibility and terminal visibility are different.
   - `task.progress` is progress-only visibility. Losing it degrades operator/UI insight but does not prove task failure.
   - `task.completed`, `task.failed`, and `task.cancelled` are terminal visibility signals.
   - The worker now classifies publish failures:
     - progress-event publish failure logs a warning-level visibility degradation
     - terminal-event publish failure logs an error-level visibility degradation
   - Execution continues either way; task-event publication is not a hard stop.
   - Transport visibility loss is a separate concern from both progress visibility and terminal visibility.
   - A stalled visible stream can still belong to a healthy provider and a running request, and a recovered stream may surface the original terminal result without implying a replay.
   - Recovery must preserve transcript integrity and avoid duplicate assistant messages.

9. Explicit terminal success gates assistant persistence.
   - Streamed visibility is not durable completion. Partial output remains
     ephemeral UI evidence until the provider adapter supplies accepted terminal
     success.
   - The shared terminal envelope distinguishes `success`, `cancelled`,
     `stream_incomplete`, `provider_error`, `malformed_terminal`, and
     `execution_timeout` without storing response content.
   - On accepted terminal success, the worker persists the assistant message to
     Postgres, writes metadata such as attempted/final provider data, and then
     publishes `task.completed`.
   - The canonical assistant-message persistence seam accepts optional structured
     Hosted Room provenance alongside content and role. Metadata-bearing worker
     tasks revalidate the room, source message, actor, requester, invitation, and
     lifecycle state before execution and immediately before the assistant insert.
     Valid Guardian completions persist participant provenance in that one insert;
     ordinary tasks omit provenance and retain the legacy call shape.
   - Missing `[DONE]` where the OpenAI-compatible adapter requires it,
     unexpected EOF, malformed frames, provider error frames, timeout, connection
     loss, parser failure, or cancellation cannot create assistant history.
   - If generation succeeds but assistant persistence fails, the worker treats that as non-authoritative success and emits `task.failed` instead of pretending the turn completed.
   - Embedding, evaluation, graph-candidate construction, and audio generation
     begin only after terminal success and successful assistant persistence.

10. Turn lock release happens in `finally`.
   - The worker releases the turn lock owned by the task regardless of terminal outcome.
   - This reduces lock leakage, but stale-lock recovery still exists because process death, Redis faults, or missing terminal visibility can leave ambiguous state behind.
   - The persisted trace snapshot now carries containment-grade retrieval and image-routing fields, including explicit absence reasons, so the debug routes can promote the same truth surface after completion.

## Acceptance Semantics

- `accepted`
  - The shared acceptance operation acquired the turn lock, enqueued the task successfully, completed any supplied participant commit, and observed the normal task-created visibility result.
  - This is the normal acceptance case.
- `accepted_degraded`
  - Use this term for the current degraded acceptance class where execution was accepted but post-acceptance coordination or lifecycle visibility is weaker than normal, for example when an optional participant cannot commit, the shared operation cannot publish `task.created`, or publication returns no event ID after a successful enqueue.
  - Queue publication must still succeed; queue failure is never degraded acceptance.
  - In other words: acceptance can be real while observability is degraded.

## Acceptance Ownership Boundary

- `guardian/routes/chat.py` owns HTTP authentication, request parsing and validation, thread/account/project authorization, retrieval/context preparation, task-input preparation, response serialization, and HTTP error mapping.
- `guardian/core/chat_completion_service.py::enqueue_chat_completion` owns the reusable acceptance transaction: canonical task identity, thread-scoped lock acquisition, stale-lock recovery, canonical queue publication, task-created publication, acceptance-status calculation, and queue-failure lock reconciliation.
- The same operation may coordinate one optional typed participant. Preparation occurs after lock acquisition and before enqueue; rollback is pre-acceptance cleanup only; commit occurs after enqueue and before `task.created`. The participant never owns the lock, queue, event stream, worker, or persistence path and is never serialized into the task.
- `guardian/workers/chat_worker.py` owns dequeue, provider execution, assistant-message persistence, terminal events, and successful-turn lock release.
- The existing task type and fields, queue name, lock key/TTL, and acceptance event sequence are unchanged. The worker has a bounded metadata-bearing branch, while ordinary worker behavior remains unchanged.
- Hosted Room invocation routes reuse `enqueue_chat_completion`; they do not implement a parallel lock, queue, or task-event sequence. The worker receives validated provenance through the canonical persistence seam and does not insert a message and apply provenance through a later update.

No current caller opts into the participant. This prerequisite exposes bounded
orchestration capability only; it does not implement a Browser Context
reference, attachment store, subject/thread binding, receipt field, or Chrome
sidebar behavior.

## Bounded Hosted Room Invocation Context

The optional task field is deliberately narrower than a general invocation
feature. Its
only fields are `room_id`, `source_message_id`, `actor_participant_id`,
`actor_source`, `actor_ref`, `requester_authority`, and
`requester_participant_id`. Version-one values accept only the resident Guardian
actor (`actor_source=resident`, `actor_ref=guardian`) and requester authority
`owner` or `guest`; guest requests must carry a participant ID and owner requests
must not. The value does not grant authority, change queueing, or alter the
model, prompt, retrieval, retry, or lifecycle pipeline. When present on an
accepted task, the worker consumes it only after fail-closed database
revalidation and persists the resulting Guardian provenance atomically with the
assistant row.

The current routes are:

- `POST /api/hosted-rooms/{room_id}/actors/{participant_id}/invoke` for an
  authenticated room owner.
- `POST /api/hosted-room-session/actors/{participant_id}/invoke` for a valid
  signed guest session.

Both accept only `message_id`. Route-neutral preparation verifies the active
room and backing thread, the explicit human source message, the single active
resident Guardian participant, and owner/guest requester lineage. The route
then delegates to `enqueue_chat_completion`. The response is `202` acceptance
metadata only; no assistant message is created by the route and no provider or
model is selected by the request body. No task type, queue name, task-created
event, or migration is added or changed.

## Completion Terminal Evidence

Terminal evidence is internal attempt metadata, not assistant content. It records
provider/model identity, terminal status, visible-output state, explicit-terminal
observation, finish reason when available, clean transport completion, bounded
failure classification, and whether pre-output retry remains permitted.

## Canonical chat capability-preparation seam (Stage 2I / R5D)

For ordinary chat, the pipeline resolves the effective provider/model first,
then both direct/shared and queued-worker execution enter the same
`chat_completion_service._prepare_chat_tool_exposure` seam before bounded
completion execution. The service-owned seam preserves explicit `task.tools`,
resolves the narrow Stage 2I exposure policy only when `task.tools is None`,
and constructs the bounded R5 `toolExposure` observation:

```text
effective provider/model resolution
→ shared capability preparation
   → preserve explicit task.tools
   → resolve automatic Stage 2I exposure when task.tools is None
   → bounded `toolExposure` advertisement evidence
→ provider inference
   → bounded `toolExposure` provider-dispatch evidence
→ normalization
→ Stage 1 advertised-subset authority
→ Command Bus
```

The only automatic result is `op::health_health_get`, a zero-argument,
read-only `GET /health` capability. DeepSeek is eligible through its native
transport. The exact Whoosh'd target additionally requires current Stage 2G
eligibility; tool-enabled Whoosh'd turns use the existing strict non-streaming
transport, while ineligible turns preserve ordinary local streaming. Stage
2F.1b still validates Whoosh'd response identity before Stage 1. No provider
error is converted into a capability error, and explicit caller-supplied
`task.tools` values are preserved.

`toolExposure` records only whether automatic resolution was attempted and the
bounded canonical command-ID subset observed after resolution and at the exact
initial `chat_with_ai` / provider-router handoff. The dispatch evidence is not
a captured raw HTTP request. It deliberately excludes tool schemas,
descriptions, arguments, messages, prompts, credentials, provider payloads,
and provider-private continuation state.

Workers consume this service-owned preparation result; they do not derive
capability exposure, project manifests, or construct an independent
`toolExposure` object. Provider adapters remain downstream translation layers.
The preparation seam neither grants authority nor executes a command: Stage 1
still checks the exact advertised subset, and the Command Bus remains the only
execution seam.

Availability and selection remain separate concepts. A provider may receive an
advertised capability and validly return a plain assistant answer. This pipeline
does not introduce `tool_choice`, forced tool use, or provider-neutral
selection-mode semantics.

| Completion path | Accepted terminal evidence |
| --- | --- |
| Whoosh'd / OpenAI-compatible local stream | `[DONE]`; a finish reason may be retained but does not replace the required marker |
| Ollama-native local stream | structured `done=true`, with `done_reason` when present |
| Local non-streaming response | validated complete response body |
| OpenAI, Groq, and Alibaba non-streaming response | validated OpenAI-compatible response body; finish reason retained when surfaced |
| DeepSeek tool/plain response | parsed structured response; each bounded tool-loop provider call must terminate successfully |
| MiniMax OpenAI/Anthropic response | parsed structured response; native finish/stop reason retained when surfaced |

Plain iterator exhaustion is not successful local streaming completion. The
terminal envelope must be present and successful before persistence. Cancellation
is checked before execution, during local streaming, after synchronous provider
return, and again immediately before persistence.

## Contract Alignment Note

- This current queue-backed pipeline already distinguishes acceptance, execution, and terminal visibility as separate truths.
- In this file, acceptance means lock acquisition plus enqueue, execution means the worker has started the completion attempt, and terminal visibility means a terminal task event and/or durable assistant persistence evidence is observable.
- `docs/architecture/chat-runtime-contract.md` adds the frontend/shared-runtime contract for ambiguity this file does not resolve on its own, including slow local-model warmup, first-token wait ambiguity, orphaned or replayed attempts, and stable message identity versus per-attempt request identity.
- `docs/architecture/adr/038-chat-transport-visibility-and-adaptive-stream-recovery-contract.md` adds the transport-visibility plane and keeps recovery separate from replay.
- That contract is normative for shared-runtime/frontend interpretation. This file remains a description of the currently scanned backend path, not a claim that every contract state is already emitted literally today.

## What Redis Is Doing In This Path

- chat task queue: `codexify:queue:chat`
- turn locks: `turn_lock:{thread_id}`
- task-event streams: `codexify:task:{task_id}:events`
- cancellation set: checked by the worker before and during execution
- worker heartbeat: `codexify:worker:chat:heartbeat`
- turn-completion anchor cache: short-lived correlation from `(thread_id, turn_id)` to assistant `message_id`
- chat-embed queue for message embeddings written adjacent to the chat loop

## What The Main Surfaces Prove

- Route `200` response:
  - proves lock + enqueue
  - does not prove dequeue or eventual success
- `task.created`:
  - proves a lifecycle breadcrumb was published when present
  - absence does not invalidate successful enqueue
- `task.running`:
  - proves the worker started observable execution when present
- `task.completed`:
  - strongest normal success signal for the async lane
  - still does not prove the UI rendered or received it
- `task.failed` / `task.cancelled`:
  - strongest terminal failure/cancel signals when publish succeeds

## Failure Modes To Keep In Mind

- Redis unavailable: route cannot trust lock or queue operations, so acceptance fails fast.
- Worker missing/stale: route may still enqueue, but completion health is degraded or unhealthy.
- Queue backlog not progressing: `/health/chat` can flag risk, but queue progression is a heuristic based on sampled depth change, not dequeue proof.
- Task-event publish failure: execution may continue while operator/UI visibility degrades.
- Provider failure with rescue: completion may succeed on local after a cloud attempt fails; the terminal payload carries that downgrade.
- Provider failure after output: partial chunks remain ephemeral; no fallback,
  assistant row, `task.completed`, or completion-only side effect is allowed.
- Missing or malformed stream terminal: the attempt fails closed even when text
  was already visible.

## Debugging Anchors

- Route and lock behavior: `guardian/routes/chat.py`
- Shared completion acceptance and assembly: `guardian/core/chat_completion_service.py::enqueue_chat_completion`
- Worker execution and rescue logic: `guardian/workers/chat_worker.py`
- Queue transport: `guardian/queue/redis_queue.py`
- Task-event visibility: `guardian/queue/task_events.py`
- Completion health truth surface: `guardian/routes/health.py`
