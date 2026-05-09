# TASK-007 Run Ledger Inspection Surface

## Objective
Provide an operator inspection surface for work orders, runs, leases, validation receipts, and cleanup outcomes.

## Scope
- Add read-only backend inspection endpoints and/or frontend pane.
- Render run lifecycle, receipt summaries, and cleanup evidence.
- Surface limitations and ambiguity explicitly.

## Files likely to edit
- `guardian/routes/` inspection endpoints
- `guardian/agents/store.py`
- `frontend/src/` operator inspection components
- `tests/routes/`
- `frontend/src/**/__tests__/`

## Validation expectations
- API contract tests for inspection payloads.
- UI render tests for loading/empty/error/data states.
- Evidence redaction checks (no secrets/unbounded logs).

## Non-goals
- No new execution authority.
- No runtime side effects from inspection views.
- No release claim changes without fresh live proof.

## Dependencies
- TASK-005 task-board API.
- TASK-006 orchestrator selector.

## Completion criteria
- Operators can inspect run/receipt/lease/cleanup lineage in one bounded surface.
- Visibility gaps are explicit and auditable.
- Inspection data aligns with durable backend records.
