# TASK-004 Commit-After-Green Gate

## Objective
Implement Phase 4 by adding an opt-in commit-after-green gate for lease-bound coding runs.

## Scope
- Add commit gate contract/helper code in `guardian/agents/commit_gate.py`.
- Propagate commit controls through coding execution contracts and queue payloads:
  - `commit_after_validation`
  - `commit_message`
  - `require_human_review_before_merge`
- Integrate the gate into `guardian/workers/coding_worker.py` so commit runs only when:
  - execution is lease-bound,
  - validation command ran,
  - final validation status is `passed`, and
  - commit-after-validation is explicitly enabled.
- Persist bounded commit metadata into coding result envelopes.
- Emit terminal task metadata with commit evidence.

## Created files
- `guardian/agents/commit_gate.py`
- `guardian/tests/agents/test_commit_gate.py`

## Edited files
- `guardian/agents/coding_agent_contracts.py`
- `guardian/routes/agent_orchestration.py`
- `guardian/tasks/types.py`
- `guardian/workers/coding_worker.py`
- `guardian/agents/store.py`
- `guardian/agents/__init__.py`
- `guardian/protocol_tokens.py`
- `tests/contracts/test_protocol_tokens.py`
- `guardian/tests/workers/test_coding_worker.py`
- `guardian/tests/routes/test_agent_orchestration_events.py`
- `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/04-worker-receipt-contract.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md`

## Validation expectations
- Commit gate tests cover commit created, no changes, invalid worktree, bounded failure surfaces, and command scope.
- Worker tests prove commit gate only runs after passing validation inside a lease-bound worktree.
- Route tests prove commit control fields propagate to queued task payload and deployment spec.
- Protocol-token tests cover commit gate error tokens.

## Validation commands
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_commit_gate.py`
- `./.venv/bin/python -m pytest -v guardian/tests/workers/test_coding_worker.py`
- `./.venv/bin/python -m pytest -v guardian/tests/routes/test_agent_orchestration_events.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_leases.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_lease_store.py`
- `./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py`
- `./.venv/bin/python scripts/validate_docs.py`
- `git diff --check`

## Non-goals
- No Git branch creation.
- No Git worktree creation/allocation.
- No merge automation.
- No push automation.
- No task-board API.
- No orchestrator selection logic.
- No UI command center.

## Dependencies
- TASK-003 coding worker lease integration.

## Completion criteria
- Commit creation is gated by passing validation and explicit opt-in policy.
- Failing or non-running validation does not create commits.
- Commit metadata is bounded and persisted in result/event envelopes.
- This phase commits only inside an existing leased worktree and does not allocate leases.
