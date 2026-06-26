# Continuity Operator Diagnostics Route Live Proof

**Artifact window:** 2026-06-25T22:45:00Z to 2026-06-25T22:55:00Z  
**Branch:** `main`  
**HEAD commit:** `9bdc4d1a5`  
**Write route:** `POST /api/operator/continuity/reality-stamp`  
**Readback route:** `GET /api/operator/continuity/context-packets/{packet_id}`  
**Diagnostics route:** `GET /api/operator/continuity/diagnostics`  
**Test-only profile:** `test-continuity`  
**Supported beta profile:** `v1-local-core-web-mcp`  
**Feature flag:** `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES`  
**Proof classification:** PASS  

## 1. Scope

**Tested:** Full operator triad live-proven: beta quarantine, test-profile exposure, write+readback+diagnostics loop, aggregate counts, hard-false flags, no raw payloads, no-write diagnostics, forbidden paths.

**Not tested:** UI, list/search APIs, state/commit/link readback beyond aggregate counts, raw payload exposure, workers, command bus, chat hooks, browser, graph, sync, export/restore, Project Pulse — all deferred.

## 2. Environment

| Item | Value |
|---|---|
| Docker Compose | Backend + db + redis + neo4j |
| Postgres | Running |
| Redis | Running |
| Neo4j | Running (not used) |
| Graph reads/writes | Not used |

## 3. Focused Tests

Full continuity suite with live Postgres: all pass, zero skips.

## 4. Supported Beta Quarantine

All three routes return 404 under `v1-local-core-web-mcp` even with flag=true:

| Route | HTTP |
|---|---|
| `POST .../reality-stamp` | 404 |
| `GET .../context-packets/{id}` | 404 |
| `GET .../diagnostics` | 404 |

## 5. Test-Only Profile Exposure

Under `test-continuity` with flag=true + valid API key:

| Route | HTTP | Key Signals |
|---|---|---|
| `POST .../reality-stamp` | 200 | `success=true`, `graph_used=false` |
| `GET .../context-packets/{id}` | 200 | `found=true`, payload round-trips |
| `GET .../diagnostics` | 200 | All 20 fields, counts correct, hard-false flags |

## 6. Diagnostics Live Proof

| Signal | Value |
|---|---|
| `context_packet_count` | 2 (1 from this proof + 1 stale) |
| `state_count` | 1 |
| `commit_count` | 0 |
| `graph_used` | `false` |
| `runtime_event_published` | `false` |
| `project_pulse_enabled` | `false` |
| `export_restore_enabled` | `false` |
| `auth_required` | `true` |
| `write_action_kind` | `create_reality_stamp` |
| `readback_mode` | `exact_context_packet_id` |
| `last_context_packet_created_at` | present |
| `warnings` | `[]` |
| `profile_name` | `test-continuity` |
| `feature_flag_enabled` | `true` |
| No raw payloads (`payload_json`, `provenance_json`) | Confirmed |
| No packet ID lists | Confirmed |
| No secrets | Confirmed |

## 7. Write + Readback + Diagnostics Loop

1. Write stamp → `success=true`, `graph_used=false`, `runtime_event_published=false`
2. Readback same packet → `found=true`, payload round-trips, `deleted=false`
3. Diagnostics after write → counts increment, flags all false, no raw payloads

## 8. No-Write Guarantee

Diagnostics creates zero new rows. Counts unchanged between consecutive diagnostics calls.

## 9. Forbidden Paths

All clean — no chat, worker, compiler, graph, browser, provider, retrieval, Project Pulse, or export/restore invocation.

## 10. Outcome

**PASS — `go`**

The operator triad is fully proven: write explicit stamp → read exact packet → diagnose gate/count truth. All three routes share `continuity_operator` surface key, profile + flag + auth gates, and `graph_used`/`runtime_event_published`/`project_pulse_enabled`/`export_restore_enabled` hard-false.
