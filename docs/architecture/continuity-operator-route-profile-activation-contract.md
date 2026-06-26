# Continuity Operator Route Profile Activation Contract

> Classification: docs-only profile activation contract  
> Status: proposed  
> Implementation status: no profile manifests changed, no route activated, no runtime behavior altered  
> Normative language: "must", "must not", "should", "quarantined", "deferred", "forbidden", and "future" are intentional.

Purpose: Define the activation boundary for the developer/operator continuity write route after live proof discovered the route is profile-quarantined by the supported profile manifest. The goal is to prevent accidental promotion of the route into the supported beta surface. This is a docs-only contract. It does not activate the route, update any profile manifest, or change runtime behavior.

Last updated: 2026-06-25

## Purpose

The continuity operator route (`POST /api/operator/continuity/reality-stamp`) exists, is tested, and is live-proofed. But the live proof (`2026-06-25-continuity-operator-route-live-proof.md`) discovered an additional defense layer: the supported profile manifest (`v1-local-core-web-mcp`) quarantines the route. Even setting `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` is not sufficient — the profile must also accept the route.

This is architecturally correct and must be preserved as doctrine. Without a profile activation contract, a future task could:

- Edit the profile manifest to add the route without explicit review
- Accidentally expose continuity writes in the supported beta release
- Assume feature flag enablement equals route activation
- Bundle profile activation with UI, worker, or chat-hook work
- Fail to verify that the route remains disabled in other profiles

This contract defines the gate between "the route exists" and "the route is exposed in a profile." It establishes that:

1. Feature flags and profile manifests are **separate gates**
2. Profile quarantine is **intentional safety behavior**
3. Activation in any profile requires **explicit, reviewable proof**
4. The supported beta profile must **not** expose the route unless separately approved

## Non-Goals

This contract does not, and must not be interpreted as:

- updating any profile manifest
- activating the route in any profile
- changing runtime behavior
- adding UI
- adding a worker
- adding command bus integration
- wiring chat-turn hooks
- enabling compiler auto-persistence
- implementing browser capture
- enabling graph writes
- implementing sync behavior
- implementing export/restore inclusion
- implementing Project Pulse
- implementing shared/dyadic reality runtime
- widening the supported beta release promise

## Current Route State

