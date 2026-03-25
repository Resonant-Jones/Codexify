# Completion Request Pipeline (Current Runtime)

## Goal and Non-Goals

- Goal: describe the queue-backed chat completion path as it exists on `main`.
- Non-goals: aspirational architecture, UI guarantees the backend cannot prove, or a line-by-line code walkthrough.

## Actors and Responsibilities

- API routes: `guardian/routes/chat.py`
  - persist user messages
  - resolve depth/provider inputs
  - acquire per-thread turn locks
  - enqueue completion tasks
  - emit best-effort `task.created` breadcrumbs
- Shared completion service: `guardian/core/chat_completion_service.py`
  - load thread messages
  - assemble retrieval context
  - build provider-ready message lists
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
     -> Redis turn lock
     -> Redis chat queue
     -> best-effort task.created breadcrumb
     -> worker dequeues
        -> shared completion service builds messages/context
        -> provider execution
        -> optional cloud-to-local rescue
        -> Postgres assistant row
        -> task.completed / task.failed / task.cancelled
        -> turn lock release
```

## Step-by-Step Flow

1. User message is persisted.
   - `POST /api/chat/{thread_id}/messages` writes the user message to Postgres and emits best-effort side effects such as domain events and chat-embed enqueue.
   - The user message is durable before completion is requested.

2. Completion route validates and acquires turn ownership.
   - `POST /api/chat/{thread_id}/complete` validates the thread and resolves effective depth mode.
   - The route acquires a Redis turn lock whose owner is the new `task_id`.
   - If Redis lock access fails, the route returns `503 completion_service_unavailable`.
   - If another turn is still in flight and cannot be safely recovered, the route returns `429 turn_in_flight`.

3. Stale-lock recovery is evidence-based, not lease-age-only.
   - Recovery only runs when the existing lock is stale by TTL.
   - The route then inspects two evidence sources:
     - task-event stream terminal evidence via `guardian/queue/task_events.py::describe_terminal_state`
     - worker-heartbeat evidence via `guardian/routes/chat.py::_chat_worker_heartbeat_evidence`
   - Recovery is allowed only when:
     - the old task has a terminal task event, or
     - the old task is nonterminal and the worker heartbeat is `stale`, `dead`, or `missing`
   - Recovery does not run when either evidence source is `unknown`.
   - This is fail-closed behavior: uncertainty blocks recovery rather than pretending confidence.

4. Route acceptance is queue acceptance, not completion success.
   - After the lock is held, the route enqueues a `ChatCompletionTask` onto `codexify:queue:chat`.
   - If enqueue fails, the route releases the lock and returns `503 queue_unavailable`.
   - If enqueue succeeds, the route returns success with `task_id`, `turn_id`, and discovery URLs.
   - What this proves:
     - the task was accepted into the Redis-backed execution lane
     - the thread lock was acquired for this task
   - What this does not prove:
     - the worker has already dequeued the task
     - the UI will receive progress events
     - the task will complete successfully

5. `task.created` is an important breadcrumb, but best-effort.
   - The route attempts to publish `task.created` after enqueue.
   - This breadcrumb is useful because it gives operators and clients evidence that lifecycle publication started.
   - It is not authoritative acceptance proof by itself because enqueue success is the stronger signal; the `task.created` publish can fail without causing the route to fail.

6. Worker execution starts with explicit running state.
   - The chat worker dequeues from `codexify:queue:chat`.
   - It publishes `task.running` and then calls the shared completion service path to build messages, retrieval context, and prompt state.

7. Provider execution can rescue from cloud failure to local.
   - When the resolved execution provider is non-local, the worker first tries that provider/model pair.
   - If that cloud attempt fails, the worker may rescue once to local inference when:
     - the selection was not explicit, or
     - explicit local fallback is enabled and the provider was not pinned
   - The worker records:
     - attempted provider/model
     - final provider/model
     - `fallback_reason="cloud_failure_local_rescue"` when rescue occurs
   - This is execution degradation, not silent success. The terminal payload carries the fallback evidence.

8. Progress visibility and terminal visibility are different.
   - `task.progress` is progress-only visibility. Losing it degrades operator/UI insight but does not prove task failure.
   - `task.completed`, `task.failed`, and `task.cancelled` are terminal visibility signals.
   - The worker now classifies publish failures:
     - progress-event publish failure logs a warning-level visibility degradation
     - terminal-event publish failure logs an error-level visibility degradation
   - Execution continues either way; task-event publication is not a hard stop.

9. Assistant persistence is the worker’s authoritative success boundary.
   - On success, the worker persists the assistant message to Postgres, writes metadata such as attempted/final provider data, and publishes `task.completed`.
   - If generation succeeds but assistant persistence fails, the worker treats that as non-authoritative success and emits `task.failed` instead of pretending the turn completed.

10. Turn lock release happens in `finally`.
   - The worker releases the turn lock owned by the task regardless of terminal outcome.
   - This reduces lock leakage, but stale-lock recovery still exists because process death, Redis faults, or missing terminal visibility can leave ambiguous state behind.

## Acceptance Semantics

- `accepted`
  - The route acquired the turn lock and enqueued the task successfully.
  - This is the normal acceptance case.
- `accepted_degraded`
  - Use this term for the current degraded acceptance class where execution was accepted but lifecycle visibility is weaker than normal, for example when the route cannot publish `task.created` after a successful enqueue.
  - The current code does not return a literal `accepted_degraded` string in the route payload, but the runtime now distinguishes this operational case from a cleanly observed acceptance.
  - In other words: acceptance can be real while observability is degraded.

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

## Debugging Anchors

- Route and lock behavior: `guardian/routes/chat.py`
- Shared completion assembly: `guardian/core/chat_completion_service.py`
- Worker execution and rescue logic: `guardian/workers/chat_worker.py`
- Queue transport: `guardian/queue/redis_queue.py`
- Task-event visibility: `guardian/queue/task_events.py`
- Completion health truth surface: `guardian/routes/health.py`
