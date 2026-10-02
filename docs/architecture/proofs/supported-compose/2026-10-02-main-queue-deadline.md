# Current-main queued chat deadline enforcement

Date: 2026-10-02. Baseline: `529f9e70983aedacbdc74c7b757a38fc3620f47e`.
Branch: `main`. Authority: active ordinary-chat reliability Goal and Development
Operator Level 0. Architecture-impact proof before repair, aligned with existing
ADR-001/002/003/038/087 and canonical queue/terminal/chat-runtime boundaries.
No new ADR, budget, error token, or release claim.

## Causal proof

The accepted-task deadline envelope was serialized and validated on current
main, but `_run_chat_task` never consulted it before shared completion entry.
A deterministic probe roundtripped actual canonical queue serialization, then
intercepted completion entry with a BaseException sentinel. This avoids real
context/provider/tool/persistence work while proving whether it was admitted.

Baseline: **three failed, six passed**. Acceptance ages 720, 721, and 800 seconds
all reached completion entry, violating the exact work boundary, terminal
reserve, and already-late-dequeue no-work invariant. Future and legacy tasks,
both existing durable-deduplication paths, and explicit cancellation controls
passed. Owner cleanup was captured independently.

Earlier separate-branch repairs were inspected as context, not treated as
current-main evidence or merged wholesale. The regression was rerun here.

## Repair and invariants

Immediately before shared completion entry, validate the already-frozen
snapshot and compare the aware UTC clock with `work_deadline_at`. At or beyond
the boundary, route the existing `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` error
through the existing `task.failed`/`completion.error` handling and owner-guarded
finally cleanup. Failure truth records accepted but not attempted/executed/
completed work and no fallback. No provider outage is assigned by the worker.

Preserve prior durable-completion lookup and explicit cancellation handling.
Never refresh acceptance or mint a replacement work budget. Future and legacy
absent-envelope tasks keep existing execution paths. Malformed in-memory
snapshots fail closed without being repaired or mislabeled as deadline expiry;
canonical decoding independently rejects malformed queue envelopes.

Tests verify request, task, attempt, turn, and latest authored-message
correlation, unchanged deadline fields, exact-boundary rejection, and no
completion/cancellation or provider runtime-status fabrication. The completion
sentinel establishes zero entry into downstream context/provider/tool/assistant
persistence work; controlled deduplication lookups remain earlier in the path.

## Declared validation

From repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/workers/test_chat_worker_queue_deadline.py \
  tests/tasks/test_chat_completion_deadline.py \
  tests/core/test_chat_completion_enqueue_service.py \
  tests/core/test_completion_terminal_integrity.py \
  tests/test_chat_worker_turn_integrity.py \
  tests/workers/test_chat_worker_queued_cancellation.py \
  tests/workers/test_chat_worker_explicit_model_authority.py \
  tests/workers/test_chat_worker_lifecycle_events.py \
  guardian/tests/workers/test_chat_worker_completion_semantics.py

/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m ruff check \
  guardian/workers/chat_worker.py tests/workers/test_chat_worker_queue_deadline.py

git diff --check
```

Pytest: **118 passed**, exit 0. Includes all 11 queue-deadline cases and adjacent
acceptance, immutable serialization, terminal integrity, cancellation, turn
ownership, lifecycle, explicit-model authority, and persistence semantics.
Diff check passed.

Combined scoped Ruff: **failed**, exit 1, on two F601 duplicate dictionary keys
already present in the worker (`model_selection`, `retrieval_provenance`). The
unmodified baseline was independently linted via stdin with the original worker
filename and reproduced exactly those two errors. No unrelated key deletion
was included. New-test-only Ruff: passed, exit 0. The existing pyproject
configuration deprecation warning was also emitted. No full lint success is
claimed.

## Controlled real Redis worker-loop proof

Run a separate subprocess in this Goal's existing owned backend container,
checking its imported worker source SHA against the current host source before
any Redis mutation. Use Redis database 15, a fresh unique queue/thread/task/
attempt/turn for each case, actual canonical enqueue/dequeue, the real worker
loop and ThreadPoolExecutor, and canonical Redis lock compare-and-delete.

Four cases crossed acceptance ages 721/800 seconds with own/successor lock
ownership. Each produced exactly one correlated deadline failure, preserved
serialized timestamps, made zero completion calls, emptied its unique queue,
and released its own lock or preserved the successor lock. Temporary keys were
removed in finally cleanup. No service restart, shared queue, provider, or
PostgreSQL mutation was performed.

Current worker source SHA-256:
`af9ed79cb21738a5493c9a2330c74d8e390579e83dd8ae4e3e685587d4f6a984`.

Evidence class: **controlled-real-Redis-worker-loop**. Deduplication/database
lookups, completion execution, and event/live publication were controlled;
terminal payloads were captured rather than durably persisted or rendered.
The resident daemon and existing frontend runtime remain tied to their older
source. This is not fresh full-stack qualification of main.

Artifacts: `/private/tmp/codexify-main-queue-deadline-529f9e709-20261002`, including
`before.xml/log`, `after.xml/log`, `baseline-ruff.log`, `test-ruff.log`, and
`redis_probe.py/json/log`.

## Closeout and remaining work

Files changed: worker, queue-deadline regression suite, this receipt.
Documentation follow-through: scoped receipt only; current-state and ADRs
unchanged. No push, merge, deployment, or runtime restart.

This guard proves queue-to-work admission only. It does not interrupt continuing
provider frames or blocked child calls, bound PostgreSQL/events/cleanup, prove
on-time terminalization after an already-late dequeue, establish historical
completion time in controlled deduplication, or qualify graceful stop/restart.
Legacy behavior is compatibility evidence, not an enforced envelope.

Path re-evaluation also found that frontend generic task-failure presentation
still calls failures provider errors even when the canonical deadline code
records no provider request. That needs a separate bounded UI proof. Fresh
current-tip end-to-end success, important live failure/retry cases, immutable
in-flight child bounds, and safe shutdown/recovery remain outstanding. Current
release posture remains HOLD; the full Goal is active and incomplete.

KB recommendation: immutable acceptance-time queue age must be checked at the
actual execution boundary; passing envelope serialization tests is not worker
enforcement or complete deadline qualification.
