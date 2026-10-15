# Chat worker activity follows owned lifecycle cleanup

Date: 2026-10-03. Classification: AUTHORIZED_IMPLEMENTATION.
Architecture-impact lane; priority P1; owner Codex.
Evaluated source: af9e6a72a plus this scoped worker change.
Worker SHA-256: b965e95921c5a20beb7e4032fa8f9bc05c270d9541e48e4a1027e4fb18eb2fde.
Full supported qualification remains HOLD.

## Atomic Task Spec and authority

This change belongs in guardian/workers/chat_worker.py.
Make the existing activity label reflect chat lifecycles owned by this process,
including executor-pending, concurrently running and inline cancellation work.
Retain activity until the existing worker lifecycle has returned after terminal
persistence and lock cleanup. Bound the change to the worker, its new regression
file and this receipt.

Authority: the explicit ordinary-chat reliability Goal, Codex Development Operator
protocol, Chat Runtime Contract, accepted ADR-087 terminal cleanup boundary and
[the completed publisher/consumer trace](./2026-10-03-chat-heartbeat-activity-gap.md).
That trace reproduced idle publication while a native executor held chat work.
The existing publisher already labels admitted work active; the repair retains
that label through the same owned lifecycle. No new architecture, protocol token,
task disposition, freshness meaning, recovery or lock-release authority is added.

Preserve queue acceptance, task parsing, cancellation priority, immutable accepted
deadlines, provider authority, message/request/attempt identity, worker persistence,
terminal events and owner-guarded cleanup. No main mutation, merge, push, deployment,
memory update or release promotion is included.

## Change and ownership

run_forever now keeps a process-local count guarded by a short bookkeeping lock.
It registers a valid dequeued chat task before pre-dispatch cancellation
observation. Both inline and executor work invoke the same existing
_run_chat_task through a wrapper whose finally releases the count only after that
entire lifecycle returns or raises. Failed pre-dispatch/submission handoff also
clears its bookkeeping while propagating the existing error.

The dispatcher's next sample is active while any lifecycle remains owned and
idle after all owned work has finished. Executor-pending work remains active;
one completed or inline-cancelled lifecycle cannot clear another one's activity.
The wrapper adds no provider invocation, message persistence, queue operation,
task event, cancellation action or application lock manipulation.

The existing Redis heartbeat key, payload fields, starting/idle/active vocabulary,
TTL, timestamp classifier and dequeue cadence are unchanged. Sampling is not an
instantaneous completion signal. The repair does not add a separate publisher
thread, change inline-path heartbeat freshness or implement graceful drain,
active-worker-loss recovery or orphan/retry policy.

## Focused and regression proof

Seven new native-executor/inline checks passed:
- successful and failed lifecycles remain active during held terminal cleanup;
- one-slot executor-pending and two-slot overlapping work preserve activity as one
  lifecycle finishes, then return to idle when all work has finished;
- inline cancellation executes ahead of a busy completion slot without clearing
  the other owned lifecycle;
- pre-dispatch and submission errors propagate without dispatching extra work or
  leaving activity in the next worker invocation.

The host regression command used PYTHONPATH=. and the repository Python:
python -m pytest -o addopts= -q
 tests/workers/test_chat_worker_heartbeat_activity.py
 tests/workers/test_chat_worker_queued_cancellation.py
 tests/workers/test_chat_worker_queue_deadline.py
 tests/workers/test_chat_worker_rescue_deadline.py
 guardian/tests/workers/test_chat_worker_dequeue_resilience.py
 tests/queue/test_chat_redis_deadline.py

It passed **64 checks**, zero failures/errors/skips. The preliminary new-file
run passed seven checks separately. The copied worker-container suite passed
**14 checks**, zero failures/errors/skips: new activity, queued cancellation,
dequeue resilience and the preceding health/acceptance classifier invariance
controls. It deliberately deselected the preceding probe that expected the
old idle-overwrite bug. XML names/counts and source hashes were independently
checked; the old bug's passing characterization remains in its original proof
root, not a passing compatibility test for the repaired behavior.

py_compile passed for the changed worker and new test file. Ruff passed for the
new tests. Full-worker Ruff **failed** with two F601 duplicate-key findings,
model_selection and retrieval_provenance, in the earlier completion payload.
A separately saved HEAD baseline produced the identical findings; this diff
adds no dictionary keys. Those existing findings were left outside this Task.
They are not hidden by the passing focused/regression checks.
git diff --check passed. No validation hook was bypassed.

## Retained runtime and cleanup

Preflight established empty chat queue, no turn locks and fresh idle heartbeat.
Exactly guardian/workers/chat_worker.py differed from the retained mounted
snapshot; only that file was refreshed. Idle backend and worker were restarted
once. All **1,136 tracked Guardian/backend Python files** then matched checkout,
source snapshot and both containers. Health reported ok. PostgreSQL migration
remained d4c69e03a712.

After the controlled suite, independent SQL and durable receipt readback retained
thread 32 messages 60/61 and its one successful completion. No model was invoked
by this repair Task. Evaluation queue stayed 29. System queue grew 9 to 10 after
restart; content-free metadata identified the newest item as warmup with origin
startup. The queue and warmup item were preserved. Chat queue remained empty,
turn locks absent, and heartbeat idle with positive TTL.

The first final-artifact validator incorrectly required system depth to remain 9.
It stopped after owned cleanup had already completed. The observed startup
warmup, original validator and error record were retained. The corrected validator
checked the actual depth of 10, preserved that item and verified the already
removed suite root instead of repeating cleanup. Nine copied container files had
been hash-checked before removal; XML was exported and the runner terminal first.

Evidence: /private/tmp/codexify-chat-heartbeat-activity-af9e6a72a-20261003/
contains Task Spec, native-executor tests, exact host/worker logs and XML,
baseline/changed Ruff diagnostics, refresh/idle custody, source matrices,
health/migration/readback, startup metadata, validators and cleanup receipts.
Previous proof roots were preserved; credentials were not printed or committed.

## Follow-through and limits

Files changed are the worker, new activity regression file and this receipt.
ADR impact is alignment only; no current-state promotion or memory write.
The next atomic Task must run a fresh ordinary browser completion/reload against
this repaired source and compare active heartbeat samples with the same task's
durable/runtime lifecycle. The preceding browser success evaluated the earlier
Redis repair; readback preservation is not new browser qualification.

The Goal remains active. Inline heartbeat freshness, remaining accepted-child
bounds, terminal-reserve exhaustion/acknowledgement ambiguity, active-worker
drain/loss recovery and newer-main integration remain unfinished. No full
failure/recovery or release qualification is claimed.
