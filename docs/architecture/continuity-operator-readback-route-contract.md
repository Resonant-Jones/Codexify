# Continuity Operator Readback Route Contract

> Classification: docs-only operator readback contract  
> Status: proposed  
> Implementation status: no readback route, UI, graph reads, Project Pulse, export/restore, or runtime behavior exists  
> Normative language: "must", "must not", "should", "proposed", "deferred", and "future" are intentional.

Purpose: Define the contract for a future developer/operator readback route that can inspect continuity records written by the test-only continuity operator profile. This is a docs-only contract. It does not implement the route, activate profiles, add UI, or widen the supported beta release promise.

Last updated: 2026-06-25

## Purpose

The continuity operator write route (`POST /api/operator/continuity/reality-stamp`) is now live-proven under the `test-continuity` profile. It creates context packet rows with explicit payloads, provenance, and receipt confirmation. But there is no way for an operator to inspect what was written — to verify that a packet exists, read its payload, check its provenance, or confirm its sensitivity and retention.

Without a readback contract, a future implementation could accidentally:

- Create a readback route that lists all packets (listing semantics belong to export or admin surfaces, not operator proof)
- Build a readback surface that queries Neo4j or graph mounts
- Confuse readback with Project Pulse by aggregating or summarizing state
- Return soft-deleted records without explicit policy
- Trigger writes as a side effect of reads
- Expose the readback route in the supported beta profile

This contract defines the smallest safe readback surface — a single exact-ID packet lookup — and establishes the boundaries that keep it separated from Project Pulse, export/restore, graph exploration, UI diagnostics, and general continuity runtime support.

## Non-Goals

This contract does not, and must not be interpreted as:

- implementing the readback route
- activating the readback route in any profile
- activating the write route in the supported beta profile
- adding UI
- implementing Project Pulse
- adding a worker
- adding command bus integration
- wiring chat-turn hooks
- enabling compiler auto-persistence
- implementing browser capture
- performing graph reads or writes
- implementing sync behavior
- implementing export/restore inclusion
- implementing shared/dyadic reality runtime
- widening the supported beta release promise

## Current Implemented Surface

| Surface | Status |
|---|---|
| Write route | `POST /api/operator/continuity/reality-stamp` exists |
| Test profile exposure | `test-continuity` exposes the write route |
| Supported beta quarantine | `v1-local-core-web-mcp` quarantines the write route |
| Feature flag gate | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` required |
| Auth | `require_api_key` (backend API key) |
| Write behavior | `create_reality_stamp` only — one context packet row per request |
| Receipt | `graph_used=false`, `runtime_event_published=false`, explicit created IDs |
| Readback route | **Does not exist** |

## Proposed Readback Surface

One future route only:

**`GET /api/operator/continuity/context-packets/{packet_id}`**

Rules:

- Route name is proposed; exact path may follow repo operator-route conventions.
- Developer/operator only — not user-facing.
- Test-only profile first (`test-continuity`). Supported beta must remain quarantined.
- Reads exactly one context packet by explicit packet ID.
- Must not list all records in MVP. Listing requires export/admin semantics.
- Must not read states, commits, or links in MVP. Single-resource reads keep the surface narrow.
- Must not query Neo4j or any graph mount.
- Must not write — no side effects on continuity tables.
- Must not publish runtime events.

## Readback Response Contract

Proposed response shape:

```json
{
    "packet_id": "<string>",
    "found": true,
    "schema_version": "<string>",
    "kind": "<ContextPacketKind>",
    "scope": { "user_id": "...", "project_id": "...", ... },
    "source": { "system": "...", "plugin": null, ... },
    "created_at": "<ISO-8601>",
    "summary": "<string>",
    "payload": { ... },
    "metadata": { ... },
    "provenance": { "source_packet_ids": [...], ... },
    "sensitivity": "local",
    "retention": "session",
    "integrity": { ... },
    "deleted": false,
    "graph_used": false,
    "runtime_event_published": false,
    "read_at": "<ISO-8601>"
}
```

Required values:

- `found` is `true` when the packet exists and is not soft-deleted.
- `found` is `false` when the packet does not exist or is soft-deleted (MVP default: treat soft-deleted as not found).
- `graph_used` is always `false`.
- `runtime_event_published` is always `false`.
- `deleted` reflects the soft-delete state of the row (informational; not returned when `found=false`).
- No task event IDs, no graph IDs, no compiler metadata in the readback response.

## Profile and Feature Flag Boundary

- The supported beta profile `v1-local-core-web-mcp` must remain quarantined — no readback route exposure.
- `test-continuity` may expose the readback route in a future implementation task.
- The feature flag `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` should gate both the write route and the readback route if they share the same operator surface module, or a separate readback flag may be introduced if repo conventions prefer independent gating.
- Readback route activation must not implicitly activate the write route in other profiles.
- If OpenAPI is profile-filtered, the readback route must not appear in the supported beta OpenAPI schema.

## Auth and Identity Boundary

- Route must require API key authentication (`require_api_key` or equivalent).
- Anonymous reads are forbidden.
- Actor/operator identity should be captured in access logs or diagnostics if repo conventions support it.
- Read-as-another-user remains forbidden unless a future delegation contract exists.
- `team`, `dyad`, `shared` semantics remain deferred.

## Read Semantics

The readback route must enforce the following semantics:

| Rule | Behavior |
|---|---|
| Read by exact packet ID only | `SELECT ... WHERE id = :packet_id` via adapter |
| Not found → appropriate response | `{"found": false}` for missing packets |
| Soft-deleted by default excluded | `WHERE deleted_at IS NULL` unless future admin policy says otherwise |
| No list records | No `GET /api/operator/continuity/context-packets` without an ID |
| No search | No query parameters for filtering, sorting, or pagination |
| No retrieval | No vector search, no context broker, no RAG |
| No inference | Packet content is returned as-is; no summarization or model calls |
| No compiler | `compile_reality_state` is not called |
| No write-action service | `ContinuityWriteActionService` is not imported or called |

## Operator Truth Surface

A future implementation proof must demonstrate:

| Signal | Required Value |
|---|---|
| Profile | `test-continuity` |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` |
| Auth | Valid API key → 200; missing/invalid → 401/403 |
| Existing packet | `found=true`, all fields populated, `deleted=false` |
| Missing packet | `found=false` |
| Soft-deleted packet | Not returned (or `found=false` if soft-delete exists) |
| Direct Postgres verification | Row matches response fields |
| Graph usage | `false` — no Neo4j calls |
| Runtime event publication | `false` — no task events |
| Write side effects | No new rows in any continuity table after read |

