# Continuity Operator Phase Explainer

**For:** Resonant Jones, Zac, future collaborators, and future agents  
**Date:** 2026-06-25  
**Status:** Phase complete — test-only, quarantined  

## Purpose

This document explains the completed Continuity operator phase in plain language. It is meant for humans, not only automation agents. It summarizes what actually exists, what was proven, and what remains deliberately unfinished. It does not define new architecture or runtime behavior.

## Executive Summary

Codexify now has a **six-route test-only Continuity operator surface**. An operator can:

- Explicitly write a Reality Stamp (a context packet with scope, source, payload, and provenance)
- Read back exact context packets, reality states, reality commits, and state-packet links by ID
- View aggregate diagnostics (row counts, gate posture, hard-false flags)

All six routes are gated behind a profile quarantine, a feature flag, and API-key authentication. They work under the `test-continuity` profile but are explicitly quarantined from the supported beta profile `v1-local-core-web-mcp`.

This is not a user-facing product feature. It is an operator-controlled, auditable continuity substrate that proves the Continuity Protocol Suite architecture can be realized in running code — without making unsafe release claims.

## What Was Actually Built

The work proceeded in staged, independently provable slices:

1. **Phase A storage** — Four Postgres tables for context packets, reality states, reality commits, and state-packet links. Live-proven with clean-start and existing-instance migration proof.

2. **Persistence adapter** — An explicit SQLAlchemy session seam that validates contracts before writes, preserves provenance, and enforces transaction atomicity. Not wired into runtime.

3. **Explicit write-action service** — Four named write actions (`create_reality_stamp`, `compile_and_save`, `create_reality_commit`, `link_state_to_packets`). Requires explicit input and an explicit adapter. No automatic or ambient writes.

4. **Developer/operator routes** — Six FastAPI routes under `POST /api/operator/continuity/*` and `GET /api/operator/continuity/*`. All share the `continuity_operator` surface key, require `require_api_key`, and are gated by `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES`.

5. **Profile quarantine** — The supported beta profile `v1-local-core-web-mcp` quarantines all operator routes. A separate tested profile `test-continuity` exposes them. Activation requires both the feature flag and the profile manifest — one alone is insufficient.

6. **Regression guardrails and documentation** — A dedicated regression test file pins the surface. Six live proof artifacts, a proof-chain map, a current-state anchor update, a documentation alignment audit, a milestone handoff, and a hardening regression rerun complete the documentation loop.

## The Six Routes

| Route | Method | Purpose | Reads/Writes | Payload Boundary | Proven? | Supported Beta? |
|---|---|---|---|---|---|---|
| `/api/operator/continuity/reality-stamp` | POST | Write one context packet | Writes 1 packet | N/A (writes) | ✅ | ❌ Quarantined |
| `/api/operator/continuity/context-packets/{id}` | GET | Read one packet by ID | Reads 1 packet | Full packet by explicit ID | ✅ | ❌ Quarantined |
| `/api/operator/continuity/diagnostics` | GET | Aggregate gate/count truth | Reads 4 table counts | Counts only; no raw payloads | ✅ | ❌ Quarantined |
| `/api/operator/continuity/reality-states/{id}` | GET | Read one state by ID | Reads 1 state | Full state by explicit ID; no source packet expansion | ✅ | ❌ Quarantined |
| `/api/operator/continuity/reality-commits/{id}` | GET | Read one commit by ID | Reads 1 commit | Commit record only; no history traversal | ✅ | ❌ Quarantined |
| `/api/operator/continuity/state-packet-links/{id}` | GET | Read one link by ID | Reads 1 link | Link record only; no state/packet expansion | ✅ | ❌ Quarantined |

Missing records return HTTP 200 with `found=false`. All routes return `graph_used=false` and `runtime_event_published=false`.

## What This Means Conceptually

Codexify can now create and inspect a bounded continuity substrate under explicit operator control.

- **Reality Stamp** is an explicit write — an operator says "capture this." It is not ambient memory, not automatic chat-turn logging, not model inference bleed.
- **State, commit, and link readbacks** are exact-ID inspection tools. They let an operator verify what was stored. They are not retrieval, not search, not graph traversal.
- **Diagnostics** is aggregate operator truth — how many packets exist, what profile is active, whether the feature flag is on. It is not Project Pulse. It does not summarize work. It does not suggest actions.
- **Profile quarantine** means the supported beta install path cannot accidentally expose these routes. They require an intentional operator to choose a test profile and set a feature flag.

