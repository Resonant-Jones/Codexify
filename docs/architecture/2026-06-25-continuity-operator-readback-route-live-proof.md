# Continuity Operator Readback Route Live Proof

**Artifact window:** 2026-06-25T21:58:00Z to 2026-06-25T22:05:00Z  
**Branch:** `main`  
**HEAD commit:** `22c302493`  
**Write route:** `POST /api/operator/continuity/reality-stamp`  
**Readback route:** `GET /api/operator/continuity/context-packets/{packet_id}`  
**Test-only profile:** `test-continuity`  
**Supported beta profile:** `v1-local-core-web-mcp`  
**Feature flag:** `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES`  
**Proof classification:** PASS  

## 1. Scope

**Tested:**

- All focused tests — full continuity suite passes with live Postgres (zero skips)
- Supported beta quarantine: both write and readback routes → 404
- Test-only profile exposure: both routes → 200 with correct responses
- Write + readback loop: stamp → packet row → exact-ID readback with full payload round-trip
- Missing packet: `found=false` with no error leakage
- No-write guarantee: zero new rows from readback
- Receipt/response shape: `graph_used=false`, `runtime_event_published=false` on both routes

**Not tested:**
- List/search APIs (none exist)
- State/commit/link readback (none exist)
- UI, worker, command bus, chat hook, browser, graph, sync, export/restore (all deferred)

## 2. Environment

| Item | Value |
|---|---|
| Docker Compose | Backend + db + redis + neo4j |
| Postgres | Running |
| Redis | Running |
| Neo4j | Running (not used) |
| Graph reads/writes | Not used |
| Supported beta profile | `v1-local-core-web-mcp` |
| Test profile | `test-continuity` |

## 3. Supported Beta Quarantine

| Route | HTTP | Response |
|---|---|---|
| `POST /api/operator/continuity/reality-stamp` | 404 | `{"detail":"Not Found"}` |
| `GET /api/operator/continuity/context-packets/{id}` | 404 | `{"detail":"Not Found"}` |

Both routes are quarantined under `v1-local-core-web-mcp` even with `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`. The `continuity_operator` route surface key is excluded from the supported beta profile.

## 4. Test-Only Profile Exposure

Under `test-continuity` with `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`:

| Route | Auth | HTTP |
|---|---|---|
| `POST /api/operator/continuity/reality-stamp` | Missing key | 404 |
| `POST /api/operator/continuity/reality-stamp` | Invalid key | 403 |
| `POST /api/operator/continuity/reality-stamp` | Valid key | **200** |
| `GET /api/operator/continuity/context-packets/{id}` | Valid key (existing) | **200** |
| `GET /api/operator/continuity/context-packets/{id}` | Valid key (missing) | **200**, `found=false` |

## 5. Write + Readback Loop

**Write response:**
```json
{
    "action_id": "proof-rb-1",
    "action_kind": "create_reality_stamp",
    "success": true,
    "created_packet_ids": ["proof-readback-1782425030"],
    "created_state_ids": [],
    "created_commit_ids": [],
    "created_link_ids": [],
    "graph_used": false,
    "runtime_event_published": false
}
```

**Readback response (same packet):**
```json
{
    "packet_id": "proof-readback-1782425030",
    "found": true,
    "schema_version": "0.1",
    "kind": "thread",
    "scope": {"user_id": "local", "project_id": "proof-proj", ...},
    "source": {"system": "developer_operator_route", ...},
    "summary": "Readback proof stamp",
    "payload": {"rb_proof": true},
    "sensitivity": "local",
    "retention": "session",
    "deleted": false,
    "graph_used": false,
    "runtime_event_published": false
}
```

Payload JSON, metadata JSON, provenance JSON, and integrity JSON all round-trip correctly.

## 6. Missing Packet

```json
{"packet_id": "nonexistent-999", "found": false, "graph_used": false, ...}
```

HTTP 200 with `found=false`. No 500 error. No raw DB exception leakage.

## 7. No-Write Guarantee

Readback route creates zero new rows. Row counts after write + readback loop show only the single new packet from the write, plus stale rows from prior test runs. No continuity rows are created by the readback route.

## 8. Forbidden Invocation Paths

All verified — no chat, worker, compiler, graph, browser, provider, retrieval, Project Pulse, or export/restore invocation.

## 9. Focused Tests

Full continuity suite with live Postgres: all tests pass, zero skips.

## 10. Outcome

**PASS — `go`**

The operator loop is proven: write → readback → confirm. Both routes share the `continuity_operator` surface key, both are gated by profile + feature flag + auth, and neither creates ambient writes, events, or graph activity.

## 11. Follow-Up

The write + readback operator loop is complete. Next steps could include a narrow operator diagnostics truth-surface contract, or continuation of deferred continuity surfaces (Project Pulse spec, browser context provider spec, etc.).
