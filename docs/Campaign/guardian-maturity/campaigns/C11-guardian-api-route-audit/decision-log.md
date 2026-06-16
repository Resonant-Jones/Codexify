# C11 Decision Log

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C11-D001 | 2026-06-16 | `go` — route topology sufficient for C01/C02/C03 planning | active |

---

### Decision: C11-D001

- **Decision ID**: C11-D001
- **Date**: 2026-06-16
- **Decision**: Gate decision is `go`. The route audit establishes sufficient backend API route topology for C01 (Command Center), C02 (Chat Runtime State), and C03 (Coding Delegation Spine) to proceed with planning and proof collection.
- **Reason**:
  - Health/catalog surfaces are fully present, registered, OpenAPI-visible, and verified in C00.
  - Chat runtime routes (task event SSE, threads, messages, complete) are present and OpenAPI-visible.
  - Coding work-order routes exist in backend code with full CRUD (POST/GET/cancel) plus orchestrator and campaign runner routers. Frontend consumers (`useCodingWorkOrders`, `useOrchestratorRecommendations`) already target these routes.
  - Delegation routes exist for draft creation and approval. Guardian delegations exist with CRUD.
  - Command bus routes exist (manifest, search, invoke, run events) but are internal_only in the supported profile.
  - All feature-gated routes use a consistent `_include_router()` mechanism with env var flags, profile posture, and `CODEXIFY_BETA_CORE_ONLY` gating.
  - Tool-turn observability data is embedded in chat message `extra_meta` per the Agent Tool Loop Contract.
  - Two critical blockers are documented and assigned: BLOCKER-001 (Pi/Coder validation route missing) → C04, BLOCKER-002 (feature-gated route availability unconfirmed) → C03/C05/C09.
  - No route topology contradictions found. No shadow control-plane behavior detected.
  - Supported profile route posture is correctly enforced. Internal-only routes are hidden from OpenAPI.
- **Evidence**:
  - `guardian/guardian_api.py` — 39 router includes confirmed via grep
  - `guardian/routes/` — all 39 route files inspected for router definitions
  - `guardian/pi/validation.py` — 28KB of validation logic, zero route registration
  - `config/supported_profiles/v1-local-core-web-mcp.yaml` — route posture: 15 enabled, 1 internal_only (command_bus), 2 quarantined
  - OpenAPI schema — 80+ paths visible; feature-gated routes absent as expected
  - `frontend/src/features/commandCenter/hooks/` — 10 hooks, 3 with backend route consumers verified
  - `frontend/src/lib/api.ts` — health, chat, personal_facts routes confirmed
  - `frontend/src/hooks/useLiveEvents.ts` — SSE consumer confirmed
  - `frontend/src/features/chat/hooks/useInferenceRequestState.ts` — task event SSE consumer confirmed
- **Consequence**:
  - C01 and C02 can proceed — they depend on health/catalog and chat runtime routes, all verified.
  - C03 can proceed with planning but must verify coding work-order and delegation route runtime availability at its proof gate.
  - C04 cannot proceed until BLOCKER-001 is resolved (Pi/Coder validation route created). The backend logic exists; route registration is the missing piece.
  - C05 can proceed with planning but must verify command bus route availability and assess tool-turn data surface.
  - C09 can proceed with planning but must assess whether to create a dedicated ledger route or use existing work-order infrastructure.
  - BLOCKER-002 is assigned to C03, C05, and C09 proof gates — they must verify route availability before enabling UI affordances.
- **Revisit Trigger**:
  - C03 proof collection begins and coding work-order routes are found unavailable at runtime.
  - C04 begins implementation and the Pi/Coder validation route registration reveals additional gaps.
  - Supported profile route posture changes (e.g., coding_work_orders moved to enabled).
  - New feature flags are added that affect route availability.
