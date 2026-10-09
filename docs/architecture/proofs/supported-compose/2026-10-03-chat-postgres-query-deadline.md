# Accepted-chat PostgreSQL query deadline repair

Date: 2026-10-03. Parent source: `a99662ec4`.
Classification: `AUTHORIZED_IMPLEMENTATION`; architecture-impact, P1.
Qualification remains `HOLD`. This is a query-bound repair, not complete Slice C.

## Atomic Task Spec and authority

Bound raw PgDB and pooled ORM query waits using the accepted task's immutable
work/terminal timestamps. Preserve transaction ownership, assistant/attempt
atomicity, cancellation precedence, canonical failure disposition, and legacy
operations. Prove actual row-lock and slow-statement behavior in disposable
databases before committing. This change belongs in PgDB query execution and
the existing worker lifecycle. Owner: Codex; target: architecture/proof review.

Authority: the explicit ordinary-chat reliability Goal,
`docs/Ops/codex-development-operator-goal.md`, Chat Runtime Contract,
Runtime Protocol Token Contract, and ADR-087. The preceding
[lock characterization](./2026-10-03-chat-postgres-terminal-envelope-gap.md)
proved the causal escape; it was not a passing deadline regression.
Current-state truth remains the release gate. Campaign Engine was not used:
this required lifecycle remains direct, bounded development-operator work.

Files: `guardian/core/chat_postgres_deadline.py`, `guardian/core/pgdb.py`,
`guardian/workers/chat_worker.py`, `tests/db/test_chat_postgres_deadline.py`,
and this receipt. Commit subject:
`fix(chat): bound PostgreSQL query waits by accepted deadline`.
Stage exactly those five paths after validation; no main merge or push.

Acceptance: frozen phase bounds reach raw and previously created ORM
connections; server statement/lock limits and native client polling enforce
query bounds; deadline-closed connections cannot escape through rollback;
healthy independent attempts, idempotence, and borrowed transactions remain
valid; actual lock/statement proof leaves no late assistant write.
Blast radius: PgDB connections and worker-owned chat. ADR impact: aligned with
ADR-087; no new architecture, protocol token, retry policy, or recovery authority.

## Implementation and meaning

The worker establishes one context-local query scope around its actual task
lifecycle. Both frozen timestamps map once to monotonic time, using a reference
sampled before the wall clock so setup cannot add budget. No query or phase
transition resets either deadline. An already work-expired task uses only the
original terminal window for completion reconciliation/failure handling.
Successful generation, explicit cancellation, durable-completion reconciliation,
and failure handling may use that same terminal reserve for database work.
Malformed present snapshots never select legacy unbounded query behavior.

Raw accepted-task connections and ORM pool connections use a psycopg Connection
subclass with native socket polling. Each wait uses remaining phase time;
expiry closes the connection and generator without an abandoned execution
thread or the driver's separate five-second interrupt-cancellation wait.
Terminal protocol replies are checked even when a generator finishes without
another I/O yield. Server statement/lock limits are positive, millisecond-clipped,
transaction-local, and preserve stricter configured limits. Expired or fractional
millisecond admission starts no new query. Autocommit accepted queries fail
closed because transaction-local limits would not cover their next statement.

Legacy operations delegate normal driver waits. Transaction-local limits do
not leak into later pooled operations. Borrowed conversation connections still
cannot commit or roll back their owner's transaction. ORM cleanup discards
an unusable connection without replacing the original failure with a rollback
error. Persistence deadline exceptions retain canonical deadline disposition,
observed successful generation (`executed=true`, `completed=false`), existing
provider/model resolution metadata, and `persistence_outcome=failed`.

## Proof and validation

Host driver: psycopg 3.2.10. The existing migration fixture created and dropped
random disposable databases on retained Postgres 15 at `127.0.0.1:55433`.
Retained application data, queues, containers, and live snapshots were untouched.

Seven real PostgreSQL cases cover raw atomic persistence, ORM terminal writing,
expired worker terminal handling, raw/pooled slow statements, bounded borrowed
transactions/limit readback, and stricter existing server policy. Held rows remain
locked until the client operation ends and independent SQL observes zero active
proof work. No failed operation writes a late assistant or terminal row. Fresh
adapter controls use a separate accepted request, prove atomic/idempotent success,
and leave the expired attempt unlinked. Pooled legacy controls retain zero
statement/lock limits. Policy timeouts shorter than the parent retain ordinary
PostgreSQL cancellation rather than falsely reporting parent expiry.

The worker contention case uses the real worker and terminal writer, with
transport, cancellation lookup, lock release, and generation controls. It emits
one canonical deadline failure through the controlled test transport and invokes
no provider. Its locked terminal row remains unmodified: durable failure recording
under an exhausted reserve is **not** proved. Synthetic protocol controls cover
late commit/rollback replies; remote commit acknowledgement is **not** proved.

Final validation from the repair repository root:

- With private `TEST_DATABASE_URL`, `PYTHONPATH=. .../.venv/bin/python -m pytest
  -o addopts= -q -s tests/db/test_chat_postgres_deadline.py
  tests/db/test_chat_completion_attempt_migration.py
  tests/workers/test_chat_worker_queue_deadline.py
  tests/workers/test_chat_worker_tool_loop.py
  tests/workers/test_chat_worker_lifecycle_events.py
  tests/test_chat_worker_turn_integrity.py`: **38 passed, zero skips**.
- Chat worker, turn-integrity, returned-command, provider stream/nonstream,
  tool-admission, and loopback deadline regressions: **139 passed, zero skips**.
- Ruff on the new helper/test, compile checks, and `git diff --check`: passed.
  PgDB/worker Ruff findings: **19 unchanged** against the parent, independently
  normalized and compared. Existing Ruff configuration, Alembic path-separator,
  and ORM overlapping-relationship warnings remain outside this task.

Initial test selections named two absent historical paths; corrected commands
ran the current lifecycle and turn-integrity files. New provider assertions were
corrected to the existing event schema (provider truth and resolved model),
without widening the event contract. Those intermediate failures are retained.
An environment-free run skipped PostgreSQL; only the final database-backed run
supports the real-Postgres claims above.

Evidence root:
`/private/tmp/codexify-chat-postgres-query-deadline-a99662ec4-20261003/`.
Runner, final source, logs, JUnit XML, Ruff baseline/current findings, and source
hashes are retained. Credentials stayed in runner environment and were not printed
or committed. This receipt is documentation follow-through; no current-state
promotion or memory update occurred.

## Complete-path re-evaluation

The previous fresh ordinary browser completion at `b67469c9a` remains evidence
for that evaluated source and healthy dependencies. This repair has not been
loaded into that retained Compose runtime and therefore has no fresh complete
browser/provider/persistence/event/restart qualification at its new tip.

Native query waits now have effective bounds on the exercised raw/ORM seams.
Connection/DNS establishment and pool admission remain separate escape gates.
Complete outbox/Redis terminal publication, non-database context/retrieval,
remote commit ambiguity/quiescence, server-side command shutdown, worker-loss
authority, and graceful drain remain unproved. In particular, an exhausted
reserve plus an unavailable durable terminal row is not full terminalization.
The next authorized obligation is connection/admission bounding and proof,
followed by fresh whole-path integration. The Goal remains active.
