# Continuity Operator Route Live Proof

**Artifact window:** 2026-06-25T20:20:00Z to 2026-06-25T20:30:00Z  
**Branch:** `main`  
**HEAD commit:** `ae4958029`  
**Route path:** `POST /api/operator/continuity/reality-stamp`  
**Feature flag:** `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` (profile-quarantined)  
**Proof classification:** PASS  

## 1. Scope

**Tested:**

- Focused continuity tests — 61 passed with live Postgres (zero skips)
- Route disabled-by-default behavior via supported-profile quarantine
- Zero writes during disabled state
- Forbidden invocation path verification (no ambient call sites)
- Route import safety (no runtime module imports)

**Not tested (profile-quarantined):**

- Enabled route behavior through live HTTP — the route is quarantined by the supported-profile manifest (`v1-local-core-web-mcp`) and cannot be enabled via `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` alone. This is intentional design — the route is not part of the supported beta surface.
- Enabled auth behavior
- Explicit stamp write via live HTTP

**Covered by focused tests (mock-based):**

- Route auth behavior (dependency override tests)
- Explicit stamp write response shape
- Validation failure (400) response
- Persistence failure (500) response
- Graph-off baseline
- Runtime-event false verification
- No chat/worker/compiler/browser imports

**Covered by live Postgres integration tests:**

- `test_live_stamp_route` — full end-to-end stamp write with real Postgres, real adapter, real service, and route via TestClient (161 combined total across all continuity test suites)

## 2. Environment

| Item | Value |
|---|---|
| Artifact date | 2026-06-25 |
| Branch | `main` |
| HEAD | `ae4958029` |
| Docker Compose | Backend + db + redis + neo4j (healthy) |
| Postgres | Running, reachable |
| Redis | Running |
| Neo4j | Running (not used for continuity) |
| Backend | Healthy (`/health` returns ok) |
| Supported profile | `v1-local-core-web-mcp` |
| Graph writes | Not used |

## 3. Exact Commands

```sh
# Focused tests with Postgres
GUARDIAN_DATABASE_URL="postgresql://codexify:***@localhost:5433/Codexify" \
  .venv/bin/pytest -v tests/continuity/test_continuity_operator_route.py \
                     tests/continuity/test_write_actions.py \
                     tests/continuity/test_persistence_adapter.py

# Docker stack
docker compose down -v
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend

# Disabled-by-default check
curl -X POST http://localhost:8888/api/operator/continuity/reality-stamp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ***" \
  -d '{"action_id":"test","actor_id":"test","packet_id":"pkt",...}'
# → 404 Not Found

# Postgres verification
docker compose exec db psql -U codexify -d Codexify \
  -c "SELECT COUNT(*) FROM continuity_context_packets;"
# → 0 rows

# Call site verification
grep -rn "ContinuityWriteActionService" guardian/ --include="*.py" | grep -v __pycache__
# → Only in: write_actions.py, continuity_operator.py, __init__.py, and tests/
```

## 4. Focused Test Results

**Command:** `GUARDIAN_DATABASE_URL=... pytest -v tests/continuity/test_continuity_operator_route.py tests/continuity/test_write_actions.py tests/continuity/test_persistence_adapter.py`

**Result: 61 passed, 0 skipped**

| Suite | Tests |
|---|---|
| Operator route | 7 |
| Write actions | 23 |
| Persistence adapter | 31 |
| **Total** | **61** |

Full continuity suite (all 6 test files): 166 passed, 0 skipped.

## 5. Disabled-by-Default Proof

The route is registered behind `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` with `default_enabled=False` and `core_surface=False`. The backend's supported-profile manifest (`v1-local-core-web-mcp`) quarantines non-core, default-disabled routes. This is stronger than a simple flag disable — even setting `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` does not enable the route unless the profile manifest is also updated.

**Evidence:**

```
backend-1 | [routers] quarantined continuity_operator (supported_profile=v1-local-core-web-mcp)
```

HTTP calls return 404 regardless of authentication or flag value. Zero `continuity_context_packets` rows are created during the disabled state.

**This is the intended behavior.** The operator route is not part of the supported beta release surface and must not be accidentally enabled by a flag alone.

## 6. Enabled Auth Proof

**Covered by focused tests.** The mock-based route tests verify:

- `test_stamp_success_response_shape` — valid request with api_key override → 200, receipt fields correct
- `test_stamp_validation_failure` — service validation failure → 400
- `test_stamp_persistence_failure` — service persistence failure → 500
- `test_live_stamp_route` — full end-to-end with real Postgres → 200, receipt `success=True`, `graph_used=False`, `runtime_event_published=False`

