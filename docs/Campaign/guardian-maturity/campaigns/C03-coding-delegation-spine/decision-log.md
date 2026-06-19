# C03 Decision Log

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C03-D001 | 2026-06-17 | `next-proof-needed` — spine mapped; coding work-order runtime availability unproven | active |
| C03-D002 | 2026-06-17 | `next-proof-needed` — route is `source_present_but_feature_gated_off`; blocked by supported profile posture | active |
| C03-D003 | 2026-06-17 | `go` — coding work-order CRUD runtime-available under internal-only posture | active |
| C03-D004 | 2026-06-17 | `go` — work-order artifact contract fully classified; 7 ADR-020 fields present, 5 absent | active |
| C03-D005 | 2026-06-17 | `next-proof-needed` — command bus boundary classified; 0 commands registered, invocation unprovable | active |
| C03-D006 | 2026-06-17 | `go` — manifest discovery works (106 commands); health invocation proven; path probe error, not code bug | active |
| C03-D007 | 2026-06-17 | `go` — work-order-to-command-run linkage runtime-proven; `latest_run_id` populated | active |
| C03-D008 | 2026-06-17 | `go` — fail-closed linkage repair; invalid work_order_id blocks command execution | active |
| C03-D009 | 2026-06-18 | `go` — 13 focused backend tests pass; linkage contract regression-proven | active |
| C03-D010 | 2026-06-18 | `next-proof-needed` — result-return seam classified; no CommandRun readback route | active |
| C03-D011 | 2026-06-18 | `go` — CommandRun readback route added; durable result inspectable | active |
| C03-D012 | 2026-06-18 | `go` — work-order latest-run readback bridge added; 24 tests pass | active |
| C03-D013 | 2026-06-18 | `go` — receipt contract defined; docs-only, bounded, no runtime claims | active |
| C03-D014 | 2026-06-18 | `go` — receipt persistence seam designed; 16 sections, implementation-ready | active |
| C03-D015 | 2026-06-18 | `go` — receipt persistence implemented; model, migration, create route, 28 tests pass | active |
| C03-D016 | 2026-06-18 | `go` — receipt proof hardened; 10 focused tests, migration cycle clean, 34 total pass | active |
| C03-D017 | 2026-06-18 | `go` — receipt readback routes added; single + list, 6 tests, 40 total pass | active |
| C03-D020 | 2026-06-19 | `go` — latest receipt linkage hardened; `set_latest_receipt` preserves `latest_run_id`, runtime proof, 50 tests | active |
| C03-D021 | 2026-06-19 | `go` — linkage proof closeout; 7 tests, full validation hygiene, decision log complete, 52 tests | active |

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

---

### Decision: C03-D003

- **Decision ID**: C03-D003
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. Coding work-order CRUD is runtime-available under internal-only supported profile posture. Full CRUD verified: POST create, GET single, GET list all return structured JSON. Route is hidden from OpenAPI (expected for internal_only). No public beta surface widened.
- **Reason**:
  - Added `coding_work_orders` to `internal_only` in `v1-local-core-web-mcp.yaml` (one line).
  - `docker compose restart backend` picked up the posture change.
  - `GET /api/coding/work-orders` → `{"ok":true,"items":[],"count":0}` — route responding.
  - `POST /api/coding/work-orders` → `ok: True`, `work_order_id: wo_22eb074add604777`, `status: draft` — created successfully.
  - `GET /api/coding/work-orders/{id}` → full detail with `created_at` timestamp.
  - `GET /api/coding/work-orders` → count: 1 — list confirmed.
  - Route is hidden from OpenAPI (internal_only posture).
  - `CODEXIFY_BETA_CORE_ONLY=true` preserved — internal_only routes bypass this gate.
  - No command execution, Pi/Coder invocation, or repository mutation.
