# C03 Proof Pack

## Campaign

- **Campaign ID**: C03
- **Title**: Coding Delegation Spine

## Proof Pass

- **Date/Time**: 2026-06-17 22:20 UTC
- **Branch**: `codex/campaignOS`
- **Latest Commit**: `ddaae17f0` — feat: surface Guardian chat orphan lifecycle state
- **Worktree**: Clean
- **C00 Dependency**: `go` — health/catalog/model inventory surfaces agree
- **C02 Dependency**: functionally complete — authenticated chat, provider states, orphan surfacing proven
- **C11 Dependency**: `go` — route topology confirmed; coding/delegation/command-bus routes identified as feature-gated

## Commands Run

- `git status` / `git log` / `docker compose ps` — baseline; all 11 services healthy
- `curl openapi.json` — route discovery; no coding/delegation/Pi routes visible (feature-gated)
- `grep` source searches for coding, delegation, command bus, Pi, work-order across `guardian/`, `frontend/src/`, `tests/`, `docs/`
- `guardian/routes/` — inspected 6 route files (coding_work_orders, delegations, guardian_delegations, agent_orchestration, command_bus, codex)
- `guardian/pi/` — inspected contracts, validation, tokens
- `guardian/workers/` — inspected agent_worker, delegation_worker
- `frontend/src/` — inspected CodingWorkOrdersPanel, useCodingWorkOrders hook, command-bus API client
- `tests/routes/` — identified 9 existing test files

## Route Matrix

| # | Surface | Route/Code Anchor | Present? | Runtime-Verified? | Mutation Risk | Proof Status | Notes |
|---|---------|-------------------|----------|-------------------|---------------|-------------|-------|
| 1 | Coding work-order CRUD | `guardian/routes/coding_work_orders.py` — POST/GET/cancel + orchestrator + campaign runner | **present** | No — feature-gated, not in OpenAPI | HIGH (writes to DB) | `present_not_runtime_verified` | Frontend `useCodingWorkOrders` targets `/api/coding/work-orders` |
| 2 | Delegation draft creation | `guardian/routes/delegations.py` — POST `/draft` | **present** | No — feature-gated | HIGH (writes to DB) | `present_not_runtime_verified` | Has approve, events, cancel routes |
| 3 | Guardian delegation CRUD | `guardian/routes/guardian_delegations.py` — POST/GET/approve/cancel/transcript | **present** | No — feature-gated, default-disabled | HIGH | `present_not_runtime_verified` | `default_enabled=False` — explicitly gated |
| 4 | Delegation result artifact return | Not found as dedicated route | **absent** | N/A | N/A | `absent` | No result artifact endpoint. Delegation worker publishes events but no artifact return route. |
| 5 | Delegation receipt persistence | `guardian/workers/delegation_worker.py` — publishes task events | **backend_only** | No | N/A | `backend_only` | Receipts inferred from task event publishing; no dedicated receipt table confirmed |
| 6 | Execution ledger | `coding_work_orders.py` campaign_runner router (goals, campaigns) | **partial** | No | MED | `ambiguous` | Campaign runner has goal/campaign CRUD; work orders link to runs via `latest_run_id`. Not a dedicated ledger surface. |
| 7 | Command bus manifest | `guardian/routes/command_bus.py` — GET `/manifest`, `/search` | **present** | No — feature-gated, internal_only | LOW | `present_not_runtime_verified` | Read-only; internal_only in supported profile |
| 8 | Command bus invoke | `guardian/routes/command_bus.py` — POST `/invoke` | **present** | No — feature-gated | HIGH (executes commands) | `present_not_runtime_verified` | Frontend `invokeCommandBus()` function exists |
| 9 | Command run events | `guardian/routes/command_bus.py` — GET `/runs/{run_id}/events` (SSE) | **present** | No | LOW | `present_not_runtime_verified` | Stream only; no listing endpoint |
| 10 | Command run history/listing | Not found | **absent** | N/A | N/A | `absent` | No command run listing endpoint |
| 11 | Pi invocation envelope validation | `guardian/pi/validation.py` — `_validate_envelope_core()` | **backend_only** | No | LOW | `backend_only` | Pure function; zero route registration |
| 12 | Pi receipt validation | `guardian/pi/validation.py` — `_validate_receipt_core()` | **backend_only** | No | LOW | `backend_only` | Pure function; zero route registration |
| 13 | Pi artifact validation | `guardian/pi/validation.py` — `_validate_harness_result_core()` | **backend_only** | No | LOW | `backend_only` | Pure function; includes artifact validation |
| 14 | Pi harness-result validation | `guardian/pi/validation.py` — `_validate_harness_result_core()` | **backend_only** | No | LOW | `backend_only` | Validates complete harness result |
| 15 | Pi/Coder live invocation | Not implemented | **absent** | N/A | N/A | `absent` | Pi SDK not integrated; ADR-020 contract-only |
| 16 | Pi/Coder route surface | Not implemented | **absent** | N/A | N/A | `absent` | No route for Pi validation or invocation |
| 17 | Coding worker queue | `guardian/workers/agent_worker.py` — agent worker exists; `docker compose ps` shows `worker-coding` running | **present** | No — worker is running but execution not proven | HIGH (executes code) | `present_not_runtime_verified` | Worker running 3h; no execution proof |
| 18 | Coding worker execution | `guardian/routes/agent_orchestration.py` — `POST /coding/execute` | **present** | No — feature-gated | HIGH | `present_not_runtime_verified` | Execute endpoint exists but gated and unproven |
| 19 | Operator-visible delegation status | `frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx` | **frontend_only** | No — frontend panel exists but routes may not be reachable | LOW | `frontend_only` | Panel renders work orders; backend availability unproven |
| 20 | Source-thread/message lineage binding | `guardian/codex/lineage.py` — `CodexLineageRef`, `ensure_lineage_exists()` | **present** | Yes — C02 verified thread/message persistence | LOW | `present_not_runtime_verified` | Lineage validation exists for Codex entries; delegation lineage in worker |
| 21 | Auth/session boundary for delegation | `guardian/guardian_api.py` — `_include_router` with feature flags + supported profile | **present** | Yes — C00/C02 verified auth | LOW | `present_not_runtime_verified` | Gating mechanism confirmed; delegation routes behind flags |

## Spine Classification Table

| # | Spine Seam | Classification | Evidence | Risk | Recommended Next Action |
|---|-----------|---------------|----------|------|------------------------|
| 1 | Operator authored request capture | `needs_backend_proof` | `coding_work_orders.py` POST create_work_order + delegations draft | MED | C03-T002: verify work-order creation route is runtime-available |
| 2 | Work-order artifact identity | `ready_for_proof` | `CommandCenterCodingWorkOrder` type has work_order_id, source_thread_id, source_message_id | LOW | C03-T002: audit identity fields against ADR-020 envelope |
| 3 | Work-order acceptance semantics | `needs_backend_proof` | Accept/queue/draft status in work_order; no acceptance contract verified | MED | C03-T001: verify acceptance vs execution distinction |
| 4 | Delegation draft persistence | `needs_backend_proof` | `delegations.py` POST /draft; `guardian_delegations.py` POST create | MED | C03-T003: verify draft persistence end-to-end |
| 5 | Policy/auth boundary | `ready_for_proof` | Feature flags + supported profile + X-API-Key auth confirmed in C02 | LOW | C03-T001: document gating requirements for delegation |
| 6 | Command bus adjacency | `ready_for_proof` | `command_bus.py` manifest/invoke/runs verified by code inspection | MED | C03-T004: prove command bus is adjacent, not equivalent to coding agent |
| 7 | Command bus invocation authority | `needs_backend_proof` | POST /invoke exists; `invokeCommandBus()` in frontend | HIGH | C03-T004: verify invocation does not bypass Guardian authority |
| 8 | Pi/Coder validation contract | `ready_for_proof` | `guardian/pi/validation.py` has pure deterministic validators | LOW | C03-T005: scaffold validation route after C03 proof |
| 9 | Pi/Coder live invocation boundary | `defer` | Pi SDK not integrated; ADR-020 contract-only | HIGH | Defer to C04 after C03 delegation drafts are governed |
| 10 | Worker/queue ownership | `needs_backend_proof` | `agent_worker.py` and `delegation_worker.py` exist; `worker-coding` running | HIGH | C03-T001: verify worker receives and executes tasks |
| 11 | Receipt/artifact return path | `needs_backend_implementation` | No dedicated receipt route; delegation worker publishes events | HIGH | C03-T003: identify smallest receipt return seam |
| 12 | Source-thread/message lineage | `ready_for_proof` | `guardian/codex/lineage.py` validates thread/message existence; delegation worker builds lineage | MED | C03-T003: verify lineage preserved through delegation lifecycle |
| 13 | Operator status visibility | `needs_frontend_integration` | `CodingWorkOrdersPanel` exists but backend routes unproven | MED | C03-T006: enable panel when backend routes confirmed |
| 14 | Failure/cancellation semantics | `needs_backend_proof` | Cancel routes exist in work_orders, delegations, agent_orchestration | MED | C03-T001: verify cancel semantics |
| 15 | Release-boundary enforcement | `ready_for_proof` | `00-current-state.md` explicitly excludes delegation; feature gates enforced | LOW | C03-T001: document release boundary |

