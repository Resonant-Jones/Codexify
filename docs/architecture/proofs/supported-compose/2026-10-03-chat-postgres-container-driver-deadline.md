# PostgreSQL query deadlines on the container driver

Date: 2026-10-03. Evaluated source: `76fab06acfe6a4ac44efa93b784e5f5e9f4e60bd`.
Classification: `PROOF_REQUIRED`; architecture-impact, P1; owner: Codex.
Seven database regressions passed on container psycopg **3.3.6**.
Full supported qualification remains `HOLD`.

## Atomic Task Spec and authority

Prove the accepted-task query repair against the actual retained chat-worker
driver, closing the version mismatch in the preceding
[ordinary browser proof](./2026-10-03-chat-postgres-browser-integration.md).
Run the seven existing real-PostgreSQL regressions inside that container against
disposable databases. Require effective row-lock/slow-query bounds, no late
assistant or terminal writes, observed server quiescence while proof locks remain
held, fresh atomic/idempotent controls, borrowed transaction ownership, and
preservation of stricter database policy and pooled legacy limits.

Authority: the explicit chat reliability Goal, Codex Development Operator Goal,
ADR-087, Chat Runtime Contract, and current-state release gate. This is direct
bounded operator proof, without Campaign Engine progression or new architecture.
Allowlist: this receipt only. Commit subject:
`docs(proof): verify PostgreSQL deadlines on container driver`.
No main merge, push, deployment, source repair, or runtime setting change.

## Executed surface and result

Project `codexify_chat_branch_proof_896387ad2`, container
`codexify_chat_branch_proof_896387ad2-worker-chat-1`. A separate `docker exec`
Python process used that container's installed psycopg 3.3.6 and current mounted
Guardian implementation. Runtime helper/PgDB/worker SHA-256 values matched the
evaluated checkout. Six exact test/bootstrap files were copied to an owned
temporary container directory and verified by SHA-256 before removal.
Existing root/test bootstraps isolate Redis and embeddings. Test environment
database defaults pointed at `postgres`, and the existing fixture created,
migrated, and dropped randomly named proof databases; retained application data
was not used as the test database. No dependencies were installed.

From that temporary test root, the effective command was:

```text
python -m pytest -o addopts= -q -s -m integration
  tests/db/test_chat_postgres_deadline.py --junitxml=<owned-root>/proof.xml
```

Result: **7 passed, 5 deselected, zero skipped, failed, or errored**, 19.05 seconds.
The deselected cases are unit/controlled-path cases already covered by the
preceding repair; these seven selections all exercised actual PostgreSQL.

| Exercised wait | Parent window | Observed duration |
| --- | --- | --- |
| Raw atomic assistant row lock | 0.50 s | 0.5013 s |
| ORM terminal-writer row lock | 0.50 s | 0.5020 s |
| Work-expired worker terminal row lock | 0.50 s | 0.5073 s |
| Raw `pg_sleep(10)` | 0.25 s | 0.2512 s |
| Pooled ORM `pg_sleep(10)` | 0.25 s | 0.2515 s |

Independent `pg_stat_activity` observed actual transaction-ID lock waits.
Each client operation ended while the original row remained locked; SQL then
observed zero active proof work before releasing it. No failed operation wrote
a late assistant or terminal row. Fresh independent requests remained atomic and
idempotent, and the expired attempt remained unlinked. Raw/ORM slow-statement
operations also ceased server work. Legacy pooled controls retained zero
statement/lock limits. Borrowed connection commit/rollback stayed forbidden to
the borrower, positive clipped limits were read back, and a stricter 40 ms
database policy retained ordinary PostgreSQL cancellation classification.

The expired-worker case runs the real worker/terminal writer with controlled
generation, transport, cancellation lookup, and lock release. It invoked no
provider and emitted one canonical `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED`
failure through test transport. This is not a queued live-browser deadline case,
nor proof that an exhausted reserve can durably record a locked terminal row.

## Custody, validation, and open obligations

JUnit XML and independent assertions confirmed the exact seven test names,
zero skips/errors/failures, observed wait rows, and source/test hashes.
The owned temporary container suite was removed after exporting its XML.
Independent SQL found no remaining `codexify_attempt_*` fixture databases and
verified retained thread 28 still held only messages 52/53 and its same completed
attempt link. The application chat queue remained empty, turn locks absent,
worker idle with heartbeat TTL 41 seconds, and health `ok`.
Evaluation/system queues remained 25/5. No container restart or queue consumption
was performed by this proof. Existing Alembic and ORM warnings remain unchanged.

Evidence root:
`/private/tmp/codexify-chat-postgres-driver-76fab06ac-20261003/`.
It retains the exact suite, container runner, output log, XML, source manifest,
independent assertion receipt, health and cleanup/readback receipts. Existing
credentials were used only in the runner environment, never printed or committed.
`git diff --check` passed; this receipt is the sole documentation follow-through.
ADR impact: aligned with ADR-087, without a new decision or release promotion.

The container-driver query-contention gap is closed on these exercised seams.
The ordinary browser proof at the same implementation remains separate evidence
for successful user completion/reload. DNS/connection establishment and pool
admission are still unbounded; inspection of the installed driver's `connect`
shows separate connection polling before instance `wait`, which the query repair
does not intercept. Redis/outbox and context bounds, exhausted durable terminal
reserves, remote commit ambiguity, graceful drain, and worker-loss recovery
remain open. The next authorized task is causal connection/admission proof before
repair. The full Goal remains active.
