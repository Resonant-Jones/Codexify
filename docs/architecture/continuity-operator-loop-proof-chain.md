# Continuity Operator Loop Proof Chain

> Classification: docs-only proof-chain consolidation  
> Status: current  
> Implementation status: operator triad exists and is live-proven under test-only profile; supported beta remains quarantined  
> Normative language: "is", "remains", "proven", "quarantined", and "deferred" are intentional.

Purpose: Consolidate the proven Continuity operator loop into one reviewable proof-chain artifact. This is a map of proven evidence, not a new capability claim. It does not activate routes, implement code, or widen the supported beta release promise.

Last updated: 2026-06-25

## Purpose

The Continuity operator triad (write, readback, diagnostics) has been implemented and live-proven through multiple contracts, code modules, tests, and live Docker Compose proofs. Without a consolidated proof-chain artifact, future agents could:

- Confuse test-only profile proof with supported beta release support
- Treat a docs-only contract as implying implemented runtime behavior
- Assume profile quarantine can be bypassed with a feature flag alone
- Confuse diagnostics aggregate counts with Project Pulse or export support
- Bundle readback expansion with list/search/UI semantics
- Add chat/worker hooks without recognizing the contract gate stack

This document is a map of what is proven, what remains quarantined, and which surfaces are explicitly not part of the release promise.

## Non-Goals

This document does not, and must not be interpreted as:

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
- implementing state/commit/link readback
- exposing raw packet payloads
- implementing shared/dyadic reality runtime
- widening the supported beta release promise

## Proof Chain Summary

| Artifact | Status | Proof Class | What It Proves | What It Does Not Prove |
|---|---|---|---|---|
| Phase A schema migration | Implemented | Live migration proof (clean-start + existing-instance upgrade) | 4 continuity tables exist in Postgres; indexes, constraints, insert/readback verified | Runtime writes, compiler persistence, export/restore |
| Persistence adapter | Implemented | Live Postgres tests (31 passed) | Adapter validates contracts, preserves provenance, enforces atomicity | Runtime call sites, auto-persistence |
| Explicit write-action service | Implemented | Live Postgres tests (23 passed) | 4 explicit write actions: stamp, compile+save, commit, link | Runtime call sites, auto-triggers |
| Runtime invocation boundary contract | Docs-only | Contract gate | Defines authorized caller surfaces; classifies 8 candidates; lists 13 forbidden paths | Runtime implementation |
| Write route implementation | Implemented | Test-covered | `POST /api/operator/continuity/reality-stamp` accepts explicit payload, writes 1 context packet, returns receipt | Supported beta exposure |
| Write route live proof | Proof artifact | Live Docker Compose + profile proof | Beta quarantine (404), test-profile exposure (200), auth, receipt shape, persistence, graph-off | Supported beta activation |
| Profile activation contract | Docs-only | Contract gate | Defines two-gate model (feature flag + profile manifest); preserves supported beta quarantine | Profile manifest changes |
| Test-only profile implementation | Implemented | Test-covered | `test-continuity` profile exposes `continuity_operator` surface key | Supported beta activation |
| Test-only profile live proof | Proof artifact | Live Docker Compose + profile proof | Beta still quarantined; test profile exposes route; flag gate works; auth works | Supported beta activation |
| Readback route contract | Docs-only | Contract gate | Defines exact-ID readback; no list/search/retrieval/writes/graph | Route implementation |
| Readback route implementation | Implemented | Test-covered | `GET /api/operator/continuity/context-packets/{id}` returns exact packet by ID | List/search APIs |
| Readback route live proof | Proof artifact | Live Docker Compose + profile proof | Beta quarantine, test exposure, write+readback loop, no-write readback | Supported beta activation |
| Diagnostics truth surface contract | Docs-only | Contract gate | Defines aggregate gate/count diagnostics; no raw payloads; hard-false flags | Route implementation |
| Diagnostics route implementation | Implemented | Test-covered | `GET /api/operator/continuity/diagnostics` returns aggregate counts and posture | Project Pulse |
| Diagnostics route live proof | Proof artifact | Live Docker Compose + profile proof | Beta quarantine, test exposure, counts correct, no raw payloads, hard-false flags, no-write | Supported beta activation |

