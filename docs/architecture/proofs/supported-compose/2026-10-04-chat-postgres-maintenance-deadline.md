# PostgreSQL bounds for post-terminal recovery maintenance

## Authority and scope

Direct human authorization permits reconciliation after an accepted task's original
terminal deadline, preserving durable attempt/message authority and the original
non-sliding envelope. That controller work needs resource bounds without granting
expired tasks more execution time. This Level 0 EXECUTE → PROOF prerequisite
extends the existing PostgreSQL resource adapter; it does not introduce a new
recovery service, worker-generation/lease identity, execution queue, or scheduler.
ADR-087/091 and the existing durable completion boundary govern; no new ADR or
runtime token is allocated.

Frozen starting repair commit: `53aba0fd723c1016d2cef3e494765f4afe0c7005` on
`codex/chat-postgres-terminal-deadline-20261003`. Task Spec, native and focused
logs/XML, driver exits, cleanup and custody evidence are retained at
`/private/tmp/codexify-chat-postgres-maintenance-53aba0fd7-20261004/`.

## Change

`guardian/core/chat_postgres_deadline.py` adds a finite, non-sliding
`postgres_operation_scope`. It reuses existing connection/query/pool/DNS physical
wait enforcement. Expiry raises the distinct internal `PostgresOperationTimeout`,
closes owned native query/connection waits, restores pool admission safely, and
reaps owned resolver children. It does not generate an AcceptedChatTaskDeadline
or report the original chat as a controlled deadline failure.

Maintenance cannot replace an inherited resource scope, and accepted-task scopes
cannot replace active maintenance. Maintenance also rejects accepted child-work,
vector-search deadline admission, and terminal-reserve authority. Existing
accepted work/terminal scopes keep their original fixed 720/60 envelope and
canonical failure classification. The adapter selects bounded native connections
for either resource scope; this selection grants no execution authority.

A maintenance timeout means recovery was not confirmed. Closing the local socket
cannot prove whether a remote commit executed. The reconciliation helper still
returns only after acknowledged commit; the controller must preserve uncertainty
and re-read durable truth, without rolling back acknowledged terminal truth or
silently replaying work.

## Validation

From the repair repo using `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`:

```text
python -m pytest tests/db/test_chat_postgres_maintenance_deadline.py \
  tests/db/test_chat_postgres_deadline.py \
  tests/db/test_chat_postgres_connect_deadline.py \
  tests/db/test_chat_postgres_dns_deadline.py \
  tests/db/test_chat_postgres_pool_deadline.py \
  tests/db/test_chat_completion_attempt_migration.py -q -s
65 passed; no errors, failures or skips

python -m pytest tests/db/test_chat_postgres_maintenance_deadline.py \
  -m 'not integration' -q -s
8 passed; no errors, failures or skips
```

The native driver privately supplies the existing proof PostgreSQL 15 connection
and creates only the fixture's disposable `codexify_attempt_<uuid>` databases.
The first command includes the original query/connect/DNS/pool regressions and all
eight migration/attempt tests. After adding explicit maintenance resolver tests,
the second command covers those two new cases plus six previously passing cases;
these counts overlap and are not a unique-test total. No failing test was hidden.

New physical observations captured in the logs:

- Held TCP handshake: 0.251370 seconds under a 0.25-second maintenance budget;
  startup bytes observed and peer EOF before peer release.
- Actual durable reconciliation under a PostgreSQL row lock: 0.501476 seconds
  under a 0.5-second maintenance budget. The server lock wait was observed,
  the operation ended and server became quiescent before unlock, and no orphan or
  assistant binding appeared. A fresh bounded operation after unlock persisted
  the distinct orphan outcome, preserving the original deadline snapshot/token.
- Actual raw/ORM `pg_sleep(1)` waits: 0.251346 / 0.251753 seconds under 0.25-second
  budgets, server quiescence verified and unscoped statement limits restored.
- Exhausted 15-connection ORM pool: 0.255085 seconds under a 0.25-second budget;
  no expired borrower admitted, capacity/shared 30-second pool policy preserved,
  and a later legacy borrower retained ordinary statement limits.
- Held native resolver: raw/ORM 0.503801 / 0.503376 seconds under 0.5-second budgets;
  both owned children were killed/reaped, pipes closed and PIDs independently
  absent. Only addressing inputs crossed the resolver pipe.

Invalid/nonfinite budgets, non-sliding remaining time, inherited-scope protection,
and denied accepted child/terminal-reserve authority also pass. Scoped Ruff,
targeted compileall, `git diff --check`, and documentation validation pass. An
optional shell process inventory was denied by the filesystem/process sandbox;
authoritative exec handles subsequently returned exit zero, and the physical
resource/child checks above established completion without that inventory.

## Custody and outstanding integration

The repair changes are not mounted into the application. Independent read-only
checks match the 1,138 frozen source hashes in the retained source snapshot and
both app containers, unchanged start times/restart counts, migration
`d4c69e03a712`, health `ok`, idle chat heartbeat with positive TTL, empty chat queue
and no turn locks, eval/system queues 34/17, and thread 37 messages 70/71 plus
metadata. A separate PostgreSQL catalog read found no disposable proof databases
remaining. Main `0163521312ef767c0884654e70094ae7b44a5eec` and its unrelated staged
Dev Log deletion are unchanged.

No application source/schema refresh, restart, worker kill, model load, browser
submission, install/download, memory write, push, merge, or deployment occurred.
The full Goal stays active and release qualification HOLD. Required next work is
bounded controller invocation and strict matching-token Redis cleanup, removal
of heartbeat/death inference from supported recovery, truthful durable/UI/operator
projection and late worker publication, new-request/task-only explicit retry, and
fresh important supported-Compose failure/recovery evidence. Historical snapshots
and unconfirmed admission are not reconstructed from Redis or later clocks;
confirmed-generation worker-loss recovery remains parked as authorized.
