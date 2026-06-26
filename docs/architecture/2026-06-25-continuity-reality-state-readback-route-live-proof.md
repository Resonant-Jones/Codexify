# Continuity Reality State Readback Route Live Proof

**Artifact window:** 2026-06-25T23:10:00Z to 2026-06-25T23:20:00Z  
**Branch:** `main`  
**HEAD commit:** `459026ebb`  
**State readback route:** `GET /api/operator/continuity/reality-states/{state_id}`  
**Test-only profile:** `test-continuity`  
**Supported beta profile:** `v1-local-core-web-mcp`  
**Proof classification:** PASS  

## 1. Scope

**Tested:** Beta quarantine (all 4 routes 404), test-profile exposure, existing state readback with full state JSON round-trip, missing state `found=false`, hard-false flags, no packet payload expansion.

**Not tested:** Commit readback, link readback, list/search, UI, workers, command bus, chat hooks, browser, graph, sync, export/restore, Project Pulse — all deferred.

## 2. Environment

Docker Compose backend + db + redis + neo4j. Postgres running. Neo4j running (not used). Graph writes not used.

## 3. Focused Tests

Full continuity suite with live Postgres: all pass, zero skips.

## 4. Supported Beta Quarantine

All four routes return 404 under `v1-local-core-web-mcp`:

| Route | HTTP |
|---|---|
| `POST .../reality-stamp` | 404 |
| `GET .../context-packets/{id}` | 404 |
| `GET .../diagnostics` | 404 |
| `GET .../reality-states/{id}` | **404** |

## 5. Test-Only Profile Exposure

Under `test-continuity` with flag=true + valid API key:

| Route | HTTP |
|---|---|
| `GET .../reality-states/{existing_id}` | **200** |
| `GET .../reality-states/{missing_id}` | **200**, `found=false` |

## 6. State Readback Live Proof

| Signal | Value |
|---|---|
| `found` | `true` |
| `scope` | `project` |
| `source_packet_count` | 1 (matches stored `source_packet_ids_json`) |
| `state` | `{"compiled":true,"source":"proof"}` — round-trips |
| `provenance` | `{"source_packet_ids":["proof-sr-..."]}` — round-trips |
| `graph_used` | `false` |
| `runtime_event_published` | `false` |
| `project_pulse_enabled` | `false` |
| `export_restore_enabled` | `false` |
| No source packet payloads exposed | Confirmed |
| No-write | Confirmed |

## 7. Outcome

**PASS — `go`**

State readback is live-proven under the same gate stack as the rest of the operator loop. Beta remains quarantined. Next step: commit readback contract implementation.