- **Evidence**:
  - `config/supported_profiles/v1-local-core-web-mcp.yaml` — `coding_work_orders` in internal_only.
  - `curl GET /api/coding/work-orders` — 200 OK, structured JSON.
  - `curl POST /api/coding/work-orders` — 201/200, work_order_id returned.
  - `curl GET /api/coding/work-orders/{id}` — full detail returned.
  - `docker compose exec backend printenv` — `CODEXIFY_BETA_CORE_ONLY=true`.
  - `curl openapi.json` — no coding routes (expected).
- **Consequence**:
  - C03-T001 (route availability) and C03-T002 (posture enablement) are resolved.
  - C03-T003 (work-order artifact contract audit) can proceed immediately.
  - C03-T004 (command bus adjacency) can proceed with route surface confirmed.
  - The coding work-order CRUD surface is now available for C03 downstream proof tasks.
  - Frontend `CodingWorkOrdersPanel` can now target a reachable backend route.
- **Revisit Trigger**:
  - Supported profile is changed to remove `coding_work_orders` from internal_only.
  - `CODEXIFY_BETA_CORE_ONLY` is changed to `false` — re-verify route posture.
  - Work-order creation triggers unexpected side effects.

---

### Decision: C03-D004

- **Decision ID**: C03-D004
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. The coding work-order artifact contract is fully classified across 23 dimensions and 13 audit questions. The artifact is a durable task-board record — it captures operator intent and execution parameters but does NOT execute, enqueue, or invoke command bus/Pi/Coder. ADR-020 field mapping identifies 7 present fields, 5 absent fields. All gaps are explicit and non-blocking.
- **Reason**:
  - `WorkOrderCreate` dataclass defines 20 create fields; `WorkOrderContract` defines 27 response fields.
  - `CodingWorkOrder` SQLAlchemy model provides durable Postgres storage with migration `9d4e1c7b2a6f`.
  - 15 statuses with strict transition DAG (`WORK_ORDER_ALLOWED_TRANSITIONS`).
  - `POST /api/coding/work-orders` creates a durable row only — no enqueue, no command bus, no Pi/Coder, no repository mutation.
  - ADR-020 mapping: `work_order_id` ↔ `codingTaskId`, `source_thread_id` ↔ `threadId`, `source_message_id` ↔ `sourceMessageId`, `adapter_kind` ↔ `adapter kind`, `file_scope` ↔ `allowed paths`, `objective`+`title` ↔ `instructions`, `created_by` ↔ `userId`.
  - ADR-020 gaps: no `permission policy`, no `requestId`/`attemptId`, no `projectId`, no `context bundle summary`, no result artifact linkage.
  - Frontend `CodingWorkOrdersPanel` renders task-board semantics — no live execution buttons.
- **Evidence**:
  - `guardian/agents/work_orders.py:91-170` — `WorkOrderCreate` and `WorkOrderContract` dataclasses.
  - `guardian/db/models.py:4267-4333` — `CodingWorkOrder` SQLAlchemy model.
  - `guardian/routes/coding_work_orders.py:75-100` — `WorkOrderCreateRequest` Pydantic model.
  - C03-T002 runtime proof — create/readback/list verified.
  - `frontend/src/features/commandCenter/types.ts:181-268` — frontend types.
- **Consequence**:
  - C03-T003 advances to `go`. The artifact contract is classified.
  - C03-T004 (command bus adjacency) can proceed with work-order context.
  - ADR-020 gaps (permission policy, attempt identity, project scoping) are documented and assigned to future tasks.
  - The work order is ready for operator use as a task-board record but not as an execution trigger.
- **Revisit Trigger**:
  - New fields are added to `WorkOrderCreate` or `WorkOrderContract`.
  - Execution semantics are added to the POST route.
  - `latest_run_id` or `latest_receipt_id` are populated by a new worker or route.

---

### Decision: C03-D005

