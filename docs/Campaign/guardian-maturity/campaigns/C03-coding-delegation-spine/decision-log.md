# C03 Decision Log

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C03-D001 | 2026-06-17 | `next-proof-needed` — spine mapped; coding work-order runtime availability unproven | active |

---

### Decision: C03-D001

- **Decision ID**: C03-D001
- **Date**: 2026-06-17
- **Decision**: Gate decision is `next-proof-needed`. The coding delegation spine is fully mapped — 21 surfaces classified, 15 seams classified, 16 audit questions answered. The single blocker is runtime verification of the coding work-order CRUD surface. All delegation-adjacent routes are feature-gated and not runtime-verified.
- **Reason**:
  - C11 route audit confirmed coding_work_orders, delegations, guardian_delegations, agent_orchestration, and command_bus routes exist in code but are feature-gated (not in OpenAPI).
  - All routes use `_include_router()` with env var flags and supported profile posture.
  - Guardian delegations are `default_enabled=False` — explicitly gated.
  - Pi/Coder validation logic exists (`guardian/pi/validation.py` — 352 lines of pure validators) but has zero route registration.
  - Agent worker and delegation worker exist and are running in Docker Compose.
  - Frontend `CodingWorkOrdersPanel` targets `/api/coding/work-orders` but backend availability is unproven.
  - ADR-020 defines the coding-agent execution contract as contract-only — no live Pi SDK integration.
  - `00-current-state.md` explicitly excludes delegation from the release promise.
  - No architecture contradictions found. No unsafe shadow execution paths found.
  - The smallest safe next step is C03-T001: verify coding work-order routes are runtime-available.
- **Evidence**:
  - `guardian/routes/coding_work_orders.py` — POST/GET/cancel + campaign runner + orchestrator (307 lines of route definitions).
  - `guardian/routes/delegations.py` — POST draft/approve/cancel, GET events (310 lines).
  - `guardian/routes/guardian_delegations.py` — POST/GET/approve/cancel/transcript (118 lines).
  - `guardian/routes/agent_orchestration.py` — POST plans/deployments/coding/execute, GET runs/events.
  - `guardian/pi/contracts.py` — `PiInvocationEnvelope`, `PiInvocationReceipt`, `PiInvocationArtifact`, `PiHarnessResult` dataclasses.
  - `guardian/pi/validation.py` — pure deterministic validators for envelope, receipt, harness result.
  - `guardian/workers/agent_worker.py` and `delegation_worker.py` — exist and running.
  - `frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx` — renders work orders.
  - `tests/routes/test_codex_draft_routes.py` etc. — 9 existing test files.
  - OpenAPI schema — no delegation/coding/Pi routes visible (feature-gated, as expected).
- **Consequence**:
  - C03 cannot advance to `go` until C03-T001 confirms coding work-order CRUD is runtime-available.
  - C03-T002 through C03-T006 are blocked on C03-T001 verification.
  - C04 (Pi/Coder Invocation Boundary) is blocked on C03 governed delegation drafts.
  - C09 (Execution Ledger) is blocked on C03 delegation runs.
  - No release claims widened — `00-current-state.md` remains authoritative.
- **Revisit Trigger**:
  - C03-T001 runtime verification confirms coding work-order routes are reachable.
  - Feature flag `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES` is enabled in the runtime environment.
  - New Pi/Coder validation route is registered — reclassify from `absent` to `present`.
  - ADR-020 implementation changes the contract-only status.
