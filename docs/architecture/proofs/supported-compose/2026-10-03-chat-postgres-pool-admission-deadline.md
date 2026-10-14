# Accepted-chat ORM pool wait deadline repair

Date: 2026-10-03. Parent source: `a8b8bb723`.
Classification: `AUTHORIZED_IMPLEMENTATION`; architecture-impact, P1.
Owner: Codex. Pool waiting is repaired; full supported qualification remains HOLD.

## Atomic Task Spec and authority

Bound the existing PgDB QueuePool wait by the accepted task's immutable remaining
work/terminal budget. Preserve shorter pool policy limits, independent legacy
borrowers, capacity/overflow/reset behavior, and transaction ownership. Prove
effective expiry while all default slots remain held, with a concurrent healthy
legacy borrower and fresh accepted control. Do not create a replacement budget,
queue, provider policy, or recovery authority.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, Runtime Protocol Token Contract, ADR-087, and current
release-truth gate. The preceding
[connection/pool characterization](./2026-10-03-chat-postgres-admission-envelope-gap.md)
proved two separate escapes. This atomic repair covers pool waiting; DNS/native
connection establishment needs its own mechanism and remains unfinished.
Campaign Engine was not used for this direct bounded operator lifecycle.

Allowlist: `guardian/core/chat_postgres_deadline.py`, `guardian/core/pgdb.py`,
`tests/db/test_chat_postgres_pool_deadline.py`, and this receipt.
Commit subject: `fix(chat): bound ORM pool waits by accepted deadline`.
No main merge, push, deployment, or current-state promotion.

## Implementation

PgDB selects a QueuePool subclass whose queue reads the context-local frozen
budget on each borrower. The inherited queue wait receives the lesser of the
pool's configured timeout and the remaining parent time. The shared pool timeout
is never changed by runtime admission, so a concurrent legacy borrower retains
its own normal policy. Outside accepted scope, the queue delegates unchanged
behavior. A shorter policy timeout retains SQLAlchemy's ordinary TimeoutError;
actual parent expiry propagates the canonical accepted-task deadline exception.

The queue mutex acquisition is bounded by the same remaining time. SQLAlchemy's
queue uses a reentrant mutex; the repair holds it through a post-wait deadline
check. An entry delivered too late is restored under that mutex before any
connection checkout, preventing a late borrower from taking a slot or leaking
capacity. Normal pool creation, overflow accounting, reset and transactions stay
with QueuePool. This uses inspected SQLAlchemy queue internals; dependency
upgrades must retain the exercised reentrant-lock and queue-class contracts.

Connection creation remains separate: a pool with room can still enter the
unrepaired native connection/DNS path. This repair does not claim otherwise.

## Proof and validation

Host driver psycopg 3.2.10; retained worker driver 3.3.6. The existing fixture
created, migrated and dropped random disposable databases on retained Postgres
15. The new cases used actual default size 5 plus overflow 10: independent SQL
observed all 15 labeled connections held. The bounded borrower exited while all
15 remained checked out and before any owner released a slot. The concurrent
legacy borrower was still waiting, then obtained a released slot and successfully
queried `SELECT 1` with ordinary zero statement timeout. A fresh accepted control
also succeeded afterward. No deadline failure required unlocking the pool.

| Case | Host | Container |
| --- | --- | --- |
| Full pool, 0.25 s parent | 0.2532 s | 0.2510 s |
| Shorter 40 ms pool policy | 0.0405 s | 0.0423 s |

Two additional focused controls proved expiry while the queue mutex remained
held, and restoration of a late delivered entry without admitting the borrower.
The latter is a controlled timing edge, distinct from real pool/SQL proof.
Existing query-contention cases still observed actual row locks, ended server
work while locks stayed held, and left no late assistant or terminal writes.

Validation from the repair repository root:

- With private `TEST_DATABASE_URL`, `PYTHONPATH=. .../.venv/bin/python -m pytest
  -o addopts= -q -s tests/db/test_chat_postgres_pool_deadline.py
  tests/db/test_chat_postgres_deadline.py
  tests/db/test_chat_completion_attempt_migration.py
  tests/workers/test_chat_worker_queue_deadline.py
  tests/workers/test_chat_worker_tool_loop.py
  tests/workers/test_chat_worker_lifecycle_events.py
  tests/test_chat_worker_turn_integrity.py`: **42 passed, zero skips**.
- Actual worker container, copied exact test/bootstrap files with private test
  environment and controlled Redis/embeddings, both deadline test files:
  **16 passed, zero skips** (nine real-PostgreSQL cases, seven controlled cases).
- Ruff on changed helper/new test, compile checks, and `git diff --check`: passed.
  PgDB has **17 preexisting Ruff findings**, unchanged against parent after
  comparing codes, normalized line references, and exact diagnostic/reference
  source lines. The first comparison failed on the two-line location shift;
  that was an evidence normalization issue, not a new finding.

The first container suite passed 15 cases but lacked the copied worker helper
required by one existing unit case. Adding that exact helper and rerunning the
complete focused set produced the final 16 passes. Initial log/XML are retained.
Existing Ruff configuration, Alembic, ORM overlap, and copied-suite unknown-marker
warnings remain outside this repair.

## Runtime custody and complete-path re-evaluation

The retained isolated project `codexify_chat_branch_proof_896387ad2` was verified
idle, with empty chat queue and no turn locks, before copying exactly the two
changed backend files into its task-owned mounted source and restarting only
backend/chat worker. All **1,135 tracked Guardian/backend Python files** matched
the evaluated checkout, snapshot, and both containers afterward; health was ok
with valid supported profile. Tests ran in a separate container process against
owned databases, with controlled transport, rather than submitting a user turn.

After exporting the XML, the owned container suite was removed and no disposable
fixture database remained. Independent SQL verified retained thread 28 still
held exactly messages 52/53. Final chat queue: zero; turn locks: none; worker idle
with positive heartbeat TTL. Evaluation queue stayed 25; system queue grew from
5 to 6 during the idle restart/test run. An initial cleanup assertion incorrectly
assumed that count would stay fixed; fresh readback corrected the receipt.
No queue consumption or deletion was performed by this task. Application
data, unrelated containers, and runtime settings were preserved. Credentials
stayed in private runner environment and were not printed/committed.

Evidence root:
`/private/tmp/codexify-chat-postgres-pool-deadline-a8b8bb723-20261003/` retains the
runner, exact tests/source, final and initial logs/XML, source matrices, Ruff
baseline/current comparison, independent assertions, health and cleanup receipts.
This receipt is the documentation follow-through. ADR impact is alignment with
ADR-087; no new architecture decision, release promotion, or memory update.

The previous ordinary browser success/reload proof evaluates the prior pool
implementation. It is not fresh complete-path browser proof for this repair.
That re-evaluation remains required after the remaining connection repair; the
Goal stays active. DNS/handshake polling, Redis/outbox and context bounds,
exhausted terminal reserves, remote commit ambiguity, and active-worker drain/
loss recovery remain separate unfinished obligations. Idle restart here does
not prove safe active-worker shutdown.
