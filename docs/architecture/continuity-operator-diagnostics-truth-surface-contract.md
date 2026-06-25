# Continuity Operator Diagnostics Truth Surface Contract

> Classification: docs-only operator diagnostics contract  
> Status: proposed  
> Implementation status: no diagnostics route, UI, Project Pulse, graph, export/restore, or runtime behavior exists  
> Normative language: "must", "must not", "should", "proposed", "deferred", and "future" are intentional.

Purpose: Define the contract for a future developer/operator diagnostics truth surface over the now-proven Continuity operator loop. This is a docs-only contract. It does not implement routes, activate profiles, add UI, or widen the supported beta release promise.

Last updated: 2026-06-25

## Purpose

The continuity operator loop is now proven end-to-end:
- `POST /api/operator/continuity/reality-stamp` — writes one explicit context packet
- `GET /api/operator/continuity/context-packets/{packet_id}` — reads one exact packet
- Both routes share the `continuity_operator` surface key
- Both are gated by profile (`test-continuity` only) + feature flag + API key auth
- Both return `graph_used=false` and `runtime_event_published=false`
- Readback creates zero writes

But there is no single operator surface that answers: "Is the continuity operator loop healthy right now, on this running instance?" An operator must separately check:

- Which profile is active?
- Is the route quarantined or exposed?
- Is the feature flag on?
- Are there any context packets in the database?
- Are there any states, commits, or links?
- Did the write and readback proofs pass?

Without a diagnostics contract, a future implementation could accidentally:
- Build a diagnostics route that dumps raw packet payloads (exposing operator data beyond gate signals)
- Confuse diagnostics with Project Pulse by aggregating project reality
- Add list/search semantics disguised as diagnostics
- Expose diagnostics in the supported beta profile
- Write to continuity tables as a side effect of diagnostic queries
- Query Neo4j for diagnostic data
- Publish runtime events for diagnostic requests

This contract defines the smallest safe diagnostics surface — gate signal, aggregate count, and last-created timestamp only — and establishes the boundaries that keep it separated from Project Pulse, export/restore, graph exploration, data dumps, and release-supported continuity runtime.

## Non-Goals

This contract does not, and must not be interpreted as:

- implementing the diagnostics route
- activating the diagnostics route in any profile
- implementing UI
- implementing Project Pulse
- adding a worker
- adding command bus integration
- wiring chat-turn hooks
- enabling compiler auto-persistence
- implementing browser capture
- performing graph reads or writes
- implementing sync behavior
- implementing export/restore inclusion
- implementing list/search APIs
- implementing state/commit/link readback
- implementing shared/dyadic reality runtime
- widening the supported beta release promise

## Current Proven Operator Loop

