# Production-Grade Chat Stabilization Plan

## 1. What “Production Grade Chat” Means (Beta Definition)

Beta scope is reliability-first: durable user message writes and reliable assistant completion visibility.

- Durability rule 1: user message must be persisted in Postgres before completion enqueue is attempted.
- Durability rule 2: assistant completion persistence is exactly-once at product level.
- Current gap: there is no first-class completion idempotency key in the current chat completion contract; beta hardening introduces a `turn_id` dedupe target (documented as future interface delta).
- Delivery rule: no phantom completions. If a task reaches terminal `completed`, UI must converge on the persisted assistant message or present explicit terminal failure.
- UI invariant: thread view must be reconstructable from `GET /chat/{thread_id}/messages` (or `/api/chat/{thread_id}/messages`) as server truth.

## 2. Current Architecture Reality (What Exists Today)

### Current (verified)

- Postgres is the system of record for threads/messages.
- Redis is used for completion queueing, per-thread turn locks, and task event streams.
- Worker chat pipeline is staged as: assemble -> generate -> persist -> emit events.
- Completion path baseline is:
1. `POST /chat/{thread_id}/messages` persists user message.
2. `POST /chat/{thread_id}/complete` enqueues chat completion task.
3. Worker persists assistant message.
4. UI converges against authoritative transcript fetch.
- Thread transcript convergence uses `GET /chat/{thread_id}/messages` as authoritative truth.
- Existing polling behavior in ChatView is baseline.

### If present (optional; verify per deployment)

- `/api/events` SSE for transcript events (for example `message.created`), only if implemented and enabled in the deployed environment.

### Target (planned)

- `/api/tasks/{task_id}/events` SSE for completion lifecycle state as the primary completion-status channel.
- Event-first UI updates with polling fallback for transcript convergence.

## 3. Misconceptions to Correct (Steer True)

- Correction 1: background task results must not be pushed into “the next assistant response.”
- Replacement primitive: task completion creates a durable result event plus an in-app notification banner plus a deep-link to the originating thread/task context.
- Assistant transcript is a conversation log, not an event bus.

- Correction 2: diagnostics must not leak into chat.
- Diagnostics (RAG traces, internal sensors, stack traces, infra details) belong in opt-in surfaces such as health/debug panels and task timelines, not the user-facing transcript.
- Frontend contract: optimistic local state is provisional; server fetch is authoritative truth.

## 4. Core Loop Stabilization Plan (Beta Critical Path)

### Checklist

- Message ordering and consistency:
- Normalize and render by `created_at ASC, id ASC`.
- Reconcile fetched transcript to prevent duplicates and out-of-order inserts.
- Completion idempotency and dedupe:
- Introduce a completion turn key (`turn_id`) to dedupe duplicate writes for the same turn.
- Event-first convergence plus polling fallback:
- Use events when available; always retain guarded polling fallback to `GET /chat/{thread_id}/messages`.
- Backpressure and request guards:
- Prevent overlapping completion submissions per thread.
- Prevent overlapping poll loops for the same in-flight turn.
- Turn lock policy:
- Enforce TTL, detect stale lock, and recover safely without silent hangs.

### Correlation / Idempotency Contract (future interface delta)

Define `turn_id` at completion-request acceptance time (UUID).

`turn_id` must flow through:
- completion enqueue payload,
- worker task metadata,
- persisted assistant message row metadata,
- task events payloads (if/when SSE exists).

`turn_id` enables:
- dedupe of duplicate completion writes,
- UI stop condition: stop polling once assistant message with matching `turn_id` arrives,
- phantom completion detection across logs, metrics, and UI convergence.

### Event and Polling Stop Conditions

Stop completion polling when any of the following occurs:
- assistant message with matching `turn_id` is visible in authoritative transcript,
- terminal task failure/cancel event is observed,
- inactivity timeout is reached and degraded terminal UX is shown.

### Turn Lock TTL and Stuck-Lock Recovery