## No-Write Guarantee

The readback route must not, under any circumstance:

- Call `ContinuityWriteActionService`
- Call `save_context_packet()`
- Call `save_reality_state()`
- Call `save_reality_commit()`
- Call `link_state_packets()`
- Mutate any continuity table
- Publish runtime events
- Create DB sessions that outlive the request

The readback route is purely read-only. A source-level AST or import audit must confirm that no write-module or write-function references exist in the readback module.

## Graph-Off Baseline

- Route must work with Neo4j disabled or absent.
- Route must not import Neo4j runtime modules, graph adapters, or graph query builders.
- Route must not perform graph lookups.
- Graph IDs must not appear as required response fields.
- Graph enrichment remains separate future work gated by its own contract.

## Project Pulse Boundary

The readback route is not Project Pulse. Specifically:

- Readback returns one raw packet record. Project Pulse would aggregate, summarize, and present multiple continuity artifacts in a user-facing UI.
- Readback is an operator diagnostic/inspection surface. Project Pulse is a user-facing brief surface.
- Readback must not compute pulse summaries, compile project state, or suggest resume actions.
- Readback must not introduce UI components, accessibility requirements, or visual design tokens.
- Project Pulse implementation requires a separate task with its own UI spec, accessibility review, and read-model contract.

## Export/Restore Boundary

- The readback route does not implement export.
- The readback route does not implement restore.
- Local DB IDs in the response must not be treated as portable export identity.
- Export/restore continuity inclusion remains deferred to a separate task.

## Failure Modes

The following failure modes must be prevented:

| Failure Mode | Prevention |
|---|---|
| Readback route exposed in supported beta profile | Profile activation tests must verify 404 for `v1-local-core-web-mcp` |
| Anonymous read succeeds | Auth tests must verify 401/403 for missing/invalid API key |
| Route lists records instead of exact-ID read | Route must reject requests without `{packet_id}`; no wildcard or list endpoint |
| Route reads soft-deleted records by default | `WHERE deleted_at IS NULL` filter in adapter read method |
| Route calls write service | AST/import audit must confirm zero write-function references |
| Route mutates continuity tables | Postgres row-count verification before/after read request |
| Route queries graph | AST/import audit must confirm zero Neo4j references |
| Route publishes runtime event | Response `runtime_event_published` must be `false` |
| Response mistaken for Project Pulse | Response shape is a single packet envelope, not an aggregated brief |
| Route leaks raw DB errors | Error responses must use structured JSON, not raw SQLAlchemy/psycopg exceptions |

