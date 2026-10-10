# Accepted-chat PostgreSQL connection and pool admission escape

Date: 2026-10-03. Evaluated source: `e3e422f2b`.
Classification: `PROOF_REQUIRED`; architecture-impact, P1; owner: Codex.
**Two distinct admission escapes reproduced. Qualification remains HOLD.**

## Atomic Task Spec and authority

Characterize effective accepted-task connection and ORM pool admission bounds
before selecting a repair. Use a temporary container-local handshake listener
and proof-owned PostgreSQL connections, preserve the frozen deadline, and observe
whether the operation remains blocked after it expires. Do not modify runtime
source/settings, retained data, or queues. Commit only this evidence receipt:
`docs(proof): record PostgreSQL connection and pool deadline escapes`.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, ADR-087, Chat Runtime Contract, and current-state release gate. This is
direct bounded operator proof, not Campaign Engine progression. ADR-087 already
requires child connection/database work to fit the immutable accepted envelope;
the intended bound needs no new policy decision. No main merge, push, deployment,
or release promotion is authorized by this task.

## Causal seam and experiment

The preceding [container-driver query proof](./2026-10-03-chat-postgres-container-driver-deadline.md)
passed all seven PostgreSQL query regressions on psycopg 3.3.6. Those operations
had already obtained their connections. `connect_with_query_bounds` checks the
budget once before inherited `Connection.connect`; installed psycopg connection
creation uses `waiting.wait_conn` separately from the subclass instance `wait`.
PgDB's existing QueuePool has size 5, overflow 10, and a 30-second admission
timeout; pool checkout does not inherit the query scope.

Run inside `codexify_chat_branch_proof_896387ad2-worker-chat-1` with its installed
psycopg 3.3.6, current mounted source, and source hashes matched to the evaluated
checkout. Each operation had an immutable terminal deadline 0.25 seconds away
(the work deadline was already expired). Harness threads observe operations;
they are not a proposed runtime deadline implementation.

For raw `_connect` and ORM `_sa_session`, a temporary `127.0.0.1` TCP listener
accepted the real PostgreSQL startup packet and withheld a handshake response.
The inert DSN explicitly disabled SSL and set `connect_timeout=1`; the listener
was released at about 0.50 seconds to finish the otherwise blocked operation.
Both operations were still pending after the parent expired and ended with
ordinary `OperationalError` when the listener closed, without parent deadline
classification. Each listener observed 35 startup bytes and was closed/joined.
This proves the handshake polling escape; DNS behavior was not injected here.

For pool admission, a proof-owned PgDB adapter used database `postgres` and
application name `accepted_pool_admission_proof`. All 15 existing default pool
slots were held. Independent SQL observed all 15 labeled connections. The next
accepted borrower remained pending after its 0.25-second window and was admitted
when a held slot was released at about 0.50 seconds, returning an
`AcceptedDeadlineConnection`. Reset subsequently logged an error as the query
scope was already expired; that later cleanup does not bound the preceding
admission wait. No application statement or assistant write was attempted by
this borrower.

| Surface | Still pending after expiry | Duration to harness release |
| --- | --- | --- |
| Raw connection handshake | yes | 0.5023 s |
| ORM new-connection handshake | yes | 0.5019 s |
| Full ORM pool admission | yes; then admitted | 0.5010 s |

These are successful assertions of a failing enforcement condition, not passing
deadline regressions. They prove that connection/pool waits can outlive the
accepted snapshot. The harness released resources rather than waiting for a
driver or 30-second pool timeout; no maximum natural escape duration is claimed.

## Validation, custody, and next repair

`docker exec -i <worker> python - < proof.py` exited zero and retained structured
results. Independent assertions verified all three escape observations, source
hashes, zero labeled connections after disposal, healthy runtime, idle worker,
empty chat queue, and absent turn locks. Evaluation/system queues stayed 25/5.
The temporary listeners and all 15 owned connections were closed. Retained
application data and process configuration were untouched. No worker restart,
queue publication, or destructive application cleanup occurred.

Evidence root:
`/private/tmp/codexify-chat-postgres-admission-e3e422f2b-20261003/` contains the
runner, log, validated results, source hashes, and final health. Existing database
credentials remained private runner environment; listener credentials were
inert test values. `git diff --check` passed. This documentation-only task adds
no automated runtime test; its executable characterization is retained above.
ADR impact: alignment with ADR-087; no new decision. This receipt is the
documentation follow-through, with no current-state promotion or memory update.

The next authorized implementation must carry the frozen remaining budget
through connection establishment (including DNS/host attempts) and pool
admission, fail with the canonical deadline disposition, close/discard late
connections, preserve stricter configured limits and normal legacy behavior,
and leave no abandoned execution/DNS work. Proof must cover actual handshake,
pool exhaustion, successful fresh/pooled controls, and server/resource quiescence.
A static `connect_timeout` alone cannot establish this requirement: its own
units/host-attempt behavior and DNS coverage need inspection and effective proof.

This task changes no source and does not repair either escape. Query bounds and
ordinary-browser success remain proven only on their exercised seams. Full
context/Redis/outbox bounds, terminal-reserve exhaustion, commit ambiguity, and
shutdown/worker-loss recovery remain open. The Goal remains active.
