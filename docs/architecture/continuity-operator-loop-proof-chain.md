# Continuity Operator Loop Proof Chain

> Classification: docs-only proof-chain consolidation
> Status: current
> Implementation status: six-route operator surface exists and is live-proven under test-only profile; supported beta remains quarantined
> Normative language: "is", "remains", "proven", "quarantined", and "deferred" are intentional.

Purpose: Consolidate the proven six-route Continuity operator surface into one reviewable proof-chain artifact. This is a map of proven evidence, not a new capability claim. It does not activate routes, implement code, or widen the supported beta release promise.

Last updated: 2026-06-25

## Purpose

The Continuity operator surface has grown from the initial triad (write, packet readback, diagnostics) to a full six-route surface including the completed staged state/commit/link readback. Without an updated proof-chain artifact, future agents could:

- Confuse the expanded test-only surface with supported beta release support
- Treat a docs-only contract as implying implemented runtime behavior
- Add list/search/traversal semantics without recognizing the contract gate stack
- Bundle future work without understanding which surfaces are already proven and which are deferred

This document is a map of what is proven, what remains quarantined, and which surfaces are explicitly not part of the release promise.

## Current Six-Route Operator Surface

| Route | Purpose | Reads/Writes | Profile | Auth | Payload Exposure | Proof Artifact |
|---|---|---|---|---|---|---|
| `POST .../reality-stamp` | Write one context packet | Writes 1 packet | `test-continuity` only | API key | N/A (writes) | operator-route-live-proof |
| `GET .../context-packets/{id}` | Read one packet by ID | Reads 1 packet | `test-continuity` only | API key | Full packet by explicit ID | operator-readback-route-live-proof |
| `GET .../diagnostics` | Aggregate gate/count truth | Reads 4 table counts | `test-continuity` only | API key | Counts only, no raw payloads | operator-diagnostics-route-live-proof |
| `GET .../reality-states/{id}` | Read one state by ID | Reads 1 state | `test-continuity` only | API key | Full state by explicit ID; no source packet expansion | reality-state-readback-route-live-proof |
| `GET .../reality-commits/{id}` | Read one commit by ID | Reads 1 commit | `test-continuity` only | API key | Commit record only; no history traversal | reality-commit-readback-route-live-proof |
| `GET .../state-packet-links/{id}` | Read one link by ID | Reads 1 link | `test-continuity` only | API key | Link record only; no state/packet expansion | state-packet-link-readback-route-live-proof |

All six routes share the `continuity_operator` surface key, `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` flag, and `require_api_key` auth. All six return 404 under `v1-local-core-web-mcp`. Missing records return HTTP 200 with `found=false`.

## Proof Chain Summary

| Artifact | Status | Proof Class | What It Proves | What It Does Not Prove |
|---|---|---|---|---|
| Phase A schema migration | Implemented | Live migration proof | 4 continuity tables exist; indexes, constraints verified | Runtime writes, compiler persistence |
| Persistence adapter | Implemented | Live Postgres tests | Adapter validates, preserves provenance, enforces atomicity | Runtime call sites |
| Explicit write-action service | Implemented | Live Postgres tests | 4 explicit write actions | Runtime call sites, auto-triggers |
| Runtime invocation boundary contract | Docs-only | Contract gate | Defines authorized caller surfaces; 13 forbidden paths | Runtime implementation |
| Write route implementation | Implemented | Test-covered | Explicit stamp write with receipt | Supported beta exposure |
| Write route live proof | Proof artifact | Live Docker + profile | Beta quarantine (404), test exposure (200), auth, receipt | Supported beta activation |
| Profile activation contract | Docs-only | Contract gate | Two-gate model (flag + profile); supported beta quarantine | Profile manifest changes |
| Test-only profile implementation | Implemented | Test-covered | `test-continuity` exposes `continuity_operator` | Supported beta activation |
| Test-only profile live proof | Proof artifact | Live Docker + profile | Beta still quarantined; test profile + flag expose route | Supported beta activation |
| Packet readback contract | Docs-only | Contract gate | Exact-ID readback; no list/search/writes/graph | Route implementation |
| Packet readback implementation | Implemented | Test-covered | Exact packet by ID, found/missing, no-write | List/search APIs |
| Packet readback live proof | Proof artifact | Live Docker + profile | Beta quarantine, test exposure, write+read loop | Supported beta activation |
| Diagnostics contract | Docs-only | Contract gate | Aggregate counts; no raw payloads; hard-false flags | Route implementation |
| Diagnostics implementation | Implemented | Test-covered | Aggregate counts + gate posture | Project Pulse |
| Diagnostics live proof | Proof artifact | Live Docker + profile | Beta quarantine, counts correct, hard-false flags | Supported beta activation |
| State/commit/link readback contract | Docs-only | Contract gate | Staged exact-ID readback; response contracts; no expansion | Route implementation |
| State readback implementation | Implemented | Test-covered | Exact state by ID; no packet expansion | List/search, compilation |
| State readback live proof | Proof artifact | Live Docker + profile | Beta quarantine, state round-trip, hard-false flags | Supported beta activation |
| Commit readback implementation | Implemented | Test-covered | Exact commit by ID; no history traversal | List/search, history expansion |
| Commit readback live proof | Proof artifact | Live Docker + profile | Beta quarantine, commit round-trip, hard-false flags | Supported beta activation |
| Link readback implementation | Implemented | Test-covered | Exact link by ID; no state/packet expansion | List/search, traversal |
| Link readback live proof | Proof artifact | Live Docker + profile | Beta quarantine, link round-trip, hard-false flags | Supported beta activation |

## Gate Model

All six routes are protected by a stack of independent gates:

| Gate | Current State |
|---|---|
| Route registration | `_include_router()` in `guardian_api.py` |
| Route surface key | `continuity_operator` — shared by all six routes |
| Supported profile manifest | **Quarantined** for `v1-local-core-web-mcp`; **enabled** for `test-continuity` |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` required |
| API key auth | `require_api_key` — unauthenticated requests fail |
| Explicit request shape | Pydantic models validate input; write-action service validates contracts |
| Postgres persistence | Phase A tables exist; adapter validates before write; reads use `deleted_at IS NULL` |

## Supported Beta Boundary

- `v1-local-core-web-mcp` remains quarantined for all six operator routes.
- All six routes were proven as **404** under `v1-local-core-web-mcp`.
- The supported beta profile manifest has not been modified.
- This proof chain does not widen the release promise.
- `00-current-state.md` remains authoritative.

## Test-Only Profile Boundary

- `test-continuity` exposes all six operator routes under `continuity_operator`.
- Requires `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`.
- All routes require API key authentication.
- Test/local-proof-only. Not production activation.

## Hard-False Runtime Flags

| Flag | Set To | Applicable Routes |
|---|---|---|
| `graph_used` | `false` | All six routes |
| `runtime_event_published` | `false` | All six routes |
| `project_pulse_enabled` | `false` | Diagnostics route |
| `export_restore_enabled` | `false` | Diagnostics route |

## No-Ambient Invocation Boundary

Confirmed absent: chat routes, workers, command bus, compiler auto-persistence, provider/retrieval, browser, export/restore call sites.

## Data Exposure Boundary

| Readback | What It Exposes | What It Must Not |
|---|---|---|
| Packet | Full packet by explicit ID | Multiple packets, search results |
| State | Full state by explicit ID | Source packet payloads |
| Commit | Full commit by explicit ID | State history, state payload |
| Link | Link record by explicit ID | State payload, packet payload, neighboring links |
| Diagnostics | Aggregate counts only | Raw payloads, ID lists, secrets |

## Staged Readback Completion

The three-stage readback contract (`continuity-operator-state-commit-link-readback-contract.md`) is now fully implemented:

1. ✅ State readback — implemented and live-proven
2. ✅ Commit readback — implemented and live-proven
3. ✅ Link readback — implemented and live-proven

No list/search, relationship traversal, or payload expansion semantics were added.

## Release Claim Boundary

- Test-only proof is not supported beta support.
- Route presence is not release support.
- Docs-only contracts are not runtime proof.
- Live proof is scoped to tested profile, commands, and environment.
- No public or user-facing continuity feature is claimed.

## Failure Modes Prevented

| Mode | Prevention |
|---|---|
| Confusing flag with profile activation | Two-gate model |
| Route presence as beta support | Supported beta boundary |
| Diagnostics as Project Pulse | `project_pulse_enabled=false` |
| Diagnostics as export | `export_restore_enabled=false` |
| Exact readback as list/search | `readback_mode` + exact-ID-only semantics |
| State readback as compiler | No `compile_reality_state` calls |
| Commit readback as history | No commit chain traversal |
| Link readback as graph traversal | No relationship expansion |
| Graph-off as graph support | `graph_used=false` |
| Postgres proof as export proof | `export_restore_enabled=false` |
| Chat/worker hooks without contract | No-ambient invocation boundary |

## Safe Next Task Options

**Allowed:**
- Docs-only contracts for deferred surfaces (list/search, Project Pulse, export/restore)
- Live regression proof rerun for all six routes
- Narrow missing-invariant test additions
- Proof-chain README indexing refinement

**Forbidden bundles:**
- Do not combine list/search with UI
- Do not combine diagnostics with Project Pulse
- Do not combine beta activation with new semantics
- Do not combine export/restore with operator diagnostics
- Do not add chat/worker hooks without architecture-impact contract
- Do not treat exact readback as relationship traversal

## Relationship to Existing Contracts

- **ADR-030, ADR-031** — runtime and migration gates
- **`continuity-storage-schema-proposal.md`** — table definitions
- **`continuity-persistence-adapter-contract.md`** — adapter contract
- **`continuity-write-action-contract.md`** — write action definitions
- **`continuity-runtime-invocation-boundary-contract.md`** — caller surface definitions
- **`continuity-operator-route-profile-activation-contract.md`** — profile activation gate
- **`continuity-operator-readback-route-contract.md`** — packet readback contract
- **`continuity-operator-diagnostics-truth-surface-contract.md`** — diagnostics contract
- **`continuity-operator-state-commit-link-readback-contract.md`** — staged readback contract
- **6 live proof artifacts** — all six routes live-proven
- **`config-and-ops.md`, `data-and-storage.md`, `account-export-restore-contract.md`** — operational contracts
- **`guardian/routes/continuity_operator.py`** — implemented route module

## Acceptance Checklist

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No route has been implemented.
- [ ] No profile manifest has been updated.
- [ ] Supported beta quarantine is preserved.
- [ ] Test-only profile boundary is explicit.
- [ ] All six route paths are listed.
- [ ] All six live proofs are referenced.
- [ ] Gate model is explicit.
- [ ] Staged readback completion is explicit.
- [ ] No-ambient invocation boundary is explicit.
- [ ] Data exposure boundary is explicit.
- [ ] No list/search semantics claimed.
- [ ] No traversal semantics claimed.
- [ ] No Project Pulse semantics claimed.
- [ ] No export/restore semantics claimed.
- [ ] Release claim boundary is explicit.
- [ ] Safe next task options are updated.
- [ ] Forbidden bundled next steps are updated.
- [ ] `00-current-state.md` remains authoritative.