| Surface | Status |
|---|---|
| Write route | `POST /api/operator/continuity/reality-stamp` — live-proven |
| Readback route | `GET /api/operator/continuity/context-packets/{packet_id}` — live-proven |
| Test profile exposure | `test-continuity` exposes both routes |
| Supported beta quarantine | `v1-local-core-web-mcp` quarantines both routes |
| Feature flag gate | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` required |
| Auth | `require_api_key` (backend API key) |
| Write behavior | `create_reality_stamp` only — one context packet row |
| Readback behavior | Exact-ID read only — no list, search, retrieval, or writes |
| Receipt/response flags | `graph_used=false`, `runtime_event_published=false` |
| No-write readback | Confirmed — zero rows created by readback |
| Diagnostics route | **Does not exist** |

## Proposed Diagnostics Surface

One future route only:

**`GET /api/operator/continuity/diagnostics`**

Rules:

- Route name is proposed; exact path may follow repo operator-route conventions.
- Developer/operator only — not user-facing.
- Test-only profile first (`test-continuity`). Supported beta must remain quarantined.
- Reports gate/proof/health signals only — profile state, feature flag state, aggregate counts, last-created timestamp.
- Must not list continuity records.
- Must not search continuity records.
- Must not return raw packet payloads.
- Must not read states, commits, or links payloads in MVP (counts only).
- Must not query Neo4j or any graph mount.
- Must not write — no side effects on continuity tables.
- Must not publish runtime events.

## Diagnostics Response Contract

Proposed response shape:

```json
{
    "profile_name": "test-continuity",
    "supported_beta_quarantined": true,
    "test_profile_enabled": true,
    "feature_flag_enabled": true,
    "write_route_available": true,
    "readback_route_available": true,
    "auth_required": true,
    "write_action_kind": "create_reality_stamp",
    "readback_mode": "exact_id",
    "context_packet_count": 3,
    "state_count": 0,
    "commit_count": 0,
    "state_packet_link_count": 0,
    "last_context_packet_created_at": "2026-06-25T22:03:50.892592+00:00",
    "graph_used": false,
    "runtime_event_published": false,
    "project_pulse_enabled": false,
    "export_restore_enabled": false,
    "diagnostics_generated_at": "2026-06-25T22:10:00.000000+00:00",
    "warnings": []
}
```

Required values:

- `graph_used` is always `false`.
- `runtime_event_published` is always `false`.
- `project_pulse_enabled` is always `false` (Project Pulse does not exist).
- `export_restore_enabled` is always `false` (export/restore continuity inclusion does not exist).
- `auth_required` is always `true`.
- `readback_mode` is `"exact_id"` (no list/search semantics).
- `write_action_kind` is `"create_reality_stamp"` (only write action exposed).

Count semantics:

- `context_packet_count` is the total number of non-deleted rows in `continuity_context_packets`.
- `state_count`, `commit_count`, `state_packet_link_count` are total non-deleted row counts in their respective tables.
- Counts are informational only — they do not imply specific records exist or are queryable through the operator routes.
- `last_context_packet_created_at` is the most recent `created_at` timestamp among non-deleted context packets, or `null` if no packets exist.

## Profile and Feature Flag Boundary

- The supported beta profile `v1-local-core-web-mcp` must remain quarantined — no diagnostics route exposure.
- `test-continuity` may expose the diagnostics route in a future implementation task.
- The feature flag `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` should gate the diagnostics route alongside the write and readback routes.
- Diagnostics activation must not implicitly activate write/readback routes in other profiles.
- If OpenAPI is profile-filtered, the diagnostics route must not appear in the supported beta OpenAPI schema.

## Auth and Operator Boundary

- Route must require API key authentication (`require_api_key` or equivalent).
- Anonymous diagnostics reads are forbidden.
- Diagnostics must not leak secrets, API keys, or environment variables.
- Actor/operator identity should be captured in access logs if repo conventions support it.
- `team`, `dyad`, `shared` semantics remain deferred.

## Diagnostic Semantics

| Rule | Behavior |
|---|---|
| Reports route/profile/gate posture | Profile name, quarantine state, flag state, route availability |
| May report aggregate counts | `SELECT COUNT(*) FROM continuity_* WHERE deleted_at IS NULL` |
| May report last-created timestamp | `SELECT MAX(created_at) FROM continuity_context_packets WHERE deleted_at IS NULL` |
| Must not return raw packet payloads | No `payload_json`, `metadata_json`, or `provenance_json` in diagnostics response |
| Must not list packet IDs | No arrays of packet IDs |
| Must not search records | No query parameters for filtering, sorting, or pagination |
| Must not perform retrieval | No vector search, no context broker, no RAG |
| Must not infer state | No summarization, no model calls, no compilation |
| Must not call compiler | `compile_reality_state` is not called |
| Must not call write-action service | `ContinuityWriteActionService` is not imported or called |
| Must not publish events | No task events, no SSE, no domain events |

## Operator Truth Surface

A future implementation proof must demonstrate:

| Signal | Required Value |
|---|---|
| Profile name | `test-continuity` |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` |
| Auth | Valid API key → 200; missing/invalid → 401/403 |
| Supported beta quarantine | Route 404 under `v1-local-core-web-mcp` |
| Counts accurate | `context_packet_count` matches `SELECT COUNT(*)` |
| No raw payloads | Response contains no `payload_json`, `metadata_json`, or `provenance_json` fields |
| Graph usage | `false` — no Neo4j calls |
| Runtime events | `false` — no task events |
| Project Pulse | `false` |
| Export/restore | `false` |
| Write side effects | No new rows in any continuity table after diagnostics call |