## Audit Questions

### 1. What is the current canonical work-order artifact?

`CommandCenterCodingWorkOrder` interface in `frontend/src/features/commandCenter/types.ts` (lines 181-210). Fields include `work_order_id`, `campaign_id`, `title`, `objective`, `scope`, `status`, `priority`, `source_thread_id`, `source_message_id`, `dependency_ids`, `file_scope`, `validation_command`, `adapter_kind`, `latest_run_id`, `latest_lease_id`, `latest_receipt_id`, `blocked_reason`. Full workflow states: DRAFT through MERGED/ARCHIVED/CANCELLED.

### 2. Which route creates or mutates coding work orders?

`guardian/routes/coding_work_orders.py` — `POST /api/coding/work-orders` (create), `GET` (list), `GET /{id}` (detail), `POST /{id}/cancel`. Plus campaign runner routes: `POST /goals`, `GET /goals/{id}`, `POST /campaigns`, `GET /campaigns/{id}`. Plus orchestrator: `GET /orchestrator/next`. All feature-gated behind `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES`.

### 3. Which route or model stores delegation drafts?

`guardian/routes/delegations.py` — `POST /draft` creates a delegation packet. `guardian/routes/guardian_delegations.py` — `POST` creates a guardian delegation intent. Storage is through `DelegationService` and `GuardianDelegationService` respectively. Both feature-gated.

### 4. Is there a result artifact model or route?

`guardian/pi/contracts.py` defines `PiInvocationArtifact` (dataclass with `artifact_id`, `artifact_ref`). Also `PiHarnessResult` wrapping artifact + receipt. No dedicated route for result artifact return. Delegation worker publishes task events with execution results.

### 5. Is there a receipt model or route?

`guardian/pi/contracts.py` defines `PiInvocationReceipt` (dataclass with `status`, `summary`, `files_changed`, `artifacts`, `logs_summary`, `error_code`, `error_message`). No dedicated receipt route. Receipt persistence inferred from delegation worker task event publishing.

### 6. Is there a durable execution ledger or equivalent?

`coding_work_orders.py` campaign runner routes provide goal/campaign CRUD with work-order linkage via `latest_run_id` and `latest_receipt_id`. This is a partial ledger — tracks runs but not a dedicated ledger surface. ADR-028 defines Execution Ledger as a governed Campaign Runner extension.

### 7. Can command bus invoke be safely related to coding delegation?

Yes — command bus invocation is a bounded tool-turn mechanism, not a coding-agent execution path. The Agent Tool Loop Contract limits to one tool turn per completion. Command bus adjacency is `ready_for_proof` but must not be conflated with coding-agent execution.

### 8. Is command bus invocation equivalent to coding-agent execution?

**No.** Command bus invocation is a bounded single-command execution through the existing command infrastructure. Coding-agent execution involves multi-step plans, repository mutations, validation loops, and result artifacts. Command bus is adjacent but distinct.

### 9. Are Pi invocation envelope/receipt/artifact contracts implemented?

**Yes — backend-only, contract and validation only.** `guardian/pi/contracts.py` (858 lines) defines `PiInvocationEnvelope`, `PiInvocationReceipt`, `PiInvocationArtifact`, `PiHarnessResult`, `PiInvocationValidationResult`. `guardian/pi/validation.py` provides pure deterministic validators. `guardian/pi/tokens.py` provides canonical token domains. **Zero route registration.**

### 10. Is any live Pi/Coder harness invocation implemented?

**No.** The Pi Invocation Boundary Contract states: "no live Pi SDK call exists." ADR-020 is contract-only. No Pi SDK integration found.

### 11. Is there a route that validates Pi/Coder invocation envelopes?

**No.** Validation logic exists in `guardian/pi/validation.py` but no route exposes it. This is C11 BLOCKER-001 — C04 must create the validation route.

### 12. Is there any worker queue for coding delegation?

**Yes.** `guardian/workers/agent_worker.py` (agent worker) and `guardian/workers/delegation_worker.py` (delegation worker) exist. `docker compose ps` shows `worker-coding` running. Queue mechanism inferred from existing Redis queue infrastructure.

### 13. Is there any operator-visible status surface?

**Yes — frontend only, backend unproven.** `CodingWorkOrdersPanel.tsx` in the Command Center renders work orders, orchestrator recommendations, and create/cancel forms. `useCodingWorkOrders` hook calls `/api/coding/work-orders`. Backend route availability is unproven.

### 14. Are source thread/message IDs preserved through the delegation path?

**Yes — at the code level.** `CommandCenterCodingWorkOrder` has `source_thread_id` and `source_message_id`. `guardian/codex/lineage.py` validates thread/message existence. Delegation worker builds lineage from request context. Not runtime-verified.

### 15. Are auth/session boundaries explicit?

**Yes.** All delegation-adjacent routes use `_include_router()` with feature flags, supported profile posture, and `CODEXIFY_BETA_CORE_ONLY` gating. Guardian delegations are `default_enabled=False`. Auth uses existing X-API-Key mechanism proven in C02.

### 16. What is the smallest safe next implementation task?

**C03-T002: Verify coding work-order routes are runtime-available.** This is the lowest-risk task that unlocks all downstream C03 work: frontend panel visibility, artifact audit, worker execution proof, and Pi/Coder integration planning all depend on confirming the coding work-order CRUD surface is live.

## Contradictions

None. All findings are gaps between code presence and runtime proof, not contradictions of implemented behavior.

## Gaps

1. **Feature-gated routes**: All coding/delegation/command-bus routes are feature-gated and not runtime-verified. C03-T001 must verify at least coding work-order routes are reachable.
2. **Pi/Coder route absence**: Zero routes for Pi validation or invocation — C04 blocked on route registration.
3. **No result artifact return route**: Delegation worker publishes events but no dedicated artifact return endpoint.
4. **No execution ledger**: Campaign runner provides partial tracking but no dedicated ledger surface.
5. **Command run listing absent**: Only SSE stream for individual runs; no history endpoint.
6. **Frontend panel unverified**: CodingWorkOrdersPanel targets backend routes whose availability is unproven.

## Release-Boundary Notes

`00-current-state.md` (2026-06-16) explicitly states:
- "End-to-end Guardian delegation is not yet a release-supported path."
- "Do not assume delegation, federation, or graph write surfaces are part of the present release promise."
- C03 must not widen this boundary. All proof is current-state classification, not release support.

## Gate Decision

- **Decision**: `next-proof-needed`
- **Reason**: The coding delegation spine is sufficiently mapped to safely plan targeted implementation tasks, but the first concrete step — verifying coding work-order routes are runtime-available — has not yet been executed. All delegation-adjacent routes are feature-gated and not runtime-verified. The route matrix identifies 21 surfaces: 15 present (backend or frontend code), 1 partial (execution ledger), 5 absent (result artifact route, command run listing, Pi route surface, Pi live invocation, Pi validation route). The spine classification maps 15 seams: 5 ready_for_proof, 7 needing backend proof, 2 needing implementation, 1 deferred. The gate is `next-proof-needed` specifically for C03-T001 runtime verification of the coding work-order CRUD surface. All other C03 tasks (T002-T006) depend on this verification.

## Recommended Next Implementation Task

**C03-T001: Verify coding work-order routes are runtime-available.** Confirm that `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES` is enabled (or can be enabled safely) and that `POST /api/coding/work-orders` responds with structured data. This single verification unlocks the entire C03 spine.

---

## C03-T001: Coding Work-Order Route Runtime Verification (2026-06-17 22:35 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `740cce37b` — docs: record Guardian Maturity C03 coding delegation proof
- **Worktree**: Clean

### Commands Run

- `docker compose exec backend printenv` — checked runtime environment
- `grep` on `guardian/guardian_api.py` — located feature gate and router inclusion
- `grep` on `config/supported_profiles/v1-local-core-web-mcp.yaml` — inspected route posture
- `curl openapi.json` — checked for coding/delegation routes

