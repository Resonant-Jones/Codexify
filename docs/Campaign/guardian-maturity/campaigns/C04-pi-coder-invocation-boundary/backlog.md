# C04 Backlog: Pi/Coder Invocation Boundary

## Campaign

**C04: Pi/Coder Invocation Boundary**

## Campaign Objective

Define and implement a governed, bounded, operator-visible Pi/Coder invocation seam that carries Guardian authority, preserves lineage, enforces validation-only run mode, and does not imply autonomous delegation, Pi/Coder execution, recursive tool loops, artifact creation, receipt creation, or release widening.

## Status

**Gate**: `go` — C04-T001 accepted. Campaign active.

| Task | Domain | Gate | Commit | Summary |
|------|--------|------|--------|---------|
| C04-T001 | audit | `go` | `e4b68e685` | Pi/Coder invocation boundary seam audit — contracts, implementation, runtime proven/not-proven, risks, backlog |
| C04-T002 | docs | `go` | `875e5266c` / `c5c0d5931` | Acceptance contract — state model, 15 criteria, 18-row proof matrix, 13 prohibited shortcuts, 7 proof classes, failure/blocker rules |
| C04-T003 | docs | `go` | `9468eeacd` / `3cbd4ad8f` | Proof matrix — state ladder, 27-row core boundary matrix, 10-class evidence matrix, 15-condition gate matrix, lineage/receipt/artifact/operator/redaction proof requirements |
| C04-T004 | backend | `go` | `74e137511` | Contract gap repair — contracts + validation already existed; added 8 boundary tests (23 total) |
| C04-T005 | backend | `go` | `32b89df06` | Policy decision contract — PiInvocationPolicyDecision, validation helper, 21 tests (44 total) |
| C04-T006 | backend | `go` | `TBD` | Result return contract — PiInvocationResultReturn, validation helper, 22 tests (66 total) |
| C04-T002 | docs | planned | — | Define Pi/Coder invocation boundary acceptance contract |
| C04-T003 | docs | planned | — | Envelope preview contract |
| C04-T004 | docs | planned | — | Validation-only run mode contract |
| C04-T005 | backend | `go` | `32b89df06` | Policy decision contract — PiInvocationPolicyDecision, validation helper, 21 tests (44 total) |
| C04-T006 | backend | `go` | `TBD` | Result return contract — PiInvocationResultReturn, validation helper, 22 tests (66 total) |
| C04-T006 | frontend | planned | — | Envelope preview UI scaffold |
| C04-T007 | frontend | planned | — | Validation-only run mode UI scaffold |
| C04-T008 | proof | planned | — | C04 integration proof and closeout |

## Next Task

**C04-T002: Define Pi/Coder invocation boundary acceptance contract**

## Campaign Status

**active**

## Deferred / Non-Goals

- No autonomous delegation.
- No ungoverned Pi/Coder execution.
- No recursive tool loops.
- No artifact creation.
- No receipt creation (unless C03/C05 receipt infrastructure is explicitly reused and receipt linkage is governed).
- No release claim widening.