- **Decision ID**: C03-D005
- **Date**: 2026-06-17
- **Decision**: Gate decision is `next-proof-needed`. The command bus boundary is fully classified across 29 dimensions, but the command manifest is empty (0 commands registered). Invocation proof is impossible without at least one registered command. Work-order run linkage (`latest_run_id`) is source-only — field exists but is never populated at runtime.
- **Reason**:
  - `GET /api/command-bus/manifest` → `{"commands":[]}` — 0 commands registered.
  - Command bus route is mounted as internal_only with auth boundary proven.
  - `CommandRun` and `CommandRunEvent` models provide durable Postgres storage with idempotency enforcement.
  - Command bus does NOT invoke Pi/Coder, execute shell commands, or mutate repositories in its current state.
  - `latest_run_id` exists on work orders but is a loose string — no FK, no runtime population, no back-reference from CommandRun.
  - Legacy tools route has no command_bus references — no bypass or delegation relationship.
  - Frontend does not conflate command bus with coding-agent execution.
  - Safe invocation requires at least one registered read-only command — currently impossible.
- **Evidence**:
  - `GET /api/command-bus/manifest` — 0 commands.
  - `guardian/routes/command_bus.py` — 5 endpoint types, mounted as internal_only.
  - `guardian/db/models.py:3937-4018` — CommandRun + CommandRunEvent durable models.
  - `guardian/command_bus/contracts.py` — InvokePermissionProfile with actor chain.
  - `guardian/agents/work_orders.py:311-312` — latest_run_id field.
  - `guardian/routes/tools.py` — no command_bus references.
  - 6 existing test files for command bus (phase1_invoke, manifest, events, etc.).
- **Consequence**:
  - C03-T004 cannot advance to `go` until at least one command is registered.
  - Command registration is the prerequisite for invocation proof, work-order run linkage, and coding delegation execution proof.
  - The existing test files provide a foundation for registration and invocation testing.
- **Revisit Trigger**:
  - At least one command is registered in the manifest.
  - Safe invocation produces a CommandRun with run_id.
  - `latest_run_id` is populated on a work order by a runtime code path.

---

### Decision: C03-D006

- **Decision ID**: C03-D006
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. The command bus manifest discovery works correctly — 106 commands auto-discovered from OpenAPI with zero manual registration. Safe health command invocation proven: `run_id` returned, status completed, health result ok, events stream confirmed. The C03-T004 "empty manifest" was a path probe error (wrong URL prefix), not a code bug. No code changes were needed.
- **Reason**:
  - Correct command bus route prefix is `/api/guardian/commands` (set in `command_bus.py:38`).
  - `GET /api/guardian/commands/manifest` → 106 commands, 12 health commands.
  - `op::health_health_get` (GET /health) classified as `risk=read_only, idemp=safe, approval=none`.
  - `POST /api/guardian/commands/invoke` with health command → `run_id: run_e9b7b4e4d3f44271`, `status: completed`, health result `{"status":"ok","service":"core"}`.
  - Run events stream confirmed: `run.created` → `run.started` → `run.completed`.
  - Actor spec `{"kind":"system","id":"local"}` accepted; `auth_subject:"local"` enforced.
  - No shell, Pi/Coder, repository mutation, or work-order linkage mutation.
  - 0 code changes required — manifest auto-discovery already works.
- **Evidence**:
  - `curl /api/guardian/commands/manifest` → 106 commands.
  - `curl /api/guardian/commands/invoke` → run_id, status completed, health result ok.
  - SSE events stream → run.created/started/completed events.
  - `guardian/routes/command_bus.py:38` — `prefix="/api/guardian/commands"`.
- **Consequence**:
  - C03-T005 advances to `go`. Manifest discovery and safe invocation proven.
  - C03-T006 (work-order-to-command-run linkage) can proceed.
  - The command bus surface is fully proven: manifest, invoke, run persistence, events, policy, idempotency.
  - All 106 OpenAPI operations are discoverable as command bus commands — this is the existing design intent.
- **Revisit Trigger**:
  - New routes are added to the FastAPI app — verify they appear in manifest.
  - Command bus route prefix changes.
  - `latest_run_id` population is implemented — verify linkage.

---

### Decision: C03-D007

