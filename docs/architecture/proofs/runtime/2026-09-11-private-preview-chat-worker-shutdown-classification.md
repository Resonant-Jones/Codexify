# Private Preview chat-worker shutdown classification

Date of bounded reproduction: 2026-09-12 (UTC)  
Execution lane: `architecture-impact`  
Mode: `EXECUTE`  
Implementation, provider, chat-completion, user-content, and database mutation
authority: `NONE`

## Result

```text
RESULT=PASS
REASON=private_preview_chat_worker_shutdown_classified
SHUTDOWN_CLASSIFICATION=FORCED_SIGKILL_AFTER_GRACE_TIMEOUT
IMPLEMENTATION_REPAIR_REQUIRED=true
```

The canonical project-scoped `docker compose stop worker-chat` targeted the
worker with signal 15, targeted it with signal 9 approximately 3.02 seconds
later, and then recorded `die` with exit code `137`. Docker reported
`OOMKilled=false`. This proves that the current operator-stop path depends on a
forced kill; the successful Compose command exit does not make the worker
shutdown clean.

No second diagnostic start was authorized or necessary after this forced-kill
classification.

## Governing contracts and scope

This classification was evaluated against ADR-001 (queue acceptance), ADR-002
(request and provider state), ADR-003 (message and request identity), ADR-067
(derived Chroma retirement), and ADR-069 (supported runtime boundary), together
with the current-state, configuration/operations, named-volume recovery, and
Tester chat-worker readiness proofs named by the task.

`ADR_IMPACT=NO_NEW_ADR_DECISION`. This proof changes no accepted contract. It
classifies the current implementation against existing completion and
persistence invariants. No implementation, Compose, ADR, current-state, test,
queue, provider, or user-content change is part of this task.

## Git rebaseline and staged custody

The task began with `git fetch origin --prune` and the required identity,
ancestry, committed-delta, status, staged-path, and binary cached-diff checks.

```text
REFRESHED_START_HEAD=18d02cd992eaf6682768078ca5061ee19d2fb54b
LOCAL_MAIN_HEAD=18d02cd992eaf6682768078ca5061ee19d2fb54b
ORIGIN_MAIN=cb551de1866715ef421026203ffe2a87cec8aaca
DEV_LOG_ONLY_HEAD_ADVANCE=true
```

`0c10eef983b61744e68bd5a90200e15c8fb3ae35` is an ancestor of the refreshed
HEAD. The only committed path in
`0c10eef983b61744e68bd5a90200e15c8fb3ae35..HEAD` is the added
`docs/DEV_LOG/2026-09-12/Dev Log - 2026-09-12.md`; no implementation,
configuration, or runtime path intervened.

The refreshed pre-existing staged inventory was:

```text
REFRESHED_STAGED_PATHS=docs/DEV_LOG/2026-09-10/Dev Log - 2026-09-10.md; docs/DEV_LOG/2026-09-11/Dev Log - 2026-09-11.md; docs/DEV_LOG/2026-09-12/Dev Log - 2026-09-12.md
REFRESHED_STAGED_PATCH_SHA256=16b60addef1d24ac09a376d92bd06202c6eb0ceabb25fe395c53d04b6751fc3e
ORIGINAL_TWO_PATH_PATCH_SHA256=4e96d8c7155e327f03f15d311ddfbf03c32dc2d86129e184b4f7a6bb29b7560e
THIRD_STAGED_DEV_LOG_PATH=docs/DEV_LOG/2026-09-12/Dev Log - 2026-09-12.md
THIRD_STAGED_DEV_LOG_PATCH_SHA256=557c0a0973874ae3bca2cfbba7d17584a05341f26ec0875734a0351e58f0fa3a
```

Those paths and cached bytes are the frozen unrelated-work custody baseline.
No Dev Log path was restored, unstaged, restaged, edited, or included in this
task's commit.

## Original retained exit-137 evidence

Before the reproduction, the retained stopped container was inspected and its
evidence preserved:

```text
ORIGINAL_WORKER_CONTAINER_ID=01b3b553b64d8cc2335dfbb5f30cb4b28cf129c9d18555254b275b9583227b22
ORIGINAL_WORKER_EXIT_CODE=137
ORIGINAL_WORKER_OOM_KILLED=false
ORIGINAL_WORKER_ERROR=
ORIGINAL_WORKER_STARTED_AT=2026-09-12T03:21:08.364906668Z
ORIGINAL_WORKER_FINISHED_AT=2026-09-12T03:23:15.315543671Z
ORIGINAL_WORKER_RESTART_COUNT=0
ORIGINAL_CONFIG_STOP_SIGNAL=unset
ORIGINAL_CONFIG_STOP_TIMEOUT=unset
ORIGINAL_HOSTCONFIG_INIT=unset
```