This gives Codexify an auditable continuity skeleton — real, tested, proven against live Postgres — without making it user-facing or autonomous.

## What This Does Not Mean

- ❌ Not supported beta behavior
- ❌ Not user-facing UI
- ❌ Not Project Pulse
- ❌ Not export/restore continuity inclusion
- ❌ Not graph support (Neo4j optional, not used)
- ❌ Not list/search continuity
- ❌ Not relationship traversal
- ❌ Not chat runtime continuity
- ❌ Not worker integration
- ❌ Not command bus integration
- ❌ Not provider or retrieval integration
- ❌ Not browser capture
- ❌ Not sync
- ❌ Not shared/dyadic reality runtime

## Gate Stack

To use the operator surface, all of these must be true:

- `continuity_operator` route surface key must be registered (it is)
- Active profile must be `test-continuity` (not `v1-local-core-web-mcp`)
- `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` must be `true`
- API key must be valid (`require_api_key`)
- Request shape must pass explicit validation
- Supported beta profile `v1-local-core-web-mcp` **cannot** activate the routes — they return **404**

## Data Boundaries

| Readback | Exposes | Does NOT Expose |
|---|---|---|
| Packet readback | One exact packet by ID | Multiple packets, search results |
| State readback | One exact stored state by ID | Source packet payloads |
| Commit readback | One exact stored commit by ID | State history, full state payload |
| Link readback | One exact stored link by ID | State payload, packet payload, neighboring links |
| Diagnostics | Aggregate counts only | Raw payloads, ID lists, secrets |

No route lists, searches, traverses relationships, or expands related records by default. Local DB IDs are not portable export identity.

## Proof and Guardrails

- **6 live proof artifacts** — each route proven against live Docker Compose + Postgres
- **1 regression guardrail** — `tests/continuity/test_continuity_operator_six_route_surface.py` (16 tests)
- **1 hardening rerun** — all suites pass, zero surface expansion detected
- **1 proof-chain doc** — `continuity-operator-loop-proof-chain.md` maps all 23+ evidence rows
- **1 current-state update** — `00-current-state.md` acknowledges the test-only quarantined surface
- **1 alignment audit** — all truth surfaces confirmed aligned (PASS)
- **1 milestone handoff** — HANDOFF COMPLETE with safe next work guidance

## Why This Phase Matters

- It makes Continuity concrete without making unsafe release claims. The code exists. The tests pass. The proofs are recorded. But the surface is quarantined — it cannot be accidentally activated in a supported beta install.
- It gives future surfaces something real to build from. Project Pulse can query real Postgres tables. Export/restore can include real continuity families. List/search can operate over real records.
- It separates explicit operator writes from ambient runtime behavior. No chat turn, heartbeat, or retrieval path writes continuity. Only an explicit operator action does.
- It establishes a pattern: contract → implementation → live proof → regression guardrail → documentation closure. Future phases can follow the same rhythm.
- It reduces ambiguity for collaborators. A new engineer reading the proof chain knows what exists, what is proven, and where the hard boundaries are.

## Why The Phase Stops Here

The surface is complete for its defined scope. Adding more would cross into new semantics:

- **More routes** would be new semantic surfaces (list/search, relationship traversal)
- **Supported beta activation** would be a release decision, not an implementation task
- **Project Pulse** would be a new operator-visible interpretation layer — summarizing state, suggesting actions, rendering UI
- **Export/restore inclusion** would be a portability and lineage contract — affecting what users can carry between instances
- **Chat/worker/browser integrations** would change runtime behavior — ambient writes, heartbeat triggers, browser capture

Each of these must be its own architecture-impact task with a separate contract. None can be bundled into the current operator phase.

## Unfinished Codexify Work This Reveals

The completed operator phase makes the following unfinished lanes more visible. None are selected — each would be a separate architecture-impact decision.

