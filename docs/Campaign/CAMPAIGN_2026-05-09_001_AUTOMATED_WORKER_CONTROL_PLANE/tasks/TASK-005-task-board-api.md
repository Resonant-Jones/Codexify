# TASK-005 Task-Board API

## Objective
Implement the Phase 5 backend foundation for durable coding work orders:
create, list, detail, and cancel surfaces for control-plane visibility.

## Phase alignment
This file now maps to the implemented Phase 5 task-board API foundation.

## Scope
- Add canonical work-order lifecycle contracts and transition validation.
- Add durable Postgres work-order storage.
- Add authenticated backend routes for create/list/detail/cancel.
- Preserve acceptance-vs-completion semantics.

## Created files
- `guardian/agents/work_orders.py`
- `guardian/agents/work_order_store.py`
- `guardian/routes/coding_work_orders.py`
- `guardian/tests/agents/test_work_orders.py`
- `guardian/tests/agents/test_work_order_store.py`
- `guardian/tests/routes/test_coding_work_orders.py`
- `guardian/db/migrations/versions/9d4e1c7b2a6f_add_coding_work_orders.py`

## Edited files
- `guardian/db/models.py`
- `guardian/agents/__init__.py`
- `guardian/guardian_api.py`
- `guardian/protocol_tokens.py`
- `tests/contracts/test_protocol_tokens.py`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/01-domain-model.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/02-task-state-machine.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/06-api-surface-sketch.md`
- `docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md`

## Validation expectations
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_work_orders.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_work_order_store.py`
- `./.venv/bin/python -m pytest -v guardian/tests/routes/test_coding_work_orders.py`
- `./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_leases.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_worktree_lease_store.py`
- `./.venv/bin/python -m pytest -v guardian/tests/workers/test_coding_worker.py`
- `./.venv/bin/python scripts/validate_docs.py`
- `git diff --check`

## Non-goals
- No worker dispatch from work-order routes.
- No lease allocation.
- No Git branch/worktree creation.
- No commit or merge behavior changes.
- No orchestrator next-task selector.
- No UI implementation.

## Dependencies
- TASK-001 through TASK-004.

## Completion criteria
- Durable work-order control-plane state is persisted and queryable.
- Create/list/detail/cancel routes are live and tested.
- Route acceptance remains separate from worker execution completion.
