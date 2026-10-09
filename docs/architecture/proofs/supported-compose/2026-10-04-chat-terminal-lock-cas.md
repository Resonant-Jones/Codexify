# Strict terminal-attempt turn-lock cleanup

## Authority and scope

This Level 0 EXECUTE → PROOF Task implements the Redis cleanup prerequisite of the
human-authorized deadline-bound reconciliation policy. It follows the durable
attempt/message boundary and ADR-087/091. The starting commit was `ff17a9224` on
`codex/chat-postgres-terminal-deadline-20261003`. Task Spec and raw evidence:
`/private/tmp/codexify-chat-terminal-lock-cas-ff17a9224-20261004/`.

Main remains `0163521312ef767c0884654e70094ae7b44a5eec`, including its unrelated
staged Dev Log deletion. No release claim, ADR, runtime token, new worker
lease/generation identity, host installation, memory write, push, merge, or
deployment was added.

## Implementation

`guardian/queue/turn_lock.py` adds `release_terminal_attempt_turn_lock`. A recovery
controller must invoke it only after acknowledged durable terminal truth, inside
the existing Redis maintenance operation scope. It accepts the existing task
owner and preserved token; a single Lua operation compares thread, task owner,
and token before deletion. An absent lock is idempotent success. Replacement,
malformed, incomplete and legacy values fail closed and remain unchanged.

There is no separate GET/DELETE fallback. Missing EVAL support, script failure,
or transport failure propagates. An ambiguous Redis acknowledgement cannot undo
the durable fence or authorize work replay. A subsequent cleanup attempt may
safely confirm absence or preserve a replacement. Legacy release/clear helpers
were not changed in this prerequisite.

PostgreSQL and Redis remain separate stores. The durable terminal row fence and
Redis's owner/token comparison each have local atomicity; this is not a claim of
a distributed atomic transaction. Controller integration must commit durable
truth first, preserve it if cleanup fails, and permit retry only with new
request/task identity.

## Verification

Using `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python` from the repair checkout:

```text
python -m pytest tests/queue/test_turn_lock.py \
  tests/queue/test_terminal_turn_lock_cleanup.py \
  tests/queue/test_chat_redis_deadline.py -q
52 passed; 12 native-only cases skipped on the host

python -m pytest tests/queue/test_chat_redis_deadline.py::test_terminal_cleanup_held_eval_closes_under_maintenance_budget -q -s
1 passed; EVAL held response closed in 0.254942 seconds under a 0.25-second budget
```

The held-response proof observed exactly one EVAL command, physical peer EOF,
Redis timeout rather than a fabricated accepted-task failure, context restoration,
and no non-atomic fallback. Its captured duration and process completion are in
`physical.log` / `physical.xml`.

A separate owned `docker exec` process loaded the candidate module only into its
own memory and ran the cleanup tests on native Redis 7 logical DB 15: **15 passed,
no failures/errors/skips** (three script contract cases and twelve native cases).
The application service processes and `/app` source were not refreshed. The
native cases cover exact/idempotent cleanup; changed owner, token or thread;
plain legacy owner, JSON string, malformed JSON, array, null, number, incomplete
binding; and simultaneous replacement versus cleanup. Replacement bytes and TTL
were preserved. All twelve generated keys had TTL safety and fixture cleanup;
an independent `redis-cli -n 15 EXISTS <exact owned keys>` returned zero. No FLUSH
or app DB 0 queue/task/event writes occurred. The private owned-key manifest is
`owned-key-cleanup.json`.

New tests pass Ruff; the module retains one baseline unused `typing.Optional`
finding, with zero new code/message findings against `ff17a9224`. Targeted
compileall, `git diff --check` and docs validation pass. Native bootstrap warnings
are retained: initial isolated pytest marker warnings were resolved by registering
the existing integration marker in the private driver; the remaining anyio
assertion-rewrite warning is not suppressed. No failing test result was hidden.

## Custody and outstanding integration

Independent read-only checks match 1,138 frozen source hashes in the retained
snapshot and both app containers, confirm unchanged backend/worker start times
and restart counts, application migration `d4c69e03a712`, health `ok`, idle chat
heartbeat with positive TTL, empty chat queue/no app turn locks, and eval/system
queues 34/17. Thread 37 messages 70/71 and metadata are unchanged. The retained
application runs the previous candidate, not the new PostgreSQL or Redis
prerequisites; no app migration, restart, worker kill or browser submission was
performed.

The full Goal remains active and release qualification HOLD. Next Tasks must wire
bounded maintenance reconciliation and cleanup into the supported path, replace
heartbeat/death inference for supported attempts, project orphan truth to durable
receipts/UI/operators, prevent late contradictory worker publication, and prove
explicit new-request/task retry and important supported-Compose failure/recovery
cases. Historical envelopes and unconfirmed admission remain honestly unresolved;
they are not reconstructed from Redis or later clocks. Confirmed-generation
worker-loss recovery stays parked under the human authorization.
