# Redis / Chat Completion Recon

## Scope

- Inspected source: `guardian/routes/chat.py`, `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`, `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`, `guardian/routes/health.py`, `guardian/core/ai_router.py`, `guardian/queue/turn_lock.py`, `docker-compose.yml`.
- Inspected tests: `tests/routes/test_chat_routes.py`, `tests/core/test_turn_lock_recovery.py`, `tests/test_chat_worker_turn_integrity.py`, `guardian/tests/workers/test_chat_worker_completion_semantics.py`, `guardian/tests/workers/test_chat_worker_turn_metadata.py`, `guardian/tests/test_health_endpoints.py`, `tests/routes/test_metrics.py`, `tests/routes/test_event_graph_emission.py`.
- Cross-checked docs for drift: `docs/architecture/completion_pipeline.md`, `docs/architecture/data-and-storage.md`, `docs/architecture/flows.md`, `docs/architecture/roadmap-signals.md`, `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/00-current-state.md`.
- Runtime verification was attempted, but live localhost access was blocked from this session, so no end-to-end completion probe could be completed.
- No automated tests apply to this report. This was a report-only task, and no production source file was modified.

## Repo state

- Branch: `main`
- HEAD: `9a8a0de1a3f011632ad5fb812a64941cb16ab8bd`
- Worktree before this task: not clean; `git status --short` already showed the unrelated untracked file `docs/Future-Features/artifact_event_capture_and_task_graph.md`.
- Recon timestamp: `2026-03-20 05:51:07 EDT`
- Runtime verification commands and results:
  - `timeout 15s docker compose ps` -> exit `124`; no compose status returned before timeout.
  - `timeout 5s curl -sv http://127.0.0.1:8888/health` -> exit `7`; connect failed with `Operation not permitted`.
  - `timeout 5s curl -sv http://127.0.0.1:8888/health/chat` -> exit `7`; same connect failure.
  - `timeout 5s curl -sv -H "X-API-Key: $GUARDIAN_API_KEY" http://127.0.0.1:8888/api/health/llm` -> exit `7`; same connect failure.
- No automated test suite was run.

## Current implementation path

1. User message persistence starts at `guardian/routes/chat.py::chat_post_message` and `chat_post_message_create_on_send`, both of which call `_persist_message_to_thread`.
2. `_persist_message_to_thread` does a short Redis turn-lock probe with `acquire_turn_lock(thread_id, "api:chat.messages:user_probe")`, returns `429 turn_in_flight` if the assistant is active, and otherwise persists the message with `chatlog_db.create_message`, audit logging, `event_bus.emit_event("message.created", ...)`, `_emit_thread_update_event(...)`, and `_embed_message(...)`.
3. The completion request enters `guardian/routes/chat.py::chat_complete`, which validates the thread exists, loads recent messages, filters unusable context, resolves depth, and builds a doc-context override before task creation.
4. `chat_complete` creates a `ChatCompletionTask`, sets `turn_lock_owner = task.task_id`, carries `turn_id` in `origin`, acquires the per-thread lock with `guardian.queue.turn_lock.acquire_turn_lock`, and tries `_recover_orphaned_turn_lock` if the lock is stale.
5. On successful lock acquisition, `chat_complete` enqueues the task to Redis with `guardian.queue.redis_queue.enqueue(task, "codexify:queue:chat")`, publishes `task.created` with `guardian.queue.task_events.publish`, and returns `task_id`, `turn_id`, and trace/message URLs.
6. `guardian/workers/chat_worker.py::run_forever` dequeues from `codexify:queue:chat`, refreshes the worker heartbeat key, deserializes the task, applies `turn_id` and `turn_lock_owner` from payload if present, handles cancellation, and submits `_run_chat_task`.
7. `_run_chat_task` publishes `task.running`, deduplicates on `turn_id`, calls `run_chat_completion_task`, caches the turn anchor, persists `turn_id` metadata, schedules assistant audio, publishes `task.completed` or `task.failed`, and releases the turn lock in `finally`.

## Redis responsibilities actually in use today

