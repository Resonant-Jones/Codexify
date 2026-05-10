# TASK-002 Worktree Lease Store

## Objective
Introduce durable Postgres-backed lease persistence and retrieval operations for worktree lease lifecycle.

## Phase alignment
- This is the intended implementation task for Phase 2 in the campaign rollout plan.
- It persists control-plane lease state only.

## Scope
- Add durable storage model for leases.
- Add a migration for `coding_worktree_leases`.
- Implement create/read/list/lifecycle/cleanup-intent store operations.
- Add lease lookup by `work_order_id` and active-state inspection.

## Files created
- `guardian/agents/worktree_lease_store.py`
- `guardian/tests/agents/test_worktree_lease_store.py`
- `guardian/db/migrations/versions/8c9d0e1f2a3b_add_worktree_leases.py`

## Files edited
- `guardian/db/models.py`
- `guardian/agents/__init__.py`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/tasks/TASK-002-worktree-lease-store.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/03-worktree-lease-contract.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md`

## Validation expectations
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_leases.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_lease_store.py`
- `./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py`
- `./.venv/bin/python scripts/validate_docs.py`
- `./.venv/bin/python -m alembic -c backend/alembic.ini heads`
- `git diff --check`

## Non-goals
- No Git branch creation.
- No Git worktree creation.
- No filesystem allocation or mutation.
- No coding-worker runtime enforcement.
- No worker orchestration policy.
- No API exposure.
- No UI surface.

## Dependencies
- TASK-001 worktree lease contract.

## Completion criteria
- Durable lease rows persist with required fields.
- Lifecycle update operations are deterministic and covered by tests.
- Active conflict protection enforces no-shared-mutable-worktree by branch and worktree path.
- Contract/status remains honest: persistence exists; runtime allocation and worker use are still deferred.
