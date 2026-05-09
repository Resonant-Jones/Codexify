# TASK-001 Worktree Lease Contract

## Objective
Define and introduce canonical contract types/tokens for worktree leasing in Guardian-mediated coding runs.

## Scope
- Add lease contract model definitions.
- Define canonical lease status tokens and transition rules.
- Add lifecycle validation rules at contract boundary.

## Files likely to edit
- `guardian/agents/coding_agent_contracts.py`
- `guardian/agents/store.py`
- `docs/architecture/runtime-protocol-token-contract.md` (only if token registry extension is required)
- `tests/agents/` contract tests

## Validation expectations
- Contract/unit tests for required fields and status transitions.
- Token discipline checks for lease statuses.
- No runtime behavior changes beyond contract seam.

## Non-goals
- No persistence schema changes.
- No worker execution changes.
- No route changes.

## Dependencies
- Campaign spec baseline (Phase 0).

## Completion criteria
- Lease contract compiles and validates.
- Tests prove allowed/forbidden transition behavior.
- Documentation reflects proposed contract boundaries only.
