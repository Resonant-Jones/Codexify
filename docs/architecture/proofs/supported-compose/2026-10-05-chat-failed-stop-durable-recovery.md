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

## Completed-task proof reinspection — 2026-10-06

Evaluated clean checkout `07157efff91d22f57f77b9c5d4f399bc383c8314`, branch
`codex/chat-postgres-terminal-deadline-20261003`, exclusively in
`/Volumes/Dev_SSD/offload/codex/worktrees/7d94/Codexify-main`.
This is a bounded evidence audit, not a new successful runtime qualification.
ADR-003/038/087/091 and the release HOLD remain unchanged.

Both `a75be300d75c83daa6edd52884fb11fe9a3d3f4f` and
`2c159c28c0c0f0d8ed9a4c1e039762ed88eea25e` are ancestors of this HEAD.
`git diff --exit-code bbf319376ca8bde42e7ff94cbf1f3d77194a9391 HEAD -- guardian`
passed: the recorded backend recovery source has not changed. Inspection of
`chat_list_tasks`, `reconcile_chat_attempt_receipts`, and
`_recover_orphaned_turn_lock` confirms that receipt reconciliation uses the
durable assistant link and matching lock cleanup without enqueueing inference.
This is code-path evidence, not a provider execution count.

The existing records report these original identity relationships:

| Thread | Authored message | Request | Task | Turn | Assistant |
| --- | --- | --- | --- | --- | --- |
| 45 | 85 | `req_52c56dad349c4649b6b63b399eec64f0` | `62ac1bd4-5f1d-40e9-8edf-1a82ce514145` | `bab621ea-f239-4ba3-ad95-a8308440939b` | 86 |
| 47 | 90 | `req_294fb929c01a47bda422956a99e0b722` | `9f4e0ff5-b000-43d3-bd0e-e5dff0eb11b4` | `06f11e48-8bab-444a-b0b7-ad645cf55e22` | 91 |

The historical artifacts report one assistant for each completed request,
unchanged authored identity, terminal receipt/transcript agreement after reload,
and no resubmission. They cover completion while the backend was already down,
followed by backend recovery. For thread 47, backend OOM occurred at
`2026-10-05T04:48:49.203680128Z`, before completion at `04:49:07.448766Z`.
The later database/Redis service transition is described above, but its raw
before/after custody and provider execution evidence are no longer available for
inspection. Consequently this audit cannot independently confirm all acceptance
criteria for completion-before-interruption and recovery without provider replay.

Fresh runtime verification is **BLOCKED** by the observed environment:

- `docker ps -a --filter label=com.docker.compose.project=codexify_chat_branch_proof_896387ad2 --format '{{.ID}} {{.Names}} {{.Status}}'`
  returned only database `6ed41da0c85c` and Redis `cbd3996632fe`. The project's
  backend and worker containers are absent; no supported API/browser recovery
  path is available in that retained project.
- Read-only `docker inspect 6ed41da0c85c cbd3996632fe` using selected state,
  image, Compose ownership, and mount fields confirmed the database is exited
  (255), `OOMKilled=false`, finished `2026-10-05T18:13:36.518061585Z`, still
  referencing `codexify_chat_branch_proof_896387ad2_pg_data`. Redis is running,
  started `2026-10-06T01:46:06.831617379Z`. No lifecycle cause is inferred.
- Neither `/private/tmp/codexify-chat-backend-recovery-f4de1af01-20261005/`
  nor `/private/tmp/codexify-chat-failed-stop-f4e0fba5e-20261005/` exists now.
  Their scripts, before/after Postgres snapshots, events and browser captures
  cannot be independently revalidated. The surviving candidate-runtime
  directory does not contain these proof packets.

No completion, cancellation, provider call, restart, recreation, migration,
or data mutation was requested in this audit. No live API/Postgres readback or
new provider-log count was obtained. Historical no-replay/one-assistant claims
remain attributed to their evaluated records; fresh absence of replay,
duplicates, ghost turns and stale in-flight state is unverified. Other running
projects were not substituted for this Goal runtime.

Validation from the current repository root:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest tests/core/test_turn_lock_recovery.py tests/test_thread_task_receipts.py tests/core/test_chat_completion_attempt_persistence.py -q -s
PASS (exit 0)

/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest guardian/tests/workers/test_chat_worker_completion_semantics.py -q
FAIL (exit 1): 9 failed, 15 passed
```

The first combined invocation additionally selected
`guardian/tests/workers/test_chat_worker_completion_semantics.py` with `-q`;
it was interrupted during sentence-transformers/torchvision import before test
execution (exit 130). This was not an assertion failure. The separate worker
run reached all 24 cases; nine fail in shared fixture setup because it patches
`chat_worker.release_turn_lock`, which the current module no longer exposes.
Those cases include duplicate suppression and post-persistence recovery, so
they cannot count as passing coverage. This inherited fixture mismatch is not
evidence of a live recovery defect; test repair is deferred because this task
authorizes implementation repair only when a recovery defect prevents the proof.
The default pytest configuration ignores `guardian/tests`; the explicit command
above exercised that additional suite. No test or runtime source was changed.

`/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py`
and `git diff --check` passed. The proof-note update remains uncommitted because
the task's commit condition requires passing validation; the worker failures
are not hidden by a documentation commit.

No implementation defect or repair is established. This fresh acceptance gate
must not be marked passed or used to advance Goal 1 past completed-task recovery.
The next bounded prerequisite is restoration of a source-qualified Goal runtime
and proof custody, then the missing completion-before-interruption observation
with before/after provider execution evidence. Full restart/shutdown qualification,
current-main integration and broader release work remain deferred. This note
does not change `00-current-state.md` or widen any release claim.