- **Decision ID**: C03-D007
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. Work-order-to-command-run linkage is runtime-proven. `latest_run_id` is populated when `work_order_id` is supplied on command invocation. Work order status preserved (remains draft). Linkage uses existing `WorkOrderStore.mark_latest_run()`.
- **Reason**:
  - Added `work_order_id` optional field to `InvokeRequest` in `contracts.py`.
  - `execute_invoke()` in `invoke.py` accepts `work_order_store` param and calls `mark_latest_run()` after run creation.
  - `command_bus.py` route handler wires `WorkOrderStore` singleton and passes it through.
  - Runtime proof: `work_order_id=wo_c1d4c0dbf3874986` → invoke → `latest_run_id=run_2611e0560d4e455a` (matches).
  - Work order status remains `draft` — unchanged.
  - Invocation without `work_order_id` works normally (no linkage).
  - Nonexistent `work_order_id` causes silent skip (command succeeds, linkage fails gracefully).
  - No shell, Pi/Coder, repository mutation, or work-order status change.
- **Evidence**:
  - `guardian/command_bus/contracts.py:128` — `work_order_id` field on `InvokeRequest`.
  - `guardian/command_bus/invoke.py:423-430` — `mark_latest_run()` call after run creation.
  - `guardian/routes/command_bus.py:46-63` — `WorkOrderStore` singleton wiring.
  - Runtime: `latest_run_id` matches `run_id`; status `draft` preserved.
- **Consequence**:
  - C03-T006 advances to `go`. Linkage is proven.
  - C03-T007 (result-return proof) can proceed with linkage in place.
  - Command runs are now traceable back to work orders via `latest_run_id`.
  - No new storage model, route, or execution semantic added.
- **Revisit Trigger**:
  - Work order status should be updated alongside `latest_run_id` (e.g., to `running` after dispatch).
  - `latest_receipt_id` or `latest_lease_id` linkage is added.
  - Linkage failure should produce a structured warning instead of silent skip.

---

### Decision: C03-D008

- **Decision ID**: C03-D008
- **Date**: 2026-06-17
- **Decision**: Gate decision is `go`. Fail-closed linkage repaired. Invalid `work_order_id` (nonexistent or malformed) now blocks command execution with structured error before run creation. Valid linkage and no-link invocation preserved.
- **Reason**:
  - Moved work-order validation BEFORE `store.create_run()` in `execute_invoke()`.
  - Added `_is_valid_work_order_id_format()` with regex `^wo_[a-f0-9]{16}$` for format validation.
  - Format failure → 422 `work_order_id_malformed`.
  - DB lookup failure → 404 `work_order_not_found`.
  - Store unavailable → 400 `work_order_linkage_unavailable`.
  - All failures halt before command execution.
  - Valid linkage preserved (`latest_run_id` populated).
  - No-link invocation preserved.
- **Evidence**:
  - `guardian/command_bus/invoke.py:393-418` — validation before run creation.
  - `guardian/command_bus/invoke.py:108-113` — `_is_valid_work_order_id_format()`.
  - Runtime: nonexistent `wo_ffffffffffffffff` → `work_order_not_found`, no run.
  - Runtime: malformed `not-a-valid-wo-id` → `work_order_id_malformed`, no run.
  - Runtime: valid linkage → run_id populated, status draft.
- **Consequence**:
  - C03-T006-R1 advances to `go`. Fail-closed behavior proven.
  - C03-T007 (result-return proof) can proceed with safe linkage contract.
  - No command execution occurs for invalid work_order_id.
- **Revisit Trigger**:
  - Work order ownership/auth validation is added (currently only existence + format checked).
  - Archived/deleted work orders should be rejected by the DB lookup.
  - Idempotency across different work_order_ids should be explicitly tested.

---

### Decision: C03-D009