## Current Proven Operator Triad

| Property | Write | Readback | Diagnostics |
|---|---|---|---|
| **Path** | `POST .../reality-stamp` | `GET .../context-packets/{id}` | `GET .../diagnostics` |
| **Surface key** | `continuity_operator` | `continuity_operator` | `continuity_operator` |
| **Profile** | `test-continuity` only | `test-continuity` only | `test-continuity` only |
| **Feature flag** | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` | Same | Same |
| **Auth** | `require_api_key` | `require_api_key` | `require_api_key` |
| **Writes?** | Yes — 1 context packet | No | No |
| **Reads?** | No | Yes — 1 exact packet by ID | Yes — aggregate counts only |
| **Payload exposure** | N/A (writes) | Full packet payload by explicit ID | None — counts only |
| **`graph_used`** | `false` | `false` | `false` |
| **`runtime_event_published`** | `false` | `false` | `false` |
| **`project_pulse_enabled`** | N/A | N/A | `false` |
| **`export_restore_enabled`** | N/A | N/A | `false` |

## Gate Model

The operator triad is protected by a stack of independent gates. Passing one does not imply passing all.

| Gate | Current State |
|---|---|
| Route registration | Passed — `_include_router()` in `guardian_api.py` |
| Route surface key | `continuity_operator` — shared by all three routes |
| Supported profile manifest | **Quarantined** for `v1-local-core-web-mcp`; **enabled** for `test-continuity` |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` required for all three routes |
| API key auth | `require_api_key` — unauthenticated requests fail |
| Explicit request shape | Pydantic models validate input; write-action service validates contracts |
| Postgres persistence | Phase A tables exist; adapter validates before write; adapter reads with `deleted_at IS NULL` |

## Supported Beta Boundary

- `v1-local-core-web-mcp` remains quarantined for all three operator routes.
- All three routes were proven as **404** under `v1-local-core-web-mcp` with `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`.
- The supported beta profile manifest has not been modified for continuity routes.
- This proof chain does not widen the release promise.
- `docs/architecture/00-current-state.md` remains the short-horizon release-truth authority.

## Test-Only Profile Boundary

- `test-continuity` exposes all three operator routes under the `continuity_operator` surface key.
- Exposure requires `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`.
- Routes require API key authentication.
- This is test/local-proof-only.
- This is not user-facing production activation.
- The profile manifest was derived from `v1-local-core-web-mcp` with exactly one change: `continuity_operator` added to `enabled` routes.

## Hard-False Runtime Flags

These flags are explicitly set to `false` in all route responses and must remain `false` unless separately approved:

| Flag | Set To | Applicable Routes | What It Proves |
|---|---|---|---|
| `graph_used` | `false` | Write receipt, readback response, diagnostics response | No Neo4j reads or writes occur |
| `runtime_event_published` | `false` | Write receipt, readback response, diagnostics response | No task events are published |
| `project_pulse_enabled` | `false` | Diagnostics response only | Project Pulse does not exist |
| `export_restore_enabled` | `false` | Diagnostics response only | Continuity export/restore does not exist |

## No-Ambient Invocation Boundary

The following invocation paths are confirmed absent:

- No chat route (`guardian/routes/chat.py`) calls `ContinuityWriteActionService` or continuity persistence
- No worker process (`guardian/workers/`) calls continuity modules
- No command bus invokes continuity writes or reads
- No `compile_reality_state` output is automatically persisted
- No provider routing or retrieval path invokes continuity
- No browser capture invokes continuity
- No export/restore path includes continuity records
- Call-site audit confirms `ContinuityWriteActionService` appears only in `write_actions.py`, `continuity_operator.py`, `__init__.py`, and tests

