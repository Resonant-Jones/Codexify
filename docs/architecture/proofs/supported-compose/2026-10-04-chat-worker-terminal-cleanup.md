# Durable-authorized worker terminal lock cleanup

## Authority and scope

Level 0 EXECUTE → PROOF on `codex/chat-postgres-terminal-deadline-20261003`, frozen
starting commit `53b74658e8591b14020d2f86f40f0c9e8af57668`. The previous Goal turn
made progress by committing exact worker terminal projection. This atomic Task
implements the already human-authorized matching-lock cleanup obligation under
ADR-087/091 and existing durable attempt/message/resource contracts. No new ADR,
schema, token, worker generation, lease authority, replay service or scheduler.

Task Spec and private evidence:
`/private/tmp/codexify-chat-worker-terminal-cleanup-53b74658e-20261004/`.
The full Goal remains active; release remains **HOLD**.

## Changes

- `guardian/core/db.py` adds an exact request/task/thread/turn **read-only** terminal
  observation using the existing private reconciliation result shape. It validates
  any completed assistant link against the actual assistant in the same thread,
  and returns only after transaction acknowledgement. A pending attempt exposes
  no cleanup capability, even when its original deadline has expired. It cannot
  create an orphan, change state/timestamps/deadlines, or backfill historical data.
  Stored tokens remain private; public attempt and receipt projections are unchanged.
- `guardian/workers/chat_worker.py` removes the owner-string release from its
  accepted lifecycle's `finally` block. After accepted scopes close, a fixed
  two-second PostgreSQL maintenance observation obtains existing durable terminal
  authority. After PostgreSQL acknowledgement, a separate bounded Redis operation
  invokes the existing single-Lua task/token/thread CAS. The original stored token
  authorizes cleanup; packet owner/token fields and an observed replacement token
  cannot substitute for it. No legacy release or separate GET/DELETE fallback.
- Already-terminal preflight and rejected-write terminal projection validate private
  terminal authority before publication
  or cleanup. Invalid assistant links cannot produce a completion event or release
  a lock. Postflight uses the same acknowledged observation to reproject an existing
  orphan; it does not publish ordinary completion again. Resource maintenance
  grants no accepted execution, retrieval, provider or rescue budget.
- Missing identity, request-less unsupported packets, pending terminal truth,
  missing historical capability, and read/commit uncertainty leave the lock intact.
  CAS mismatch or acknowledgement uncertainty retains the durable result. Receipt
  recovery can later retry cleanup; workers do not manufacture an alternate
  failure, infer death timing, or silently replay work.
- Worker orchestration fixtures now observe a cleanup boundary rather than the
  removed raw release. Queued cancellation tests exercise the strict CAS seam with
  acknowledged durable terminal capabilities. A native unacknowledged deadline
  terminal write now expects no lock cleanup as well as no inferred terminal event.

These changes preserve the original non-sliding accepted deadline envelope.
Post-deadline maintenance is independently finite observation/cleanup, not an
extension of accepted work or a cross-store atomic transaction.

## Validation and proof limits

From the repair repo using `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`:

- Worker terminal authority/cleanup, queue/rescue deadlines, streaming/tool loops,
  lifecycle/cancellation, turn integrity/model authority/timing/heartbeat, durable
  acceptance, supported recovery and receipt regressions: **152 passed**.
- Native PostgreSQL query/connect/DNS/pool/maintenance bounds, migration, recovery
  controller, worker terminal authority and private cleanup observation: **82 passed**.
- After adding the invalid-assistant-link case and using that same private validation for late
  rejected-write projection, native worker terminal authority
  and cleanup files: **12 passed**. The native observation cases cover pending,
  completion, failure, cancellation, orphan, exact identity mismatch, unchanged
  original snapshot/public token exclusion and lost read-transaction acknowledgement.
  Counts overlap prior runs and do not imply independent full-runtime qualifications.
  Final private-read projection validation also passed 38 terminal-focused cases.
  Its first refinement run exposed nine old fixture-seam failures; after updating
  those seams, all 38 passed. The failed and repaired JUnit/log artifacts remain
  distinct. These fixture results do not replace native persistence evidence.
- Worker cleanup focused cases including a real owned TCP peer holding EVAL:
  **9 passed**. With a configured 0.25-second maintenance resource bound, the
  worker returned the durable result in **0.253250459 seconds**, issued exactly
  one EVAL, observed one socket EOF and restored both scope/client custody. No
  fallback delete or alternate terminal claim. The PostgreSQL acknowledgement in
  this transport test is a seam; native PostgreSQL is proven separately.
- An owned ephemeral process loaded the candidate worker cleanup helper and bounds,
  then executed real Redis 7 Lua on nine generated DB-15 keys. Exact original and
  absent locks clean idempotently; same-owner replacement token, replacement owner,
  wrong thread, pending attempt, missing capability, request-less packet and legacy
  value retain their original bytes. PostgreSQL acknowledgement is an explicit
  observation seam in this probe. It is not a combined production PG/Redis worker
  or a Compose crash/restart proof. Exact generated keys have TTLs and independent
  Redis inspection verified all nine absent after cleanup; app DB-0 is untouched.
- Ruff comparison introduced zero diagnostics. Existing baselines remain three
  database, two worker and five first-token-fixture diagnostics. New tests pass
  Ruff; compile, diff checks and documentation validation pass. Initial and later
  scoped test results remain separate rather than overwriting earlier evidence.

## Custody and follow-through

Read-only custody compares the 1,138 frozen runtime source hashes in source and
both retained application containers, lifecycle/restart counters, health, migration,
queues/locks and prior thread 37 messages. Protected main remains
`0163521312ef767c0884654e70094ae7b44a5eec` with its unrelated staged Dev Log deletion.
Native PostgreSQL tests use only random disposable databases; independent catalog
inspection verifies their absence after process completion. No application source
or migration refresh, service restart/kill, host/model installation, main mutation,
memory write, push, merge or deployment.

The retained runtime remains the pre-reconciliation candidate at application
migration `d4c69e03a712`. This Task closes the worker's raw cleanup path but does
not establish supported-Compose recovery qualification. Next required obligations
are UI/operator projection and explicit new-request retry, unconfirmed-admission
ambiguity, then coherent candidate source/schema refresh and fresh ordinary
success/failure, active-worker-loss, restart/shutdown and persistence evidence.
No release-truth promotion or full Goal completion. Documentation follow-through
is this proof receipt; release anchors and shared memory are unchanged.
