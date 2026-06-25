# Continuity Operator State Commit Link Readback Contract

> Classification: docs-only readback contract  
> Status: proposed  
> Implementation status: no state, commit, or link readback routes exist  
> Normative language: "must", "must not", "should", "proposed", "deferred", and "future" are intentional.

Purpose: Define the contract for future developer/operator readback routes over the remaining Phase A Continuity tables — reality states, reality commits, and state-packet links. This is a docs-only contract. It does not implement routes, activate profiles, add UI, or widen the supported beta release promise.

Last updated: 2026-06-25

## Purpose

The Continuity operator triad is live-proven:
- `POST /api/operator/continuity/reality-stamp` — writes one context packet
- `GET /api/operator/continuity/context-packets/{id}` — reads one exact packet
- `GET /api/operator/continuity/diagnostics` — reports aggregate counts

Diagnostics exposes aggregate counts for all four Phase A tables, but there is no way for an operator to inspect individual reality states, reality commits, or state-packet links by exact ID.

States, commits, and links carry stronger semantic meaning than individual context packets. A state is compiled truth over multiple source packets. A commit is a durable state transition record with trigger, kind, and provenance. A link is the provenance seam between a state and its contributing packets. Exposing these records without a contract could accidentally:

- Create a state readback route that reconstructs Project Pulse by summarizing compiled truth
- Create a commit readback route that traverses commit history and becomes an audit/export surface
- Create a link readback route that expands to full packet payloads and becomes a graph traversal
- Bundle all three routes into a single list/search API
- Expose raw payloads beyond the exact-ID boundary
- Confuse operator readback with export manifests or Project Pulse briefs

This contract defines the smallest safe readback surface — three exact-ID routes, staged independently — and establishes the boundaries that keep them separated from Project Pulse, export/restore, graph exploration, list/search, and release-supported continuity runtime.

## Non-Goals

This contract does not, and must not be interpreted as:

- implementing any route
- activating any profile
- activating the supported beta profile
- implementing UI or Project Pulse
- adding a worker or command bus integration
- wiring chat-turn hooks
- enabling compiler auto-persistence
- implementing browser capture
- performing graph reads or writes
- implementing sync behavior
- implementing export/restore inclusion
- implementing list/search APIs
- exposing raw packet payloads through diagnostics
- implementing shared/dyadic reality runtime
- widening the supported beta release promise

## Current Proven Operator Loop

