# Chat Reliability Hardening Draft

## Purpose
Define a concrete hardening plan that makes chat reliability durable (not temporary), reduces dropped messages, and eliminates invisible failures through bounded retries and instructive user notifications.

## Date
2026-05-17

## Problem statement
Current chat execution remains operationally coupled to Redis for queue transport, turn locks, cancellation flags, task-event streams, and worker heartbeat.

Evidence anchors:
- Redis queue enqueue/dequeue: `guardian/queue/redis_queue.py`
- Turn locks: `guardian/queue/turn_lock.py`
- Completion route acceptance depends on turn-lock + enqueue: `guardian/routes/chat.py`
- Task lifecycle stream for chat is Redis-backed: `guardian/guardian_api.py` (`/api/tasks/{task_id}/events`)
- `/health/chat` already calls out queue/heartbeat degradation: `guardian/routes/health.py`
- Known residual risks: `docs/architecture/tech-debt-and-risks.md`
- Compose Redis is non-durable today (`--appendonly no`, `--save ""`): `docker-compose.yml`

## Durable vs temporary outcome
This plan is durable if and only if we move completion attempt truth and retry lifecycle into Postgres-backed records.

Temporary mitigation only:
- Better health checks
- Better retry copy
- Redis config tweaks without durable attempt ledger

Durable mitigation:
- Postgres-backed chat attempt ledger
- DB-anchored retry state machine
- Deterministic terminal failure semantics
- Durable event replay for lifecycle evidence

## Goals
1. Reduce dropped-message scenarios caused by queue restart/eviction races.
2. Remove invisible failures by making every terminal path explicit and inspectable.
3. Add bounded automatic retries for retryable failure classes.
4. Ensure all user-visible failure messages are instructive and action-oriented.

## Non-goals
- No collapse of the queue acceptance model from ADR-001.
- No claim that route acceptance equals completion.
- No broad federation/command-bus redesign in this slice.

## Target runtime model
### Nodes
- API route node (`guardian/routes/chat.py`)
- Worker node (`guardian/workers/chat_worker.py`)
- Redis transport node (queue, short-lived wakeups)
- Postgres durable truth node (attempt state + events)
- Frontend node (request-state rendering + user actions)

### Trust boundaries
- API boundary: accepts request and creates durable attempt record
- Worker boundary: claims queued attempts and mutates attempt lifecycle
- Transport boundary: Redis may fail; durability must survive that failure
- UI boundary: shows user only explicit runtime truth from attempt lifecycle

### Failure model assumptions
- Honest-but-buggy runtime failures
- Process restarts
- Redis transient unavailability
- Provider transient failures and timeouts

## State model (aligned to existing runtime contract)
Use canonical request states from `docs/architecture/chat-runtime-contract.md`:
- `queued`
- `dispatching`
- `awaiting_ack`
- `awaiting_model`
- `awaiting_first_token`
- `streaming`
- `completed`
- `cancelled`
- `timed_out`
- `failed_retryable`
- `failed_fatal`
- `orphaned`
- `replayed`

## Retry loop contract
### Policy
- Retry only retryable failures.
- Retry immediately for first retry, then bounded backoff.
- Hard cap retries using max attempts.
- When cap is reached, emit terminal failure with instructive action.

### Recommended defaults
- `CHAT_COMPLETION_MAX_ATTEMPTS=3` (1 initial + 2 retries)
- Backoff schedule (ms): `[0, 750, 2000]`
- Jitter: +/-20%
- Retryable classes:
  - queue transport transient unavailability
  - worker dispatch transient failure
  - provider timeout / transient 5xx
  - explicit `failed_retryable`
- Non-retryable classes:
  - validation failures
  - auth/permission failures
  - unsupported capability errors
  - explicit `failed_fatal`

### Required emitted lifecycle events
- `task.created`
- `task.attempt_started`
- `task.retrying` with `{attempt, max_attempts, reason_code, next_retry_ms}`
- `task.completed` OR `task.failed` OR `task.cancelled`