## No-Write Guarantee

The diagnostics route must not, under any circumstance:

- Call `ContinuityWriteActionService`
- Call `save_context_packet()`
- Call `save_reality_state()`
- Call `save_reality_commit()`
- Call `link_state_packets()`
- Mutate any continuity table
- Publish runtime events

The diagnostics route is purely read-only. A source-level AST or import audit must confirm that no write-module or write-function references exist in the diagnostics code path.

## Data Exposure Boundary

Diagnostics exposes aggregate signals only. The following data must not be exposed:

- Raw packet payloads (`payload_json`, `metadata_json`, `provenance_json`, `integrity_json`)
- Raw state or commit payloads
- Packet IDs (except as aggregate counts)
- API keys or secrets
- Browser context
- Provider state
- Graph IDs or graph data
- Export manifests or restore state

Diagnostics is a gate-and-count surface. It is not a data export, not an admin data browser, and not a Project Pulse summary.

## Graph-Off Baseline

- Diagnostics must work with Neo4j disabled or absent.
- Diagnostics must not import Neo4j runtime modules, graph adapters, or graph query builders.
- Diagnostics must not perform graph lookups.
- Graph IDs must not appear as required response fields.
- Graph enrichment remains separate future work gated by its own contract.

## Project Pulse Boundary

Diagnostics is not Project Pulse. Specifically:

- Diagnostics reports gate posture and aggregate counts. Project Pulse would render project-level briefs, summaries, open loops, and suggested resume actions.
- Diagnostics is an operator health/inspection surface. Project Pulse is a user-facing working state surface.
- Diagnostics must not aggregate project reality, compile project state, or suggest resume actions.
- Diagnostics must not introduce UI components, accessibility requirements, or visual design tokens.
- Project Pulse implementation requires a separate task with its own UI spec, accessibility review, and read-model contract.

## Export/Restore Boundary

- The diagnostics route does not implement export.
- The diagnostics route does not implement restore.
- Diagnostics aggregate counts are not export manifests.
- Local DB IDs must not be treated as portable export identity.
- Export/restore continuity inclusion remains deferred to a separate task.

## Failure Modes

| Failure Mode | Prevention |
|---|---|
| Diagnostics exposed in supported beta profile | Profile activation tests must verify 404 for `v1-local-core-web-mcp` |
| Anonymous diagnostics read succeeds | Auth tests must verify 401/403 for missing/invalid API key |
| Diagnostics returns raw packet payloads | Response model must exclude `payload_json` and similar fields |
| Diagnostics lists records | Response model must contain only aggregate counts, not ID arrays |
| Diagnostics calls write service | AST/import audit must confirm zero write-function references |
| Diagnostics mutates continuity tables | Postgres row-count verification before/after diagnostics call |
| Diagnostics queries graph | AST/import audit must confirm zero Neo4j references |
| Diagnostics publishes runtime event | Response `runtime_event_published` must be `false` |
| Diagnostics mistaken for Project Pulse | Response contains gate signals and counts, not project summaries |
| Diagnostics mistaken for export support | Response explicitly sets `export_restore_enabled=false` |
| Diagnostics leaks raw DB errors | Error responses must use structured JSON, not raw SQLAlchemy/psycopg exceptions |

## Required Tests for Future Implementation

When the diagnostics route is implemented, the following tests must pass:

| Test | What It Proves |
|---|---|
| Supported beta → 404 | Quarantine preserved for `v1-local-core-web-mcp` |
| Test profile → 200 (valid request) | Route exposed in `test-continuity` |
| Test profile → 401/403 (no auth) | Auth boundary works |
| All required fields present | `profile_name`, `feature_flag_enabled`, `graph_used`, etc. |
| Counts accurate | `context_packet_count` matches DB query |
| No raw payloads | Response excludes `payload_json` and similar fields |
| Zero new rows after diagnostics | No write side effects |
| No write-service calls | AST audit confirms zero references to `ContinuityWriteActionService` |
| No compiler calls | AST audit confirms zero references to `compile_reality_state` |
| No graph queries | AST audit confirms zero Neo4j references |
| `graph_used=false` | Explicit field in response |
| `runtime_event_published=false` | Explicit field in response |
| `project_pulse_enabled=false` | Explicit field in response |
| `export_restore_enabled=false` | Explicit field in response |

## Relationship to Existing Contracts

### ADR-030: Continuity Protocol Suite Runtime Gate

ADR-030 gates all continuity runtime work. This contract gates the operator diagnostics route — a read-only surface that reports gate/proof/count signals without broadening runtime integration.

### ADR-031: Continuity Phase A Storage Migration Gate

ADR-031 gates schema migration. The diagnostics route queries aggregate counts from the already-proven Phase A tables.

### continuity-write-action-contract.md

The write-action contract defines write actions. The diagnostics route must not call any write action. It reads counts only.

### continuity-runtime-invocation-boundary-contract.md

The invocation boundary contract defines the first caller surface. The diagnostics route is a third developer/operator route — a health complement to the write+readback loop.

### continuity-operator-route-profile-activation-contract.md

The profile activation contract defines the two-gate model. The diagnostics route must follow the same gating discipline.

### continuity-operator-readback-route-contract.md

The readback contract defines exact-ID read semantics. The diagnostics route is distinct — it reports aggregate counts, not individual packet records.

### 2026-06-25-continuity-operator-route-live-proof.md, 2026-06-25-continuity-test-profile-live-proof.md, 2026-06-25-continuity-operator-readback-route-live-proof.md

All three live proofs confirm the operator loop is functional under the test-only profile. The diagnostics route would be the fourth route under the same gate.

### continuity-persistence-adapter-contract.md

The diagnostics route may use the persistence adapter for read-only aggregate queries, or may use direct SQLAlchemy `SELECT COUNT(*)` queries if the adapter does not expose aggregate methods.

### config-and-ops.md

No new environment variables are required. The existing `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` flag gates the diagnostics route.

### data-and-storage.md

The diagnostics route queries Postgres only. No Redis, vector, file, or graph storage is accessed.

### account-export-restore-contract.md

The diagnostics route is not export. It reports aggregate counts, not export artifacts.

### guardian/routes/continuity_operator.py

The diagnostics route may be added to the existing operator route module or a separate diagnostics module.

### guardian/continuity/persistence.py

The diagnostics route may use the persistence adapter's read methods or direct SQLAlchemy for aggregate queries.

## Required Follow-Up Before Implementation

Before the diagnostics route is implemented, a future task must:

1. Choose exact module path (extend `guardian/routes/continuity_operator.py` or create a separate diagnostics module).
2. Define the Pydantic response model matching the diagnostics response contract.
3. Define DB read/session dependency.
4. Define profile exposure: add to `test-continuity` enabled routes; keep `v1-local-core-web-mcp` quarantined.
5. Define aggregate query strategy (adapter vs. direct SQLAlchemy).
6. Define no-write tests (zero new rows after diagnostics call).
7. Define data exposure tests (no raw payloads in response).
8. Define graph-off tests (no Neo4j imports or queries).
9. Keep UI, Project Pulse, export, browser, chat, and sync modules out of scope.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No route has been implemented.
- [ ] No profile manifest has been updated.
- [ ] The supported beta profile quarantine is preserved.
- [ ] The test-only profile-first boundary is explicit.
- [ ] Diagnostics reports gate signals and aggregate counts only.
- [ ] No raw packet payloads are exposed.
- [ ] No list/search semantics are defined.
- [ ] No write-service calls are authorized.
- [ ] Auth boundary is explicit.
- [ ] Graph-off baseline is explicit.
- [ ] Project Pulse boundary is explicit.
- [ ] Export/restore boundary is explicit.
- [ ] Data exposure boundary is explicit.
- [ ] Required follow-up steps before implementation are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
