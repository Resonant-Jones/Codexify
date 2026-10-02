# Current-main queued chat cancellation cleanup

Date: 2026-10-02. Source baseline: `d384fe74ea50ca6493cf5842e5990c62bfbfc07e`.
Branch: `main`. Goal: ordinary supported chat reliability and truthful state.
Authority: active human Goal; Codex Development Operator protocol, Level 0.
Task classification: proof before repair, architecture-impact, aligned with
ADR-001 acceptance, ADR-003 identity, chat-runtime cancellation, and canonical
turn-lock ownership. No architecture decision, release claim, or support change.

## Causal proof and repair

The baseline `run_forever` cancellation shortcut published `task.cancelled`,
cleared the cancellation marker, then continued without calling `_run_chat_task`.
It bypassed that function's owner-guarded turn-lock cleanup in `finally`.

Two regression cases failed on the frozen baseline:

- A cancelled task retained its owned lock and prevented a subsequent acquisition.
- A successor lock remained intact, but the cancellation event lacked `thread_id`.

The repair removes the shortcut. All dequeued chat tasks enter the existing
worker lifecycle. Cancellation of an unanswered task reaches its existing
terminal branch, preserves thread/turn correlation, and runs owner-guarded cleanup.
Existing durable assistant deduplication still takes precedence. No automatic
retry, generation, assistant persistence, token, schema, or shutdown policy is added.

## Verification

Runner from repository root:
`PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -q`.

Scoped green suite: **21 passed**, exit 0:

- `tests/workers/test_chat_worker_queued_cancellation.py`
- `tests/queue/test_turn_lock.py`
- `tests/core/test_turn_lock_recovery.py`
- `guardian/tests/workers/test_chat_worker_dequeue_resilience.py`
- `tests/workers/test_chat_worker_lifecycle_events.py`

The initially declared neighboring provider-resolution suite was also run.
Including it: **26 passed, 6 failed**, exit 1. All six failures were independently
reproduced with the baseline worker loop; none was introduced by this repair.
Two synthetic routing tests encounter ambient egress-policy validation; four
Persona tests use a legacy lock stub that rejects `turn_id`. These failures are
not hidden by the green scoped suite and require a separate test-fixture task.

Baseline comparison used an external pytest plugin to load only `run_forever`
from `git show HEAD:guardian/workers/chat_worker.py` before collection. The
baseline suite produced **20 passed, 8 failed**: the same six neighboring failures
plus both cancellation regression cases. Repaired evidence covers those same
28 cases and four additional dequeue/lifecycle cases.

`git diff --check`: passed.

## Controlled actual-Redis evidence

A separate Python process inside the owned
`codexify_chat_proof_f091_20261002-worker-chat-1` container imported the repaired
mounted source and ran the actual `run_forever` with its real ThreadPoolExecutor.
The worker-source SHA-256 matched the host exactly:
`f6c34ee38993ccad59e898eb8102fa985fc5fab2565b547e90fa761926bf77c5`.

This used real Redis database 15 with unique probe queue/lock/task identities.
Canonical enqueue, blocking dequeue, cancellation-set operations, lock SET NX EX,
and atomic Lua compare-and-delete ran against Redis. Both own-lock and
successor-lock cases passed: one correlated cancellation, cancellation marker
cleared, queue empty, own lock released and next acquisition allowed, successor
lock preserved and next acquisition rejected. Only probe-owned keys were cleaned.
No services restarted, no application queue consumed, and no data/volumes removed.

Initialization, heartbeat, assistant lookup, and event delivery were controlled
seams. Completion work raised if called. This is controlled worker/Redis evidence,
not live API acceptance, PostgreSQL transcript, frontend receipt, provider,
or complete supported-Compose qualification. The container image retains its
older image identity and is not a newly frozen current-main runtime bundle.

## Artifacts and limits

External root:
`/private/tmp/codexify-main-queued-cancellation-d384fe74e-20261002`.
Artifacts: `baseline_worker_plugin.py`, `baseline.xml`, `baseline.log`,
`repaired.xml`, `repaired.log`, `scoped.xml`, `scoped.log`, `redis_probe.py`,
`redis_probe.json`, `redis_probe.log`. Artifacts are local and not published.

Current truth remains HOLD. Fresh full current-tip browser/API/PostgreSQL proof,
explicit-model failure, stream ownership, finite child execution, bounded database
work, terminal recovery, and safe restart/drain remain to be evaluated. The active
Goal is incomplete. Earlier separate-branch proof is not current-main proof.

Documentation follow-through: this receipt only. No ADR/current-state update.
KB recommendation: cancellation terminal publication is insufficient proof of
cleanup; verify owned-lock release and successor ownership independently.