## Instructive notification contract
Every terminal non-success response shown to users must include:
- What happened (plain status)
- What the system already did (retry count / fallback attempted)
- What the user can do next (explicit action)

### Required payload fields
- `error_code`
- `reason_code`
- `attempt`
- `max_attempts`
- `retry_exhausted` (bool)
- `recommended_action` (string token)
- `user_message` (fully rendered fallback-safe text)

### Notification templates
- Queue unavailable, retries exhausted:
  - "We could not start your reply after 3 attempts. Check Docker/Redis health, then press Retry."
- Provider timed out, retries exhausted:
  - "The model timed out after 3 attempts. Retry now or switch to a faster model."
- Turn already in flight:
  - "A reply is already running for this thread. Wait for it to finish or cancel it, then retry."
- Fatal validation error:
  - "This request could not run because required inputs were invalid. Edit the message and try again."

## Implementation slices
### Slice A: Transport hardening now (low blast radius)
1. Make queue Redis durable in non-dev profiles (`appendonly yes`, snapshotting, persistent volume).
2. Remove eviction policy risk for queue Redis (`noeviction` for queue instance).
3. Keep `/health/chat` status_reason explicit and machine-readable.

Deliverable: fewer losses from restart/eviction, but not full durability guarantee yet.

### Slice B: Durable attempt ledger (core durability slice)
1. Add `chat_attempts` table:
   - `attempt_id`, `thread_id`, `message_id`, `task_id`, `attempt_number`, `status`, `error_code`, `reason_code`, `created_at`, `started_at`, `ended_at`, `retry_of_attempt_id`, `idempotency_key`
2. Add `chat_attempt_events` append-only table:
   - ordered lifecycle evidence (`sequence`, `event_type`, `payload_json`, `created_at`)
3. Route writes durable `queued` attempt before enqueueing Redis wakeup token.
4. Worker claims attempt and performs atomic state transitions.
5. Retry loop mutates attempt state and creates successor attempts up to cap.

Deliverable: durable completion truth independent of Redis continuity.

### Slice C: Visibility hardening (eliminate invisible failures)
1. Dual-write task lifecycle to durable event lane and Redis stream during migration.
2. Prefer durable replay for `/api/tasks/{task_id}/events` when available.
3. Keep Redis stream as low-latency mirror until parity proof passes.

Deliverable: dropped UI visibility no longer implies invisible terminal state.

## Acceptance criteria
1. No accepted request can end without terminal attempt state (`completed`, `failed_*`, `cancelled`, `orphaned`).
2. Retryable failures auto-retry up to configured max attempts.
3. Retry exhaustion always returns instructive user text + actionable next step.
4. Attempt history is queryable after restart.
5. Health surfaces distinguish:
   - transport degradation
   - worker degradation
   - retry exhaustion
   - fatal validation failure

## Test plan
### Backend
- Route acceptance still follows ADR-001 (acceptance != completion)
- Retry loop attempts exactly `max_attempts`
- Retry exhaustion produces terminal `failed_retryable` with instructive payload
- Non-retryable failures do not retry
- Restart simulation preserves attempt history and terminal visibility

### Frontend
- User sees attempt progress and retry count where applicable
- Terminal failure copy includes explicit next action
- `turn_in_flight` messaging remains thread-specific and non-ambiguous

## Rollout strategy
1. Ship Slice A with no contract break.
2. Ship Slice B behind feature flag (`CHAT_DURABLE_ATTEMPT_LEDGER=1`).
3. Run dual-write proof window.
4. Promote durable attempt ledger to default.
5. Degrade Redis role to transport acceleration only.

## Notes
- This draft preserves ADR-001 semantics while hardening durability and observability.
- If implemented fully, this is not a temporary patch; it is a durable runtime contract improvement.
