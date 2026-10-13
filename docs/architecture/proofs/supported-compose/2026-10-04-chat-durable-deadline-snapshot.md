# Durable original chat recovery envelope prerequisite — 2026-10-04

## Authority and atomic scope

Development Operator Level 0, AUTHORIZED_IMPLEMENTATION, EXECUTE then PROOF.
The human explicitly authorized deadline-bound reconciliation: persist the
exact server-owned original envelope for future accepted tasks; after its
terminal deadline, prefer exact durable completion or terminal truth, otherwise
record an honest lost-worker/orphan outcome, fence late writes and matching
lock cleanup, and allow only explicit new-request/task retry. No worker death
time inference, controlled-deadline label for a crash, silent replay, or new
worker-generation/lease authority. That decision resolves the preceding
worker-loss policy frontier; confirmed-generation recovery is parked.

This first atomic prerequisite persists the original envelope required by that
policy. Frozen clean branch `codex/chat-postgres-terminal-deadline-20261003`
at `2fc73965c`. ADR-001/003/087/091 and Chat Runtime govern acceptance, identity,
immutable 720/60 deadlines and existing durable attempt/message authority.
No new ADR, current-state promotion or canonical runtime token.

## Change

Shared acceptance already builds a server-owned `AcceptedChatTaskDeadline`
after acceptance participants finish and renews its existing turn lock. It now
passes that exact frozen object and the existing lock token into the durable
attempt creation transaction **before enqueue**. Ordinary, owner and guest
completion producers all use this boundary. Queue serialization sees the same
three accepted/work/terminal timestamps that have already committed.

Alembic revision **`e8a9b03d6712`**, following verified head `d4c69e03a712`, adds
nullable `deadline_snapshot` JSONB and `turn_lock_token` to the existing attempt.
The creation helper requires a validated 720/60 object and a nonempty existing
lock token as a pair. The paired fields have a database check. A PostgreSQL
update trigger freezes both after creation, including NULL legacy records;
updates cannot refresh an envelope, replace the token, or invent a historical
snapshot. No backfill occurs. SQL NULL is explicit in the ORM JSONB mapping.

The later `accepted_at` field remains the existing post-enqueue acknowledgement
clock read. It is distinct from the original envelope's accepted timestamp and
cannot refresh it. A queue failure retains its unaccepted attempt and snapshot;
persistence failure still prevents enqueue and follows existing cleanup. A
post-enqueue acknowledgement failure still reports degraded acceptance without
denial or replay of already accepted work. The snapshot does not, by itself,
prove queue acceptance for an unacknowledged candidate.

Generic task readers and public receipts do not expose the stored lock token
or change their response shape. Existing assistant/terminal fencing remains.
The token is the already existing per-turn lock capability; it creates no new
worker lease, generation, heartbeat-death or ownership authority.

Changed files: `guardian/db/models.py`, `guardian/core/db.py`,
`guardian/core/chat_completion_service.py`, the migration above,
`tests/core/test_chat_completion_attempt_persistence.py`,
`tests/db/test_chat_completion_attempt_migration.py`, and this receipt.

## Validation and preserved failures

Private evidence root:
`/private/tmp/codexify-chat-durable-deadline-2fc73965c-20261004/`.
Task Spec, migration/head evidence, focused and native JUnit/process logs,
frozen-source lint comparison, disposable-database absence and runtime custody
validation are retained.

**35 focused checks pass**, zero failure/error/skip:

```text
python -m pytest tests/core/test_chat_completion_attempt_persistence.py tests/tasks/test_chat_completion_deadline.py tests/test_thread_task_receipts.py -q
```

They verify prequeue identity/snapshot order across all producers, exact queue
payload equality, client-deadline overwrite, fixed immutable intervals, queue
failure/persistence failure and degraded acknowledgement behavior, while
preserving existing task-receipt truth and private lock-token boundaries.

**Three native PostgreSQL checks pass**, zero failure/error/skip:

```text
python -m pytest tests/db/test_chat_completion_attempt_migration.py -q
```

They run full Alembic upgrades on independently named disposable databases
inside the existing PostgreSQL 15 proof container. The new check seeds a
historical accepted attempt at the prior head, proves unchanged timestamp and
NULL snapshot/token after upgrade, persists a future original envelope, performs
a later acknowledgement without changing it, and rejects refreshed timestamps,
replacement tokens, snapshot erasure and legacy backfill in PostgreSQL itself.
Failure terminal recording preserves the snapshot. Downgrade removes the new
surface and preserves attempt rows. Existing atomic assistant/message-link
and durable terminal tests also pass. All owned test-database names under
`codexify_attempt_` were independently verified absent afterward.

Initial native execution failed two existing legacy-creation cases: the ORM
encoded absent snapshot as JSON `null`, which correctly failed the new paired
check. Setting `JSONB(none_as_null=True)` fixed that real compatibility bug;
initial XML/log/process evidence remains in `first-native-*`. The first driver
also assumed a password despite the existing disposable container's explicit
trust-auth configuration; it failed before any test/database operation. The
corrected driver validates that configuration, never prints credentials, and
preserves the initial driver/output in `initial-*`.

New model/migration/test Ruff checks and targeted compile checks pass;
`git diff --check` passes. Full modified-file Ruff reports 18 inherited findings
in the existing DB/service files. Exact frozen-source comparison proves identical
code/message diagnostics and **zero introduced findings**; no unrelated lint or
unreachable-code repair was folded into this task. Docs and local links were
validated before the scoped commit, reported in closeout.

## Runtime custody and next required work

No application source refresh, migration, service restart, model/native vector
work, ordinary chat submission or queue mutation occurred in this prerequisite.
The retained application still runs the previous repaired source and migration
`d4c69e03a712`; **1,138** Python hashes match its frozen snapshot and both running
containers. This is not candidate-runtime evidence. Health `ok`, chat health
`healthy`, queue zero, no locks, positive idle heartbeat TTL, evaluation/system
queues **34/17** unchanged. Thread 37 messages 70/71, contents and `extra_meta`,
and backend/worker lifecycle remain unchanged. Main remains `016352131`, with
its unrelated staged dev-log deletion preserved.

This completes the durable snapshot prerequisite, not lost-worker recovery.
The next atomic task uses that exact durable snapshot after original terminal
expiry, reconciles completion/terminal truth under the same attempt row lock,
persists the explicit authorized orphan outcome, and applies idempotent matching
Redis cleanup only after durable fencing. PostgreSQL and Redis are separate
stores; their safety must not be described as one distributed transaction.
Acceptance acknowledgement ambiguity remains explicit where durable acceptance
confirmation is absent. Historical tasks with no original snapshot remain
unreconstructed. UI/receipt/retry semantics, races and actual retained-stack
failure/recovery/browser proof still require implementation and validation.
Full qualification **HOLD**, Goal active; no push, merge or deployment.