- TTL policy: default 180s, minimum 15s.
- Stale-lock recovery:
- if lock is stale and no active progression signal exists, recover via owner-safe release.
- emit recovery log and metric for observability.
- never leave UI in an unbounded pending state.

### UX Definitions

Happy path UX:
- fast send acknowledgment,
- pending indicator for in-flight turn,
- assistant response appears via event or poll convergence,
- pending indicator clears.

Degraded path UX:
- clear failure banner with actionable retry,
- preserve user input state,
- no infinite spinner.

## 5. Failure Modes and How We Detect Them

### Operational Phantom Completion Definition

- Phantom completion = task reaches terminal `completed` (or server claims completion) but no assistant message exists for `(thread_id, turn_id)` within `N` seconds.
- Beta default `N`: 20 seconds.

Detection requirements:
- emit structured log event,
- increment metric,
- record visibility latency.

Required structured log fields:
- `thread_id`
- `turn_id`
- `task_id`
- `task_completed_at`
- `detected_at`
- `assistant_message_id` (nullable)
- `provider`
- `model`
- `worker_run_id` (if available)

Metric examples:
- `chat_phantom_completion_total`
- `chat_completion_visible_latency_ms`

### Failure-Mode Matrix

| Failure mode | Detection signals (logs/metrics/health/events) | Required user-visible banner | Actionable guidance |
|---|---|---|---|
| Redis down / queue unavailable | enqueue failure, `queue_unavailable`, `/health/chat` queue reachability false | “Completions are temporarily unavailable. Your message is saved.” | Retry after service recovery; check queue health |
| Worker down / task never completes | missing worker heartbeat, task inactivity timeout, no terminal event | “Assistant is delayed. You can retry this turn.” | Retry and inspect worker health |
| Provider timeout / upstream error | terminal task failure with timeout/upstream classification | “Model provider timed out. Retry or switch provider.” | Retry with fallback provider |
| Persist succeeded but UI didn’t refresh | DB has assistant row but UI did not converge in SLA | “Reply is ready but not visible yet. Refresh thread.” | Refresh thread; inspect event delivery path |
| UI refreshed but message missing (DB read mismatch) | completed task + no assistant row for `(thread_id, turn_id)` by `N` seconds | “Completion could not be confirmed. Retry this turn.” | Trigger phantom incident workflow |

### Minimum Metrics Set (Beta)

- enqueue/start/complete/fail counts
- completion latency
- lock acquisition failures
- polling fallback activation count
- phantom completion mismatch count

Reference metric names:
- `chat_completion_enqueue_total`
- `chat_completion_started_total`
- `chat_completion_completed_total`
- `chat_completion_failed_total`
- `chat_completion_latency_ms`
- `chat_turn_lock_acquire_failed_total`
- `chat_polling_fallback_activated_total`
- `chat_phantom_completion_total`
- `chat_completion_visible_latency_ms`

## 6. Event Delivery Strategy

### Short-term (beta)

Polling is acceptable with controlled cadence:

- base interval: 1.5s
- capped backoff: 5s
- jitter: ±20%
- hard timeout: 5 minutes
- stop when assistant with matching `turn_id` arrives or completion becomes terminal/inactive

Spinner policy:
- no spinner beyond 2 minutes without terminal banner and retry action.

### Mid-term

- adopt `/api/tasks/{task_id}/events` SSE for completion lifecycle updates,
- retain `/api/events` (if present) for transcript updates,
- keep guarded polling fallback for convergence and disconnect recovery.

### Notifications

- Beta target is in-app notification banner with deep-link to thread + task summary.
- Notification content must not be appended into assistant chat text.
- OS-level desktop notifications are out of scope for beta unless already implemented and verified.

## 7. Command Surface Roadmap (@Command.Name)

### Parsing Contract

- Detect `@Command.Name` token.
- Support quoting and escaping for arguments.
- Support multi-command input in one message.
- Fallback to plain chat when parse fails or command is unknown.