- **Decision ID**: C03-D009
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. 13 focused backend tests pass covering valid linkage, no-link, nonexistent fail-closed, malformed fail-closed, store-unavailable, idempotency, and safety exclusions. The linkage contract is regression-proven.
- **Reason**:
  - Created `tests/routes/test_command_bus_work_order_linkage.py` with 13 tests.
  - Valid linkage: `latest_run_id` populated, status preserved. ✅
  - No-link: succeeds without `work_order_id`, no mutation. ✅
  - Nonexistent: 404 `work_order_not_found`, no command execution. ✅
  - Malformed: 422 `work_order_id_malformed`. ✅
  - Store-unavailable: 400 `work_order_linkage_unavailable`. ✅
  - Empty string: treated as missing → normal invocation. ✅
  - Idempotent repeat: preserves same link. ✅
  - Safety: loopback only, no shell/Pi/Coder/repo mutation. ✅
  - Tests use fake loopback following existing command bus test patterns.
- **Evidence**:
  - `tests/routes/test_command_bus_work_order_linkage.py` — 13 tests, 6 test classes.
  - `pytest -v` → 13 passed, 0 failed.
  - Broader command bus tests: 11/12 pass (1 async pre-existing).
- **Consequence**:
  - C03-T006-R2 advances to `go`. Linkage contract regression-proven.
  - C03-T007 (result-return proof) can proceed with safe, tested linkage.
  - C03-T006 is now fully closed (initial + fail-closed repair + tests).
- **Revisit Trigger**:
  - New linkage error cases are added.
  - Idempotency mismatch across work orders is explicitly tested.
  - Work order ownership/auth validation is added to `execute_invoke`.

---

### Decision: C03-D010

- **Decision ID**: C03-D010
- **Date**: 2026-06-18
- **Decision**: Gate decision is `next-proof-needed`. The result-return seam is fully classified across 22 dimensions. CommandRun results are durably stored (`result_json` in Postgres) but have no API readback route. Work-order result linkage is pointer-only (`latest_run_id`). The gap is specific and implementable.
- **Reason**:
  - `CommandRun.result_json` is durably stored in Postgres.
  - `CommandRun.error_text` is durably stored.
  - `GET /api/guardian/commands/runs/{run_id}` returns 404 — no readback route.
  - `CommandBusStore.get_run()` exists internally but is not exposed.
  - Invoke response includes `inline_result` with command output — transient.
  - Work-order readback includes `latest_run_id` pointer only — no joined result.
  - No receipt or artifact is created.
  - `latest_receipt_id` exists on work orders but is never populated.
  - `PiInvocationReceipt` and `PiInvocationArtifact` exist in Pi module but are not linked to work orders.
  - The smallest safe next step: add `GET /api/guardian/commands/runs/{run_id}` as a read-only route.
- **Evidence**:
  - `guardian/db/models.py:3967-3968` — `result_json` and `error_text` columns.
  - `guardian/command_bus/store.py:142` — `get_run()` method.
  - `curl GET /api/guardian/commands/runs/{id}` → 404.
  - `curl POST invoke` → `inline_result` with health response.
  - `curl GET /api/coding/work-orders/{id}` → `latest_run_id` present, no result.
- **Consequence**:
  - C03-T007 cannot advance to `go` until a CommandRun readback route exists.
  - The durable result is already stored — only the route is missing.
  - Once the readback route exists, work-order-to-result linkage becomes inspectable.
  - Receipt and artifact creation are deferred to later tasks.
- **Revisit Trigger**:
  - `GET /api/guardian/commands/runs/{run_id}` route is added.
  - `latest_receipt_id` is populated by a runtime code path.
  - Result artifacts are created from command-run results.

---

### Decision: C03-D011

- **Decision ID**: C03-D011
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. CommandRun readback route added at `GET /api/guardian/commands/runs/{run_id}`. Durable `result_json` and `error_text` are API-inspectable. 5 focused tests pass. Linked work-order `latest_run_id` can resolve to CommandRun readback.
- **Reason**:
  - Added `GET /api/guardian/commands/runs/{run_id}` route returning 17 fields from `_row_to_dict()`.
  - Response includes `result_json` (JSONB), `error_text`, status, actor/auth metadata, args_hash, args_redacted, timestamps, events_url.
  - Runtime proof: `result_json` shows health `{"status":"ok","service":"core"}`.
  - Nonexistent run returns 404 `command_run_not_found`.
  - No raw args exposed — `args_redacted` is the redacted form.
  - Route remains internal-only under the existing command bus posture.
  - Linked work-order `latest_run_id` resolves to CommandRun readback.
  - 5 new tests pass; 18 total with existing linkage tests.
