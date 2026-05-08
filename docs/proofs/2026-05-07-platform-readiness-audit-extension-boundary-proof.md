# 2026-05-07 Platform Readiness Audit Extension Boundary Proof

## Problem

`scripts/audit_platform_readiness.py` treated `guardian/routes/tools.py` as a hard requirement for the Extension Boundary domain. In the current architecture, that route is a legacy compatibility shim and may be absent while current extension seams remain intact.

## Change

The Extension Boundary checks were updated to evaluate current architecture seams:

- `guardian/routes/command_bus.py`
- `guardian/command_bus/contracts.py`
- `guardian/routes/cron.py`
- `guardian/workers/cron_worker.py`
- `guardian/routes/agent_orchestration.py`
- `guardian/agents/store.py`
- `guardian/agents/events.py`
- `guardian/workers/coding_worker.py`

The legacy `/tools` route now reports as:

- `PASS` when absent and not required by current architecture docs
- `WARN` when docs still reference legacy compatibility language but the route is absent
- `PASS` when present as a compatibility surface

It no longer emits `FAIL` solely because `guardian/routes/tools.py` is absent.

## Unit Proof

`tests/scripts/test_audit_platform_readiness.py` now verifies:

- Missing `guardian/routes/tools.py` does not produce a `FAIL` by itself
- Command bus route and contracts register as positive evidence
- Cron route and cron worker register as positive evidence
- Guardian intent/orchestration and coding-worker seams register as positive evidence when present
- The Extension Boundary domain remains conservative (`manual review required`) and retains warning/manual-review posture

## Script Proof

The audit script remains executable in normal text mode via:

- `python scripts/audit_platform_readiness.py`

## Manual Review Still Required

This change preserves cautionary posture for extension-boundary maturity. The audit still requires human review for:

- cross-surface policy consistency on the intent spine
- extension governance and runtime binding boundaries
- avoiding ad hoc process-local execution paths

## Scope and Readiness Statement

This proof updates an operator/readiness truth surface only. It does **not** change runtime behavior, routing behavior, worker behavior, command bus behavior, cron behavior, coding-agent execution behavior, or release readiness by itself.
