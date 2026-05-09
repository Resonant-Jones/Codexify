# TASK-004 Commit-After-Green Gate

## Objective
Introduce a policy gate where commits are permitted only after successful validation status.

## Scope
- Encode commit eligibility predicate from normalized validation receipts.
- Block commit emission on `failed`, `error`, or `not_run` statuses.
- Preserve explicit stop reasons and human-review flags.

## Files likely to edit
- `guardian/workers/coding_worker.py`
- `guardian/agents/test_results.py`
- `guardian/agents/store.py`
- `tests/workers/` and `tests/agents/`

## Validation expectations
- Tests prove commit hash is absent when validation is non-passing.
- Tests prove commit hash appears only on `passed` path.
- Receipt-level evidence remains bounded and normalized.

## Non-goals
- No merge automation.
- No branch cleanup automation.
- No task-board API.

## Dependencies
- TASK-003 coding worker lease integration.

## Completion criteria
- Commit behavior is deterministically gated by validation outcome.
- Worker receipts reflect gate decision and stop reason.
- Regression tests cover pass/fail/retry exhaustion paths.