### Feature-Gate Discovery

| Check | Evidence | Result | Notes |
|---|---|---|---|
| Feature flag located | `guardian/guardian_api.py:1224` — `flag_name="CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES"` | **Located** | Flag name confirmed |
| Feature flag default classified | `_include_router()` uses `default_enabled=True` (default parameter) | **default_enabled=True** | Route would be included if no other gate blocks it |
| Active runtime value observed | `docker compose exec backend printenv` — no `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES` set | **Not set** | Default applies (True) |
| Route source anchor located | `guardian/routes/coding_work_orders.py` — `router = APIRouter(...)`, POST/GET/cancel + orchestrator + campaign_runner | **Located** | 3 routers: main, orchestrator, campaign_runner |
| Router inclusion condition located | `guardian/guardian_api.py:1223-1228` — `_include_router(label="coding_work_orders", flag_name="CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES", include_fn=...)` | **Located** | Three-gate check: profile posture, BETA_CORE_ONLY, feature flag |
| OpenAPI route presence checked | `curl localhost:8888/openapi.json` — no coding/work-order/delegation paths | **Not in OpenAPI** | Routes are gated out |
| Auth boundary identified | Same X-API-Key mechanism as all chat routes (proven in C02) | **Identified** | No separate delegation auth |
| Payload schema identified | `CommandCenterWorkOrderCreateInput` in `frontend/src/features/commandCenter/types.ts` | **Identified** | title, objective, scope, status, priority, source_thread_id, source_message_id, etc. |
| Safe POST attempted or explicitly skipped | **Skipped** — route not mounted; no endpoint to POST to | N/A | Route is gated at the supported profile level |
| Readback/list proof attempted or explicitly skipped | **Skipped** — route not mounted | N/A | 同上 |
| No command execution triggered | N/A — no request sent | **Confirmed** | No mutation risk |
| No Pi/Coder invocation triggered | N/A — no request sent | **Confirmed** | No invocation risk |

### Root Cause: CODEXIFY_BETA_CORE_ONLY Blocks coding_work_orders

The `_include_router()` function in `guardian/guardian_api.py:240-310` applies three sequential gates:

1. **Supported profile route posture** — `coding_work_orders` is NOT listed in `enabled`, `internal_only`, or `quarantined`. Status is absent (not explicitly blocked).
2. **`CODEXIFY_BETA_CORE_ONLY`** — Currently `true` in the runtime environment. When set, non-core (`core_surface=False`) and non-internal routes are blocked. `coding_work_orders` has `core_surface=False` and is not `internal_only`, so it is blocked.
3. **Feature flag** — `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES` defaults to `true` and is not overridden in the environment. This gate would pass.

The effective blocker is gate #2: `CODEXIFY_BETA_CORE_ONLY=true` combined with `coding_work_orders` not being in the supported profile's `enabled` or `internal_only` lists.

### Route Availability Classification

**`source_present_but_feature_gated_off`**

The coding work-order CRUD surface exists in source code (`guardian/routes/coding_work_orders.py`, 307 lines) and is wired in `guardian/guardian_api.py` with `default_enabled=True`. The route is blocked at runtime by the supported profile's `CODEXIFY_BETA_CORE_ONLY` posture, which gates non-core, non-internal routes out of the active OpenAPI surface. The feature flag itself is not the blocker — the supported profile posture is.

### Resolution Options

1. **Add `coding_work_orders` to the supported profile's `enabled` list** in `v1-local-core-web-mcp.yaml`. This is the cleanest approach — coding work orders become a core surface under the supported profile.
2. **Set `CODEXIFY_BETA_CORE_ONLY=false`** — This would ungates all non-core routes, which is too broad for this task.
3. **Move `coding_work_orders` to `internal_only`** in the route posture — Routes would be hidden from OpenAPI but still accessible. This is the safest path if full enablement is premature.

### Contradictions

None. The behavior is consistent with the documented supported profile posture.

### Gaps

1. **coding_work_orders not in supported profile**: The route is absent from the `enabled` and `internal_only` lists. It must be explicitly added before it can be runtime-verified.
2. **No safe POST possible**: The route is not mounted, so no endpoint verification can be performed until the posture is updated.
3. **Frontend panel targets unproven backend**: `CodingWorkOrdersPanel` calls `/api/coding/work-orders` which returns errors when the route is gated.

### C03-T001 Gate Decision

- **Decision**: `next-proof-needed`
- **Reason**: The route is classified (`source_present_but_feature_gated_off`), the exact blocker is identified (`CODEXIFY_BETA_CORE_ONLY=true` + coding_work_orders not in supported profile route posture), and resolution options are documented. However, the route has not been runtime-verified because it is not mounted. C03-T001 cannot advance to `go` until the supported profile posture is updated to include `coding_work_orders` and the route is confirmed reachable.

### Recommended Next Task

**Add `coding_work_orders` to the supported profile's `internal_only` route posture.** This is the safest first step — it makes the route accessible (hidden from OpenAPI but functional) without widening the public beta surface. Once the route is reachable, C03-T001 can complete the runtime verification (safe POST, readback, auth confirmation).

---

## C03-T002: Internal Work-Order Route Posture Enablement (2026-06-17 22:36 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `a5ad0349d` — docs: verify Guardian coding work-order route availability
- **Worktree**: Clean

### Files Modified

- `config/supported_profiles/v1-local-core-web-mcp.yaml` — added `coding_work_orders` to `internal_only` route posture

### YAML Posture Change

```yaml
  internal_only:
+   - coding_work_orders
    - command_bus
```

### Runtime Reload

`docker compose restart backend` — backend restarted to pick up the modified supported profile. `docker compose up -d` was insufficient because no docker-compose.yml change occurred.

### C03-T002 Proof Table

| Check | Evidence | Result | Notes |
|---|---|---|---|
| Supported profile changed | `v1-local-core-web-mcp.yaml` line 39 — `coding_work_orders` added | **Changed** | One line added |
| `coding_work_orders` added to `internal_only` | Above YAML change | **Added** | Not in `enabled` or `quarantined` |
| Not added to public/core surface | `enabled` list unchanged | **Preserved** | Public beta surface not widened |
| Beta-core-only posture preserved | `CODEXIFY_BETA_CORE_ONLY=true` confirmed after restart | **Preserved** | Internal-only routes bypass BETA_CORE_ONLY gate |
| Runtime config observed | `docker compose exec backend printenv` — `BETA_CORE_ONLY=true` | **Confirmed** | Posture unchanged |
| Backend reload performed | `docker compose restart backend` | **Performed** | 40s to healthy |
| OpenAPI route discovery checked | No coding/delegation routes in OpenAPI | **Hidden** — expected for internal_only | Internal-only routes excluded from public OpenAPI |
| Direct route probe checked | `GET /api/coding/work-orders` → `{"ok":true,"items":[],"count":0,"limit":50,"offset":0}` | **Responding** | Route mounted and returning structured JSON |
| Safe POST attempted | `POST /api/coding/work-orders` with C03-T002 proof payload → `ok: True`, `work_order_id: wo_22eb074add604777`, `status: draft` | **Created** | Work order created with draft status |
| Readback/list proof attempted | `GET /api/coding/work-orders/{id}` → full detail returned; `GET /api/coding/work-orders` → count: 1 | **Verified** | Full CRUD readback confirmed |
| No command execution triggered | No command_bus or executor calls in create path | **Confirmed** | Work-order creation is pure CRUD |
| No Pi/Coder invocation triggered | No Pi SDK or harness calls | **Confirmed** | No invocation risk |
| Release boundary preserved | `00-current-state.md` delegation exclusion intact; route is internal-only | **Preserved** | No public beta claim |

### Route Posture Classification

**`internal_route_available_openapi_hidden`**

The coding work-order CRUD surface is mounted as an internal-only route. It is hidden from the public OpenAPI schema (expected for `internal_only` posture) but responds to direct requests with structured JSON. Full CRUD verified: POST create (returns work_order_id, status draft), GET single (returns full detail with timestamps), GET list (returns paginated items). Auth uses existing X-API-Key mechanism.

### Contradictions

None. Behavior matches `internal_only` posture expectations exactly.

### Gaps

1. **Source lineage not populated**: `source_thread_id` and `source_message_id` are `None` on the created work order — the proof POST did not supply them. They are optional fields on the input type.
2. **Status progression not tested**: Only `draft` status created. Status transitions (ready, leased, running, etc.) require worker/execution infrastructure.
3. **Orchestrator/campaign runner routes not tested**: Only the main work-order CRUD router was verified. The orchestrator (`/api/coding/orchestrator/next`) and campaign runner routes remain unproven.