The reproduction reused the existing Compose container only after those fields
were captured. The prior safe-start result remains `BLOCKED`; this document
does not rewrite it as a pass.

## Resolved Compose and PID posture

The exact Private Preview merge was rendered with the repository project
directory, `.env.private-preview`, project name, base Compose file, and Private
Preview overlay. Only the worker's non-environment fields were emitted.

```text
WORKER_ENTRYPOINT=["python"]
WORKER_COMMAND=["-m","guardian.workers.chat_worker"]
WORKER_INIT=default false (not explicitly configured)
WORKER_STOP_SIGNAL=default SIGTERM (not explicitly configured)
WORKER_STOP_GRACE_PERIOD=default/unset in the rendered service
WORKER_RUNTIME_PATH=python
WORKER_RUNTIME_ARGS=["-m","guardian.workers.chat_worker"]
```

The Python interpreter is container PID 1; there is no configured init process
between Docker and the worker. The rendered service does not explicitly set an
init process, stop signal, or stop grace period. The diagnostic event gap
provides the observed effective stop wait: 3.016628502 seconds from signal 15
to signal 9.

## Worker shutdown and queue-loop inspection

`guardian/workers/chat_worker.py` contains no signal registration, SIGTERM or
SIGINT handler, shutdown event/state, `KeyboardInterrupt` handling, or
`atexit`-based cleanup.

```text
EXPLICIT_SIGTERM_HANDLER_PRESENT=false
EXPLICIT_SIGINT_HANDLER_PRESENT=false
EXPLICIT_GRACEFUL_SHUTDOWN_STATE_PRESENT=false
HEARTBEAT_BEFORE_DEQUEUE=true
DEQUEUE_BLOCK_TIMEOUT_SECONDS=5
```

The main loop writes the idle heartbeat and then calls
`dequeue(QUEUE_NAME, block=True, timeout=5)`. The Redis queue implementation
uses `BRPOP` with that timeout. Provider/completion execution occurs only after
a non-empty payload is returned and accepted as a `ChatCompletionTask`; the
diagnostic queue remained empty.

## Accepted-task safety consequence

The current worker owns material accepted-task lifecycle operations:

- it publishes queued/running and terminal task events;
- it invokes the completion path and persists the assistant message;
- it publishes `task.completed`, `task.failed`, or cancellation evidence; and
- its `_run_chat_task` `finally` block conditionally releases the turn lock.

SIGKILL cannot execute Python exception handling or `finally` cleanup. A
SIGKILL after dequeue while `_run_chat_task` is in flight can therefore stop the
process before assistant persistence or terminal event publication, or between
those operations, and can bypass the worker-owned turn-lock release.

```text
FORCED_KILL_CAN_INTERRUPT_ACCEPTED_TASK_LIFECYCLE=true
FORCED_KILL_CAN_BYPASS_WORKER_CLEANUP=true
```

This is a bounded consequence statement about the current code path. No task
was placed in flight to demonstrate data loss.

## Bounded live reproduction

Before start, the canonical PostgreSQL state was
`7e5a5fccf253`, 72 chat threads, and 805 chat messages. The external
`codexify_private_preview_chroma` local named volume existed. Application
writers were stopped, the reconciliation LaunchAgent was absent, and a
read-only process check found no Private Preview reconciliation process.

The normal chat queue was checked immediately before backend start, before
worker start, and immediately before stop; each observation was zero. The
minimal existing `backend` prerequisite was started with `--no-build`; the
worker was then started once with the canonical merged Compose project and
`--no-deps`. Frontend, origin, embedding workers, ingestion, and backfill were
not started.

```text
DIAGNOSTIC_WORKER_START_ATTEMPTS=1
DIAGNOSTIC_WORKER_RESTART_COUNT=0
DIAGNOSTIC_WORKER_STARTED_AT=2026-09-12T04:00:08.054769043Z
DIAGNOSTIC_HEARTBEAT_STATUS=idle
DIAGNOSTIC_HEARTBEAT_QUEUE=codexify:queue:chat
CHAT_QUEUE_DEPTH_BEFORE=0
DIAGNOSTIC_QUEUE_DEPTH=0
```

No chat payload was submitted. The backend's existing startup path logged its
ordinary `type=warmup` system task creation, but the warmup worker remained
stopped; that separate queue was not consumed or altered by this task. It was
not a chat completion, did not reach `worker-chat`, and caused no provider
invocation or chat-message creation.

Before the canonical stop, a bounded event reader was started for the worker
container. Its first window elapsed before the stop command was issued. A
second bounded, read-only query of the Docker daemon's retained events for the
exact stop interval recovered the following timestamped lifecycle evidence:

