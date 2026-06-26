# C08 Backlog: Whoosh'd Runtime Integration & Context Fidelity

## Campaign

**C08: Whoosh'd Runtime Integration & Context Fidelity**

## Campaign Objective

Prove Codexify can route to Whoosh'd cleanly, preserve system identity and context bundle delivery, expose runtime/provider truth surfaces, keep local-only posture honest, and prove `/v1/models` and runtime availability seams before any execution authority campaign (C09) depends on this substrate.

## Status

**Gate**: `go` — C08-T001 accepted. Campaign **closed**.

| Task | Domain | Gate | Commit | Summary |
|------|--------|------|--------|---------|
| C08-T001 | audit | `go` | `TBD` | Runtime config and model inventory seam audit — 17 files, 7 gaps, 7 risks, 6-task backlog |
| C08-T002 | proof | `go` | `68d174d02` | Endpoint health proof — 16 tests, endpoint config, health probes, timeout, lifecycle |
| C08-T003 | proof | `go` | `82742d8fc` | Model inventory identity proof — 14 tests, profile ID vs repo ID separation, 4 gaps |
| C08-T004a | docs | `go` | `TBD` | Context assembly seam inspection — 7-step chain, candidate proof seam, 3 gaps |
| C08-T004b | proof | `go` | `345265704` | Context delivery proof — 12 tests, context -> system message, local provider path |
| C08-T004c | proof | `go` | `48a9a02e6` | Context fidelity closeout — 42-test validation, boundary table, 3 gaps |
| C08-T005 | proof | `go` | `fef59df8b` | Operator runtime truth surfaces — 13 tests, health/llm + health/chat routes, provider governance |
C08-T004 was split into C08-T004a, C08-T004b, C08-T004c — see context-assembly-seam-inspection.md |
| C08-T005 | frontend | planned | — | Expose Whoosh'd runtime truth in operator diagnostics |
| C08-T006 | proof | planned | — | Close C08 Whoosh'd runtime context fidelity proof |

## Next Task

**C08-T002: Prove Whoosh'd endpoint configuration and health-check semantics**

## Campaign Status

**closed**

## Deferred / Non-Goals

- No live execution authority.
- No Pi/Coder execution.
- No new provider implementation.
- No cloud-provider enablement.
- No context pipeline rewrite.
- No frontend control redesign.
- No model download/install automation.
- No Whoosh'd daemon changes.
- No release claim widening.