- Chat task queue: yes. `guardian/queue/redis_queue.py::enqueue/dequeue` operate on `codexify:queue:chat`, and `guardian/routes/chat.py::chat_complete` plus `guardian/workers/chat_worker.py::run_forever` are the primary producer/consumer pair.
- Turn locks: yes. The primary chat path uses `guardian/queue/turn_lock.py` and the `turn_lock:{thread_id}` key; the route acquires the lock and the worker releases it. `guardian/queue/redis_queue.py` still contains legacy raw-string lock helpers, but the chat path does not use them.
- Task event transport: yes. `guardian/queue/task_events.py` writes to `codexify:task:{task_id}:events`, and `guardian/guardian_api.py::stream_task_events` exposes the SSE consumer.
- Cancellation: yes. `guardian/queue/redis_queue.py` stores cancellation in `codexify:queue:cancelled`, and the worker checks `is_cancelled()` before and during execution.
- Worker heartbeat: yes. `guardian/workers/chat_worker.py::_publish_worker_heartbeat` writes `codexify:worker:chat:heartbeat`, and `/health/chat` reads it.
- Completion turn-anchor cache: yes. The worker stores `codexify:chat:turn-anchor:{thread_id}:{turn_id}` in Redis so turn IDs can be resolved after persistence.
- Chat embedding queue: yes. `enqueue_chat_embed()` pushes to `codexify:queue:chat-embed`.
- Health probe queue: yes, transiently. `/health/chat` creates a throwaway `codexify:queue:healthcheck:{uuid}` list and round-trips it with `LPUSH`/`RPOP` to test Redis queue primitives.

## Chat completion execution path

1. The shared completion service, `guardian/core/chat_completion_service.py::build_messages_for_llm`, loads the thread, recent messages, and the latest user utterance, then calls `ContextBroker.assemble(...)`.
2. That service builds the system prompt, thread-document context, and final provider-ready message list, then returns the bundle and trace payload alongside the resolved provider/model.
3. `guardian/core/chat_completion_service.py::run_chat_completion_task` runs either `stream_local(...)` or `chat_with_ai(...)`, captures the assistant text, and preserves the trace/bundle for later use.
4. When `persist_assistant_message=True`, `run_chat_completion_task` writes the assistant row with `chatlog_db.create_message`, appends audit state, emits `message.created`, and auto-embeds the response.
5. `guardian/workers/chat_worker.py::_run_chat_completion_task_compat` is a compatibility wrapper around that shared service. It can rescue a non-explicit cloud failure to local execution if a local model exists, which is a real fallback branch, not a general retry loop.
6. After persistence, `_run_chat_task` writes the turn ID into `chat_messages.extra_meta`, caches the turn anchor in Redis, and treats those failures as non-fatal unless the assistant message itself is missing.

## Turn-lock and task-event contract

- `turn_id` is normalized at route entry, threaded into the task origin, and copied into `task.turn_id`.
- `turn_lock_owner` is set to the task ID before enqueue so the worker can release the same lock later.
- The intended stale-lock recovery path is `_recover_orphaned_turn_lock(...)`, which checks `turn_lock_is_stale(...)`, `_task_terminal_event(...)`, and `_chat_worker_heartbeat_age_seconds()`.
- In the current code, `_task_terminal_event` and `_chat_worker_heartbeat_age_seconds` are local stubs in `guardian/routes/chat.py` that return `None`, so recovery does not actually inspect Redis task events or worker heartbeat age.
- That means stale-lock recovery is effectively driven by the Redis lease check alone, even though the code path reads as if it is heartbeat-aware.
- On success, the worker publishes `task.running`, `task.progress`, `task.completed`, and on failure `task.failed`; on cancellation it publishes `task.cancelled`.
- `task.completed` is the signal the debug trace path reads back through `guardian/routes/chat.py::_get_task_completed_payload(...)` and `GET /api/chat/debug/rag-trace/{thread_id}/latest`.
- `guardian/guardian_api.py::stream_task_events` is the operator-facing SSE stream for a specific task ID.
- Task-event publish failures are best-effort; `_safe_publish` logs and swallows Redis stream errors instead of turning them into route failures.

## Health/readiness surfaces

| Surface | What it proves | What it does not prove |
|---|---|---|
| `GET /health` | The backend app process is responding. | Redis reachability, worker presence, queue consumption, task-event flow, and provider health. |
| `GET /health/chat` | Redis responds to `PING`, a throwaway queue can be `LPUSH`/`RPOP`'d, and the worker heartbeat key exists. | It does not prove that `codexify:queue:chat` is being consumed, that completions succeed, or that task events are flowing. It also ignores heartbeat age when setting `ok`. |
| `GET /api/health/llm` | The active provider is configured, and for `local` it actively probes the local base URL; it also embeds the completion-service subcheck. | It does not prove chat worker consumption or end-to-end task completion. For cloud providers it returns `status=unknown`/`runtime_unprobed` rather than a live probe. |
| `GET /api/tasks/{task_id}/events` | A specific task's Redis-backed event stream is readable. | It does not prove queue health for other tasks or the system as a whole. |
| `docker compose ps` and `docker compose logs --tail=200 backend|worker-chat|redis` | Operator can inspect whether the relevant containers are present and what they logged. | These are inspection surfaces, not end-to-end proofs. |

