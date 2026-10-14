# PostgreSQL lock waits escape the accepted terminal envelope

Date: 2026-10-03. Evaluated source: `5a1435d78`.
Classification: `PROOF_REQUIRED`; architecture-impact proof under ADR-087.
Qualification remains `HOLD`.

## Atomic Task Spec

Use separately created disposable databases on the retained PostgreSQL server
to characterize current atomic assistant persistence and expired-task failure
recording. Run the real PostgresChatLogDB/PgDB adapter and worker terminal
handler against proof-owned attempt rows. Hold a row lock, independently
observe PostgreSQL's lock wait, and compare elapsed time against an immutable
acceptance snapshot whose terminal reserve is nearly exhausted. Release only
proof locks, join every worker, check durable outcomes/no active work, and run
fresh-adapter no-lock controls. Do not alter the retained application database,
queues, containers, or live task snapshots.

This change belongs in this receipt alone. P1; owner Codex; proof review.
Authority: the explicit reliability Goal, Codex Development Operator Goal,
Chat Runtime Contract, and ADR-087's PostgreSQL/terminal envelope requirements.
No new ADR, deadline policy, state, or recovery authority is introduced.
Validation: two real-Postgres characterization cases, exact immutable timestamps,
server wait/readback/cleanup assertions, and `git diff --check`. Commit this
receipt only with subject `docs(proof): record PostgreSQL terminal deadline escape`.

## Actual persistence seam

Worker initialization selects `PostgresChatLogDB`, a thin PgDB alias.
PgDB `_connect()` calls synchronous `psycopg.connect()` without an inherited
deadline; `_sa_session()` obtains a normal SQLAlchemy session and commits or
rolls back without a task deadline. The accepted deadline helper has immutable
timestamps but no database scope at this revision.

Atomic assistant persistence uses a raw PgDB conversation transaction and
`SELECT ... FOR UPDATE` on the exact completion attempt. Worker-controlled
failure recording calls `record_chat_completion_attempt_terminal_event` through
the SQLAlchemy seam and also uses `FOR UPDATE`. Both therefore reach actual
PostgreSQL row-lock waits. The worker checks queued task expiry before provider
execution, but that check does not bound its subsequent failure write.

## Controlled proof and outcome

The existing disposable-database fixture created two random, separate databases
on retained project `codexify_chat_branch_proof_896387ad2`'s Postgres 15 server
at `127.0.0.1:55433`, upgraded each to migration head, then dropped each during
successful fixture teardown. The retained chat application database was not
modified. Actual host driver: psycopg 3.2.10.

Each case inserted a proof account/thread/attempt, acquired a proof-owned row
lock, and constructed a snapshot at `now - 779 seconds`: original work budget
720 seconds, terminal reserve 60 seconds, about one second total remaining.
No policy values or live accepted tasks were changed. A native worker thread
ran the blocking operation. An independent autocommit connection observed
`pg_stat_activity.wait_event_type=Lock`, `wait_event=transactionid`, and active
server work before observing beyond `terminal_deadline_at`.

| Case | Observation while lock held | Outcome after deliberate unlock |
| --- | --- | --- |
| Atomic assistant adapter | Still blocked more than 250 ms beyond terminal deadline | Assistant inserted and linked atomically, after the envelope |
| Expired-task worker failure | Still blocked more than 250 ms beyond terminal deadline; no terminal event yet | One canonical deadline `task.failed` and durable failure kind, after the envelope; no assistant or provider call |

Both sessions reported `statement_timeout=0` and `lock_timeout=0`. Both exact
timestamp snapshots remained unchanged. Unlocking released the operation;
all worker futures joined and independent SQL found zero active proof work.
Fresh-adapter no-lock controls preserved normal assistant binding and terminal
failure persistence. Each disposable database's teardown succeeded.

**Two characterization cases passed by confirming the current violation.**
These are not passing deadline enforcement tests. JUnit reports zero skips,
failures, or errors for the characterization assertions. Existing Alembic
path-separator deprecation and ORM MemoryRecord overlapping-relationship
warnings appeared; neither was repaired in this proof task.

The expired-worker case executes the real `_run_chat_task` and real terminal
writer. Event transports, cancellation lookup, lock release, and provider
dispatch are mocked to isolate the PostgreSQL seam. Generation is forbidden
and asserted absent. The atomic-adapter case represents already completed
generation entering persistence; it does not run a real provider or establish
that every assistant insert reaches this exact timing in supported Compose.

Evidence root:
`/private/tmp/codexify-chat-postgres-envelope-proof-5a1435d78-20261003/`.
Retained source fixture/runner, migration/proof log, XML, exact timestamp/wait/
durable readback JSON for both cases, and cleanup observations are available.
The temporary repository fixture was removed after byte-identical source
retention. Credentials were reused only in runner environment and were not
printed or committed. `git diff --check` passed; no application files changed.

## Whole-path re-evaluation and next obligation

Fresh ordinary browser success at `b67469c9a` remains valid for that evaluated
tip and healthy dependencies. This proof establishes a different failure:
PostgreSQL contention can keep an accepted task nonterminal beyond its whole
envelope, even when generation is never invoked. Increasing Compose stop grace
or adding drain handlers would not fix this causal seam.

The next already-authorized repair must carry the existing snapshot into both
raw psycopg and SQLAlchemy operations, enforce effective connect/statement/lock
limits, preserve transaction ownership and bounded rollback, and retain exact
terminal identity/precedence. Connection establishment, non-lock statements,
transport loss/rollback, outbox/Redis terminal publication, context/retrieval,
server-side command quiescence, and graceful drain need their own effective
bound evidence; no complete Slice C or safe-stop claim follows from these two
lock cases. Active-worker-loss semantics remain a separate human frontier.

This receipt is documentation follow-through. No current-state promotion,
main merge, push, runtime mutation, deployment, or memory update occurred.
The Goal remains active.
