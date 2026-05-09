# TASK-001 Worktree Lease Contract

## Objective
Define and introduce canonical contract types/tokens for worktree leasing in Guardian-mediated coding runs.

## Phase alignment
- This file represents Phase 1 implementation intent from `07-rollout-plan.md`.
- Phase 1 scope is contract-only and does not include persistence, worker execution, routes, or UI behavior.

## Scope
- Add lease contract model definitions.
- Define canonical lease status tokens and transition rules.
- Add lifecycle validation rules at contract boundary.

## Files likely to edit
- `guardian/agents/worktree_leases.py`
- `guardian/tests/agents/test_worktree_leases.py`
- `guardian/agents/__init__.py`
- `tests/contracts/test_protocol_tokens.py`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/03-worktree-lease-contract.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/tasks/TASK-001-worktree-lease-contract.md`

## Validation expectations
- Contract/unit tests for required fields and status transitions.
- Token discipline checks for lease statuses.
- No runtime behavior changes beyond contract seam.

## Validation commands
```bash
./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_leases.py
./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py
./.venv/bin/python scripts/validate_docs.py
git diff --check
```

## Non-goals
- No persistence schema changes.
- No worker execution changes.
- No route changes.
- No Git branch/worktree allocation behavior.

## Dependencies
- Campaign spec baseline (Phase 0).

## Completion criteria
- Lease contract compiles and validates.
- Tests prove allowed/forbidden transition behavior.
- Documentation reflects proposed contract boundaries only.
- Runtime allocation/store remains explicitly unimplemented.
