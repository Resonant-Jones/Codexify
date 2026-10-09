# PostgreSQL DNS admission still escapes the accepted deadline

Date: 2026-10-03. Evaluated source: `29ebd7226`.
Classification: `PROOF_REQUIRED`; architecture-impact, P1; owner: Codex.
DNS admission gap confirmed at a controlled resolver seam; full qualification HOLD.

## Atomic Task Spec and authority

Characterize raw/ORM hostname resolution on the actual retained worker driver
against the frozen accepted work and terminal deadlines. Keep resolution held
past expiry, measure whether the caller exits, release the owned resolver safely,
verify no late connection admission, then run healthy raw/ORM/legacy SQL controls.
This change belongs in this receipt; repository allowlist: this receipt only.
Commit subject: `docs(proof): characterize PostgreSQL DNS deadline escape`.

Authority: active ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, ADR-087 and current-state release gate. The preceding
[connection repair](./2026-10-03-chat-postgres-connect-deadline.md) bounds native
polling but explicitly excludes DNS. No runtime repair, new architecture, policy
change, main merge, push, deployment or release promotion is performed here.

## Verified call site and proof class

Installed psycopg **3.3.6** invokes `conninfo_attempts(params)` from its synchronous
`Connection.connect()` before `_connect_gen`. For unresolved non-local hostnames,
`_resolve_hostnames` calls synchronous `socket.getaddrinfo`. The accepted
connection subclass's selector/deadline checks begin in `_connect_gen`, after
that hostname resolution returns. Inspected host psycopg **3.2.10** has the same
pre-polling resolution seam; this task's execution evidence uses 3.3.6 only.

An isolated `docker exec` Python process in the retained worker imported the
actual mounted helper and PgDB. It cached genuine addresses for the retained
PostgreSQL host, then held only that host's `getaddrinfo` call behind an owned
event. Four borrowers exercised actual PgDB raw or ORM admission, each with a
0.25-second frozen remaining work/terminal window. The controller verified the
caller was still live and blocked at 0.5 seconds, then released resolution.

This is a controlled Python resolver-call probe, **not a real DNS outage or
network-level resolver failure**. The driver call path, wrapper, inherited
deadline and elapsed wall time are real. Healthy controls afterward performed
actual `SELECT 1` against retained PostgreSQL, in database `postgres`; no
application rows or messages were written.

| Surface / phase | Still blocked at 0.5 s | Exit after release |
| --- | --- | --- |
| Raw / work | yes | 0.5007 s |
| Raw / terminal | yes | 0.5009 s |
| ORM / work | yes | 0.5003 s |
| ORM / terminal | yes | 0.5017 s |

All four raised `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` only after release and
admitted no connection. This prevents late query work but fails to interrupt
resolution at the accepted deadline. All owned borrower threads finished, the
resolver hook was restored in its isolated process, its engine was disposed,
and the probe process reached terminal exit zero. Fresh accepted raw/ORM and
ordinary legacy SQL controls passed.

## Runtime custody, validation and provenance

Project `codexify_chat_branch_proof_896387ad2` stayed idle, with an empty chat
queue, no turn locks and positive worker heartbeat TTL. All **1,135 tracked
Guardian/backend Python files** matched checkout, mounted snapshot, backend and
worker. The probe independently reported the helper's SHA-256, matching the
evaluated checkout. Health remained ok with valid `v1-local-core-web-mcp`.
SQL retained thread 30's exact messages 56/57. Evaluation/system queues remained
27/7. No worker restart, runtime source refresh or application write occurred.

Validation: private `run-probe.py`, independent JSON assertions, driver-source
inspection, runtime source hashes, read-only SQL controls, health/idle/retained
message checks and `git diff --check` passed. No new automated runtime test suite
applies to this documentation-only characterization. The prior 52 host/26
container tests and successful ordinary browser/reload turn remain separate
evidence for the unchanged runtime implementation.

An initial reused preflight runner overwrote the preceding browser proof's
`preconditions.json` and `health-before.json`. The prior state snapshot was
restored from the recorded preflight tool output (exec session 94798); the later
snapshot is now in this task's evidence directory. The overwritten historical
raw health-before snapshot is unavailable; its original tool output confirms
status ok, and the original health-after snapshot still proves that profile.
The later health snapshot was explicitly renamed in the old evidence directory
and copied here. Both directories contain custody-restoration provenance.
No source, application data or evaluated runtime result changed.

Evidence root:
`/private/tmp/codexify-chat-postgres-dns-29ebd7226-20261003/` contains exact probe,
runner/log/result, both installed driver sources, runtime source matrix, custody,
health/retained-message checks and artifact-restoration provenance. Credentials
remain in private process environment and are not printed or committed.
This receipt is documentation follow-through; ADR impact is alignment only,
with no current-state promotion or memory update.

## Next authorized obligation

Bound the actual hostname-resolution operation by the same frozen remaining
budget, terminate and reap any owned resolver on expiry, and preserve driver
host/address ordering, explicit hostaddr, Unix-socket/numeric-host behavior,
authentication/TLS hostname identity and ordinary error disposition. Do not
discard a background resolver thread or reset the deadline after resolution.
Prove deadline interruption plus healthy DNS/SQL controls before refreshing the
ordinary browser path. No particular mechanism is selected by this proof.

The Goal remains active. Native polling and pool/query bounds alone do not prove
the full PostgreSQL connection envelope. Redis/outbox/context bounds, exhausted
terminal reserves, remote commit ambiguity and active-worker drain/loss recovery
also remain unfinished; none are qualified by this resolver characterization.
