# TASK-006 Orchestrator Next-Task Selector

## Objective
Implement deterministic policy logic that recommends or dispatches the next safe work order.

## Scope
- Read work-order states, dependencies, and receipts.
- Rank/select next task under conflict and policy constraints.
- Emit durable `OrchestratorDecision` records.

## Files likely to edit
- `guardian/agents/` new orchestrator policy module
- `guardian/agents/store.py`
- `guardian/routes/` orchestrator endpoints
- `tests/agents/` policy tests
- `tests/routes/` endpoint tests

## Validation expectations
- Deterministic selection tests from fixed fixtures.
- Block/escalation behavior tests under ambiguity.
- Conflict-avoidance tests for overlapping file scopes.

## Non-goals
- No autonomous merge loop.
- No hidden self-modifying retry planner.
- No replacement of Guardian policy boundaries.

## Dependencies
- TASK-005 task-board API.
- Receipt and lease data from prior phases.

## Completion criteria
- Selector behavior is explainable through persisted decision reasons.
- Recommendation mode and dispatch mode remain distinct.
- Ambiguous states fail closed to `blocked` or recommendation-only outcomes.
