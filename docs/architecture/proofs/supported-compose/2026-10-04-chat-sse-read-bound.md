# Bounded ordinary-chat task SSE reads — 2026-10-04

## Authority and evaluated source

Development Operator Level 0, architecture-impact, AUTHORIZED_IMPLEMENTATION,
EXECUTE → PROOF. Starting clean repair `6d5835ed3fbf8fedd4441a9cbbeac7903c033ece`,
branch `codex/chat-postgres-terminal-deadline-20261003`. Private Task Spec
preceded implementation. The ordinary-chat reliability Goal authorizes repair
of existing supported-path resource waits. ADR-038 distinguishes transport
visibility from task/provider outcome; ADR-087 preserves the original accepted
deadline. Existing message/attempt identity and API authorization stay intact.
No new ADR, runtime token, task authority or release claim.

## Repair and ownership

The supported generic `/api/tasks/{task_id}/events` route previously sent its
executor thread into `read_events`, whose queue client had no socket timeout and
whose exception loop retried indefinitely. Cancelling the coroutine could not
stop that thread. The route also retried after reader errors.

`guardian/queue/task_events.py::read_events_bounded` owns one read under the
existing physical Redis operation mechanism with a fixed two-second budget.
Positive BLOCK is at most 1,000 ms, count at most 100. Invalid limits fail before
starting a client. The owned native pool covers DNS/connect/transport waits and
native retry, closes on scope exit, and does not replace global request/queue
clients. It refuses to replace an inherited accepted budget. This observation
budget grants no task work and cannot extend an accepted work/terminal deadline.
The common decoder preserves event order, exact IDs, fallback type and malformed
JSON behavior. Count bounds cardinality; arbitrary payload CPU/memory decoding
is not proven to have a hard wall-clock bound by this task.

`guardian/guardian_api.py` uses that reader for the existing task SSE route.
Configured blocks are clamped to 1–1,000 ms; malformed configuration closes
before Redis. On read uncertainty it closes the subscription without inventing
a failed/cancelled/completed event, writing durable state, releasing a turn lock
or enqueueing work. Existing clients may reconnect with their cursor or read
[durable receipts](./2026-10-04-chat-orphan-ui-observation.md). Last-Event-ID,
terminal classification, event ordering and 15-second ping behavior remain.
The legacy reader used by separate voice/delegation/agent surfaces retains its
existing behavior; those surfaces were outside this ordinary-chat task.

Changed files: the two runtime files above,
`tests/queue/test_task_event_bounded_read.py`,
`tests/routes/test_chat_task_event_stream_bounds.py`,
`tests/queue/test_chat_redis_deadline.py`,
`tests/routes/test_chat_task_events_lifecycle.py`, and this receipt.
The existing lifecycle test's reader spy follows the new dependency; its
lifecycle assertions are unchanged. No provider, persistence, schema, auth,
queue acceptance, vector or worker mutation was added.

## Tests, native evidence and preserved failure

Evidence root:
`/private/tmp/codexify-chat-sse-read-bound-6d5835ed3-20261004/`.
Task Spec, original/final JUnit/logs, baseline failure, real Redis driver/results,
Ruff comparison, custody driver and concurrent-main checkpoint are retained.
Existing host virtual environment only; no install/download.

Focused command surface from repair repo:

```text
python -m pytest tests/queue/test_task_event_bounded_read.py tests/routes/test_chat_task_event_stream_bounds.py tests/queue/test_chat_redis_deadline.py guardian/tests/queue/test_task_events.py tests/routes/test_chat_task_events_lifecycle.py -k 'not test_worker_scopes_share_one_wall_and_monotonic_anchor' -q -s --junitxml=<private final-focused.xml>
python -m pytest tests/queue/test_chat_redis_deadline.py::test_supported_sse_cancelled_consumer_leaves_no_unbounded_reader -q -s --junitxml=<private cancel-physical.xml>
```

**66 focused tests and one physical cancellation test passed**, no errors/skips.
Actual generator checks cover read uncertainty without synthetic terminal,
disconnected consumer without a read, header cursor precedence, terminal
completion/failure/cancellation order, invalid/zero/oversized block controls,
pings and unchanged cursor. Reader checks cover positive bounded limits,
decoding, no queue client, no outer retry, and inherited-budget rejection.

A real TCP peer holds XREAD response with native Redis retry configured three.
The 0.25-second fixture operation returns timeout after **0.251832917 s**,
exactly one XREAD and peer EOF; global clients and budget context are preserved.
A second physical test starts the actual SSE generator and held executor-thread
read, cancels its coroutine, then observes reader completion and socket EOF
within the fixture bound. It does not claim cancellation kills Python threads
immediately; the owned transport budget finishes that work.

The retained worker Python executed the candidate event helper in memory,
against real Redis DB 15 with two generated private names and TTL. First
count-one read and resumed read returned exactly the original ordered IDs;
resume excluded its cursor and preserved terminal message payload. Empty BLOCK
returned in **0.125604166 s**. No global client changed or source file was written
inside the container. The private stream retained exactly two entries before
cleanup; independent Redis CLI confirmed both generated names absent afterward.
This is native mechanism proof, not a real accepted application turn.

Initial broad run: 63 passes, one existing worker-anchor fixture failure. That
same test copied byte-for-byte from starting HEAD failed independently with the
same `durable_attempt_unconfirmed` admission: its fake task supplies no durable
attempt evidence, so the later worker body cannot run. The worker and admission
logic were not changed here. This known pre-existing test remains failed and
explicitly deselected in the final focused run, not marked green or repaired
outside transport scope. Original and baseline failures are retained.

Scoped Ruff comparison found **91 identical inherited findings**, zero new.
It is not a clean full lint result. `git diff --check`, receipt-link checks and
`python3 scripts/validate_docs.py` passed. No full browser/deployment claim.

## Independent preservation and next obligation

All **1,138** frozen Guardian/backend runtime hashes match the retained source
and both app containers. Backend/worker start instants remain
`2026-10-04T21:47:17.506339553Z` / `2026-10-04T21:34:16.858728583Z`, restart zero.
Health `ok`, chat queue zero, locks absent, idle heartbeat with positive TTL,
evaluation/system queues 34/17. Thread 37 messages 70/71 contents and metadata
are unchanged; migration stays `d4c69e03a712`. No app source/schema refresh,
application request, service restart, replay or app Redis DB mutation occurred.

Main HEAD remains `0163521312ef767c0884654e70094ae7b44a5eec`, with the staged
dev-log deletion retained. The initial strict old-status custody check detected
additional concurrent main edits in architecture/KG/workspace/memory-vault/test
files. They were not changed by this task. A separate read-only status/hash
checkpoint records them; final verification matches that checkpoint. Main is
not claimed clean or identical to the previous turn's dirty-file inventory.

Full Goal remains active and release HOLD. Coherent candidate source/schema
refresh and fresh supported-path success, failure, orphan-loss, explicit retry,
restart and graceful-shutdown proof remain required. Unconfirmed admission and
permanent receipt-window exclusion remain separate recovery limitations. This
transport repair does not silently qualify the older retained application.
No release anchor, shared memory, push, merge or deploy change. Commit hash is
recorded in the Task closeout.