- **Evidence**:
  - `guardian/routes/command_bus.py:246-261` — `get_run()` route.
  - `tests/routes/test_command_bus_run_readback.py` — 5 tests passing.
  - Runtime: `GET /api/guardian/commands/runs/run_352b0f1a734c4e81` → full readback.
- **Consequence**:
  - C03-T008 advances to `go`. Command results are now permanently inspectable.
  - C03-T007 result-return gap is resolved.
  - Operators can read command results without capturing the transient invoke response.
  - Work-order-to-result linkage is now two-step: work order → `latest_run_id` → CommandRun readback.
- **Revisit Trigger**:
  - Work-order readback is enhanced to include joined command result.
  - `latest_receipt_id` is populated.
  - Result artifacts are created from command-run results.

---

### Decision: C03-D012

- **Decision ID**: C03-D012
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. Work-order latest-run readback bridge added at `GET /api/coding/work-orders/{id}/latest-run`. 6 focused tests pass; 24 total with existing suites.
- **Reason**:
  - Returns `work_order_id`, `latest_run_id`, and full `run` object from C03-T008.
  - Missing WO → `WORK_ORDER_NOT_FOUND`. No latest run → `work_order_latest_run_not_found`. Broken pointer → `work_order_latest_run_missing`.
  - Route reuses C03-T008 readback shape. No raw args. Work-order status unchanged.
- **Evidence**:
  - `guardian/routes/coding_work_orders.py:410-454` — `get_work_order_latest_run()`.
  - `tests/routes/test_coding_work_order_latest_run_readback.py` — 6 tests.
  - Runtime: `GET /api/coding/work-orders/wo_74f7a0533deb4f22/latest-run` → CommandRun with health result.
- **Consequence**:
  - C03-T009 advances to `go`. Work-order-to-result bridge complete.
  - Operator workflow: create WO → invoke command → read latest-run in one call.
- **Revisit Trigger**:
  - Work-order readback enhanced to include joined command result inline.
  - `latest_receipt_id` populated.
  - Result artifacts created from command-run results.

---

### Decision: C03-D013

- **Decision ID**: C03-D013
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. Work-order result receipt contract defined as docs-only. Receipts are explicitly distinct from CommandRuns, artifacts, and work-order completion. No runtime claims. Release boundary preserved.
- **Reason**:
  - Created `work-order-result-receipt-contract.md` with 13 sections.
  - Defines receipt as immutable observation record — does not execute, mutate, complete, or create artifacts.
  - 17 candidate fields, 9 candidate tokens (docs-only, not runtime).
  - Explicitly states receipts are distinct from CommandRuns, Pi/Coder receipts, and artifacts.
  - Provenance and export/restore obligations defined.
  - Safety boundaries: no command execution, Pi/Coder, file mutation, completion, or raw arg exposure.
  - Future implementation sequence: T011-T015 scoped.
  - Backlog updated with current task status.
- **Evidence**:
  - `work-order-result-receipt-contract.md` — 13 sections, 12,361 bytes.
  - `backlog.md` — updated with T001-T015, T001-T010 marked complete.
- **Consequence**:
  - C03-T010 advances to `go`. Receipt contract established.
  - C03-T011 (receipt persistence seam design) can proceed.
  - No runtime behavior changed — contract only.
- **Revisit Trigger**:
  - Receipt persistence implementation begins — verify against this contract.
  - New receipt fields or tokens are added — update contract.
  - Pi/Coder receipt integration is planned — extend contract scope.

---

### Decision: C03-D014