| Property | Value |
|---|---|
| Route path | `POST /api/operator/continuity/reality-stamp` |
| Route module | `guardian/routes/continuity_operator.py` |
| Registration file | `guardian/guardian_api.py` |
| Feature flag | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` |
| Default enabled | `False` (`default_enabled=False`, `core_surface=False`) |
| Auth dependency | `require_api_key` (existing backend API key) |
| Supported profile | `v1-local-core-web-mcp` |
| Profile status | **Quarantined** (non-core, default-disabled routes are excluded) |
| Live proof outcome | PASS — 404 when disabled; zero ambient writes; 166 focused tests pass |
| Ambient writes | Zero call sites outside approved modules |
| Action kind invoked | `create_reality_stamp` only |

## Two-Gate Activation Model

The continuity operator route is protected by five independent gates. All must pass before the route may write:

### Gate 1: Code-Level Registration

The route must be registered in `guardian/guardian_api.py` via `_include_router()`. This gate is already passed — the route module exists and is imported.

### Gate 2: Feature Flag Gate

The environment variable `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` must be `true`. This gate is separate from the profile gate. A future activation task must verify that setting the flag to `false` disables the route even if the profile accepts it.

### Gate 3: Profile Manifest Gate

The active supported profile manifest must **not** quarantine the route. The `_include_router()` function checks the profile's `route_status(label)` before evaluating the feature flag. If `route_status` returns `"quarantined"`, the route is excluded regardless of the flag. This is the current state.

### Gate 4: Auth/Session Gate

The route requires `require_api_key`. Unauthenticated requests must fail regardless of all other gates. This gate is implemented and tested.

### Gate 5: Explicit Request/Action Gate

The route accepts only explicit `RealityStampRequest` payloads. The write-action service validates the input and rejects invalid candidates. This gate is implemented and tested.

**Current gate status:**

| Gate | Passed? |
|---|---|
| Code-level registration | Yes |
| Feature flag | Conditional (set to `true` by operator) |
| Profile manifest | **No — quarantined** |
| Auth/session | Yes |
| Explicit request/action | Yes |

The profile manifest gate is the single remaining closed gate for this route.

## Profile Quarantine Principle

Profile quarantine is intentional safety behavior. The following principles govern it:

1. **Supported beta profiles must not expose continuity writes by accident.** The `v1-local-core-web-mcp` profile is the current supported beta surface. Adding continuity writes to it would alter the release promise and operator-visible surface.

2. **Non-core, default-disabled routes must remain quarantined** unless a future task explicitly promotes them with a profile manifest update and a corresponding proof.

3. **Profile activation must be reviewable and testable.** Any profile manifest change must be accompanied by live HTTP proof, Postgres persistence verification, auth verification, and ambient write call-site audit.

4. **Profile activation must not be bundled** with UI, worker, chat-hook, graph, browser, sync, or export/restore work. Profile activation is a standalone, atomic change.

5. **Feature flag enablement alone must not be treated as route activation.** The presence of `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` in an environment does not imply the route is exposed. The profile gate is independent and must be verified separately.

## Candidate Activation Profiles

Future profile activation must choose a profile scope. The following are classified:

| Profile Scope | Status | Reason |
|---|---|---|
| **Supported beta profile** (`v1-local-core-web-mcp`) | **Forbidden for now** | Would widen the supported beta release promise. Requires current-state document update, ADR review, and explicit release approval. |
| **Test-only profile** | **Allowed candidate** | A profile that exists only for automated or manual testing. No release surface impact. The route can be exposed safely in test environments. |
| **Local developer/operator profile** | **Allowed candidate** | A profile for local development and operator use only. May coexist with the supported beta profile without widening release claims. |
| **Future advanced continuity profile** | **Deferred** | A profile that bundles multiple continuity surfaces (route, Project Pulse, compiler persistence, etc.). Requires proof of each bundled surface before activation. |
| **User-facing production profile** | **Deferred** | Requires UI, accessibility review, user consent, and Project Pulse integration. Premature for MVP. |

### Recommendation

- **Do not activate in the supported beta profile.** The route is intentionally excluded from the supported surface.
- **Prefer a test-only profile** if activation is needed for continued development and CI proof.
- **Or a local developer/operator profile** if the route needs to be exercised by operators during local development.
- **Defer production activation** until multiple continuity MVP surfaces are proven and a broader release ADR exists.

## Approved Next Activation Boundary

**Recommendation: Test-only profile activation.**

If the continuity developer/operator route needs to be reliably accessible for ongoing development, CI, and integration testing, the safest next step is a test-only profile activation. A test-only profile:

- Has zero release surface impact
- Does not widen the supported beta claim
- Can be scoped to test environments only
- Allows automated CI to exercise the full route → adapter → Postgres path without mocks

### Exact recommended activation category

- **Profile scope**: Test-only (`test-continuity` or equivalent)
- **What route path may be exposed**: `POST /api/operator/continuity/reality-stamp`
- **What auth must remain required**: API key (`require_api_key`)
- **What action kinds remain limited**: `create_reality_stamp` only
- **What runtime surfaces remain forbidden**: UI, worker, command bus, chat hooks, browser capture, graph writes, Project Pulse, sync, export/restore
- **What profile flag controls it**: `CODEXIFY_SUPPORTED_PROFILE=test-continuity` or equivalent

## Activation Requirements

A future profile activation task must prove all of the following before the manifest change is accepted:

| Requirement | Proof |
|---|---|
| Route remains disabled in supported beta profile | HTTP 404 from `POST /api/operator/continuity/reality-stamp` with `v1-local-core-web-mcp` |
| Route appears only in the chosen opt-in profile | HTTP 200 with correct receipt from `POST /api/operator/continuity/reality-stamp` with test profile |
| Feature flag must still gate the route | Setting `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=false` disables route in test profile |
| Unauthenticated requests fail | HTTP 401/403 from unauthenticated POST to route in test profile |
| Valid API-key request succeeds only in activated profile | HTTP 200 with receipt in test profile; HTTP 404 in supported beta profile |
| Explicit Reality Stamp writes exactly one context packet | `SELECT COUNT(*)` shows exactly 1 new `continuity_context_packets` row |
| No state/commit/link rows created by stamp route | `SELECT COUNT(*)` shows 0 new rows in other continuity tables |
| `graph_used` is `False` | Receipt field `graph_used` is `false` |
| `runtime_event_published` is `False` | Receipt field `runtime_event_published` is `false` |
| No ambient writes | Call-site audit confirms only approved modules invoke `ContinuityWriteActionService` |

## Auth and Operator Boundary

Regardless of profile, the route must preserve its auth boundary:

- Route must remain authenticated. Anonymous writes are forbidden.
- Actor ID must be explicit in the request payload. The route must not derive actor identity from the API key alone.
- Write-as-another-user remains forbidden unless a future delegation contract exists.
- `team`, `dyad`, `shared` semantics remain deferred.
- API-key auth is acceptable for developer/operator and test-only profiles. Stronger auth (e.g., session token, OAuth) may be required before user-facing activation.
- The API key must be the existing `GUARDIAN_API_KEY` or equivalent backend auth. No separate operator auth system is introduced by this route.

## Runtime Surface Boundary

Profile activation of the route does not authorize any other runtime surface:

| Surface | Authorized by profile activation? |
|---|---|
| UI | No — deferred |
| Worker invocation | No — deferred |
| Command bus integration | No — deferred |
| Chat-turn hooks | No — forbidden for MVP |
| Compiler auto-persistence | No — forbidden for MVP |
| Browser context capture | No — deferred |
| Graph writes | No — forbidden for MVP |
| Project Pulse | No — deferred |
| Sync protocol | No — deferred |
| Export/restore inclusion | No — deferred |
| Runtime event publication | No — forbidden for MVP |

Profile activation is exclusively about exposing the existing `POST /api/operator/continuity/reality-stamp` route in a chosen profile. It does not authorize any other continuity surface.

## Operator Truth Surface

A future activation proof must record the following operator-visible truth:

| Signal | Required Value |
|---|---|
| Profile name | Exact profile identifier (e.g., `test-continuity`) |
| Route registration state | Route registered and functional |
| Feature flag state | `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true` |
| Auth behavior | Unauthenticated → 401/403; authenticated → 200 |
| Receipt behavior | `success=True`, `action_kind=create_reality_stamp`, `graph_used=False`, `runtime_event_published=False` |
| Persistence verification | Exactly 1 context packet row; 0 state/commit/link rows |
| Graph usage | `False` — no Neo4j calls |
| Runtime event publication | `False` — no task events |
| Ambient write call-site audit | Only `write_actions.py`, `continuity_operator.py`, `__init__.py`, and tests |

## Failure Modes

The following failure modes must be prevented by the activation contract and any future activation task:

| Failure Mode | Prevention |
|---|---|
| Feature flag true but profile still quarantines route | Profile activation task must verify route actually responds; 404 during quarantine is correct |
| Profile exposes route while feature flag false | Activation tests must verify `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=false` disables route in test profile |
| Route exposed in supported beta profile accidentally | Supported beta profile tests must verify 404; profile manifest diff must show no change to `v1-local-core-web-mcp` |
| Unauthenticated writes succeed | Auth tests must verify 401/403 for missing/invalid API key |
| Route writes more than context packet | Persistence tests must verify zero state/commit/link rows |
| Route publishes runtime event | Receipt must have `runtime_event_published=False`; no task event in event stream |
| Route uses graph | Receipt must have `graph_used=False`; no Neo4j import |
| Route appears in OpenAPI when profile says quarantined | If OpenAPI visibility is trackable, quarantined routes must be excluded |
| Tests pass with mocks but live profile exposure fails | Live HTTP proof against running backend with activated profile is required |

## Required Tests for Future Profile Activation

When a profile activation task is implemented, the following tests must pass:

| Test | What It Proves |
|---|---|
| Supported beta profile → 404 | Quarantine preserved for `v1-local-core-web-mcp` |
| Test profile → 200 (valid request) | Route exposed in chosen profile |
| Test profile → 401/403 (no auth) | Auth boundary works in test profile |
| Test profile → 404 (flag off) | Feature flag still gates route in test profile |
| Explicit stamp persistence | Exactly 1 `continuity_context_packets` row; correct fields |
| Zero state/commit/link writes | 0 rows in other continuity tables |
| Receipt `graph_used=False` | No graph used |
| Receipt `runtime_event_published=False` | No events published |
| No ambient call sites | Only approved modules invoke `ContinuityWriteActionService` |
| OpenAPI visibility (if trackable) | Route absent from OpenAPI in quarantined profiles; present in activated profiles |

## Relationship to Existing Contracts

### ADR-030: Continuity Protocol Suite Runtime Gate

ADR-030 gates all continuity runtime work. This contract gates the profile activation of one specific route surface. It does not authorize broader runtime integration.

### ADR-031: Continuity Phase A Storage Migration Gate

ADR-031 gates schema migration and requires that runtime writes remain separately approved. Profile activation would expose a write route, but the write path (adapter, service, validation) is already proven. This contract is the separate approval required.

### continuity-write-action-contract.md

The write-action contract defines the four allowed MVP write actions. Profile activation exposes one action (`create_reality_stamp`) via one route surface.

### continuity-runtime-invocation-boundary-contract.md

The invocation boundary contract recommends `developer_operator_route` as the next caller. Profile activation does not add a new caller — it exposes the existing caller in a chosen profile.

### continuity-persistence-adapter-contract.md

The adapter contract defines the persistence seam. Profile activation does not change the adapter or add new write paths.

### 2026-06-25-continuity-operator-route-live-proof.md

The live proof discovered the profile quarantine. This contract codifies that discovery as doctrine and defines the gate for lifting the quarantine in a non-beta profile.

### config-and-ops.md

Profile activation uses `CODEXIFY_SUPPORTED_PROFILE` and `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES` — existing config surfaces. No new env vars are required.

### chat-runtime-contract.md

Profile activation does not change chat runtime states, request lifecycle states, or message/attempt identity.

### runtime-protocol-token-contract.md

No runtime events are approved. Profile activation does not change this.

### account-export-restore-contract.md

Profile activation does not implement export/restore inclusion.

### data-and-storage.md

Profile activation writes to Postgres only via the existing adapter path.

### guardian/routes/continuity_operator.py

The route module is unchanged by profile activation. Only the profile manifest changes.

### guardian/guardian_api.py

The route registration is unchanged by profile activation. The `_include_router()` function reads the profile manifest.

## Required Follow-Up Before Profile Activation

Before any profile manifest is changed, a future task must:

1. Identify the exact profile manifest file(s) to modify.
2. Choose test-only or local developer/operator activation scope.
3. Keep the supported beta profile (`v1-local-core-web-mcp`) disabled — no manifest changes to it.
4. Define feature flag behavior in the activated profile (must still require `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`).
5. Define OpenAPI visibility expectations (quarantined routes should be excluded; activated routes may be included).
6. Define auth proof: unauthenticated → 401/403, authenticated → 200.
7. Define live HTTP proof: real backend, real Postgres, real route.
8. Define Postgres persistence proof: exactly 1 context packet row, zero state/commit/link rows.
9. Define ambient write call-site audit: only approved modules.
10. Keep UI, browser, chat, worker, export, and sync modules out of scope. Do not bundle profile activation with any other surface.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No profile manifest has been edited.
- [ ] No route has been activated.
- [ ] The supported beta profile quarantine is preserved.
- [ ] The distinction between feature flag and profile manifest is explicit.
- [ ] The approved next activation boundary is explicit (test-only profile recommended).
- [ ] Auth/operator boundary is explicit.
- [ ] Forbidden runtime surfaces are explicit (10 surfaces).
- [ ] Failure modes are explicitly listed (9 modes).
- [ ] Required follow-up steps before profile activation are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
