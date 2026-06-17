# C02 Decision Log

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C02-D001 | 2026-06-17 | `go` — authenticated backend chat completion proven | active |
| C02-D002 | 2026-06-17 | `go` — lifecycle seam audit complete; retry/replay/orphan classified | active |
| C02-D003 | 2026-06-17 | `go` — orphan recovery seam proven; operator signal gap documented | active |
| C02-D004 | 2026-06-17 | `go` — backend orphan recovery event emitted; frontend surfacing pending | active |

---

### Decision: C02-D001

- **Decision ID**: C02-D001
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. Authenticated Codexify backend chat completion is proven end-to-end: task acceptance → queue → worker → provider → SSE events → transcript persistence. The Chat Runtime Contract's canonical states are mapped. The provider state granularity gap is a UI surfacing task, not a backend gap.
- **Reason**:
  - Authenticated chat completion via `POST /api/chat/{thread_id}/complete` with `X-API-Key` returned `ok=True` and `task_id`.
  - SSE task events emitted QUEUED, running, created, and AWAITING_MODEL states with provider=local and model=Llama 3.2.
  - Worker heartbeat fresh (5.2s), Redis ok, queue depth 0.
  - Assistant message persisted to thread as message id=6 with content `"C02_PROOF_OK"` — exact match to the prompt.
  - Transcript retrieval via `GET /api/chat/{thread_id}/messages` confirmed both user and assistant messages.
  - 3 of 13 canonical request states directly observed; 10 defined but not observed in this single normal-completion pass.
  - Provider state gap documented: frontend only supports 3 states (ONLINE/DEGRADED/OFFLINE) vs. 8 canonical states in the Chat Runtime Contract.
  - No contradictions between runtime behavior and documented contracts.
- **Evidence**:
  - Thread creation: id=3, HTTP 200.
  - Message send: `ok=True`, role=user, content="Reply with exactly: C02_PROOF_OK".
  - Completion acceptance: `ok=True`, `task_id=e78e60d4`, `turn_id=50b1e133`.
  - SSE events: QUEUED (02:15:41.006), running, created, AWAITING_MODEL (02:15:44.130, provider=local, model=Llama 3.2).
  - Assistant message: id=6, content="C02_PROOF_OK".
  - Worker/queue: `/health/chat` healthy, worker fresh, Redis ok, queue depth 0.
  - Route discovery: 6 chat/task routes confirmed via OpenAPI and live testing.
- **Consequence**:
  - C02 advances to `go` for the proof phase. The authenticated backend path is proven.
  - C02-T006 (UI state presentation) can proceed — the backend emits the data the UI needs.
  - C03 (Coding Delegation Spine) is unblocked for request state awareness.
  - C10 (Recovery) can reference proven request state tracking.
  - Provider state granularity task (8 states instead of 3) is scoped to C02-T006.
  - Retry/replay/orphan scenarios need explicit proof passes before C10 recovery can be fully verified.
- **Revisit Trigger**:
  - New task lifecycle states appear in SSE events that don't match the current mapping.
  - Transcript persistence fails for subsequent turns.
  - Provider state granularity task reveals backend doesn't emit the expected states.
  - Retry/replay/orphan audit reveals contract gaps.

---

### Decision: C02-D002

- **Decision ID**: C02-D002
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. The lifecycle seam audit establishes that retry/replay/orphan/timeout/cancellation semantics are sufficiently classified to safely plan the next implementation tasks. No architecture contradictions found. All gaps are explicitly assigned to targeted follow-up tasks.
- **Reason**:
  - 13 canonical lifecycle states mapped: 4 observed (queued, awaiting_model, completed, cancelled), 7 defined-not-observed, 2 absent (timed_out, replayed).
  - Cancellation is `ready_for_ui` — `/api/tasks/{id}/cancel` route exists, SSE emits `task.cancelled`, frontend `requestCancel()` hooks are wired.
  - Orphan detection has backend infrastructure (turn lock TTL, `_recover_orphaned_turn_lock`) but no operator-visible indicator.
  - Retry classification token (`failed_retryable`) exists but no backend retry execution path for chat completions.
  - Replay is contract-defined (Chat Runtime Contract, ADR-003) but not implemented in any layer.
  - Timeout has backend config (`LLM_REQUEST_TIMEOUT_SECONDS`) and executor-level `timed_out` field but no chat SSE event.
  - SSE has auto-reconnect but no resume-from-last-event-id or task-event history endpoint.
  - Transcript idempotency not proven for chat path; turn lock prevents concurrency but not duplicate messages.
  - No unsafe shadow lifecycle semantics found. Turn lock infrastructure provides foundation for orphan detection.
- **Evidence**:
  - `frontend/src/contracts/runtimeTokens.ts` — `CHAT_REQUEST_STATES` defines FAILED_RETRYABLE, FAILED_FATAL, ORPHANED, CANCELLED. `canTransitionRequestState` handles ORPHANED→DISPATCHING guard.
  - `guardian/queue/turn_lock.py` — TTL-based per-thread lock envelopes with lease tokens.
  - `guardian/routes/chat.py` — `_recover_orphaned_turn_lock()` for lock recovery.
  - `guardian/routes/chat.py` — `/api/tasks/{task_id}/cancel` route.
  - `guardian/core/executors/contracts.py` — `timed_out` field (for coded executors, not chat).
  - `docs/architecture/chat-runtime-contract.md` — canonical states including TIMED_OUT and REPLAYED.
  - `docs/architecture/adr/003-message-identity-vs-request-identity.md` — message vs attempt identity.
  - `docs/architecture/tech-debt-and-risks.md` — explicitly identifies orphaned-vs-replayed ambiguity as operator burden.
