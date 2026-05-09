# TASK-005 Task-Board API

## Objective
Expose backend API surfaces for durable `WorkOrder` and run visibility/operations.

## Scope
- Implement work-order create/list/detail/cancel routes.
- Implement run creation entrypoint and receipt readback route.
- Preserve acceptance-vs-completion semantics in response models.

## Files likely to edit
- `guardian/routes/agent_orchestration.py` or new `guardian/routes/coding_control_plane.py`
- `guardian/agents/store.py`
- `guardian/core/dependencies.py`
- `tests/routes/`

## Validation expectations
- Route contract tests for request/response shapes.
- Auth/policy tests for guarded operations.
- Idempotency tests for dispatch-like endpoints.

## Non-goals
- No frontend task board UI.
- No orchestrator dispatch policy.
- No merge execution path.

## Dependencies
- TASK-001 through TASK-004.

## Completion criteria
- Proposed route set is live and tested.
- Lifecycle state is queryable with dependency and run metadata.
- Receipt route returns bounded normalized evidence.
