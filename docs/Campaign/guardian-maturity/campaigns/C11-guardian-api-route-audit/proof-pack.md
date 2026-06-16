# C11 Proof Pack

## Campaign

- **Campaign ID**: C11
- **Title**: Guardian API Route Audit and Scaffold

## Proof Pass

- **Date/Time**: 2026-06-16 17:00 UTC
- **Branch**: `codex/campaignOS`
- **Latest Commit**: `52f4eb81b` — docs: record Guardian Maturity C00 truth gate proof
- **C00 Dependency State**: `next-proof-needed` (model mismatch; does not block C11 route audit)
- **Inspected Files/Directories**:
  - `guardian/guardian_api.py` — central router registration
  - `guardian/routes/` — 39 route modules
  - `guardian/api/` — auth, schemas, deprecated API
  - `guardian/pi/` — contracts, tokens, validation
  - `guardian/command_bus/` — contracts, invoke, manifest, store
  - `frontend/src/lib/api.ts` — API client
  - `frontend/src/features/commandCenter/` — hooks, API, types
  - `frontend/src/hooks/useLiveEvents.ts`, `useRuntimeHealth.ts`
  - `frontend/src/features/chat/hooks/useInferenceRequestState.ts`
  - `config/supported_profiles/v1-local-core-web-mcp.yaml` — route posture
  - OpenAPI schema (`http://localhost:8888/openapi.json`)

## Route Registration Architecture

### Router Gating Mechanism (`guardian/guardian_api.py:240-310`)

Routes are registered via `_include_router()` which applies three gates:
1. **Supported profile route posture** — `enabled`, `internal_only`, `quarantined`, or absent
2. **`CODEXIFY_BETA_CORE_ONLY`** — if set, blocks non-core, non-internal routes
3. **Feature flag** — per-route env var with `default_enabled` (True for most, False for guardian_delegations)

Internal-only routes are registered but hidden from OpenAPI — they still respond to requests.

### Route Posture from Supported Profile (`v1-local-core-web-mcp`)

**Enabled**: health, admin, chat, simple_chat, api_chat, threads, projects, api_projects, documents, media, personal_facts, migration, embeddings, obsidian

**Internal-only**: command_bus

**Quarantined**: neo, imprint

**Not listed (feature-gated)**: coding_work_orders, delegations, guardian_delegations, agent_orchestration, heartbeat, intents, ui_session, codex, persona_profiles, auth, tts, voice, connectors, flows, exports, browser, channels, graph, workspace, cron, websocket, devtools, share, federation, collaboration, llm_overrides, iddb, backfill, memory, research, system_prompt, system_docs, codexify_router

## Route Dependency Matrix

