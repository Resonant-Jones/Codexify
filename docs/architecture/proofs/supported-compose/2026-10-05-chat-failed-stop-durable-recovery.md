# Failed-Stop durable completion recovered after backend restart

Level 0 architecture-impact evidence under ADR-003/038/087/091. Candidate checkout `844df8741f4ac18f73155b6de7ce12413e787e5a`; backend/worker image remains `bbf319376ca8bde42e7ff94cbf1f3d77194a9391`. No product, ADR, protocol-token, or release-claim change. Supported Compose release status remains HOLD.

## Task Spec

Reconcile the already completed failed-Stop request from its durable PostgreSQL message link and retained task-event evidence. Do not replay the request. Prove the canonical receipt and thread transcript after backend recovery and browser reload. Preserve proof data, volumes, active runtimes, and unrelated stacks.

## Durable identity and completion

The existing accepted attempt is request `req_294fb929c01a47bda422956a99e0b722`, task `9f4e0ff5-b000-43d3-bd0e-e5dff0eb11b4`, thread `47`, turn `06f11e48-8bab-444a-b0b7-ad645cf55e22`, accepted at `2026-10-05T04:47:42.354299Z`. Its PostgreSQL row links `completed_message_id=91`; `terminal_event_type` is null.

Before the Redis service transition, the retained stream snapshot recorded 52 events for this task and exactly one terminal event: `task.completed` at `2026-10-05T04:49:07.448766Z`. It recorded no `task.failed` or `task.cancelled` terminal event. The authored message is 90; assistant message 91 is persisted in `chat_messages` for thread 47. The existing failure receipt documents that the worker produced this completion while the backend was OOM-killed; this recovery did not submit another completion or cancellation.

The canonical read-only `GET /api/chat/threads/47/tasks` response returned the same request, task, thread, turn, accepted time, and message ID, with `state=terminal`, `event_type=task.completed`, and `reason=durable_completion_recorded`. `GET /api/chat/47/messages` returned messages 90 and 91. This is the supported durable fallback: the recovered receipt used the persisted assistant link when the Redis stream was unavailable.

The Redis stream now has length 0 after its service restart; the chat queue is empty and no `turn_lock:*` keys remain. The earlier event snapshot in the failed-Stop evidence directory remains the evidence for the original `task.completed` publication. Redis stream retention across this service transition is not proven.

## Runtime recovery and custody

No verified-idle obsolete proof resource was stopped. The bootstrap proof Redis instances still held `eval` and `system` work; the older chat proof Redis had an `eval` backlog and blocked clients. Private Preview and active workers remained untouched. No volumes or container data were removed.

The Goal PostgreSQL container had exited cleanly with code 0 and still referenced volume `codexify_chat_branch_proof_896387ad2_pg_data` on its existing Compose network. It was started in place at `2026-10-05T10:12:19.447964Z`; health became healthy and a read-only `SELECT 1` succeeded. The same backend container was started at `2026-10-05T10:14:38.500376Z`; `/health` returned HTTP 200 and Docker reported healthy. Neither container identity changed, and restart counters remained zero. No Compose recreation or migration was run.

An earlier backend start at `10:05Z` timed out waiting for PostgreSQL because the `db` container was stopped; its log reported `failed to resolve host 'db'` and it exited 1 with `OOMKilled=false`. At `09:53Z`, inspection had also shown the database exit 0, Neo4j exit 137, and an earlier backend exit 137 with `OOMKilled=false`. No Docker lifecycle event identified the actor or cause. These are separate from the previously captured backend OOM event. Neo4j remains stopped; the live receipt and transcript GETs succeeded with PostgreSQL and Redis available.

## Browser reload

The exact private proof frontend was served on `127.0.0.1:5183` with its one-use Stop-503 fault disarmed. Playwright selected `/chat/47`, then directly reloaded that route. After history loading completed, the accessible snapshot showed the authored message and assistant response `FAILED STOP OBSERVATION OK F4E0FBA5E 20261005`. The view had no active Working or Stop state; the empty composer had Send disabled.

The UI also showed one earlier-response deadline notice. The thread receipt page contains a separate earlier attempt, request `req_0a35c4af64b54a8ba7d7dcfffac172a5`, terminal `task.failed` with `CHAT_ACCEPTED_TASK_ORPHANED` and no completed message. The notice is consistent with that earlier failed attempt; the current request remains completed by its own receipt and message 91.

## Remaining gates

The native 503 sample still did not prove visibility of its Stop-specific diagnostic while the response remained active. Source inspection explains the gap: `useInferenceRequestState` sets `CANCEL_FAILED`, while `InferenceStatusBanner` hides active-state details unless they match its lifecycle-progress text pattern. A separate atomic frontend task is required to render this existing diagnostic during active observation, followed by bounded proof.

This recovery is branch-local evidence. Full supported-Compose restart and graceful-shutdown qualification, current-main reconciliation, OOM root-cause attribution, and release readiness remain open. No push, merge, deploy, or memory update occurred.