## Data Exposure Boundary

| Surface | What It Exposes | What It Must Not Expose |
|---|---|---|
| Write receipt | Action IDs, created IDs, success flags | Raw packet payloads, secrets, graph IDs |
| Readback | Exact packet by explicit ID — full payload, provenance, metadata | Multiple packets, search results, list output |
| Diagnostics | Aggregate counts, gate posture, hard-false flags, last-created timestamp | Raw packet payloads, raw provenance arrays, packet ID lists, secrets |

Local DB IDs are not portable export identity. Continuity data is not currently included in account export/restore.

## Release Claim Boundary

- Test-only profile proof is not supported beta release support.
- Route presence in a profile is not release support.
- Docs-only contracts are not runtime proof.
- Live proof is scoped to the tested profile, commands, and environment.
- No public or user-facing continuity feature is claimed.
- `00-current-state.md` remains the authoritative source for what is supported.

## Failure Modes Prevented

| Failure Mode | Prevention |
|---|---|
| Confusing feature flag with profile activation | Two-gate model explicitly documented |
| Treating route presence as beta support | Supported beta boundary explicitly documented |
| Treating diagnostics as Project Pulse | `project_pulse_enabled=false` flag + explicit boundary |
| Treating diagnostics counts as export manifests | `export_restore_enabled=false` flag + explicit boundary |
| Treating readback as list/search | `readback_mode="exact_context_packet_id"` |
| Treating graph-off proof as graph support | `graph_used=false` in all responses |
| Treating Postgres proof as export/restore proof | `export_restore_enabled=false` flag |
| Adding chat/worker hooks without new contract | No-ambient invocation boundary documented |

## Safe Next Task Options

**Allowed:**
- Docs-only contract for future state/commit/link readback
- README refinement or proof-chain index entry
- Live regression proof rerun for the operator triad
- Narrow test additions if a missing invariant is found

**Forbidden bundles:**
- Do not combine state/commit/link readback with UI
- Do not combine diagnostics with Project Pulse
- Do not combine supported beta activation with new semantics
- Do not combine export/restore inclusion with operator diagnostics
- Do not add chat/worker hooks without a separate architecture-impact contract

## Relationship to Existing Contracts

This proof chain is the consolidation artifact for the operator loop. It references:

- **ADR-030** — overall continuity runtime gate
- **ADR-031** — Phase A storage migration gate
- **`continuity-write-action-contract.md`** — write action definitions
- **`continuity-runtime-invocation-boundary-contract.md`** — caller surface definitions
- **`continuity-operator-route-profile-activation-contract.md`** — profile activation gate
- **`continuity-operator-readback-route-contract.md`** — readback contract
- **`continuity-operator-diagnostics-truth-surface-contract.md`** — diagnostics contract
- **4 live proof artifacts** — operator route, test profile, readback, diagnostics
- **`continuity-persistence-adapter-contract.md`** — adapter contract
- **`config-and-ops.md`**, **`data-and-storage.md`**, **`account-export-restore-contract.md`** — operational contracts
- **`guardian/routes/continuity_operator.py`** — implemented route module

## Acceptance Checklist

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No route has been implemented.
- [ ] No profile manifest has been updated.
- [ ] Supported beta quarantine is preserved.
- [ ] Test-only profile boundary is explicit.
- [ ] Proof chain table is complete (15 rows).
- [ ] Operator triad route paths are listed with all properties.
- [ ] Gate model is explicit (7 gates).
- [ ] No-ambient invocation boundary is explicit.
- [ ] Data exposure boundary is explicit.
- [ ] Release claim boundary is explicit.
- [ ] Failure modes prevented are listed (8 modes).
- [ ] Safe next task options are listed (4 allowed, 5 forbidden bundles).
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