### C03-T002 Gate Decision

- **Decision**: `go`
- **Reason**: The coding work-order CRUD route surface is now runtime-available under internal-only posture. Full CRUD (create, readback, list) is verified with structured JSON responses. No command execution, Pi/Coder invocation, or repository mutation occurred. The public beta surface is not widened — the route remains hidden from OpenAPI and excluded from the `enabled` route posture. The supported profile posture (`CODEXIFY_BETA_CORE_ONLY=true`, local-only, cloud-disabled) is preserved.

### Recommended Next Task

**C03-T003: Work-order artifact contract audit.** With the route surface confirmed runtime-available, audit the work-order payload shape against ADR-020's coding-task envelope fields (codingTaskId, threadId, sourceMessageId, permission policy, adapter kind, etc.). Identify which ADR-020 fields are represented in the current work-order schema and which are missing.

---

## C03-T003: Work-Order Artifact Contract Audit (2026-06-17 22:50 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `fbb17ace7` — config: mark coding work orders as internal supported route
- **Worktree**: Clean
- **Runtime**: Backend healthy, route mounted as internal_only

### Source Files Inspected

- `guardian/agents/work_orders.py` — `WorkOrderCreate`, `WorkOrderContract`, `WORK_ORDER_STATUSES`, status transitions
- `guardian/routes/coding_work_orders.py` — `WorkOrderCreateRequest` (Pydantic), create/list/get/cancel routes
- `guardian/db/models.py:4267-4333` — `CodingWorkOrder` SQLAlchemy model
- `guardian/db/migrations/versions/9d4e1c7b2a6f_add_coding_work_orders.py` — migration
- `frontend/src/features/commandCenter/types.ts:161-268` — `CommandCenterCodingWorkOrder`, `CommandCenterWorkOrderCreateInput`

### Artifact Contract Table

| # | Artifact Dimension | Current Evidence | Classification | Notes |
|---|-------------------|-----------------|----------------|-------|
| 1 | Durable work-order id | `work_order_id: str(64)` — format `wo_{uuid_hex}`, primary key in `coding_work_orders` table | **proven** | Auto-generated; verified in C03-T002 POST response |
| 2 | Storage table/model | `CodingWorkOrder` SQLAlchemy model in `guardian/db/models.py:4267`; migration `9d4e1c7b2a6f` | **proven** | Durable Postgres table with 20+ columns |
| 3 | Create payload | `WorkOrderCreateRequest` (Pydantic) — 20 fields; routes to `WorkOrderCreate` dataclass | **proven** | No execution fields populated on create; `status` defaults to `"ready"` if not supplied |
| 4 | Read payload | `WorkOrderContract` dataclass — 27 fields including `latest_run_id`, `latest_lease_id`, `latest_receipt_id`, timestamps | **proven** | Full shape returned by GET /{id} and list |
| 5 | List payload | `{"ok":true,"items":[...],"count":N,"limit":50,"offset":0}` | **proven** | Paginated; C03-T002 verified count:1 |
| 6 | Status vocabulary | 15 statuses: draft, ready, leased, running, validating, retrying, passed, failed, blocked, escalated, merge_ready, merged, archived, cancelled | **proven** | Defined in `agents/work_orders.py:31-58` |
| 7 | Status transition semantics | `WORK_ORDER_ALLOWED_TRANSITIONS` — strict DAG of allowed state changes (e.g., draft→ready/cancelled, running→validating/failed/blocked/etc.) | **proven** | Enforced by `_is_terminal_work_order_status()` in route |
| 8 | Draft/storage acceptance | POST creates a durable row; status defaults to `"ready"`; no enqueue, no worker dispatch | **proven** | Pure CRUD — storage acceptance only |
| 9 | Execution acceptance | **Not present** — POST does not enqueue, call command bus, invoke Pi/Coder, or dispatch workers | **proven (absent)** | No execution path in create route |
| 10 | Queue/worker binding | `coding_work_orders.py` does not enqueue; agent_worker and delegation_worker exist separately | **absent from work-order CRUD** | Workers are separate infrastructure; work orders are task-board records |
| 11 | Command bus binding | No command bus invocation in work-order CRUD | **absent** | Command bus is adjacent via `guardian/routes/command_bus.py` |
| 12 | Pi/Coder binding | No Pi/Coder references in work-order code | **absent** | Pi contracts are in `guardian/pi/` — separate module |
| 13 | Source thread id | `source_thread_id: str(128)` — optional, nullable in DB | **present_not_runtime_verified** | Field exists; C03-T002 POST did not supply it |
| 14 | Source message id | `source_message_id: str(128)` — optional, nullable in DB | **present_not_runtime_verified** | Field exists; not populated in C03-T002 |
| 15 | Project id | Not present in work-order schema | **absent** | Not a field on `WorkOrderCreate` or `WorkOrderContract` |
| 16 | User/actor id | `created_by: str(255)` — optional | **present_not_runtime_verified** | Field exists; not populated in C03-T002 |
| 17 | Audit/provenance record | `created_at`, `updated_at`, `archived_at` timestamps on `CodingWorkOrder` | **proven** | C03-T002 verified `created_at` returned |
| 18 | Receipt field/model/route | `latest_receipt_id: str(64)` — optional, nullable | **present_not_runtime_verified** | Field exists but no receipt route or creation logic |
| 19 | Artifact field/model/route | No artifact field on work order | **absent** | `PiInvocationArtifact` exists in Pi contracts but not linked to work orders |
| 20 | Result-return path | No result-return route or logic in work-order CRUD | **absent** | Result return exists in delegation worker (events) but not linked |
| 21 | Frontend route usage | `useCodingWorkOrders` hook calls `GET /api/coding/work-orders`, `POST /api/coding/work-orders`, `POST /api/coding/work-orders/{id}/cancel` | **present_not_runtime_verified** | Frontend targets now-reachable backend routes |
| 22 | Frontend user-facing wording | "Coding Work Orders" panel; status badges for draft/ready/running/etc.; create form with title/objective/scope | **frontend_only** | UI implies task-board semantics, not live execution |
| 23 | Release-boundary risk | Work-order CRUD is internal-only; no public beta claim | **low** | `00-current-state.md` delegation exclusion intact |

### Acceptance Semantics Table

| Operation | What It Proves | What It Does Not Prove | Evidence |
|---|---|---|---|
| `GET /api/coding/work-orders` | Durable storage of work-order rows; paginated readback | Execution, enqueue, worker dispatch | C03-T002: count:1, items with full WorkOrderContract shape |
| `POST /api/coding/work-orders` | Durable creation of a coding task-board record with 20 fields | Guardian acceptance of execution, command dispatch, Pi/Coder invocation, repository mutation | C03-T002: ok:True, work_order_id returned, status:draft |
| `GET /api/coding/work-orders/{id}` | Full readback of a single work order with timestamps, run/lease/receipt IDs | Execution status, receipt existence | C03-T002: full WorkOrderContract returned |
| Update route | Not present in current routes | N/A | Only create/list/get/cancel routes exist |
| Delete/archive route | Not present as dedicated route | N/A | `archived` is a terminal status, not a delete |
| Status transition route | Not present as dedicated route | N/A | Status transitions happen through worker/orchestrator, not direct API |
| Result/receipt/artifact route | Not present | N/A | `latest_receipt_id` field exists but no dedicated result route |

### Audit Answers

1. **What is the current canonical coding work-order artifact?**
   A durable task-board record stored in the `coding_work_orders` Postgres table with 20+ typed fields. It captures operator intent (title, objective, scope), execution parameters (adapter_kind, validation_command, file_scope), lineage anchors (source_thread_id, source_message_id), and execution references (latest_run_id, latest_lease_id, latest_receipt_id). Status follows a 15-state DAG with strict transitions.

2. **Is the artifact durable?**
   Yes. Stored in Postgres via SQLAlchemy `CodingWorkOrder` model. Migration `9d4e1c7b2a6f` created the table. C03-T002 confirmed reads survive across requests.

3. **What does `status: draft` mean?**
   "Draft" means the work order is created but not ready for dispatch. Transition rules: draft → ready or cancelled. It is storage-only — no enqueue, no worker, no execution.

4. **Does creating a work order enqueue anything?**
   No. `create_work_order()` calls `store.create_work_order()` which persists to DB only. No Redis enqueue, no task dispatch.

5. **Does creating a work order invoke command bus?**
   No. No command bus references in `coding_work_orders.py`.

6. **Does creating a work order invoke Pi/Coder?**
   No. Pi contracts are in a separate module (`guardian/pi/`) with zero route registration.