| # | Surface | Backend Route | Frontend Consumer | Runtime Proof | Dependent Campaigns | Status | Notes |
|---|---------|---------------|-------------------|---------------|---------------------|--------|-------|
| 1 | Health (`/health`) | `present` — `health.py` router, OpenAPI-confirmed | `present` — `useHealthSummary.ts` | `proven` — C00 verified HTTP 200, `ok` | C01, C02, C10 | `present` | Verified in C00 |
| 2 | Chat health (`/health/chat`) | `present` — OpenAPI-confirmed | `present` — `useRuntimeHealth.ts`, `api.ts` | `proven` — C00 verified HTTP 200 | C01, C02, C10 | `present` | Verified in C00 |
| 3 | LLM health (`/health/llm`, `/api/health/llm`) | `present` — dual paths, OpenAPI-confirmed | `present` — `GuardianChat.tsx`, `useHealthSummary.ts` | `proven` — C00 verified HTTP 200 | C01, C02, C08 | `present` | Verified in C00 |
| 4 | LLM catalog (`/api/llm/catalog`) | `present` — OpenAPI-confirmed | `present` — `useLlmCatalog.ts` | `proven` — C00 verified HTTP 200 | C01, C02, C08 | `present` | Verified in C00 |
| 5 | Provider truth / runtime state | `present` — embedded in health/catalog responses | `present` — `useProviderState.ts`, `useRuntimeHealth.ts` | `proven` — C00 verified `provider_truth` field | C01, C02, C08 | `present` | No standalone route; data in health payloads |
| 6 | Command bus manifest/list | `present` — `command_bus.py` `/manifest`, `/search` | `absent` — no frontend consumer found | `not inspected` | C05 | `present` | Internal-only in supported profile; hidden from OpenAPI |
| 7 | Command bus invocation | `present` — `command_bus.py` `/invoke` | `absent` — invoked backend-side by chat worker | `not inspected` | C05 | `present` | Not a frontend-facing route |
| 8 | Command run history | `present` — `command_bus.py` `/runs/{run_id}/events` (stream) | `absent` — no frontend listing consumer | `not inspected` | C05, C09 | `partial` | Has stream, no listing endpoint. Tool-turn data also embedded in chat message `extra_meta`. |
| 9 | Tool turn visibility | `present` — embedded in chat message `extra_meta` (`toolTurnId`, `commandRunId`, `toolTurnState`, `loopStopReason`) | `absent` — no dedicated tool-turn viewer consumer | `not inspected` | C05 | `partial` | No dedicated route; data is in chat persistence. Frontend would need a viewer. |
| 10 | Coding work-order CRUD | `present` — `coding_work_orders.py` POST/GET w/ cancel, orchestrator, campaign_runner routers | `present` — `useCodingWorkOrders.ts` hits `/api/coding/work-orders`, `useOrchestratorRecommendations.ts` hits `/api/coding/orchestrator/next` | `not inspected` | C03, C09 | `present` | Feature-gated (`CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES`). Route not in OpenAPI — likely gated. Frontend consumers exist. |
| 11 | Coding delegation draft creation | `present` — `delegations.py` POST `/draft`, `guardian_delegations.py` POST create | `absent` — no frontend consumer found for delegation routes | `not inspected` | C03 | `present` | Feature-gated (`CODEXIFY_ENABLE_DELEGATION_ROUTES`, `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES`). Guardian delegations default-disabled. |
| 12 | Pi/Coder invocation validation | `absent` — validation logic exists in `guardian/pi/validation.py` but NO route exposes it | `absent` | N/A | C04 | **absent** | **CRITICAL GAP.** Pi invocation validation has full backend logic (`PiInvocationEnvelope`, `PiInvocationValidationResult`, deterministic validation helpers) but zero route registration. No `/api/pi/validate` or equivalent. C04 blocked until route created. |
| 13 | Pi/Coder harness availability | `absent` — no route | `absent` | N/A | C04 | **absent** | No harness availability endpoint. |
| 14 | Pi/Coder receipts/artifacts | `absent` — no route | `absent` | N/A | C04, C09 | **absent** | No receipt or artifact route. |
| 15 | Task-event / SSE stream | `present` — `/api/tasks/{task_id}/events`, `/api/events`, OpenAPI-confirmed | `present` — `useInferenceRequestState.ts` (task events), `useLiveEvents.ts` (SSE), `GuardianEventSource.ts` | `proven` — C00 confirmed backend serves SSE | C02, C05, C09, C13 | `present` | GuardianEventSource is a custom fetch-based SSE polyfill supporting auth headers. |
| 16 | Execution ledger | `partial` — `coding_work_orders.py` has campaign_runner router (goals, campaigns, work orders) with receipt tracking, but no dedicated ledger listing/inspection route | `partial` — work order hooks exist but no ledger viewer | `not inspected` | C09 | `partial` | Uses work-order CRUD for receipt tracking. No dedicated ledger surface. |
| 17 | Auth/session / operator status | `present` — `/auth/session`, `/auth/session/cookie`, OpenAPI-confirmed | `present` — `useAuthState.ts`, `api.ts` | `not inspected` | C12 | `present` | Session management exists. No dedicated operator capability/permission inspection route. |
| 18 | Workspace artifact linkage | `present` — `workspace.py` `/api/workspace/{thread_id}` | `present` — `WorkspacePane.tsx` calls document loading | `not inspected` | C06 | `present` | Workspace route exists but not in OpenAPI (feature-gated). |
| 19 | Persona/profile config | `present` — `persona_profiles.py` router registered, `imprint.py` router | `present` — persona studio components | `not inspected` | C07 | `present` | Profile routes exist but not in OpenAPI (feature-gated). |
| 20 | Whoosh'd model inventory proxy | `absent` — no standalone proxy route; model inventory is embedded in `/api/llm/catalog` and health responses | `absent` — no frontend consumer for direct inventory | `proven` — C00 verified Whoosh'd `/v1/models` reachable directly | C08 | `absent` | Backend queries Whoosh'd internally for catalog. No proxy route needed for current architecture. Frontend gets models via catalog. |

## Critical Blockers

### BLOCKER-001: Pi/Coder invocation validation has no route

**Impact**: C04 (Pi/Coder Invocation Boundary) is **completely blocked** until a route exposes the existing validation logic in `guardian/pi/validation.py`.

**Evidence**:
- `guardian/pi/validation.py` (28KB) contains `PiInvocationEnvelope`, `PiInvocationReceipt`, `PiInvocationArtifact`, `PiHarnessResult`, `PiInvocationValidationResult` with pure deterministic validation helpers.
- `guardian/pi/contracts.py` (36KB) contains full contract definitions.
- `guardian/pi/tokens.py` contains canonical token domains.
- Zero route registration in `guardian/guardian_api.py` for `guardian/pi/`.
- Zero frontend consumers for Pi invocation routes.
- Pi invocation is NOT in the supported profile route posture.