## Failure modes visible in code

- `turn_lock_unavailable`: `guardian/routes/chat.py::chat_complete` catches lock acquisition exceptions and returns structured `503 completion_service_unavailable`. User impact: immediate HTTP error, no task ID.
- `queue_unavailable`: the same route catches enqueue failures, releases the lock best-effort, and returns structured `503 completion_service_unavailable`. User impact: immediate HTTP error after lock acquisition.
- `turn_in_flight`: if the lock already exists or recovery declines to clear it, the route returns `429`. User impact: immediate HTTP conflict and no enqueue.
- `queued_but_never_completed`: the route can return `200` with a task ID even if `worker-chat` is absent or stuck. User impact: silent/stalled UX until task events or logs are inspected.
- `provider_failure_after_dequeue`: provider exceptions inside `run_chat_completion_task` or `_run_chat_task` become `task.failed` and `completion.error` after the HTTP request has already succeeded. User impact: task failure event, not a route error.
- `assistant_message_persist_failed`: a successful provider response can still fail when `chatlog_db.create_message(...)` raises `AssistantPersistenceError`. User impact: task failure after apparent generation success.
- `task_event_visibility_failure`: Redis stream publish failures are swallowed by `_safe_publish`, so the worker may keep running while the UI loses progress/completion signals. User impact: missing progress, stalled spinner, or partial observability.
- `stale_turn_lock_behavior`: because the route-level heartbeat and terminal-event hooks are stubs, stale-lock cleanup is not actually heartbeat-aware. If the lease expires while a worker is still running, the route can clear the lock and enqueue a second completion. User impact: duplicate work risk or false recovery.
- `worker_absence_while_api_healthy`: `GET /health` can remain green while chat completion is unavailable. User impact: the API looks healthy even though the assistant path is degraded.

## Drift between docs and implementation

| Document | Status | Notes |
|---|---|---|
| `docs/architecture/completion_pipeline.md` | clearly stale | It says there is no retry in the worker path, but `_run_chat_completion_task_compat` now has a cloud-to-local rescue branch when the request was not explicitly pinned. The doc also does not capture the current best-effort event publishing and richer completion payloads. |
| `docs/architecture/data-and-storage.md` | partially stale | The Redis role list is broadly right, but it omits the `chat-embed` queue, the transient health-probe queue, and the fact that the main chat path uses `guardian/queue/turn_lock.py` instead of the legacy raw-string helpers in `redis_queue.py`. |
| `docs/architecture/flows.md` | partially stale | The coarse sequence still matches, but it does not mention route-side stale-lock recovery caveats, best-effort task-event emission, or the current provider rescue behavior. |
| `docs/architecture/roadmap-signals.md` | still accurate | The statement that the primary chat loop is queue-coupled still matches the code. |
| `docs/architecture/tech-debt-and-risks.md` | still accurate | The Redis/worker coupling risk and non-durable Compose Redis configuration still hold. |
| `docs/architecture/00-current-state.md` | unresolved ambiguity | The release-state claim is directionally consistent with the code, but this session could not fresh-prove the "without stuck turns" outcome because live runtime access was blocked. |

## Open questions / unknowns

- The worker path does not show a general replay or retry mechanism after `task.failed`; I did not find a separate requeue path in this repo scan.
- The route-level stale-lock recovery hooks are stubs today. It is unclear whether that is intentional placeholder code or an incomplete integration that should be wired to real Redis task-event and heartbeat reads.
- `health/chat` reports heartbeat age, but `ok` ignores that age. It is unclear whether operators are expected to treat a stale heartbeat as unhealthy or merely informational.
- I could not prove whether the live system currently consumes `/api/tasks/{task_id}/events` directly in the UI or primarily relies on the chat debug trace endpoint for progress visibility.
- I could not prove whether any external supervisor watches worker failures and re-enqueues tasks after the worker itself publishes `task.failed`.

## Decision-ready recommendations

- Immediate next investigation: run a real compose-backed completion probe with a known thread, capture `/api/tasks/{task_id}/events`, and verify whether the worker heartbeat changes and the turn lock is released. If the runtime remains inaccessible, the next investigation is Docker daemon access, not code changes.
- Likely robustness work: wire `_task_terminal_event` and `_chat_worker_heartbeat_age_seconds` to real data or remove the stale-lock recovery branch until it is real; consider making stale heartbeat age visible as an explicit readiness failure; surface task-event publish failures more loudly than a debug log.
- Do not change yet: do not redesign the queue architecture, add a synchronous fallback execution mode, or alter completion semantics or health endpoint behavior in response to this recon alone.