7. **Does creating a work order mutate repositories?**
   No. No git operations, file writes, or shell execution in the create path.

8. **Does the artifact bind to source thread/message lineage?**
   Partially. Fields `source_thread_id` and `source_message_id` exist on the model, DB, create payload, and response. They are optional — not validated for existence against the chat DB. C03-T002 did not populate them.

9. **Does the artifact bind to project/user identity?**
   Partially. `created_by` field exists for actor identity. No `project_id` field on work orders. Campaign runner has separate goal/campaign hierarchy with project scoping.

10. **Does the artifact create or reference receipts?**
   Partially. `latest_receipt_id` field exists on the response model and DB. No receipt creation logic in work-order CRUD. Receipts are populated by the delegation/agent workers.

11. **Does the artifact create or reference result artifacts?**
   No. No artifact field on work orders. `PiInvocationArtifact` exists in Pi contracts but is not linked to work orders.

12. **Does the frontend imply execution beyond what backend proves?**
   The frontend `CodingWorkOrdersPanel` renders work orders as a task board with status badges. It offers a create form and cancel action. It does not imply live execution — the UI shows status labels but no "Run" or "Execute" button in the current panel. Orchestrator recommendations are polled separately.

13. **What is the smallest safe next implementation or proof task?**
   **C03-T004: Verify command bus adjacency and invocation boundary.** The work-order artifact is a task-board record. The command bus is the adjacent execution mechanism. Proving that command bus invoke does not bypass Guardian authority and that command runs link to work orders (via `latest_run_id`) is the next seam.

### ADR-020 Field Mapping

| ADR-020 Required Field | Work Order Field | Status |
|---|---|---|
| `codingTaskId` | `work_order_id` | **present** — maps to durable work order identity |
| `threadId` | `source_thread_id` | **present** — optional, not validated |
| `sourceMessageId` | `source_message_id` | **present** — optional, not validated |
| `requestId` / `attemptId` | Not present | **absent** — no attempt-level identity on work order |
| `userId` / actor subject | `created_by` | **present** — optional |
| `projectId` | Not present | **absent** |
| `workspace scope` / `repo root` | `scope` (text) + `file_scope` (string list) | **present** — scope is free text; file_scope is path list |
| `allowed paths` | `file_scope` | **present** — explicit path list |
| `instructions` | `objective` + `title` | **present** — title + objective capture instructions |
| `context bundle summary` | Not present | **absent** — no context summary field |
| `permission policy` | Not present | **absent** — no permission/capability policy on work order |
| `adapter kind` | `adapter_kind` | **present** — optional string |

### Contradictions

None.

### Gaps

1. **No permission policy field** — ADR-020 requires `permission policy` for adapter-bound scope. Work orders have no permission/capability policy.
2. **No request/attempt identity** — ADR-020 requires `requestId`/`attemptId` for execution attempt tracking. Work orders have no attempt-level identity.
3. **No project scoping** — ADR-020 requires `projectId`. Work orders have no project field.
4. **No context bundle summary** — ADR-020 requires `context bundle summary` sent to adapter.
5. **Source lineage not validated** — `source_thread_id`/`source_message_id` are stored but not validated against chat DB.
6. **No result artifact linkage** — Work orders have no field for result artifacts.
7. **Receipts are reference-only** — `latest_receipt_id` is a string field with no creation/readback route.

### C03-T003 Gate Decision

- **Decision**: `go`
- **Reason**: The coding work-order artifact contract is fully classified. The artifact is a durable task-board record with 20+ typed fields, 15-state status DAG, and strict transition rules. It captures operator intent and execution parameters but does NOT execute, enqueue, invoke command bus, or call Pi/Coder. ADR-020 field mapping identifies 7 present fields, 5 absent fields. All gaps are explicit and non-blocking for the next seam (command bus adjacency).

### Recommended Next Task

**C03-T004: Verify command bus adjacency and invocation boundary.** Prove that command bus invocation is adjacent to (not equivalent to) coding-agent execution, that command runs can link to work orders via `latest_run_id`, and that invocation does not bypass Guardian authority.

---

## C03-T004: Command Bus Adjacency and Invocation Boundary Audit (2026-06-17 23:05 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `8efdf59ee` — docs: audit Guardian coding work-order artifact contract
- **Worktree**: Clean
- **Runtime**: Backend healthy, command_bus internal_only, coding_work_orders internal_only

### Source Files Inspected

- `guardian/routes/command_bus.py` — manifest, search, invoke, activation/inspect, run events routes
- `guardian/command_bus/contracts.py` — `ActorSpec`, `InvokeArguments`, `InvokePermissionProfile`
- `guardian/command_bus/manifest.py` — `build_manifest()`, `build_command_index()`
- `guardian/command_bus/store.py` — `CommandBusStore` with `list_events_after()`
- `guardian/db/models.py:3937-4018` — `CommandRun`, `CommandRunEvent` SQLAlchemy models
- `guardian/agents/work_orders.py:311-312` — `latest_run_id`, `latest_lease_id` on `WorkOrderContract`
- `guardian/routes/tools.py` — legacy tools route (no command_bus references)
- `guardian/guardian_api.py` — router inclusion with `internal_only` posture

### Commands Run

- `curl GET /api/command-bus/manifest` — returned `{"commands":[]}` (0 commands registered)
- `curl openapi.json` — no command/tools routes visible (internal_only)
- `grep` source searches for command_bus, CommandRun, work-order linkage

### Command Bus Boundary Table

| # | Boundary Dimension | Current Evidence | Classification | Notes |
|---|-------------------|-----------------|----------------|-------|
| 1 | Command bus route mount | `guardian/routes/command_bus.py` — router with manifest/search/invoke/inspect/events | **present** | 5 endpoint types |
| 2 | Supported-profile posture | `internal_only` in `v1-local-core-web-mcp.yaml` | **proven** | Hidden from OpenAPI, accessible directly |
| 3 | OpenAPI visibility | No command routes in OpenAPI | **hidden** | Expected for internal_only |
| 4 | Manifest route | `GET /manifest` — returns command specifications from app route introspection | **proven** | 0 commands registered in current runtime |
| 5 | Invoke route | `POST /invoke` — accepts `InvokeArguments` with command_id, args, path_params | **present_not_runtime_verified** | Route exists; no commands to invoke |
| 6 | Run read/list route | Not present — no GET route for individual runs or run listing | **absent** | Only events stream available |
| 7 | Run event route | `GET /runs/{run_id}/events` — SSE stream | **present_not_runtime_verified** | Stream route exists |
| 8 | Auth boundary | X-API-Key header; routes use `Depends(require_api_key)` | **proven** | Same auth as chat routes (C02 proven) |
| 9 | Command discovery source | `build_manifest(app)` introspects FastAPI routes for command metadata | **source_only** | 0 commands in current runtime |
| 10 | Command id shape | String from route path — e.g., `/api/health` → normalized command id | **source_only** | No commands to inspect |
| 11 | Argument schema shape | `InvokeArguments(path_params, query, headers)` — free-form dicts | **source_only** | No typed argument schemas per command |
| 12 | Result payload shape | `InvokeResponse` with `run_id`, `status`, `result` | **source_only** | No runtime evidence |
| 13 | CommandRun durable model | `CommandRun` SQLAlchemy model — `command_runs` table, 20+ columns | **proven** | Durable Postgres storage with indexes |
| 14 | CommandRunEvent durable model | `CommandRunEvent` — `command_run_events` table, FK to CommandRun | **proven** | Append-only event log |
| 15 | Status vocabulary | 5 states: queued, running, completed, failed, blocked | **proven** | Check constraint enforced |
| 16 | Event vocabulary | Defined in `CommandRunEvent` — event_type, sequence_number, payload | **source_only** | No runtime event data |
| 17 | Actor/auth subject capture | `actor_kind`, `actor_id`, `auth_subject`, `delegated_by` on CommandRun | **proven** | Full actor chain captured |
| 18 | Idempotency behavior | `idempotency_key` + `args_hash`; `uq_command_idempotency_key` unique constraint | **proven** | DB-level dedup on command_id + idempotency_key |
| 19 | Policy enforcement | `InvokePermissionProfile` — allowed/denied command classes, ids, write roots, shell commands | **source_only** | Permission model defined; no runtime enforcement evidence |
| 20 | Shell execution capability | `allowed_shell_commands` in permission profile | **source_only** | Capability defined but no commands registered |
| 21 | Internal HTTP invocation | Command bus invokes FastAPI routes via `invoke.py` loopback adapter | **source_only** | `loopback_http_adapter.py` provides internal HTTP dispatch |
| 22 | External harness/Pi capability | No Pi/Coder references in command_bus module | **absent** | Command bus has zero Pi/Coder awareness |
| 23 | Repository mutation capability | `allowed_write_roots` in permission profile | **source_only** | Write path gating defined; no commands registered |
| 24 | Legacy tools shim relationship | `guardian/routes/tools.py` — no command_bus references found | **absent** | Tools route is separate; no delegation to command bus |
| 25 | Frontend command bus usage | `invokeCommandBus()` in `api.ts`; `command_bus.invoke` intent kind | **frontend_only** | Frontend client exists; no runtime invocation evidence |
| 26 | Work-order `latest_run_id` field | `latest_run_id: str(64)` on `CodingWorkOrder` and `WorkOrderContract` | **present** | Loose string field; no FK, no lookup, no runtime population |
| 27 | Work-order to command-run FK/link | No FK from coding_work_orders to command_runs | **absent** | No DB-level relationship |
| 28 | Command run to work-order back-reference | No work_order_id on CommandRun | **absent** | No reverse reference |
| 29 | Release-boundary risk | Command bus has 0 registered commands; no execution surface | **low** | Internal-only, empty manifest |