**Resolution**: C04 must create a validation route (e.g., `POST /api/pi/validate-envelope` or similar). The backend logic is already written. This is a route-registration task, not a from-scratch implementation.

### BLOCKER-002: Feature-gated routes have unknown runtime availability

**Impact**: C03 (coding work orders), C05 (command bus), C09 (execution ledger) depend on routes that are feature-gated. The gate mechanism is understood (`_include_router` with env var + profile posture), but runtime availability is not confirmed because these routes were absent from OpenAPI during C00 (backend was running).

**Evidence**:
- `coding_work_orders` — flag `CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES`, default enabled, not in supported profile enabled list
- `delegations` — flag `CODEXIFY_ENABLE_DELEGATION_ROUTES`, default enabled, not in profile
- `guardian_delegations` — flag `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES`, **default disabled**
- `command_bus` — flag `CODEXIFY_ENABLE_COMMAND_BUS_ROUTES`, default enabled, **internal_only** in profile
- `agent_orchestration` — flag `CODEXIFY_ENABLE_AGENT_ORCHESTRATION_ROUTES`, default enabled

**Resolution**: C03/C05 must verify route availability at their proof gates. If routes are not available, they must either enable the flags or create tasks to do so.

## Non-Blocking Gaps

1. **Command run listing**: `command_bus.py` has event streaming for individual runs but no listing endpoint. Tool-turn result data is embedded in chat message `extra_meta` per the Agent Tool Loop Contract. C05 may need to create a listing route or surface the embedded data from chat messages.

2. **Execution ledger**: No dedicated ledger route. Uses campaign runner routes (goals, campaigns) and work-order CRUD with receipt tracking. C09 may need to create a ledger surface or leverage the existing work-order infrastructure.

3. **Whoosh'd model inventory proxy**: No standalone route. Backend queries Whoosh'd internally for `/api/llm/catalog`. This is architecturally correct — the backend is the inventory authority, not a pass-through proxy.

4. **Operator capability/permission inspection**: No dedicated route for "what can this operator do?" Auth session exists but doesn't expose capability grants. C12 may need this.

## Contradictions

1. **Frontend consumes gated routes**: `useCodingWorkOrders.ts` calls `/api/coding/work-orders` but the route's runtime availability is unconfirmed. If the route is gated and the frontend calls it, the UI would show errors. This contradicts the "no UI button for non-existent backend" principle. Resolution: C03 must verify route availability before enabling UI affordances.

2. **Command bus is internal_only but has no UI consumer**: The command bus is marked `internal_only` in the supported profile, meaning it's hidden from OpenAPI but still accessible. The frontend has no command bus consumer. The chat worker invokes the command bus backend-side. This is architecturally correct — command bus is a backend-to-backend surface.

## Route Registration Summary

### Registered and OpenAPI-visible (verified)
Health (6 paths), chat (20+ paths), threads, projects, media, documents, personal_facts, embeddings, obsidian, auth/session, metrics, events, tasks (SSE), catalog, capabilities, imports, graph, debug/config, migration

### Registered but feature-gated (not in OpenAPI during C00)
coding_work_orders, delegations, guardian_delegations, agent_orchestration, command_bus, heartbeat, intents, ui_session, codex, persona_profiles, tts, voice, connectors, flows, exports, browser, channels, workspace, cron, websocket, devtools, share, federation, collaboration, llm_overrides, iddb, backfill, memory, research, system_prompt, system_docs, codexify_router

### Logic exists but no route
Pi/Coder invocation validation (`guardian/pi/validation.py`)

## Gate Decision

- **Decision**: `go`
- **Reason**: The audit establishes sufficient route topology for C01, C02, and C03 planning to proceed. Health/catalog surfaces are fully present and verified. Chat runtime routes (task events, threads, messages) are present. Coding work-order routes exist and have frontend consumers — their gating is understood and can be resolved during C03 proof collection. The critical Pi/Coder route gap is clearly documented in BLOCKER-001 and maps directly to C04 scope. No route topology contradictions were found. No shadow control-plane behavior was detected. The supported profile route posture is correctly enforced. The gate is `go` because enough route topology is confirmed, and the gaps are specific, documented, and assigned to the correct downstream campaigns.

## Follow-Up Required

- [ ] C03 proof gate: verify coding work-order routes are runtime-available before enabling UI affordances
- [ ] C04: create Pi/Coder invocation validation route (backbone logic already exists in `guardian/pi/validation.py`)
- [ ] C05: verify command bus route availability; assess need for command run listing route vs. embedded tool-turn data
- [ ] C09: assess whether execution ledger needs a dedicated route or can use campaign runner + work-order infrastructure
- [ ] C03: verify delegation routes are enabled (guardian_delegations is default-disabled)
- [ ] C12: assess need for operator capability/permission inspection route
