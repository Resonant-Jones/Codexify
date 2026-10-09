# Durable post-terminal chat orphan fence

## Authority and scope

Direct human authorization in the active ordinary-chat reliability Goal permits
reconciliation after the original non-sliding terminal deadline. Durable assistant
completion wins; existing terminal truth wins; otherwise an exact accepted attempt
may become an explicit orphan. This Level 0 EXECUTE → PROOF Task implements the
PostgreSQL arbitration prerequisite only. It follows ADR-001/003/087/091 and the
existing durable attempt/message authority. No worker generation or new lease
identity is introduced. The frozen starting commit is `b09744eb7` on
`codex/chat-postgres-terminal-deadline-20261003`.

The accepted Task Spec and raw evidence are retained at
`/private/tmp/codexify-chat-orphan-fence-b09744eb7-20261004/`. Main remains
`0163521312ef767c0884654e70094ae7b44a5eec` with its pre-existing staged Dev Log
deletion. No main mutation, push, merge, deployment, host installation, or memory
write occurred.

## Change and durable behavior

- `guardian/core/db.py` reconciles exact request/task/thread/turn identity under
  `SELECT FOR UPDATE` on the existing attempt. A linked assistant must really be
  an assistant in that thread. Existing completion or failure/cancellation wins.
- An unresolved attempt requires durable queue acceptance confirmation and a
  valid original immutable deadline snapshot. The clock is read after acquiring
  the row lock. Before its terminal deadline no orphan is written; at or after
  that boundary `task.failed` and a distinct `CHAT_ACCEPTED_TASK_ORPHANED` outcome
  commit together. `reconciled_at` is the reconciliation observation, never a
  claimed worker-death timestamp. The original envelope and identity do not slide.
- The helper returns only after transaction commit acknowledgement. Failure of
  persistence propagates; it cannot return a confirmed recovery. Its private
  result retains the existing matching lock capability for a later controller.
  Public attempt projections expose the terminal detail, never that capability.
- Migration `f1a6d83b9024`, directly after `e8a9b03d6712`, adds nullable
  `terminal_outcome`. Its constraint rejects an orphan without admission,
  snapshot, the canonical failure kind, or a timestamp at least as late as the
  persisted original terminal deadline. Its trigger freezes an orphan's detail,
  terminal kind, and completion field, and forbids recasting pre-existing terminal
  truth as an orphan. Existing assistant persistence already locks this same row
  and rejects a failed/cancelled attempt before inserting an assistant.
- A late worker's terminal-record helper returns false for a controller-owned
  orphan, including an attempted same-kind `task.failed`; it cannot claim that
  terminal outcome as its own reason. Caller publication behavior still needs
  integration and proof.
- The canonical token registry and its contract distinguish an orphan from
  controlled `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED`. Downgrade preserves the
  durable `task.failed` truth while removing the new detail column. No historical
  snapshot backfill is performed.

## Validation

Using `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python` from the repair repo:

```text
python -m pytest tests/core/test_chat_completion_attempt_persistence.py \
  tests/tasks/test_chat_completion_deadline.py tests/test_thread_task_receipts.py \
  tests/contracts/test_protocol_tokens.py -q
73 passed; no errors, failures, or skips

python -m pytest tests/db/test_chat_completion_attempt_migration.py -q
8 passed on native PostgreSQL 15; no errors, failures, or skips
```

The native driver obtains the existing proof Postgres connection in memory and
runs only the disposable fixture's generated `codexify_attempt_<uuid>` databases.
It does not print credentials or mutate the application database. An independent
catalog read confirmed no disposable test databases remain.

The eight native cases include the three previous migration/atomic-completion
proofs plus terminal-boundary/idempotence/downgrade, durable truth and exact
identity precedence, missing acknowledgement/legacy/invalid snapshot fail-closed,
injected orphan persistence rollback, and both assistant/reconciler race orders.
The assistant-winning race retains exactly one assistant and no orphan. The
reconciler-winning race commits the orphan and the blocked writer creates zero
assistants. Direct SQL attempts to change the orphan's detail, terminal kind, or
completion binding fail; an early direct SQL orphan and recasting an existing
cancellation also fail.

Scoped Ruff passes for the model, new migration, tokens and changed tests.
`guardian/core/db.py` retains three baseline Ruff findings: unused `timedelta`,
`EventOutbox`, and `SyncJob`. Comparison with frozen `b09744eb7` finds zero new
code/message findings. Targeted compileall, `git diff --check`, and documentation
validation pass. These checks prove their respective surfaces only.

Initial failures are preserved, not discarded: the first compile exposed a
misquoted JSON fixture literal; the first focused run missed the registry test's
exact-set update; the first native run found a fixture SQL parameter needing an
explicit text cast in `jsonb_build_object`. Two new test lambda assignments were
also corrected after lint. The corrected suites above passed.

## Retained runtime custody and remaining proof

Independent read-only checks match all 1,138 retained source hashes in the source
snapshot and both app containers. Those containers run the previous candidate,
not this prerequisite. The application migration remains `d4c69e03a712`; backend
and worker start times/restart counts are unchanged, health is `ok`, chat queue is
empty with no turn locks, the chat heartbeat is idle with a positive TTL, and the
eval/system queue counts remain 34/17. Prior thread 37's messages 70/71 and metadata
are unchanged. No application source refresh, migration, worker kill, restart, or
new browser acceptance was performed in this Task.

This does not complete lost-worker recovery or qualify release readiness.
Outstanding integration includes bounded maintenance invocation, strict atomic
Redis owner/token comparison and cleanup after the durable fence, durable receipt
and UI/operator orphan projection, suppression or reprojection of late worker
publication, and explicit retry through a new request/task identity. PostgreSQL
and Redis are separate stores; no cross-store atomic transaction is claimed.

An envelope created before enqueue does not prove queue admission. Historical
missing snapshots and attempts with unconfirmed post-enqueue acknowledgement
remain unresolved, including accepted-degraded ambiguity; this Task does not
relabel them or reconstruct authority from Redis. The full Goal remains active,
and release posture remains HOLD. Confirmed task-scoped worker-generation recovery
stays parked as authorized. No KB/memory addition was made or required.
