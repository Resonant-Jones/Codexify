# TASK-006 Orchestrator Next-Task Selector

## Objective
Implement Phase 6 as a deterministic, recommendation-only selector that ranks next safe coding work orders from durable state.

## Scope
- Read durable work-order state plus active lease metadata.
- Evaluate dependency readiness, active lease conflicts, and file-scope conflicts.
- Return ranked recommendations and explicit skip reasons.
- Expose recommendation-only API surface at `GET /api/coding/orchestrator/next`.

## Files likely to edit
- `guardian/agents/orchestrator_policy.py`
- `guardian/routes/coding_work_orders.py`
- `guardian/tests/agents/test_orchestrator_policy.py`
- `guardian/tests/routes/test_coding_work_orders.py`
- `guardian/protocol_tokens.py`
- `tests/contracts/test_protocol_tokens.py`
- `guardian/agents/__init__.py`
- Campaign docs for Phase 6 status updates

## Validation expectations
- Policy tests prove deterministic ranking, dependency checks, and conflict skip reasons.
- Route tests prove recommendation reads durable state and does not dispatch or mutate.
- Protocol token tests prove canonical decision/reason token registration.
- Docs validation and diff hygiene checks pass.

## Validation commands
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_orchestrator_policy.py`
- `./.venv/bin/python -m pytest -v guardian/tests/routes/test_coding_work_orders.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_work_orders.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_work_order_store.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_leases.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_lease_store.py`
- `./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py`
- `./.venv/bin/python scripts/validate_docs.py`
- `git diff --check`

## Non-goals
- No worker dispatch or task enqueueing.
- No lease allocation or lease mutation.
- No Git branch/worktree/commit/merge/push behavior.
- No orchestrator dispatch endpoint implementation.
- No UI implementation.

## Dependencies
- TASK-005 task-board API.
- Lease contracts/store from prior phases.
- Runtime token governance for decision and reason codes.

## Completion criteria
- Recommendation output is deterministic and bounded.
- Recommendation and dispatch authority remain explicitly separate.
- Unready/ambiguous/conflicting tasks surface explicit skip reasons.
- Route acceptance remains read-only and does not imply execution.