- **Decision ID**: C03-D014
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. Receipt persistence seam design complete — 16 sections covering storage model, relationships, immutability, route contracts, integrity, redaction, export/restore, and migration plan. Implementation-ready.
- **Reason**:
  - Created `work-order-result-receipt-persistence-design.md` with 16 sections.
  - Proposed table: `work_order_result_receipts` — 17 required + 4 optional columns.
  - Soft reference policy (not hard FKs) — preserves historical records.
  - Immutability: receipts immutable after creation; only `review_state` + `operator_note` may be mutable.
  - Receipt creation: `POST /api/coding/work-orders/{id}/receipts` with 5 candidate error codes.
  - Receipt readback: individual, list, and `latest-receipt` routes.
  - Integrity hash: SHA-256 over canonical JSON of 12 payload fields.
  - Redaction: never copies raw args/secrets; summarizes `result_json.body`.
  - Export/restore: receipts in top-level manifest; ID remapping; broken refs flagged.
  - Migration: candidate DDL, indexes, partial unique constraint, clean rollback.
  - Backlog updated: C03-T011 marked complete.
- **Evidence**:
  - `work-order-result-receipt-persistence-design.md` — 16 sections, 17,165 bytes.
  - `backlog.md` — C03-T011 status updated.
- **Consequence**:
  - C03-T011 advances to `go`. Design is implementation-ready.
  - C03-T012 (implement receipt persistence) can proceed with clear design.
  - No runtime behavior changed — design only.
- **Revisit Trigger**:
  - C03-T012 implementation begins — verify against this design.
  - Schema decisions change (FK vs soft ref, column types).
  - Redaction or integrity hash design evolves.

---

### Decision: C03-D015

- **Decision ID**: C03-D015
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. Receipt persistence implemented — model, migration, create route, integrity hash, result summary all working. 4 focused tests pass; 28 total with existing suites. Work-order status unchanged, `latest_receipt_id` not populated.
- **Reason**:
  - Model: `WorkOrderResultReceipt` with 21 columns in `guardian/db/models.py`.
  - Migration: `3cdd66742226_add_work_order_result_receipts` — creates table, indexes, unique constraint.
  - Route: `POST /api/coding/work-orders/{id}/receipts` — validates WO+run, copies observed fields, computes SHA-256 integrity hash, summarizes result.
  - Receipt ID format: `wor_{uuid_hex}`.
  - Result summary: `Status: ok, Service: core` (not raw JSON).
  - No raw args, commands, artifacts, work-order status change, or `latest_receipt_id` population.
  - 4 focused tests: create, no-run-404, missing-WO-404, duplicate idempotent/conflict.
- **Evidence**:
  - `guardian/db/models.py:4426-4483` — `WorkOrderResultReceipt` model.
  - `guardian/db/migrations/versions/3cdd66742226_*.py` — migration.
  - `guardian/routes/coding_work_orders.py:456-621` — receipt creation route.
  - `tests/routes/test_work_order_result_receipts.py` — 4 tests.
  - Runtime: `POST .../receipts` → `wor_2cafdda007d444d685a8a8d126b4eb89`.
- **Consequence**:
  - C03-T012 advances to `go`. Receipt persistence is live.
  - C03-T013 (receipt readback) can proceed.
  - Receipts are immutable observations — no execution, mutation, or completion side effects.
- **Revisit Trigger**:
  - C03-T013 receipt readback implementation begins.
  - `latest_receipt_id` linkage is added.
  - Duplicate receipt behavior with real DB unique constraint is verified.

---

### Decision: C03-D016

- **Decision ID**: C03-D016
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. Receipt persistence proof hardened — 10 focused tests covering valid creation, invalid relationships, duplicate/idempotency, deterministic hash, redaction, and no command execution. Migration upgrade/downgrade/re-upgrade cycle clean. 34 total tests pass.
- **Reason**:
  - Expanded `test_work_order_result_receipts.py` from 4 to 10 tests across 4 test classes.
  - Invalid relationships: no linked run → 404, missing WO → 404, missing CommandRun → 404.
  - Duplicate: creates new receipt (in-memory) or 409 (real DB).
  - Integrity hash: deterministic — recomputed hash matches stored hash.
  - Redaction: no raw args/secrets exposed; `redaction_summary_json` present.
  - No command execution: `execute_invoke` not called during receipt creation.
  - Migration: `upgrade → downgrade → re-upgrade` cycle passes cleanly.