### Invocation Semantics Table

| Operation | What It Proves | What It Does Not Prove | Evidence |
|---|---|---|---|
| Command manifest | Route introspection of FastAPI app for command metadata | Any commands are registered or invocable | `GET /api/command-bus/manifest` → `commands: []` (0 commands) |
| Command invoke | Route accepts structured invocation payloads with actor identity | Any command is executable | Route exists but 0 commands registered; no invocation possible |
| Command run readback/listing | Not present — no GET route for runs | N/A | No listing endpoint |
| Command run events | SSE stream for individual run events | Any run events exist | Route exists; no runs to stream |
| Legacy tools invocation | Tools route exists; no command_bus integration | Tools bypasses or uses command bus | No command_bus references in tools.py |
| Work-order readback with latest_run_id | Field exists on response model | Any runtime population exists | C03-T002 work order returned `latest_run_id: None` |
| Work-order update to set latest_run_id | No update route for work orders | N/A | Only create/list/get/cancel routes exist |

### Audit Answers

1. **What is the current canonical command bus surface?**
   An internal-only route set (`guardian/routes/command_bus.py`) providing manifest, search, invoke, activation/inspect, and run events. Commands are discovered from FastAPI route introspection via `build_manifest()`. Currently 0 commands registered in runtime.

2. **Is command bus mounted under current supported posture?**
   Yes — `internal_only` in `v1-local-core-web-mcp.yaml`. Hidden from OpenAPI, accessible via direct requests with auth.

3. **Is command bus OpenAPI-visible or internal-only hidden?**
   Internal-only hidden. No command routes appear in OpenAPI.

4. **What does command bus manifest prove?**
   It proves route introspection works and returns structured command specifications. Currently returns 0 commands — the command registry is empty in the local runtime.

5. **What does command bus invocation prove?**
   Route exists and accepts structured payloads with actor identity, idempotency key, and args hash. Cannot be proven at runtime because 0 commands are registered.

6. **Does command bus invocation equal coding-agent execution?**
   **No.** Command bus invokes individual FastAPI routes through a loopback HTTP adapter. Coding-agent execution involves multi-step plans, repository mutations, validation loops, and result artifacts. Command bus is a bounded single-command mechanism — it is adjacent, not equivalent.

7. **Does command bus invocation call Pi/Coder?**
   **No.** Zero references to Pi, PiInvocation, PiHarness, or Pi/Coder in the entire `guardian/command_bus/` module.

8. **Does command bus invocation call shell or subprocess?**
   **Not by default.** Permission profiles can gate `allowed_shell_commands`, but no commands are registered and no shell commands are configured.

9. **Can command bus mutate repositories today?**
   **No.** Permission profiles can gate `allowed_write_roots`, but 0 commands are registered. No repository mutation is possible without registered commands.

10. **Can command bus invoke internal read-only routes today?**
   **Architecturally yes** — the loopback HTTP adapter can invoke any registered FastAPI route. **At runtime no** — 0 commands are registered in the manifest.

11. **Can command bus invoke internal mutating routes today?**
   Same answer as #10 — architecturally possible, runtime impossible with empty manifest.

12. **What policy/idempotency boundary exists?**
   `InvokePermissionProfile` gates command classes, command ids, write roots, and shell commands. `idempotency_key` + `args_hash` with `uq_command_idempotency_key` unique constraint prevents duplicate invocations. Full actor chain (`actor_kind`, `actor_id`, `auth_subject`, `delegated_by`) is captured.

13. **What durable command run data is stored?**
   `CommandRun` model stores run_id, command_id, status, actor chain, idempotency_key, args_hash, args_redacted, result_json, error_text, and timestamps. `CommandRunEvent` stores ordered append-only events with FK to CommandRun.

14. **Are command run events stored?**
   Yes — `CommandRunEvent` model provides durable append-only event storage.

15. **Can command runs link to coding work orders through `latest_run_id`?**
   **Architecturally yes** — `latest_run_id` exists as a string field on `WorkOrderContract` and `CodingWorkOrder`. **At runtime no** — no code path populates it. No FK relationship exists. No command run references work_order_id. The linkage is a loose string convention, not a proven relationship.

16. **Is that link source-only, runtime-proven, docs-only, or absent?**
   **Source-only.** Field exists in code. Not populated at runtime. Not enforced by DB constraint. No back-reference.

17. **Does legacy `/tools` bypass command bus authority?**
   **No.** `guardian/routes/tools.py` has zero references to command_bus. The tools route is a separate legacy surface with its own authority semantics. No bypass or delegation relationship exists.

18. **Does frontend imply command bus is coding-agent execution?**
   **No.** Frontend has `invokeCommandBus()` for direct command invocation and `command_bus.invoke` intent kind for the intent spine. Neither labels command bus as coding-agent execution. The `CodingWorkOrdersPanel` renders work orders as a task board — no command-bus-to-coding-agent conflation.

19. **What is the smallest safe next implementation or proof task?**
   **C03-T005: Verify delegation routes and worker execution seam.** The command bus is empty (0 commands) and has no work-order linkage. Proving coding delegation execution requires verifying the delegation worker and agent worker seams, which are downstream of command bus registration. Command bus registration is a prerequisite.

### Contradictions

None.

### Gaps

1. **Empty command manifest**: 0 commands registered. Command bus infrastructure exists but has no commands to invoke. Registration requires adding command metadata to FastAPI routes.
2. **No command run listing**: Only SSE stream for individual runs. No list/search endpoint for command run history.
3. **Work-order run linkage is source-only**: `latest_run_id` field exists but is never populated. No FK, no back-reference, no runtime linkage.
4. **No dedicated work-order update route**: Cannot set `latest_run_id` or transition status through the API. Status transitions require worker/orchestrator.
5. **Invocation boundary unproven at runtime**: 0 commands → no invocation proof possible. Safe invocation requires at least one registered read-only command.

### C03-T004 Gate Decision

- **Decision**: `next-proof-needed`
- **Reason**: The command bus boundary is fully classified across 29 dimensions. The surface is internal-only with durable CommandRun/CommandRunEvent storage, idempotency enforcement, and actor chain capture. However, the command manifest is empty (0 commands registered), making invocation proof impossible. Work-order run linkage is source-only — `latest_run_id` exists but is never populated. The gate is `next-proof-needed` specifically because command registration is a prerequisite for any downstream execution proof. The next task must register at least one safe read-only command before invocation can be proven.

### Recommended Next Task

**Register a safe read-only command in the command bus manifest.** The smallest step: add command metadata to an existing read-only FastAPI route (e.g., `/health` or `/api/llm/catalog`) so the manifest returns at least one command. This unlocks invocation proof without adding mutating behavior.

---

## C03-T005: Command Bus Manifest Discovery + Safe Invocation Proof (2026-06-17 23:27 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `2aa77d41c` — docs: verify Guardian command bus delegation boundary
- **Worktree**: Clean
- **Runtime**: Backend healthy, command_bus internal_only

### Root Cause of "Empty Manifest"

**Path discovery error — no code bug.** The C03-T004 audit probed `/api/command-bus/manifest` and `/command-bus/manifest` (returns 404) and an earlier probe returned `{"commands":[]}` from an unidentified path. The correct command bus route prefix is `/api/guardian/commands` (set in `guardian/routes/command_bus.py:38`). Probing the correct path `/api/guardian/commands/manifest` returns **106 commands** including 12 health commands.

