# C04 Backlog: Pi/Coder Invocation Boundary

## Campaign

**C04: Pi/Coder Invocation Boundary**

## Campaign Objective

Define and implement a governed, bounded, operator-visible Pi/Coder invocation seam that carries Guardian authority, preserves lineage, enforces validation-only run mode, and does not imply autonomous delegation, Pi/Coder execution, recursive tool loops, artifact creation, receipt creation, or release widening.

## Status

**Gate**: `go` — Campaign active.

| Task | Domain | Gate | Commit | Summary |
|------|--------|------|--------|---------|
| C04-T001 | audit | `go` | `e4b68e685` | Seam audit — contracts, implementation, runtime proven/not-proven, risks, backlog |
| C04-T002 | docs | `go` | `875e5266c` | Acceptance contract — state model, 15 criteria, 18-row proof matrix, 13 shortcuts, 7 proof classes, failure/blocker rules |
| C04-T003 | docs | `go` | `9468eeacd` | Proof matrix — state ladder, 27-row core boundary matrix, 10-class evidence matrix, 15-condition gate matrix |
| C04-T004 | backend | `go` | `74e137511` | Contract gap repair — contracts + validation already existed; added 8 boundary tests (23 total) |
| C04-T005 | backend | `go` | `32b89df06` | Policy decision contract — PiInvocationPolicyDecision, validation helper, 21 tests (44 total) |
| C04-T006 | backend | `go` | `c4e63a55f` | Result return contract — PiInvocationResultReturn, validation helper, 22 tests (66 total) |
| C04-T007 | backend | `go` | `1c7a386ca` | Operator evidence read model — PiInvocationOperatorEvidence, validation helper, 24 tests (90 total) |
| C04-T008a | docs | `go` | `340c9501e` | Route seam inspection — route ownership, auth, response patterns, hazards, contract, test matrix |
| C04-T008b | backend | `go` | `da966c060` | Validation-only dry-run route — POST /api/agents/pi-invocation/dry-run, 14 route tests |
| C04-T008c | proof | `go` | `ace560585` | Dry-run route proof closeout — route path, ownership, auth, contracts, 13 side-effect boundaries |
| C04-T009 | frontend | `go` | `493d1ca75` | Dry-run operator read surface — static card with truth labels, validation-only, no execution controls |
| C04-T010 | test | `go` | `bad0eaf5a` | Dry-run fixture pack — 7 fixture functions, 13 fixture tests, route test reuse |
| C04-T011 | frontend | `go` | `8f617fe5e` | Dry-run API helper — validatePiCoderDryRun(), typed request/response, no forbidden exports |
| C04-T012 | frontend | `go` | `a77b3367b` | Validation flow wired — interactive card with envelope textarea + Validate dry-run button |
| C04-T013 | docs | `go` | `b18a05ba1` | Route-to-operator evidence seam — field mapping, safe rendering rules, prohibited claims, proof requirements |
| C04-T014 | impl | `go` | `6fc146700` | Evidence adapter — build_operator_evidence_from_dry_run_response(), pure, 13 tests (116 Pi) |

## Next Task

**C04-T014: Implement Pi/Coder dry-run route-to-operator evidence adapter**

## Campaign Status

**active**

## Deferred / Non-Goals

- No autonomous delegation.
- No ungoverned Pi/Coder execution.
- No recursive tool loops.
- No artifact creation.
- No receipt creation (unless C03/C05 receipt infrastructure is explicitly reused and receipt linkage is governed).
- No release claim widening.