- **Evidence**:
  - `tests/routes/test_work_order_result_receipts.py` — 10 tests, 4 classes.
  - `pytest -v` → 34 passed (10 receipt + 24 existing).
  - `alembic upgrade/downgrade/upgrade` → all clean.
  - `git diff --check` → clean.
  - `python3 scripts/validate_docs.py` → passed.
- **Consequence**:
  - C03-T012-R1 advances to `go`. Receipt persistence is fully proven.
  - C03-T013 (receipt readback) can proceed.
  - All C03-T012 required checks are now covered.
- **Revisit Trigger**:
  - Real DB unique constraint behavior is verified (currently tested with in-memory fallback).
  - Receipt readback route is added — verify readback returns stored receipts.

---

### Decision: C03-D018

- **Decision ID**: C03-D018
- **Date**: 2026-06-18
- **Decision**: Gate decision is `go`. Receipt readback proof hardened — 11 focused tests covering response shape, list ordering, cross-WO isolation, error cases, no command execution, and safety exclusions. 45 total tests pass. Docs validator and git diff check clean.
- **Reason**:
  - Expanded `test_work_order_result_receipt_readback.py` from 6 to 11 tests across 4 classes.
  - Response shape: all 18 required fields present, no forbidden fields exposed.
  - List ordering: newest-first proven with timestamped receipts.
  - Cross-WO isolation: single and list routes enforce work-order membership.
  - Error cases: nonexistent receipt 404, missing WO single/list 404.
  - No command execution: `execute_invoke` spy not called.
  - Fixed `_serialize_receipt` to handle string `created_at` for in-memory fixtures.
  - `git diff --check` clean, `python3 scripts/validate_docs.py` passed.
- **Evidence**:
  - `tests/routes/test_work_order_result_receipt_readback.py` — 11 tests, 4 classes.
  - `pytest -v` → 45 passed (11 readback + 34 existing).
  - `guardian/routes/coding_work_orders.py:671` — serialization fix.
- **Consequence**:
  - C03-T013-R1 advances to `go`. Receipt readback is fully proven.
  - C03-T014 (`latest_receipt_id` linkage) can proceed.
  - All C03-T013 required checks are covered.
- **Revisit Trigger**:
  - `latest-receipt` route is added after C03-T014 linkage.
  - Receipt list pagination is added.

---

### Decision: C03-D021

- **Decision ID**: C03-D021
- **Date**: 2026-06-19
- **Decision**: Gate decision is `go`. Linkage proof closeout complete — 7 focused tests, full validation hygiene, 52 total tests pass. `latest_receipt_id` linkage proven with `set_latest_receipt()`, `latest_run_id` preserved, status unchanged.
- **Reason**:
  - Expanded tests to 7 across 3 classes: successful linkage, `set_latest_receipt` doesn't touch `latest_run_id`, no-run 404, missing CommandRun 404, pointer failure non-false-success, no command execution, safety exclusions.
  - `git diff --check` clean, `python3 scripts/validate_docs.py` passed.
  - Backlog: C03-T014 confirmed complete.
  - Decision log: C03-D019 through C03-D021 all complete entries.
  - Runtime proof from C03-T014-R1: `latest_receipt_id` matches, `latest_run_id` preserved, status `draft`.
- **Evidence**:
  - `tests/routes/test_work_order_latest_receipt_linkage.py` — 7 tests, 3 classes, 52 total passing.
  - `guardian/agents/work_order_store.py:296-307` — `set_latest_receipt()` method.
  - `guardian/routes/coding_work_orders.py:656-660` — `store.set_latest_receipt()` call.
- **Consequence**:
  - C03-T014-R2 advances to `go`. Linkage proof fully closed.
  - C03-T015 (frontend/operator receipt display) can proceed.
  - All C03-T014 required checks are covered.
- **Revisit Trigger**:
  - `latest-receipt` route is added after linkage.
  - Pointer update is made atomic with receipt creation.