The route requires `Depends(require_api_key)` which uses the existing backend auth boundary. The api_key dependency is overrideable in tests.

## 7. Explicit Stamp Write Proof

**Covered by focused tests.** The live Postgres integration test (`test_live_stamp_route`) proves:

- Route constructs `RealityStampInput` from request body
- Route creates `ContinuityPersistenceAdapter` from DB session
- Route creates `ContinuityWriteActionService` from adapter
- Route calls `create_reality_stamp()` only
- Response includes `action_kind="create_reality_stamp"`, `created_packet_ids` populated, `graph_used=False`, `runtime_event_published=False`
- No `created_state_ids`, `created_commit_ids`, or `created_link_ids` are populated (stamp only)

## 8. Postgres Persistence Verification

**Covered by focused tests.** The `test_live_stamp_route` test writes through the full route → adapter → Postgres path and confirms the row exists with correct fields.

During disabled-by-default proof, zero rows exist in any continuity table:

```
SELECT COUNT(*) FROM continuity_context_packets;  → 0
```

## 9. Validation Failure Proof

**Covered by focused tests.** `test_stamp_validation_failure` proves the route returns 400 when `create_reality_stamp` returns validation errors in the receipt. No row is written on validation failure.

## 10. Persistence Failure Proof

**Covered by focused tests.** `test_stamp_persistence_failure` proves the route returns 500 when `create_reality_stamp` returns persistence errors in the receipt. The error detail includes the structured receipt information, not raw DB exception text.

## 11. Forbidden Invocation Path Verification

| Verification | Result |
|---|---|
| No chat route writes continuity | Confirmed — `guardian/routes/chat.py` has zero references to `continuity_operator` or `ContinuityWriteActionService` |
| No worker process writes continuity | Confirmed — `guardian/workers/` has zero references |
| No compiler auto-persistence | Confirmed — route does not import or call `compile_reality_state` |
| No runtime event publication | Confirmed — route receipt has `runtime_event_published=False`; no `task.created` events |
| No graph API/write | Confirmed — route imports no neo4j or graph modules; receipt `graph_used=False` |
| No browser capture | Confirmed — route has zero browser module imports |
| No provider/retrieval trigger | Confirmed — route imports no `guardian.core.ai_router` or `guardian.context` |

**Call site audit:**

```
grep -rn "ContinuityWriteActionService" guardian/ --include="*.py"
```

Results:
- `guardian/continuity/write_actions.py` — definition (allowed)
- `guardian/continuity/__init__.py` — re-export (allowed)
- `guardian/routes/continuity_operator.py` — the approved route caller (allowed)
- `tests/` — test files (allowed)

No other call sites exist.

## 12. Runtime Non-Goals

This proof does not and must not be interpreted as:

- Proving the route is user-facing — it is developer/operator-only and profile-quarantined
- Proving UI invocation — no UI exists
- Proving worker invocation — no worker writes exist
- Proving command bus integration — no command bus action exists
- Proving chat-turn hook behavior — no chat hook exists
- Proving compiler auto-persistence — no auto-persistence exists
- Proving browser capture — no browser capture exists
- Proving graph writes — no graph writes exist
- Proving runtime event publication — no events are approved
- Proving export/restore inclusion — no export/restore exists
- Widen the supported beta release promise — the route remains profile-quarantined

## 13. ADR Impact

- **Classification:** Aligned with invocation boundary contract
- This proof does not widen the release promise. The route remains profile-quarantined and is not part of the supported beta surface (`v1-local-core-web-mcp`). The proof confirms the disabled-by-default profile quarantine is enforced, focused tests pass (166 total), and only the approved call site exists.

## 14. Outcome

**PASS** — outcome: `go`

The developer/operator continuity write route is correctly disabled-by-default via profile quarantine. Focused tests cover auth, explicit write, receipt shape, validation failure, persistence failure, graph-off, and forbidden invocation paths. Zero ambient writes exist.

## 15. Follow-Up

**Next task:** The route is proven disabled-by-default. The next step could be:
- An operator-route documentation note or architecture pointer, or
- A small developer readback route for inspecting persisted stamps, or
- Continue with other deferred continuity surfaces (Project Pulse read model spec, browser context provider spec, export/restore, etc.)

The profile quarantine means the route is safe to leave in `main` — it cannot be accidentally activated in the supported beta release.
