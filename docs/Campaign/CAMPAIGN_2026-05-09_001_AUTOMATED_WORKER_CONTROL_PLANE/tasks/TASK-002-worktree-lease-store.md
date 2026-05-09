# TASK-002 Worktree Lease Store

## Objective
Introduce durable lease persistence and retrieval operations for worktree lease lifecycle.

## Scope
- Add durable storage model for leases.
- Implement create/update/expire/cleanup-intent store operations.
- Add lease lookup by `work_order_id`, `run_id`, and `worker_id`.

## Files likely to edit
- `guardian/db/models.py`
- `guardian/db/migrations/`
- `guardian/agents/store.py`
- `guardian/core/db.py`
- `tests/db/` and `tests/agents/`

## Validation expectations
- Migration applies cleanly in test environment.
- Store tests cover lifecycle transitions and uniqueness boundaries.
- Idempotent write behavior for repeated heartbeat updates.

## Non-goals
- No worker orchestration policy.
- No API exposure.
- No UI surface.

## Dependencies
- TASK-001 worktree lease contract.

## Completion criteria
- Durable lease rows persist with required fields.
- Lifecycle update operations are tested and deterministic.
- Recovery semantics for expired/abandoned leases are represented in storage contract.