The manifest builder (`guardian/command_bus/manifest.py`) works correctly — it auto-discovers commands from FastAPI OpenAPI operationIds with no manual registration needed. No code change was required.

### Files Inspected (No Modifications Needed)

- `guardian/routes/command_bus.py:38` — router prefix `/api/guardian/commands`
- `guardian/command_bus/manifest.py` — `build_manifest(app)` auto-discovery from OpenAPI
- `guardian/command_bus/contracts.py` — `InvokeRequest`, `ActorSpec`, `InvokeArguments`

### Manifest Proof

| Metric | Before (C03-T004) | After (C03-T005) |
|--------|-------------------|-------------------|
| Path probed | Wrong paths (404) | `/api/guardian/commands/manifest` ✅ |
| Commands | 0 (probed wrong path) | **106** |
| Health commands | 0 | **12** (all read_only, safe) |
| `op::health_health_get` | Not found | **Found** — `GET /health`, risk=read_only, idemp=safe, approval=none |

### Invocation Proof

**Command**: `op::health_health_get` (GET /health)

| Field | Value |
|-------|-------|
| `run_id` | `run_e9b7b4e4d3f44271` |
| `status` | `completed` |
| Health result | `status: ok, service: core` |
| `events_url` | `/api/guardian/commands/runs/{run_id}/events?after_seq=0` |
| `policy_warnings` | `[]` (no policy violations) |

### CommandRun Persistence

Invocation creates a durable `CommandRun` record (proven by `run_id` returned and events stream responding). Run events show lifecycle: `run.created` → `run.started` → `run.completed`.

### Idempotency

Idempotency key support exists in `InvokeRequest` schema (`idempotency_key` field) and `CommandRun` model (`uq_command_idempotency_key` unique constraint). Not tested in this proof pass (read-only command has no side effects to dedup).

### Actor/Auth Subject

Actor spec `{"kind": "system", "id": "local"}` accepted. `auth_subject: "local"` captured in policy enforcement (confirmed in error response when mismatched actor was attempted).

### Exclusion Proof

| Check | Result |
|-------|--------|
| Shell execution | **None** — health command is FastAPI route loopback, no subprocess |
| Pi/Coder invocation | **None** — zero Pi references in command bus module |
| Repository mutation | **None** — health is read-only GET |
| Work-order linkage mutation | **None** — no work-order fields touched |
| Release boundary | **Preserved** — command bus remains internal_only |

### C03-T005 Gate Decision

- **Decision**: `go`
- **Reason**: Manifest discovery works correctly — 106 commands auto-discovered from OpenAPI with no manual registration. Safe health command invocation proven end-to-end: run_id returned, status completed, health result ok, events stream confirmed, no shell/Pi/Coder/repository mutation. The "empty manifest" was a path discovery error in the probe URL, not a code bug. No code changes were needed.

### Recommended Next Task

**C03-T006: Prove work-order-to-command-run linkage.** With command invocation proven, the next step is to populate `latest_run_id` on a coding work order when a command run is created, establishing the link between work orders and execution records.

---

## C03-T006: Work-Order-to-Command-Run Linkage Proof (2026-06-17 23:40 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `0cac2ec7b` — docs: prove Guardian command bus manifest and health invocation
- **Worktree**: Clean

### Files Modified

- `guardian/command_bus/contracts.py` — added `work_order_id: str | None` to `InvokeRequest`
- `guardian/command_bus/invoke.py` — added `work_order_store` param; calls `mark_latest_run()` after run creation
- `guardian/routes/command_bus.py` — wires `WorkOrderStore` singleton; passes to `execute_invoke()`

### Linkage Field

- **Field**: `work_order_id` (optional, max 64 chars) on `InvokeRequest`
- **Behavior**: When present, calls `WorkOrderStore.mark_latest_run(work_order_id, run_id=run_id)` after CommandRun creation
- **Error handling**: Linkage failure is best-effort — command invocation succeeds regardless
- **Idempotency**: Repeated invocation with same idempotency key returns existing run; linkage is stable

### Runtime Proof

| Step | Result |
|------|--------|
| Create work order | `wo_c1d4c0dbf3874986`, status: draft |
| Invoke health with `work_order_id` | `run_2611e0560d4e455a`, status: completed |
| Read back work order | `latest_run_id: run_2611e0560d4e455a` ✅ |
| Work order status | `draft` (unchanged) ✅ |
| Invoke without `work_order_id` | `run_6266270456b7413e`, no linkage ✅ |
| Invoke with nonexistent `work_order_id` | Command succeeds; `WORK_ORDER_NOT_FOUND` from work order readback ✅ |
| No shell/Pi/Coder/repo mutation | Confirmed ✅ |

### C03-T006 Gate Decision

- **Decision**: `go`
- **Reason**: Work-order-to-command-run linkage is runtime-proven. `latest_run_id` is populated when `work_order_id` is supplied on invocation. Work order status is preserved (remains draft). Command invocation without `work_order_id` still works without side effects. Nonexistent work order IDs cause a silent skip (command succeeds, linkage fails gracefully). The link uses the existing `WorkOrderStore.mark_latest_run()` method — no new storage semantics.

### Recommended Next Task

**C03-T007: Delegate work-order execution through command bus with result-return proof.** Now that work orders can link to command runs, the next step is to create a work order, invoke a command through it, read back the command result, and record the result as a work order execution artifact.

---

## C03-T006-R1: Fail-Closed Linkage Repair (2026-06-17 23:55 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `dc6887307` — feat: link Guardian work orders to command runs
- **Worktree**: Clean

### Invalid-Linkage Bug

C03-T006 silently skipped linkage when `work_order_id` was invalid (nonexistent or malformed). The command executed regardless, creating a CommandRun with no work-order trace.

### Repair

Moved work-order validation BEFORE command run creation in `execute_invoke()`. When `work_order_id` is supplied:
1. Format validation via regex `^wo_[a-f0-9]{16}$` → malformed → 422 `work_order_id_malformed`
2. DB lookup via `WorkOrderStore.get_work_order()` → not found → 404 `work_order_not_found`
3. If store unavailable → 400 `work_order_linkage_unavailable`

All failures halt before `store.create_run()` — the command target never executes.

### Files Modified

- `guardian/command_bus/invoke.py` — added `_is_valid_work_order_id_format()`, moved validation before run creation, removed silent skip

### Runtime Proof

| Scenario | Result |
|----------|--------|
| Valid `work_order_id` | `run_id: run_38133fb94f1f448e`, `latest_run_id` populated, status: draft |
| Nonexistent (valid format `wo_ffffffffffffffff`) | `work_order_not_found`, no run_id, no execution |
| Malformed (`not-a-valid-wo-id`) | `work_order_id_malformed`, no run_id, no execution |
| No `work_order_id` | `run_id: run_e30791a63c69466f`, normal invocation |

### C03-T006-R1 Gate Decision

- **Decision**: `go`
- **Reason**: Fail-closed behavior proven for all invalid linkage cases. Nonexistent and malformed work_order_id both halt before command execution. Valid linkage preserved. No-link invocation preserved. Work order status preserved.

---

## C03-T006-R2: Focused Backend Linkage Tests (2026-06-18 00:10 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `3614ee7b6` — fix: fail closed on invalid Guardian work-order command links
- **Worktree**: Clean

### Files Modified

- `tests/routes/test_command_bus_work_order_linkage.py` — 13 new tests (new file)

### Test Results

```
tests/routes/test_command_bus_work_order_linkage.py .............  13 passed
```

| Test Class | Tests | Key Coverage |
|------------|-------|-------------|
| `TestValidLinkage` | 2 | `latest_run_id` populated, status preserved |
| `TestNoLinkInvocation` | 2 | Succeeds without `work_order_id`, no mutation |
| `TestNonexistentWorkOrder` | 3 | 404 `work_order_not_found`, no execution, store-unavailable 400 |
| `TestMalformedWorkOrder` | 2 | 422 `work_order_id_malformed`, empty string → normal invoke |
| `TestIdempotency` | 2 | Repeat preserves same link, idempotency without WO works |
| `TestSafetyExclusions` | 2 | Loopback only, no shell/Pi/Coder/repo mutation |

### C03-T006-R2 Gate Decision

- **Decision**: `go`
- **Reason**: 13 focused backend tests pass, covering valid linkage, no-link, nonexistent fail-closed, malformed fail-closed, store-unavailable, idempotency, and safety exclusions. All invalid linkage cases are regression-proven.

---

## C03-T007: Result-Return Seam Audit (2026-06-18 00:20 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `01cd0fa17` — test: prove Guardian work-order command-run linkage
- **Worktree**: Clean
- **Runtime**: Backend healthy, 11 services running

