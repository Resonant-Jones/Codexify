# TASK-003 Coding Worker Uses Leased Worktree

## Objective
Require coding-worker execution attempts to honor assigned `WorktreeLease` context.

## Phase alignment
- This is the intended implementation task for Phase 3 in the campaign rollout plan.
- It enforces lease-bound execution when lease context is provided.

## Scope
- Propagate optional `worktree_lease_id` and `require_worktree_lease` through route, deployment spec, and queued worker task payload.
- Resolve durable lease state in worker before adapter execution.
- Fail closed when required lease context is missing, invalid, inactive, or unavailable.
- Use lease `worktree_path` as effective worker execution/validation cwd when lease-bound.
- Emit bounded lease-linked metadata in terminal worker events and stored result envelopes.

## Files edited
- `guardian/agents/coding_agent_contracts.py`
- `guardian/routes/agent_orchestration.py`
- `guardian/tasks/types.py`
- `guardian/workers/coding_worker.py`
- `guardian/agents/store.py`
- `guardian/tests/workers/test_coding_worker.py`
- `guardian/tests/routes/test_agent_orchestration_events.py`
- `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/tasks/TASK-003-coding-worker-uses-leased-worktree.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/03-worktree-lease-contract.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/04-worker-receipt-contract.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md`

## Validation expectations
- `./.venv/bin/python -m pytest -v guardian/tests/workers/test_coding_worker.py`
- `./.venv/bin/python -m pytest -v guardian/tests/routes/test_agent_orchestration_events.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_leases.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_lease_store.py`
- `./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py`
- `./.venv/bin/python scripts/validate_docs.py`
- `git diff --check`

## Non-goals
- No lease allocator in this phase.
- No Git branch/worktree creation in this phase.
- No commit-after-green policy in this phase.
- No merge-candidate generation in this phase.
- No orchestrator selection logic in this phase.
- No API-route expansion or UI surface in this phase.

## Dependencies
- TASK-001 worktree lease contract.
- TASK-002 worktree lease store.

## Completion criteria
- Worker refuses lease-required execution when lease context is missing or invalid.
- Lease-bound execution uses lease `worktree_path` for adapter and validation cwd.
- Worker emits bounded lease-linked metadata (`worktree_lease_id`, `branch_name`, `worktree_path`) in terminal/event/result evidence.
- Legacy non-lease execution remains backward compatible.
