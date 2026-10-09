# Accepted-chat native PostgreSQL connection deadline repair

Date: 2026-10-03. Parent source: `3b52bd465`.
Classification: `AUTHORIZED_IMPLEMENTATION`; architecture-impact, P1.
Owner: Codex. Native connection polling is bounded; full qualification remains HOLD.

## Atomic Task Spec and authority

Bound existing raw/ORM native PostgreSQL connection polling by the accepted
attempt's frozen remaining work or terminal budget. Preserve shorter driver
timeouts, ordinary legacy behavior, host ordering, connection setup and adapter
ownership. Prove actual stalled TCP handshakes close before harness release,
multiple host attempts cannot reset the parent budget, and healthy new/reused
connections remain usable. DNS resolution is outside this atomic slice and
still needs proof and repair before full connection establishment is bounded.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, Runtime Protocol Token Contract, ADR-087 and current
release-truth gate. The preceding
[admission characterization](./2026-10-03-chat-postgres-admission-envelope-gap.md)
proved the native connection escape. This change belongs in
`guardian/core/chat_postgres_deadline.py`.

Allowlist: that helper, `tests/db/test_chat_postgres_connect_deadline.py`, and
this receipt. Commit subject: `fix(chat): bound native PostgreSQL connection polling`.
Direct operator execution; no Campaign Engine progression, new architecture,
main merge, push, deployment, or release promotion.

## Implementation

The existing connection subclass drives the upstream native connection generator
with a local selector. Each wait uses the smaller of the original accepted
remaining time and the driver's connection policy. Driver policy may restart for
another host; the accepted budget never does. Actual parent expiry propagates
the canonical `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` exception. Shorter policy
expiry remains psycopg's ordinary `ConnectionTimeout`.

The generator closes in `finally`, releasing the partial PGconn/socket without
an abandoned connector thread. A connection returned after expiry is closed
before admission. Selector registration is removed before advancing the native
generator, matching upstream behavior even when socket replacement reuses the
same descriptor. Upstream `connect()` continues to own parameter processing,
host ordering, error aggregation, authentication and adapter setup. Outside
accepted scope, native polling delegates directly to the driver.

This exercises driver internals across psycopg 3.2.10 and 3.3.6: the former
passes policy timeout into the generator; the latter applies it in outer
`wait_conn`. Dependency upgrades must retain these tested contracts. DNS runs
before this generator and remains outside the bound. Remote commit ambiguity
also remains separate; this repair does not claim to resolve either.

## Proof and validation

Real inert loopback peers accepted PostgreSQL startup bytes and withheld replies.
Raw and ORM creation were exercised in both work and terminal phases. Peers
observed socket EOF before the harness released them; no connector survived the
accepted deadline. No provider, application write or mocked connect operation
was used for these network cases.

| Case | Host 3.2.10 | Container 3.3.6 |
| --- | --- | --- |
| Four handshake cases, 0.25 s parent | 0.2516–0.2523 s | 0.2509–0.2531 s |
| Two hosts sharing 2.4 s parent | 2.4023 s | 2.4012 s |
| Shorter driver policy, accepted 5 s parent | 2.0003 s | 2.0037 s |

The shorter policy retains the driver's two-second minimum. Direct-driver and
legacy-wrapper controls matched each other. With psycopg 3.3.6, an ordinary
timeout exception's traceback retains the suspended native socket until that
exception is released; accepted-scope polling closes it while the exception is
still retained. Legacy behavior was preserved rather than globally patched.
Healthy raw, newly created ORM and reused ORM connections passed actual SQL
checks, followed by an ordinary pooled connection with zero statement timeout.
Two controlled edge cases verify late-result closure and replacement of an owned
socket descriptor with unchanged descriptor number and read interest.

Validation from the repair repository root:

- Private `TEST_DATABASE_URL`, `PYTHONPATH=. .../.venv/bin/python -m pytest
  -o addopts= -q -s tests/db/test_chat_postgres_connect_deadline.py
  tests/db/test_chat_postgres_pool_deadline.py tests/db/test_chat_postgres_deadline.py
  tests/db/test_chat_completion_attempt_migration.py
  tests/workers/test_chat_worker_queue_deadline.py
  tests/workers/test_chat_worker_tool_loop.py
  tests/workers/test_chat_worker_lifecycle_events.py
  tests/test_chat_worker_turn_integrity.py`: **52 passed, zero skips**, 39.28 s.
- Actual retained worker, exact copied test/bootstrap files with private test
  environment and controlled Redis/embeddings, connect/pool/query deadline files:
  **26 passed, zero skips**, 26.80 s. Ten real-PostgreSQL cases, seven real-TCP
  cases and nine controlled cases are separate evidence classes.
- Ruff on helper/new test, `python -m py_compile` on both, and
  `git diff --check`: passed. Existing configuration, Alembic, ORM-overlap and
  copied-suite marker warnings are outside this repair.

An initial container run passed 25 cases and failed the legacy socket-close
expectation. A direct-driver comparison established the traceback lifetime
behavior; the test now compares legacy behavior and releases its owned exception.
A subsequent concurrent host/container run passed 25 container cases and failed
the existing slow-query observer check. Its observer is autocommit, but its
constant application label is counted across every database. A separate controlled
read-only probe proved another database's owned query enters that count while
the observer's own database has zero active queries. Cross-suite contamination
is therefore a supported explanation, not a proven historical attribution.
The unchanged container suite passed alone; no query assertion or timing limit
was weakened. Both failed logs/XML are retained, with private credentials redacted.

## Runtime custody and remaining work

Retained project `codexify_chat_branch_proof_896387ad2` was verified idle before
copying exactly this helper into its task-owned source and restarting only the
backend/chat worker. All **1,135 tracked Guardian/backend Python files** matched
checkout, mounted source and both containers. Both drivers are 3.3.6; health is
ok and the database remains at migration head `d4c69e03a712`.

Random fixture databases were migrated and dropped by their owners. The copied
container suite was exported and removed; no fixture database remained.
Independent SQL retained thread 29's exact messages 54/55. Final chat queue was
empty, turn locks absent, worker idle with positive heartbeat TTL. Evaluation
queue remained 26; system queue grew from 6 to 7 during idle restart/testing.
No queue consumption or deletion was performed. Unrelated containers, application
data and runtime policy were preserved.

Evidence root:
`/private/tmp/codexify-chat-postgres-connect-deadline-3b52bd465-20261003/`
retains runner/test hashes, host/container logs and XML, initial failures,
driver source, focused characterizations, source matrices, health and cleanup
receipts. This receipt is documentation follow-through. ADR impact is alignment
with ADR-087; no new ADR, current-state promotion or memory update.

Fresh ordinary browser completion/reload after this repair remains the next
required integration proof. The Goal stays active. DNS, Redis/outbox/context
bounds, exhausted terminal reserves, remote commit ambiguity and active-worker
drain/loss recovery remain unfinished; idle restart is not active-shutdown proof.