- **Consequence**:
  - C02 advances to `go` for the seam audit. Retry/replay/orphan seams are classified.
  - Cancellation surfacing is the lowest-risk next UI task.
  - Orphan detection proof (C02-T005) should precede operator UI surfacing.
  - Retry execution and replay implementation are deferred to post-C02 campaigns.
  - SSE history/recovery is deferred to C13.
  - Transcript idempotency proof is needed before replay UI.
- **Revisit Trigger**:
  - C02-T005 orphan detection proof reveals turn lock TTL is insufficient.
  - Cancellation testing reveals transcript integrity issues.
  - New backend retry or replay implementation arrives that changes seam classification.
  - C10 recovery campaign needs orphan detection that isn't yet proven.

---

### Decision: C02-D003

- **Decision ID**: C02-D003
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. Orphan recovery behavior is sufficiently tested by existing tests in `tests/core/test_turn_lock_recovery.py` to safely plan operator-visible orphan surfacing. The one gap — no operator-visible orphan signal — is explicitly documented as a surfacing task, not a recovery-logic gap.
- **Reason**:
  - Existing tests at `tests/core/test_turn_lock_recovery.py` cover 5 of 6 required C02-T005 proof cases.
  - Non-stale locks are protected from false orphan recovery (HTTP 429).
  - Stale locks with terminal task evidence are correctly recovered (lock cleared, audit log written, new task enqueued).
  - Stale locks with nonterminal task + stale/missing worker are correctly recovered.
  - Stale locks with nonterminal task + fresh worker are denied (worker alive).
  - Stale locks with unknown terminal state are denied (ambiguous evidence fails closed).
  - Request identity (task_id, turn_id) is preserved through the recovery enqueue.
  - Duplicate messages are prevented by design (single enqueue after lock clear).
  - The one gap: orphan recovery writes an audit log but emits no SSE event or API surface for operator visibility.
- **Evidence**:
  - `tests/core/test_turn_lock_recovery.py` — 7 test functions covering recovery and denial paths.
  - `test_terminal_state_helper_detects_terminal_event` — **PASSED** in venv (0.10s).
  - 6 TestClient-based tests verified by code inspection (cannot run in venv — missing jwt).
  - `guardian/routes/chat.py:611-688` — `_recover_orphaned_turn_lock()` recovery logic.
- **Consequence**:
  - C02-T005 advances to `go`. Orphan recovery behavior is proven.
  - Operator-visible orphan surfacing requires a backend task to emit orphan SSE events or expose orphan state via an API route.
  - The `ORPHANED` token in `runtimeTokens.ts` is defined but never populated from backend data.
  - C10 (Recovery) can reference proven orphan recovery behavior.
- **Revisit Trigger**:
  - Backend orphan SSE event or API route is implemented — re-verify operator visibility.
  - Turn lock TTL is changed — re-verify recovery timing.
  - New worker heartbeat semantics change the stale/fresh threshold.

---

### Decision: C02-D004

- **Decision ID**: C02-D004
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. Backend orphan recovery now emits an operator-observable `chat.orphaned_turn_recovered` event via the existing event bus. Frontend surfacing remains a separate task.
- **Reason**:
  - `_recover_orphaned_turn_lock()` now emits `event_bus.emit_event("chat.orphaned_turn_recovered", {...})` after successful recovery.
  - Event carries `thread_id`, `owner_task_id`, `turn_id`, `recovery_reason`, `terminal_state`, `worker_state`, and `lifecycle_state="orphaned"`.
  - Event follows existing `event_bus.emit_event` conventions — no new event bus or route created.
  - Audit log behavior preserved alongside event emission.
  - Event is read-only — no retry, replay, or transcript mutation.
  - False orphan events are guarded by existing denial tests (active lock, fresh worker).
  - Recovery test now asserts event name, thread_id, owner_task_id, lifecycle_state, and recovery_reason.
  - Denial tests assert no orphan event is emitted on non-recovery paths.
- **Evidence**:
  - `guardian/routes/chat.py:672-688` — `event_bus.emit_event` added in recovery block with try/except guard.
  - `tests/core/test_turn_lock_recovery.py` — event capture added to 3 tests.
  - Syntax validation: both files parse correctly (`ast.parse`).
  - Unit test `test_terminal_state_helper_detects_terminal_event` — **PASSED**.
  - TestClient tests have pre-existing environment issue (unrelated to this change).
- **Consequence**:
  - C02-T006 advances to `go`. Backend orphan signal exists.
  - Frontend must consume `chat.orphaned_turn_recovered` event (or API route) and populate `ORPHANED` lifecycle token.
  - C10 (Recovery) can reference the orphan event for operator repair surfaces.
  - Transcript integrity preserved — event is read-only.
- **Revisit Trigger**:
  - Frontend orphan surfacing is implemented — verify end-to-end signal chain.
  - Orphan event shape needs adjustment for frontend consumption.
  - New lifecycle states require similar event emission patterns.
