# Bounded durable recovery in supported receipts and explicit retry

## Authority and scope

This Level 0 EXECUTE → PROOF Task invokes the directly human-authorized
post-terminal reconciliation policy through the existing supported chat path.
ADR-087/091 and durable attempt/message authority govern. Starting repair commit:
`3ca66cfb9`, branch `codex/chat-postgres-terminal-deadline-20261003`. No new ADR,
runtime token, recovery service, scheduler, queue, or worker-generation/lease
identity is introduced. The Task Spec and private raw evidence are retained at
`/private/tmp/codexify-chat-recovery-controller-3ca66cfb9-20261004/`.

## Behavior and changed surfaces

- `guardian/core/chat_completion_service.py` replaces stale-lock/heartbeat/Redis
  terminal-event recovery authority with exact durable request/task/thread/turn
  reconciliation. It reads the current lock under bounded Redis maintenance,
  reads/reconciles the exact attempt under a fixed two-second PostgreSQL scope,
  then uses the acknowledged terminal result's preserved task/token capability
  for strict atomic Redis cleanup. It never enqueues recovered work. An explicit
  caller still obtains a new task/request identity through ordinary acceptance.
- The lock's later safety expiry is not a replacement task deadline: a qualifying
  unresolved attempt can be orphaned after its original terminal deadline while
  the lock is still live. Durable assistant completion or existing terminal truth
  takes precedence. Missing identity, mismatched thread/turn, historical missing
  snapshot and unconfirmed admission cannot become inferred worker loss. A legacy
  attempt with **existing durable terminal truth** and exact current structured
  task/thread/turn binding may atomically compare its observed current token;
  that token/envelope is not persisted or backfilled.
- `guardian/routes/chat.py` bounds thread lookup, authorization and page query
  together before any recovery mutation. A separate fixed two-second PostgreSQL
  scope reconciles the authorized page (up to 100 attempts), not a renewed budget
  per row. Redis matching cleanup is a fixed bounded batch after durable commit.
  PostgreSQL uncertainty returns HTTP 503 without observational Redis fallback.
  Redis cleanup uncertainty retains and returns durable terminal truth; later
  receipt reads retry cleanup idempotently. Authorization errors, lookahead and
  pagination remain distinct and unchanged.
- `guardian/core/db.py` exposes the original immutable deadline snapshot in
  read-only attempt projections. Receipts expose the distinct canonical orphan
  failure detail; the lock token remains private and is defensively excluded at
  the route. The original accepted snapshot and post-enqueue acceptance
  confirmation timestamp retain their different meanings.
- Inspection found that terminal probes called the retrying queue-client XREAD
  path and could wait indefinitely. `guardian/queue/task_events.py` now probes
  with request-client XRANGE scans under an existing bounded maintenance scope.
  Standalone diagnostics own a scope; receipt observation shares one page-wide
  Redis scope. Exclusive cursors, descriptor classification and event decoding
  are preserved. A held/failed probe reports observation uncertainty, not task
  execution failure. Live SSE `read_events` behavior was not changed.
- The old non-atomic clear and unbounded recovery audit write are removed from
  this path. It no longer emits an orphan event for a completed/cancelled/failed
  task merely because its lock was cleaned. Durable attempt outcome and receipts
  are the recovery evidence; an observation never reconstructs the deadline or
  infers death timing.

PostgreSQL fencing and Redis owner/token cleanup each have local atomicity; no
cross-store atomic transaction is claimed. If an acknowledgement is uncertain,
durable truth is re-read, never undone or silently replayed.

## Validation and limits of evidence

From the repair repo using `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`:

```text
python -m pytest tests/core/test_turn_lock_recovery.py \
  tests/test_thread_task_receipts.py \
  tests/core/test_chat_completion_attempt_persistence.py \
  tests/tasks/test_chat_completion_deadline.py \
  tests/queue/test_chat_redis_deadline.py -q -s
102 passed; no errors, failures or skips

python -m pytest tests/db/test_chat_recovery_controller.py \
  tests/db/test_chat_completion_attempt_migration.py -q
12 passed on native PostgreSQL 15; no errors, failures or skips
```

After including the initial thread/authorization lookup in the resource scope,
the four native controller cases and 37 route/recovery cases were rerun and
passed. These counts overlap; they are not additional unique-test totals.

The focused cases cover completed/failed/cancelled priority; refusal to consult
heartbeat or Redis terminal evidence for recovery; live-lock safety margin;
exact identity mismatch; uncertainty and unavailable persistence; legacy terminal
capability comparison; new accepted queue identity with no recovery replay;
authorization before mutation; private-token exclusion; cleanup failure and
idempotent retry; original envelope/admission ambiguity; and non-sliding page
budgets. New code does not create a fake accepted-task budget for maintenance.

Native PostgreSQL invokes the real receipt/retry controller and reconciliation
helper. It proves the orphan is already durably committed when the cleanup
callback executes; a cleanup exception preserves that truth and a later read
retries with the exact token. It verifies original snapshot retention, orphan
receipt readback, recovery before lock safety expiry without enqueue/heartbeat,
legacy/unconfirmed admission remaining unknown, and injected persistence failure
returning 503 with no cleanup or Redis truth fallback. The cleanup callback is a
test seam; this is not combined production PostgreSQL/Redis/worker recovery proof.
All generated disposable proof databases were independently absent afterward.

A held real XRANGE response ended in **0.252918 seconds** under a 0.25-second
maintenance budget: exactly one command, physical peer EOF, unknown observation,
no XREAD fallback, and restored scope/client. An owned ephemeral `docker exec`
process loaded the candidate event-probe module only into its own memory and
verified native Redis 7 logical DB 15 nonterminal/terminal/missing classification,
exclusive scanning past 100 events, and completed payload/task identity. Its
single generated stream key was removed and independently confirmed absent.
No app DB 0 queue/task/event mutation occurred.

Changed tests pass Ruff. Frozen/candidate comparison finds zero introduced
findings in DB (three inherited), service (15 inherited), routes (ten inherited)
and event helpers (five inherited). One newly unused service import found during
lint was corrected; the initial candidate lint evidence is preserved. Targeted
compileall, `git diff --check`, and docs validation pass. Initial passing
focused/native runs preceding the bounded-probe refinement are also retained.

## Custody and remaining Goal work

The retained app is not refreshed to this candidate. Independent checks match
all 1,138 frozen source hashes in its snapshot and both containers; confirm
unchanged backend/worker lifecycle, application migration `d4c69e03a712`, health
`ok`, idle chat heartbeat with positive TTL, empty chat queue/no turn locks,
eval/system queues 34/17, and unchanged thread 37 messages 70/71 and metadata.
Main `0163521312ef767c0884654e70094ae7b44a5eec` and its staged Dev Log deletion are
preserved. No application restart, worker kill, model load, browser submission,
host installation, memory write, push, merge, or deployment occurred.

The full Goal remains active and release qualification HOLD. Required next work
includes preventing late worker publication from contradicting the durable orphan,
truthful frontend/operator projection and explicit new-request/task retry, then
fresh supported-Compose success and important failure/recovery evidence on the
coherent refreshed candidate. Historical missing snapshots and unconfirmed
post-enqueue admission still cannot be honestly reconstructed; accepted-degraded
ambiguity remains an explicit obligation. Confirmed-generation recovery remains
parked under the human authorization. No KB/memory addition was made.