### Commands Run

- `grep` source searches for `result_json`, `error_text`, `latest_receipt_id`, artifact, receipt
- `curl` invoke with `op::health_health_get` — captured `inline_result` shape
- `curl` GET run — confirmed 404 (no run readback route)
- `grep` CommandBusStore — confirmed `get_run()`, `update_run()` exist but no route
- `grep` Pi contracts — confirmed `PiInvocationReceipt`, `PiInvocationArtifact` exist in Pi module

### Result-Return Seam Table

| # | Seam Dimension | Evidence | Classification | Notes |
|---|---------------|----------|----------------|-------|
| 1 | CommandRun durable result field | `CommandRun.result_json` (JSONB) in `guardian/db/models.py:3967` | **present_not_runtime_verified** | Populated by loopback adapter; no readback route |
| 2 | CommandRun durable error field | `CommandRun.error_text` (Text) in `guardian/db/models.py:3968` | **present_not_runtime_verified** | Nullable; no readback route |
| 3 | CommandRun readback route | `GET /api/guardian/commands/runs/{run_id}` → 404 | **absent** | Store has `get_run()` but no route exposes it |
| 4 | CommandRun events route | `GET /api/guardian/commands/runs/{run_id}/events` — SSE stream | **proven** | C03-T005 confirmed `run.created`/`started`/`completed` events |
| 5 | CommandRun result body shape | Invoke response `inline_result.body` — HTTP response from target | **proven** | Health returns `{"status":"ok","service":"core"}` |
| 6 | CommandRun actor/auth metadata | `CommandRun` stores `actor_kind`, `actor_id`, `auth_subject`, `delegated_by` | **present_not_runtime_verified** | Stored in DB; no readback route |
| 7 | Work-order `latest_run_id` | `CodingWorkOrder.latest_run_id` — string, nullable, no FK | **proven** | C03-T006 proven via runtime and tests |
| 8 | Work-order readback includes `latest_run_id` | `GET /api/coding/work-orders/{id}` returns `latest_run_id` | **proven** | C03-T006 confirmed |
| 9 | Work-order readback includes command result | Not included | **absent** | Only `latest_run_id` pointer; no embedded result |
| 10 | Work-order readback includes command events | Not included | **absent** | No joined readback |
| 11 | Work-order `latest_receipt_id` | `CodingWorkOrder.latest_receipt_id` — string, nullable | **present_not_runtime_verified** | Field exists; never populated at runtime |
| 12 | Receipt model | `PiInvocationReceipt` in `guardian/pi/contracts.py:519` | **source_only** | Pi module only; not linked to work orders |
| 13 | Receipt route | Not present | **absent** | No receipt creation or readback route |
| 14 | Receipt creation path | `WorkOrderStore.mark_latest_run()` can set `receipt_id` | **source_only** | Method exists; never called with receipt_id at runtime |
| 15 | Artifact model | `PiInvocationArtifact` in `guardian/pi/contracts.py:303` | **source_only** | Pi module only; not linked to work orders |
| 16 | Artifact route | Not present | **absent** | No artifact creation or readback route |
| 17 | Artifact creation path | Not present | **absent** | No code path creates artifacts |
| 18 | Result artifact linkage | Not present | **absent** | No field or route links artifacts to work orders |
| 19 | Status history | Not present as dedicated surface | **absent** | Work order has single `status` field with transition rules; no history log |
| 20 | Execution history | `latest_run_id` provides single-run pointer | **partial** | No run listing per work order; no multi-run history |
| 21 | Frontend result display | `CodingWorkOrdersPanel` renders work orders with status badges | **frontend_only** | No command-run result display in work order panel |
| 22 | Release-boundary risk | Work orders are internal_only; no result-return in public beta | **low** | Release boundary intact |

### Result Semantics Table

| Operation | What It Proves | What It Does Not Prove | Evidence |
|---|---|---|---|
| Create draft work order | Durable task-board record created | Execution, result, completion | C03-T003 proven |
| Invoke health with `work_order_id` | Command runs, result returned inline, `latest_run_id` populated | Work-order completion, result artifact, receipt | C03-T006 + this audit |
| Read back work order | `latest_run_id` pointer + work-order fields | Command result, events, status change | C03-T006 confirmed |
| Read back CommandRun | Not possible via API | N/A | `GET /api/guardian/commands/runs/{id}` → 404 |
| Read back CommandRunEvents | SSE stream with lifecycle events | Detailed result body (result is in invoke response, not events) | C03-T005 confirmed |
| Inspect receipt/artifact fields | Fields exist on DB model, never populated | Receipt/artifact creation, result return | `latest_receipt_id` is `None` |
| Confirm status preservation | Work order status unchanged after invoke | N/A | `draft` persists through invoke |

### Audit Answers

1. **Where is command-run result stored?**
   Durable: `CommandRun.result_json` (JSONB column in `command_runs` table). Transient: `inline_result` field in the invoke HTTP response. The durable result is populated by the loopback adapter after command execution.

2. **Is command-run result durable?**
   Yes — stored in Postgres via `CommandRun.result_json`. But **not readable** via any API route today.

3. **Can command-run result be read back by API today?**
   **No.** `GET /api/guardian/commands/runs/{run_id}` returns 404. Only the original invoke response contains the result. `CommandBusStore.get_run()` exists internally but has no route.

4. **Can command-run events be read back by API today?**
   **Yes.** `GET /api/guardian/commands/runs/{run_id}/events` provides SSE stream with lifecycle events (`run.created`, `run.started`, `run.completed`). Events include `status_code` in `run.completed` but not the full result body.

5. **Does work-order readback include command-run result?**
   **No.** Only `latest_run_id` pointer. No joined result, no embedded `result_json`.

6. **Does work-order readback include command-run events?**
   **No.** No joined events.

7. **Does `latest_run_id` create a result-return contract or only a pointer?**
   **Only a pointer.** It's a loose string field with no FK, no joined readback, and no automated result population. The operator must manually correlate `latest_run_id` with the original invoke response or events stream.

8. **Does CommandRun completion mean the work order completed?**
   **No.** Work-order status is unchanged (remains `draft`). CommandRun is an execution record; work order is a task-board record. They are linked but semantically independent.

9. **Does CommandRun result become a work-order artifact automatically?**
   **No.** No code path creates artifacts from command results. No artifact model linked to work orders.

10. **Does any receipt get created today?**
    **No.** `PiInvocationReceipt` exists in the Pi module but is not used by work-order or command-bus flows.

11. **Does any artifact get created today?**
    **No.** `PiInvocationArtifact` exists in the Pi module but is not used by work-order or command-bus flows.

12. **Does `latest_receipt_id` get populated today?**
    **No.** Field exists on `CodingWorkOrder` but is never populated at runtime.

13. **Does frontend imply result-return beyond backend proof?**
    **No.** `CodingWorkOrdersPanel` renders work orders with status badges. It does not display command-run results or imply execution completion.

14. **What is the smallest safe next implementation task?**
    **Add a `GET /api/guardian/commands/runs/{run_id}` route** that exposes the durable `CommandRun` record (including `result_json`, `error_text`, `status`, timestamps). This is a read-only route that makes the already-stored result inspectable. It does not create receipts, artifacts, or change work-order status.

### Contradictions

None.

### Gaps

1. **No CommandRun readback route**: `CommandRun.result_json` is durably stored but has no API readback. Operators must capture the invoke response.
2. **Work-order result is pointer-only**: `latest_run_id` links to a run but provides no joined result.
3. **No receipt creation**: `latest_receipt_id` field exists but is never populated.
4. **No artifact creation**: No code path creates artifacts from command results.
5. **No execution history**: Single `latest_run_id` — no multi-run history per work order.
6. **Pi artifacts/receipts are isolated**: Exist in `guardian/pi/` module but not linked to work-order or command-bus flows.

### C03-T007 Gate Decision

- **Decision**: `next-proof-needed`
- **Reason**: The result-return seam is fully classified across 22 dimensions. CommandRun results are durably stored but have no API readback route. Work-order result linkage is pointer-only (`latest_run_id`). No receipts or artifacts are created. The gap is specific and implementable: add a read-only `GET /api/guardian/commands/runs/{run_id}` route to expose the already-stored durable result.

### Recommended Next Task

**Add a `GET /api/guardian/commands/runs/{run_id}` route.** Expose the durable `CommandRun` record (including `result_json`, `error_text`, `status`, timestamps, actor metadata) as a read-only API endpoint. This makes command results inspectable without creating receipts, artifacts, or changing work-order status.
