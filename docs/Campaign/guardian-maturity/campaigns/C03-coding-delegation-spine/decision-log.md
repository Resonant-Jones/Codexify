# C03 Decision Log

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C03-D001 | 2026-06-17 | `next-proof-needed` — spine mapped; coding work-order runtime availability unproven | active |
| C03-D002 | 2026-06-17 | `next-proof-needed` — route is `source_present_but_feature_gated_off`; blocked by supported profile posture | active |

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

---

### Decision: C03-D002

- **Decision ID**: C03-D002
- **Date**: 2026-06-17
- **Decision**: Gate decision is `next-proof-needed`. The coding work-order route is classified as `source_present_but_feature_gated_off`. The exact blocker is `CODEXIFY_BETA_CORE_ONLY=true` combined with `coding_work_orders` not being listed in the supported profile's route posture (`enabled` or `internal_only`). The route cannot be runtime-verified until the supported profile posture is updated.
- **Reason**:
  - Feature flag `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES` defaults to `true` and is not overridden in the runtime environment.
  - The `_include_router()` gating mechanism applies three checks: profile posture, `CODEXIFY_BETA_CORE_ONLY`, and feature flag.
  - `coding_work_orders` is NOT in the supported profile's `enabled`, `internal_only`, or `quarantined` lists.
  - `CODEXIFY_BETA_CORE_ONLY=true` blocks non-core, non-internal routes. `coding_work_orders` has `core_surface=False` and is not `internal_only`.
  - Result: route is present in source code but gated out of the active OpenAPI surface.
  - No safe POST possible — the route is not mounted.
  - Resolution: add `coding_work_orders` to the supported profile's `internal_only` route posture (safest first step) or `enabled` list.
- **Evidence**:
  - `guardian/guardian_api.py:240-310` — `_include_router()` gating logic.
  - `guardian/guardian_api.py:1223-1228` — `coding_work_orders` router inclusion with `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES` flag.
  - `config/supported_profiles/v1-local-core-web-mcp.yaml` — `coding_work_orders` absent from route posture.
  - `docker compose exec backend printenv` — `CODEXIFY_BETA_CORE_ONLY=true`.
  - `curl localhost:8888/openapi.json` — no coding/delegation routes visible.
- **Consequence**:
  - C03-T001 cannot advance to `go` until the supported profile posture is updated.
  - C03-T002 through C03-T006 remain blocked on C03-T001.
  - Frontend `CodingWorkOrdersPanel` targets routes that return errors when the route is gated.
  - The resolution is a supported profile configuration change, not a code change.
- **Revisit Trigger**:
  - `coding_work_orders` is added to the supported profile route posture (enabled or internal_only).
  - `CODEXIFY_BETA_CORE_ONLY` is changed to `false`.
  - Re-run C03-T001 to verify route is mounted and reachable.