| Surface | Status |
|---|---|
| Write route | `POST /api/operator/continuity/reality-stamp` — live-proven |
| Packet readback | `GET /api/operator/continuity/context-packets/{id}` — live-proven |
| Diagnostics | `GET /api/operator/continuity/diagnostics` — live-proven |
| Test profile | `test-continuity` exposes the triad |
| Beta quarantine | `v1-local-core-web-mcp` quarantines the triad |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` required |
| Auth | `require_api_key` |
| Hard-false flags | `graph_used=false`, `runtime_event_published=false`, `project_pulse_enabled=false`, `export_restore_enabled=false` |
| State readback | **Does not exist** |
| Commit readback | **Does not exist** |
| Link readback | **Does not exist** |

## Proposed Future Readback Surface

Three future exact-ID routes, staged independently:

- `GET /api/operator/continuity/reality-states/{state_id}`
- `GET /api/operator/continuity/reality-commits/{commit_id}`
- `GET /api/operator/continuity/state-packet-links/{link_id}`

Rules:

- Route names are proposed; exact paths may follow repo operator-route conventions.
- Developer/operator only — not user-facing.
- Test-only profile first (`test-continuity`). Supported beta must remain quarantined.
- Each route reads exactly one record by explicit ID.
- Must not list records.
- Must not search records.
- Must not expand related record graphs by default (e.g., a state readback must not automatically fetch all linked packets).
- Must not query Neo4j or any graph mount.
- Must not write — no side effects on continuity tables.
- Must not publish runtime events.

## Route Staging Order

Future implementation must proceed in this order, one atomic task per route:

1. **Reality state exact-ID readback** — reads one state by explicit `state_id`
2. **Reality commit exact-ID readback** — reads one commit by explicit `commit_id`
3. **State-packet link exact-ID readback** — reads one link by explicit `link_id`

Rules:

- Each implementation must be a separate atomic task unless a later contract explicitly approves bundling.
- Each implementation must have its own targeted tests.
- Each implementation must preserve supported beta quarantine.
- Each implementation must preserve feature flag gating and API-key auth.
- Order matters: state readback is the most useful operator surface and should come first. Commit readback depends on states existing. Link readback is the narrowest and should come last.

## Reality State Readback Response Contract

Proposed response shape:

```json
{
    "state_id": "<string>",
    "found": true,
    "schema_version": "<string>",
    "scope": "<RealityScope>",
    "compiled_at": "<ISO-8601>",
    "summary": "<string>",
    "state": { ... },
    "metadata": { ... },
    "provenance": { ... },
    "source_packet_count": 3,
    "deleted": false,
    "graph_used": false,
    "runtime_event_published": false,
    "project_pulse_enabled": false,
    "export_restore_enabled": false,
    "read_at": "<ISO-8601>"
}
```

Required hard-false values: `graph_used`, `runtime_event_published`, `project_pulse_enabled`, `export_restore_enabled`.

`state` is the stored state payload for the exact state ID only. Rules:

- Must expose the state exactly as stored — one RealityState envelope.
- Must not automatically expand all source packet payloads (link traversal is separate).
- Must not summarize, rank, infer, or compile a new state.
- Must not compute open loops, rejected paths, or suggested actions beyond what is stored.

`source_packet_count` is the count of linked source packet IDs for this state. It is informational only — no packet payloads are exposed through the state readback.

## Reality Commit Readback Response Contract

Proposed response shape:

```json
{
    "commit_id": "<string>",
    "found": true,
    "state_id": "<string | null>",
    "schema_version": "<string>",
    "committed_at": "<ISO-8601>",
    "summary": "<string>",
    "change_reason": "<string>",
    "actor": { ... },
    "metadata": { ... },
    "provenance": { ... },
    "deleted": false,
    "graph_used": false,
    "runtime_event_published": false,
    "project_pulse_enabled": false,
    "export_restore_enabled": false,
    "read_at": "<ISO-8601>"
}
```

Required hard-false values: `graph_used`, `runtime_event_published`, `project_pulse_enabled`, `export_restore_enabled`.

Rules:

- Commit readback must describe the stored commit record only — one RealityCommit envelope.
- Must not reconstruct project reality from the commit chain.
- Must not traverse commit history by default (no `previous_commit_id` expansion).
- Must not auto-fetch the referenced state payload.

## State Packet Link Readback Response Contract

Proposed response shape:

```json
{
    "link_id": "<string>",
    "found": true,
    "state_id": "<string>",
    "packet_id": "<string>",
    "link_kind": "<string>",
    "created_at": "<ISO-8601>",
    "metadata": { ... },
    "deleted": false,
    "graph_used": false,
    "runtime_event_published": false,
    "project_pulse_enabled": false,
    "export_restore_enabled": false,
    "read_at": "<ISO-8601>"
}
```

Required hard-false values: `graph_used`, `runtime_event_published`, `project_pulse_enabled`, `export_restore_enabled`.

Rules:

- Link readback must return the link record only — one state-packet link envelope.
- Must not automatically return the linked packet's payload.
- Must not automatically return the linked state's payload.
- Must not compute a graph traversal of related links.
- The operator may use separate exact-ID readback routes for the linked packet and state if needed.

## Profile and Feature Flag Boundary

- Supported beta profile `v1-local-core-web-mcp` must remain quarantined — no readback route exposure.
- `test-continuity` may expose future readback routes in separate implementation tasks.
- Feature flag behavior must remain explicit — `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` gates the routes.
- Routes must not appear in supported beta OpenAPI if existing continuity operator routes do not.
- Readback activation must not implicitly activate write routes in other profiles.

## Auth and Identity Boundary

- Routes must require API key authentication (`require_api_key` or equivalent).
- Anonymous reads are forbidden.
- Read-as-another-user remains forbidden unless a future delegation contract exists.
- `team`, `dyad`, `shared` semantics remain deferred.
- Actor/operator identity should be captured in logs or diagnostics if repo conventions support it.
- Raw secrets must never be exposed in readback responses.

## Read Semantics

| Rule | Behavior |
|---|---|
| Read by exact ID only | `SELECT ... WHERE id = :record_id` via DB session |
| Not found → appropriate response | `{"found": false}` for missing records |
| No list | No `GET /api/operator/continuity/reality-states` without an ID |
| No search | No query parameters for filtering, sorting, or pagination |
| No retrieval | No vector search, no context broker, no RAG |
| No inference | Record content returned as-is; no summarization or model calls |
| No compilation | `compile_reality_state` is not called |
| No graph traversal | No Neo4j queries for related records |
| No events | No task events published |
| No writes | `ContinuityWriteActionService` is not called |

## No-Write Guarantee

Future readback routes must not, under any circumstance:

- Call `ContinuityWriteActionService`
- Call `create_reality_stamp()`
- Call `compile_and_save_reality_state_from_explicit_packets()`
- Call `create_reality_commit()`
- Call `link_state_to_packets()`
- Call any persistence save method
- Mutate any continuity table
- Publish runtime events

## Graph-Off Baseline

- Routes must work with Neo4j disabled or absent.
- Routes must not import Neo4j runtime modules, graph adapters, or graph query builders.
- Routes must not perform graph lookups.
- Graph IDs must not appear as required response fields.
- Graph enrichment remains separate future work gated by its own contract.

## Project Pulse Boundary

State/commit/link readback is not Project Pulse. Specifically:

- Readback returns one raw record by exact ID. Project Pulse would aggregate, summarize, and present multiple continuity artifacts in a user-facing UI.
- Readback is an operator diagnostic/inspection surface. Project Pulse is a user-facing brief surface.
- Readback must not aggregate project reality, compile project state, or suggest resume actions.
- Readback must not introduce UI components, accessibility requirements, or visual design tokens.
- Project Pulse implementation requires a separate task with its own UI spec.

## Export/Restore Boundary

- Readback routes do not implement export.
- Readback routes do not implement restore.
- Response IDs are not portable export identity.
- Readback route output is not an export manifest.
- Local DB IDs must not be treated as portable export identity.
- Export/restore continuity inclusion remains deferred.

## Data Exposure Boundary

| Surface | What It Exposes | What It Must Not Expose |
|---|---|---|
| State readback | One stored state payload by exact ID | All linked packet payloads |
| Commit readback | One stored commit record by exact ID | Full state history, full state payload |
| Link readback | One link record by exact ID | Linked packet payload, linked state payload |
| Diagnostics | Aggregate counts only (unchanged) | Raw payloads, ID lists, secrets |

## Failure Modes

| Failure Mode | Prevention |
|---|---|
| Routes exposed in supported beta profile | Profile activation tests must verify 404 |
| Anonymous read succeeds | Auth tests must verify 401/403 |
| State readback compiles a new state | Must not call `compile_reality_state` |
| Commit readback reconstructs project reality | Must not traverse commit chain |
| Link readback exposes packet payloads | Must return link envelope only, not linked record payloads |
| Routes list or search records | Must reject requests without exact ID |
| Routes query graph | AST/import audit on Neo4j |
| Routes call write service | AST/import audit on `ContinuityWriteActionService` |
| Routes mutate continuity tables | Postgres row-count verification |
| Routes publish runtime events | Response `runtime_event_published=false` |
| Mistaken for Project Pulse | `project_pulse_enabled=false` in every response |
| Mistaken for export support | `export_restore_enabled=false` in every response |
| Raw DB errors leak | Structured error responses, no raw exception text |

## Required Tests for Future Implementation

When any of the three routes is implemented, the following tests must pass:

| Test | What It Proves |
|---|---|
| Supported beta → 404 | Quarantine preserved |
| Test profile → 200 (valid request) | Route exposed |
| Unauthenticated → 401/403 | Auth boundary |
| Existing record → full response | All fields populated; `found=true` |
| Missing record → `found=false` | Not-found handling |
| No-write | Zero new rows after readback |
| No compiler calls | AST audit on `compile_reality_state` |
| No graph queries | AST audit on Neo4j |
| No write-service calls | AST audit on `ContinuityWriteActionService` |
| Hard-false flags | `graph_used`, `runtime_event_published`, `project_pulse_enabled`, `export_restore_enabled` all `false` |
| Data exposure | State readback does not expose linked packet payloads; link readback does not expose linked record payloads |

## Relationship to Existing Contracts

This contract extends the operator readback doctrine. It references:

- **ADR-030** — overall continuity runtime gate
- **ADR-031** — Phase A storage migration gate
- **`continuity-storage-schema-proposal.md`** — table definitions for states, commits, links
- **`continuity-persistence-adapter-contract.md`** — adapter read methods
- **`continuity-write-action-contract.md`** — write actions (must not be called by readback)
- **`continuity-runtime-invocation-boundary-contract.md`** — caller surface definitions
- **`continuity-operator-route-profile-activation-contract.md`** — profile activation gate
- **`continuity-operator-readback-route-contract.md`** — parent readback contract (context packets)
- **`continuity-operator-diagnostics-truth-surface-contract.md`** — diagnostics contract (aggregate counts)
- **`continuity-operator-loop-proof-chain.md`** — consolidated proof chain
- **4 live proof artifacts** — operator route, test profile, readback, diagnostics
- **`data-and-storage.md`**, **`account-export-restore-contract.md`** — operational contracts
- **`guardian/routes/continuity_operator.py`** — existing route module
- **`guardian/continuity/persistence.py`** — existing adapter
- **`guardian/continuity/write_actions.py`** — existing write service (must not be called)

## Required Follow-Up Before Implementation

Before any state/commit/link readback route is implemented, a future task must:

1. Choose exactly one route to implement first (reality state readback is recommended).
2. Choose exact module path (extend `continuity_operator.py` or create a separate readback module).
3. Define the response model matching the relevant response contract in this document.
4. Define DB read/session dependency (use existing `get_database_dsn` pattern).
5. Define profile exposure in `test-continuity`; keep supported beta quarantined.
6. Define direct Postgres verification tests.
7. Define no-write tests (zero new rows after readback).
8. Define graph-off tests (no Neo4j imports or queries).
9. Define data exposure tests (link readback must not expose linked record payloads).
10. Keep UI, Project Pulse, export, browser, chat, and sync modules out of scope.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No route has been implemented.
- [ ] No profile manifest has been updated.
- [ ] Supported beta quarantine is preserved.
- [ ] Test-only profile-first boundary is explicit.
- [ ] Exact-ID read semantics only — no list/search.
- [ ] Route staging order is explicit (state → commit → link).
- [ ] State readback response contract is explicit.
- [ ] Commit readback response contract is explicit.
- [ ] Link readback response contract is explicit.
- [ ] No-write guarantee is explicit.
- [ ] Graph-off baseline is explicit.
- [ ] Project Pulse boundary is explicit.
- [ ] Export/restore boundary is explicit.
- [ ] Data exposure boundary is explicit.
- [ ] Required follow-up steps before implementation are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
