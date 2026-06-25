# Continuity Test Profile Live Proof

**Artifact window:** 2026-06-25T21:15:00Z to 2026-06-25T21:30:00Z  
**Branch:** `main`  
**HEAD commit:** `e3d7ac61c`  
**Test-only profile:** `test-continuity`  
**Supported beta profile:** `v1-local-core-web-mcp`  
**Route path:** `POST /api/operator/continuity/reality-stamp`  
**Feature flag:** `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES`  
**Proof classification:** PASS  

## 1. Scope

**Tested:**

- All focused tests — 177 passed with live Postgres (0 skips)
- Supported beta profile quarantine: live backend with `v1-local-core-web-mcp` → 404
- Test-only profile exposure: live backend with `test-continuity` + flag=true → 200
- Auth behavior: missing key → 404, invalid key → 403, valid key → 200
- Feature flag requirement: flag=false → 404 even under test profile
- Explicit stamp write: correct receipt, correct row count, correct fields
- Postgres persistence: exactly 1 context packet row, JSON round-trip verified
- Receipt shape: `graph_used=false`, `runtime_event_published=false`, all entity arrays correct

**Not tested:**

- Runtime write paths beyond the single route (none exist)
- UI, worker, command bus, chat hook, browser, graph, sync, export/restore (all deferred)

## 2. Environment

| Item | Value |
|---|---|
| Docker Compose | Backend + db + redis + neo4j |
| Postgres | Running, reachable |
| Redis | Running |
| Neo4j | Running (not used) |
| Graph writes | Not used |
| Supported beta profile | `v1-local-core-web-mcp` |
| Test profile | `test-continuity` |

## 3. Exact Commands (secrets redacted)

```sh
# Focused tests
GUARDIAN_DATABASE_URL="postgresql://codexify:***@localhost:5433/Codexify" \
  pytest -v tests/continuity/

# Beta profile quarantine
CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp \
  docker compose up -d backend
curl -X POST http://localhost:8888/api/operator/continuity/reality-stamp \
  -H "X-API-Key: ***" -d '{...}'
# → 404 Not Found

# Test profile exposure
CODEXIFY_SUPPORTED_PROFILE=test-continuity \
  CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true \
  docker compose up -d backend
curl -X POST http://localhost:8888/api/operator/continuity/reality-stamp \
  -H "X-API-Key: ***" -H "Content-Type: application/json" \
  -d '{"action_id":"...","actor_id":"proof-actor","packet_id":"test-profile-pkt-001",...}'
# → 200, full receipt
```

## 4. Focused Test Results

**Full suite with live Postgres: 177 passed, 0 skipped**

| Suite | Tests |
|---|---|
| Profile activation | 11 |
| Operator route | 7 |
| Write actions | 23 |
| Persistence adapter | 31 |
| Storage schema | 18 |
| Contracts | 45 |
| Compiler | 42 |
| **Total** | **177** |

## 5. Supported Beta Quarantine Proof

| Signal | Result |
|---|---|
| Profile | `v1-local-core-web-mcp` |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` |
| HTTP status | 404 Not Found |
| Response body | `{"detail":"Not Found"}` |
| `continuity_context_packets` rows | 0 (from stamp-only writes during this proof) |
| `continuity_reality_states` rows | 0 (from stamp-only writes) |
| `continuity_reality_commits` rows | 0 |
| `continuity_state_packet_links` rows | 0 |

**Backend log confirmation:**
```
[routers] quarantined continuity_operator (supported_profile=v1-local-core-web-mcp)
```

## 6. Test-Only Profile Exposure Proof

| Signal | Result |
|---|---|
| Profile | `test-continuity` |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` |
| Unauthenticated request | 404 Not Found |
| Invalid API key | 403 Invalid API key |
| Valid API key + valid payload | **200 OK** |

**Backend log confirmation:**
```
[routers] enabled continuity_operator as enabled via supported profile test-continuity
```

## 7. Feature Flag Behavior Proof

| Signal | Result |
|---|---|
| Profile `test-continuity`, flag `true` | 200 (route exposed) |
| Profile `test-continuity`, flag absent | **404** (route disabled via flag gate) |

**Backend log confirmation (flag absent):**
```
[routers] quarantined continuity_operator (CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=false)
```

The feature flag remains a required gate even under the test-only profile.

## 8. Explicit Stamp Write Proof

**Request:**
```json
{
    "action_id": "test-profile-stamp-1",
    "actor_id": "proof-actor",
    "packet_id": "test-profile-pkt-001",
    "created_at": "2026-06-25T00:00:00Z",
    "summary": "Test profile live stamp",
    "payload": {"test": true},
    "project_id": "test-proj",
    "sensitivity": "local",
    "retention": "session"
}
```

**Response:**
```json
{
    "action_id": "test-profile-stamp-1",
    "action_kind": "create_reality_stamp",
    "success": true,
    "created_packet_ids": ["test-profile-pkt-001"],
    "created_state_ids": [],
    "created_commit_ids": [],
    "created_link_ids": [],
    "validation_errors": [],
    "persistence_errors": [],
    "warnings": [],
    "provenance_refs": ["test-profile-pkt-001"],
    "graph_used": false,
    "runtime_event_published": false,
    "created_at": "2026-06-25T21:22:22.792492+00:00"
}
```

## 9. Postgres Persistence Verification

**Row count after stamp write:**

| Table | Rows (post-stamp) |
|---|---|
| `continuity_context_packets` | 1 |
| `continuity_reality_states` | 0 (from stamp-only) |
| `continuity_reality_commits` | 0 |
| `continuity_state_packet_links` | 0 (from stamp-only) |

**Packet row details:**

| Column | Value |
|---|---|
| `id` | `test-profile-pkt-001` |
| `kind` | `thread` |
| `sensitivity` | `local` |
| `retention` | `session` |
| `source_system` | `developer_operator_route` |
| `summary` | `Test profile live stamp` |
| `payload_json->>'test'` | `true` |

Payload JSON, metadata JSON, and provenance JSON all round-trip correctly.

## 10. Forbidden Invocation Path Verification

| Verification | Result |
|---|---|
| Supported beta profile quarantine | Confirmed — 404 |
| No chat route writes | Confirmed |
| No worker writes | Confirmed |
| No compiler auto-persistence | Confirmed |
| No runtime event publication | Confirmed — `runtime_event_published=false` |
| No graph usage | Confirmed — `graph_used=false` |
| No browser capture | Confirmed |
| No provider/retrieval trigger | Confirmed |
| Call-site audit | Only `write_actions.py`, `continuity_operator.py`, `__init__.py`, tests |

## 11. Runtime Non-Goals

This proof does not and must not be interpreted as:

- Activating the route in `v1-local-core-web-mcp` (remains quarantined)
- Authorizing UI, worker, command bus, chat hooks, browser, graph, sync, or export/restore
- Widening the supported beta release promise

## 12. ADR Impact

- **Classification:** Aligned with profile activation contract
- The route is proven functional under `test-continuity` profile with `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`. The supported beta profile remains quarantined. The release promise is not widened.

## 13. Outcome

**PASS** — outcome: `go`

Supported beta quarantine, test-only profile exposure, feature flag gating, auth behavior, explicit stamp write, receipt shape, persistence, and forbidden invocation paths are all confirmed.

## 14. Follow-Up

**Next task:** Developer/operator readback route or diagnostics contract for inspecting persisted stamps. The write path is proven; a symmetrical read path for the same operator surface would complete the operator loop.