| Lane | Why It Matters | Why Not Done | Contract Needed |
|---|---|---|---|
| Export/restore continuity inclusion | Users should be able to export and restore continuity state alongside chat history | Requires manifest schema, family-level export policy, restore ID remapping | Export/restore continuity inclusion contract |
| Project Pulse | Operators and users should see a "where was I?" brief compiled from continuity state | Requires UI spec, accessibility review, read model, diagnostic boundary | Project Pulse UI contract |
| List/search or discovery surface | Operators need to find records without knowing exact IDs | Currently only exact-ID readback exists; list/search is new semantics | List/search contract |
| Supported beta activation | The operator surface could be exposed in the supported beta install | Release decision; requires current-state update, ADR, release scope change | Supported beta activation contract |
| User-facing UI | Operators could use a visual interface instead of HTTP | Requires frontend development, accessibility, token/layout law | UI contract |
| Graph mount | Neo4j could enrich continuity with relationship visualization | Graph remains optional; must not become required for baseline | Graph mount contract |
| Browser context provider | Browser activity could feed context packets | Requires consent architecture, scope controls, user visibility | Browser context contract |
| Chat runtime integration | Chat turns could populate context packets | Would create ambient writes — must be explicit-action, not automatic | Chat continuity contract |
| Worker/command bus integration | Heartbeat or scheduled writes, tool-execution writes | Requires worker infrastructure, command bus policy | Worker/command bus contract |
| Collaborator onboarding | New team members need to understand the surface quickly | Requires docs that are human-readable, not just architecture contracts | This explainer begins that work |

## Suggested Reading Order

**For a human collaborator:**
1. This explainer
2. `00-current-state.md` — the release-truth anchor
3. `continuity-operator-six-route-milestone-handoff.md` — what was completed
4. `continuity-operator-loop-proof-chain.md` — the evidence map
5. `continuity-operator-documentation-alignment-audit.md` — only if you need to verify consistency

**For a coding agent:**
1. `00-current-state.md`
2. `adr/030-continuity-protocol-suite-runtime-gate.md` — the overall gate
3. `adr/031-continuity-phase-a-storage-migration-gate.md` — the storage gate
4. `continuity-write-action-contract.md` — what write actions are allowed
5. `continuity-operator-readback-route-contract.md` — packet readback rules
6. `continuity-operator-state-commit-link-readback-contract.md` — staged readback rules
7. `continuity-operator-loop-proof-chain.md` — full evidence chain
8. `continuity-operator-six-route-milestone-handoff.md` — handoff record
9. `guardian/routes/continuity_operator.py` — the implemented routes
10. `tests/continuity/test_continuity_operator_six_route_surface.py` — the regression guardrail

## Safe Next Moves

Each must be its own architecture-impact task. Do not combine.

- **Pause and harden** — rerun the regression suite, add narrow missing-invariant tests
- **Create a narrative build log** — a chronological record of the phase for Zac and collaborators
- **Create an export/restore continuity inclusion contract** — define manifest families, lineage preservation, ID remapping
- **Create a Project Pulse contract** — define the brief surface, UI token law, diagnostics boundary
- **Create a list/search contract** — define query semantics without becoming retrieval or graph traversal
- **Create a supported beta activation contract** — define when and how the operator surface could enter the supported beta path
- **Create Zac onboarding documentation** — if Zac is joining the work, how does he orient?

## Forbidden Bundles

- Do not combine list/search with UI
- Do not combine diagnostics with Project Pulse
- Do not combine supported beta activation with new semantics
- Do not combine export/restore inclusion with operator diagnostics
- Do not add chat/worker hooks without a separate architecture-impact contract
- Do not treat exact readback as relationship traversal
- Do not treat route presence as release support

## Source Map

- `docs/architecture/00-current-state.md` — release-truth anchor
- `docs/architecture/continuity-operator-loop-proof-chain.md` — full evidence chain
- `docs/architecture/2026-06-25-continuity-operator-six-route-milestone-handoff.md` — handoff record
- `docs/architecture/2026-06-25-continuity-operator-six-route-hardening-regression-rerun.md` — hardening rerun
- `docs/architecture/2026-06-25-continuity-operator-documentation-alignment-audit.md` — alignment audit
- `tests/continuity/test_continuity_operator_six_route_surface.py` — regression guardrail
- `guardian/routes/continuity_operator.py` — implemented routes
- `config/supported_profiles/test-continuity.yaml` — test profile (exposes operator surface)
- `config/supported_profiles/v1-local-core-web-mcp.yaml` — supported beta profile (quarantines operator surface)

## Bottom Line

The Continuity operator phase is complete as a test-only, quarantined, operator-controlled substrate. It is **not** a product feature yet. It proves the architecture works in running code. Future work should proceed by choosing one next semantic surface and writing a separate architecture-impact contract.

**The cathedral holds. The gates are locked. The map is drawn. 🏛️**