```text
1789185698230719084|container|kill|signal=15|exitCode=
1789185701247352586|container|kill|signal=9|exitCode=
1789185701368213253|container|die|signal=|exitCode=137
```

The reproduction command was the project-scoped equivalent of:

```text
docker compose \
  --project-directory /Volumes/Dev_SSD/Codexify-main \
  --env-file /Volumes/Dev_SSD/Codexify-main/.env.private-preview \
  -p codexify_private_preview \
  -f /Volumes/Dev_SSD/Codexify-main/docker-compose.yml \
  -f /Volumes/Dev_SSD/Codexify-main/docker-compose.private-preview.yml \
  stop worker-chat
```

```text
STOP_STARTED_AT=2026-09-12T04:01:38Z
STOP_FINISHED_AT=2026-09-12T04:01:41Z
COMPOSE_STOP_EXIT=0
COMPOSE_STOP_DURATION_SECONDS=3
REPRO_WORKER_EXIT_CODE=137
REPRO_WORKER_OOM_KILLED=false
REPRO_WORKER_FINISHED_AT=2026-09-12T04:01:41.274284169Z
REPRO_SIGTERM_EVENT=true
REPRO_SIGKILL_EVENT=true
REPRO_OOM_EVENT=false
```

The event sequence—not exit 137 alone—is the causal proof. Signal 15 followed
by signal 9 under the canonical stop, with no OOM event and
`OOMKilled=false`, meets the forced-SIGKILL classification rule.

## No-work and preservation proof

The worker log for its diagnostic lifetime contains only dependency
initialization and the idle-worker startup line. It contains no accepted chat
task, terminal task event, completion execution, or provider-attempt evidence.
PostgreSQL counts remained identical after shutdown.

```text
CHAT_QUEUE_DEPTH_AFTER=0
CHAT_TASK_EXECUTION_COUNT=0
PROVIDER_BACKED_INVOCATION_COUNT=0
TASK_CREATED_MESSAGE_COUNT=0
LIVE_ALEMBIC_REVISION=7e5a5fccf253
LIVE_THREAD_COUNT=72
LIVE_MESSAGE_COUNT=805
```

After both worker and backend were stopped, the named volume was mounted
read-only into an isolated, network-disabled container. SQLite opened in
read-only URI mode and returned `ok` from `PRAGMA integrity_check`.

```text
PRIVATE_PREVIEW_NAMED_VOLUME_PRESENT=true
FRESH_CHROMA_SQLITE_EXISTS=true
FRESH_CHROMA_SQLITE_BYTES=253952
FRESH_CHROMA_SQLITE_SHA256=47573f206329cb54d775562c14349a2e1541522b56c5b9b34fc8b05e92e4efac
FRESH_CHROMA_SQLITE_INTEGRITY=ok
HISTORICAL_CHROMA_PANIC_COUNT=0
SQLITE_READONLY_DBMOVED_COUNT=0
```

This is integrity-only evidence. No rebuild, reindex, semantic retrieval check,
or historical-content import was performed or claimed.

## Maintenance boundary and follow-through

The diagnostic worker and backend were stopped through canonical Compose. The
worker heartbeat was allowed to expire naturally and was not cleared. Redis,
PostgreSQL, and Neo4j infrastructure remain available; every application writer
is stopped or unstarted. The recovered named volume was not removed.

```text
worker-chat=stopped (exit 137)
backend=stopped (exit 0)
PRIVATE_PREVIEW_WRITERS_QUIESCED=true
PRIVATE_PREVIEW_RECONCILIATION_SUSPENDED=true
```

Current-state remains unchanged because its statement that worker safe-start is
not yet proven remains accurate.

Exactly one next task is recommended:

```text
NEXT_RECOMMENDED_TASK_TITLE=Make worker-chat terminate gracefully under operator stop
NEXT_RECOMMENDED_WORKFLOW_LANE=architecture-impact
```

That separate task must define and prove graceful termination without assuming
that a successful Compose command is sufficient lifecycle evidence.

## Validation and commit receipt

The following scoped checks are required after this file is complete:

```text
python3 scripts/validate_docs.py
.venv/bin/python scripts/validate_docs.py
git diff --check -- docs/architecture/proofs/runtime/2026-09-11-private-preview-chat-worker-shutdown-classification.md
```

```text
DOCS_VALIDATION=PASS
VENV_DOCS_VALIDATION=PASS
DIFF_CHECK=PASS
```

Both validators reported that required architecture docs, README links, and
source headings were verified. The scoped diff check emitted no errors. The
exact one-file commit receipt is recorded in the task closeout. No broad runtime
regression suite applies to this classification-only proof.