## Required Tests for Future Implementation

When the readback route is implemented, the following tests must pass:

| Test | What It Proves |
|---|---|
| Supported beta → 404 | Quarantine preserved for `v1-local-core-web-mcp` |
| Test profile → 200 (valid request) | Route exposed in `test-continuity` |
| Test profile → 401/403 (no auth) | Auth boundary works |
| Existing packet → full response | All fields populated; `deleted=false`; `found=true` |
| Missing packet → not found | `found=false`; no 500 error |
| Soft-deleted packet → not found (if implemented) | Soft-delete filter working |
| Zero new rows after read | No write side effects |
| No write-service calls | AST audit confirms zero references to `ContinuityWriteActionService` |
| No compiler calls | AST audit confirms zero references to `compile_reality_state` |
| No graph queries | AST audit confirms zero Neo4j references |
| Response `graph_used=false` | Explicit field in response |
| Response `runtime_event_published=false` | Explicit field in response |

## Relationship to Existing Contracts

### ADR-030: Continuity Protocol Suite Runtime Gate

ADR-030 gates all continuity runtime work. This contract gates the operator readback route — a read-only surface that does not alter write semantics or broaden runtime integration.

### ADR-031: Continuity Phase A Storage Migration Gate

ADR-031 gates schema migration. The readback route reads from the already-proven Phase A tables via the already-proven persistence adapter.

### continuity-write-action-contract.md

The write-action contract defines write actions. The readback route must not call any write action. It reads only.

### continuity-runtime-invocation-boundary-contract.md

The invocation boundary contract recommends `developer_operator_route` as the next caller. The readback route is a second developer/operator route — a read complement to the write route.

### continuity-operator-route-profile-activation-contract.md

The profile activation contract defines the two-gate model (feature flag + profile manifest). The readback route must follow the same gating discipline.

### 2026-06-25-continuity-operator-route-live-proof.md

The write route live proof confirmed the route works behind profile quarantine. The readback route must be live-proven under the same conditions.

### 2026-06-25-continuity-test-profile-live-proof.md

The test profile live proof confirmed `test-continuity` exposes the write route while `v1-local-core-web-mcp` quarantines it. The readback route must be verified under the same profile pair.

### continuity-persistence-adapter-contract.md

The readback route reads via `ContinuityPersistenceAdapter.load_reality_state()` or a similar adapter read method.

### config-and-ops.md

No new environment variables are required. The existing `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` flag or a new readback-specific flag may gate the route.

### data-and-storage.md

The readback route reads from Postgres only. No Redis, vector, file, or graph storage is accessed.

### account-export-restore-contract.md

The readback route is not export. It returns a single packet record, not an export artifact.

### guardian/routes/continuity_operator.py

The readback route may be added to the existing operator route module or a separate readback module.

### guardian/continuity/persistence.py

The readback route reads via the adapter. It must not use direct SQLAlchemy queries that bypass the adapter's soft-delete and scope filters.

## Required Follow-Up Before Implementation

Before the readback route is implemented, a future task must:

1. Choose exact module path (extend `guardian/routes/continuity_operator.py` or create a separate readback module).
2. Choose whether to share `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` flag or introduce a readback-specific flag.
3. Define DB read/session dependency (use existing `get_database_dsn` or adapter session pattern).
4. Define response model (Pydantic or dict shape matching the readback response contract).
5. Define profile exposure: add to `test-continuity` enabled routes; keep `v1-local-core-web-mcp` quarantined.
6. Define direct Postgres verification tests.
7. Define no-write tests (zero new rows after read).
8. Define graph-off tests (no Neo4j imports or queries).
9. Keep UI, Project Pulse, export, browser, chat, and sync modules out of scope.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No route has been implemented.
- [ ] No profile manifest has been updated.
- [ ] The supported beta profile quarantine is preserved.
- [ ] The test-only profile-first boundary is explicit.
- [ ] Exact-ID read only — no list, search, or retrieval semantics defined.
- [ ] No write-service calls are authorized.
- [ ] Auth boundary is explicit.
- [ ] Graph-off baseline is explicit.
- [ ] Project Pulse boundary is explicit.
- [ ] Export/restore boundary is explicit.
- [ ] Required follow-up steps before implementation are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
