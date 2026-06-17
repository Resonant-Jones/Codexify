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