### Routing Contract

- command parse result -> command bus/tools invocation -> task events -> structured render block in chat.
- Commands produce tasks; tasks produce events; chat renders results from structured payloads.

### Safety Boundaries

- read-only commands can auto-run.
- mutating commands require explicit approval prompt/token.
- authorization enforced at invoke boundary.

### Output Schema (future interface delta)

Command results are structured blocks, not prose blobs.

Required fields:
- `status`
- `run_id`
- `summary`
- `details`
- `actions`

## 8. Flows / Cron / Tools Integration Strategy

### Chat Trigger Mappings (reference targets)

- create flow: `POST /api/flows`
- update flow: `PATCH /api/flows/{flow_id}`
- run flow: `POST /api/flows/{flow_id}/run`
- create cron job: `POST /api/cron/jobs`
- schedule/update cron job: `PATCH /api/cron/jobs/{job_id}`
- execute cron job now: `POST /api/cron/jobs/{job_id}/trigger`
- execute tool task: `POST /api/tools/execute`
- approval path: `POST /api/tools/approve`

### Result Visibility Model

- task timeline/event stream for lifecycle visibility,
- final artifact/result block in chat,
- escalation prompt for approval flows (approval token path),
- result rendering remains separate from assistant prose channel.

## 9. Implementation Sequencing (1–2 week Beta Path)

### Milestone 1: stop the bleeding

- lock/queue checks before and during completion flow,
- convergence guarantees from authoritative transcript fetch,
- degraded UX banners for all terminal failure states.

### Milestone 2: idempotency/dedupe + observability hardening

- implement `turn_id` correlation contract,
- enforce dedupe target behavior for duplicate completion writes,
- add phantom detection logs and metrics,
- add SLA dashboards for visibility and failures.

### Milestone 3: task-event SSE + in-app completion banner deep-linking

- wire completion lifecycle stream consumption,
- retain polling fallback as resilience path,
- ship in-app completion banner deep-linking to originating thread/task summary.

### Strict Beta Non-Goals

- no full natural-language command interpreter,
- no diagnostics in transcript,
- no injecting background task output into next assistant response,
- no workflow marketplace/polish before core loop reliability,
- no new OS-level desktop notification system unless already implemented.

## 10. Acceptance Criteria

Pass/fail criteria:

- Every accepted completion ends in either:
- persisted assistant message visibility, or
- explicit terminal failure state.
- No indefinite spinner without terminal UX.
- No phantom completion mismatch between task completion claims and thread history.
- Thread reload reconstructs correct transcript from server truth.
- `/health/chat` reflects worker heartbeat + queue reachability accurately.
- Failure-mode banners appear with actionable guidance.

SLA targets (beta):
- P95 assistant message visibility <= 15s under normal conditions.
- Terminal failure rendered <= 5s after task failure is known.
- No spinner longer than 2 minutes without terminal banner + retry.

### Scenario Matrix

| Scenario | Expected behavior | Pass condition |
|---|---|---|
| Happy path end-to-end (persist -> enqueue -> worker -> persist -> UI) | Assistant appears in thread with matching correlation key | Visible within SLA and pending clears |
| Redis down / queue unavailable | Completion not accepted, user message remains durable | Banner shown + retry path available |
| Worker down / task never completes | Inactivity and heartbeat checks detect stall | Terminal degraded banner shown |
| Provider timeout / upstream error | Task fails explicitly | Failure banner within SLA |
| Persist succeeded but UI didn’t refresh | Convergence miss detected | Refresh/retry resolves visibility |
| UI refreshed but message missing | Phantom detection fires | Metric/log emitted + terminal guidance shown |
| Reconnection/reload convergence | UI rehydrates from authoritative fetch | No duplicates or gaps |
| Duplicate submit/overlap guard | Second completion blocked while turn in flight | Single in-flight completion per thread |
| Stale lock recovery | Stale lock is safely recovered | New completion proceeds after recovery |
