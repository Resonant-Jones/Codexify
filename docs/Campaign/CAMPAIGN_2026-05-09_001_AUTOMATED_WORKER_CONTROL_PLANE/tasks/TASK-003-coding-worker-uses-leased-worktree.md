# TASK-003 Coding Worker Uses Leased Worktree

## Objective
Require coding-worker execution attempts to run inside an assigned `WorktreeLease` context.

## Scope
- Enforce lease acquisition before mutable execution.
- Bind run attempts and retries to the same lease unless explicitly reissued.
- Emit lease-linked worker receipts.

## Files likely to edit
- `guardian/workers/coding_worker.py`
- `guardian/tasks/types.py`
- `guardian/agents/store.py`
- `guardian/queue/redis_queue.py` (only if payload extension is required)
- `tests/workers/` and `tests/agents/`

## Validation expectations
- Integration tests prove worker writes happen in leased worktree path.
- Retry tests prove lease continuity across attempts.
- Failure-path tests prove proper lease state updates.

## Non-goals
- No commit-after-green policy yet.
- No merge-candidate generation.
- No orchestrator selection logic.

## Dependencies
- TASK-001 worktree lease contract.
- TASK-002 worktree lease store.

## Completion criteria
- Worker refuses mutable execution without valid lease.
- Terminal receipts include `lease_id`, `branch_name`, and `worktree_path`.
- Lease heartbeat and terminal updates are persisted.
