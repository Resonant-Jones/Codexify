# C04-T017 Loop Closeout: Pi/Coder Dry-Run Operator Evidence

## Gate Decision

**`go`** — The validation-only Pi/Coder dry-run operator evidence loop is closed. C04-T018 may proceed.

## Scope

This closes the validation-only Pi/Coder dry-run operator evidence loop: from backend route response through pure adapter through frontend API helper through read-only UI rendering. This does **not** implement Pi/Coder execution, live Pi SDK behavior, Coder execution, result return, result reinjection, receipt/artifact creation, worker enqueue, transcript persistence, database writes, or release support.

## End-to-End Loop Map

```
Request Contract:     PiInvocationEnvelope
Validator:            validate_invocation_envelope()
Backend Route:        POST /api/agents/pi-invocation/dry-run
Route Response Field: operator_evidence
Adapter Module:       guardian/pi/evidence.py
Adapter Function:     build_operator_evidence_from_dry_run_response
Evidence Contract:    PiInvocationOperatorEvidence
Frontend API Helper:  frontend/src/api/piCoderDryRun.ts
UI Card:              GuardianWorkspacePiCoderDryRunCard
```

## Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| Route exists | ✅ | `guardian/routes/agent_orchestration.py:355` |
| Route validates envelope | ✅ | Calls `validate_invocation_envelope()` |
| Route returns dry-run response | ✅ | `dry_run: true`, `execution_performed: false`, `persistence_performed: false`, `release_support: unsupported` |
| Route returns operator evidence | ✅ | `operator_evidence` field via `build_operator_evidence_from_dry_run_response()` |
| Adapter maps response to evidence | ✅ | `guardian/pi/evidence.py` — pure, deterministic |
| API helper types operator evidence | ✅ | `operator_evidence?: Record<string, unknown>` in `PiCoderDryRunResponse` |
| UI renders operator evidence | ✅ | `Operator evidence` section in validation card |
| UI remains read-only | ✅ | No execution controls |
| UI preserves validation-only copy | ✅ | "Validation only", "Dry-run only" labels |
| UI preserves no-execution copy | ✅ | "No execution performed" |
| UI preserves no-persistence copy | ✅ | "No persistence performed" |
| UI preserves unsupported release posture | ✅ | "Release support: unsupported" |
| Route remains side-effect-free | ✅ | No `_store`, no `_event_publisher`, no DB writes |
| Adapter is pure and deterministic | ✅ | No I/O, no side effects |
| No execution exists | ✅ | Proven across route + adapter + UI |
| No persistence exists | ✅ | Proven across route + adapter + UI |
| No receipt creation exists | ✅ | Proven across route + adapter + UI |
| No artifact creation exists | ✅ | Proven across route + adapter + UI |
| No release support exists | ✅ | `release_support: unsupported` everywhere |

## Boundary Table

| Boundary | Proven | Evidence |
|----------|--------|----------|
| No live Pi SDK | ✅ | Not imported, not called (C04-T001, all route tests) |
| No Coder execution | ✅ | Not imported, not called (C04-T001, all route tests) |
| No command bus execution | ✅ | Not called by route or adapter |
| No worker enqueue | ✅ | Not called by route or adapter |
| No transcript persistence | ✅ | Not called by route or adapter |
| No receipt creation | ✅ | Not called by route or adapter |
| No artifact creation | ✅ | Not called by route or adapter |
| No database write | ✅ | Not called by route or adapter |
| No result return runtime | ✅ | Not implemented |
| No result reinjection | ✅ | Not implemented |
| No frontend execution controls | ✅ | No Execute/Run/Dispatch/etc buttons |
| No release-support claim | ✅ | `release_support: unsupported` everywhere |

## Safety Surface

| Safety Rule | Enforced |
|-------------|----------|
| Forbidden raw payload fields filtered | ✅ Adapter filters 22 keys; card renders safe fields only |
| Completion verdicts not rendered | ✅ Not in types, not in card |
| Receipt claims not rendered | ✅ Not in types, not in card |
| Artifact claims not rendered | ✅ Not in types, not in card |
| Unsupported release posture preserved | ✅ All layers show `unsupported` |
| Operator evidence is validation-only | ✅ Boundary copy in card |
| Anchor: route-presence ≠ execution | ✅ |
| Anchor: helper-presence ≠ execution | ✅ |
| Anchor: UI rendering ≠ execution | ✅ |

## Validation Summary

| Suite | Tests | Result |
|-------|-------|--------|
| Adapter tests (`test_operator_evidence_adapter.py`) | 13 | passed |
| Full Pi tests (`tests/pi/`) | 116 | passed |
| Route tests (`test_pi_invocation_dry_run_route.py`) | 14 | passed |
| Frontend shell tests (`CommandCenterShell.test.tsx`) | 65 | passed |
| `guardian.pi` import | — | ok |
| `agent_orchestration` import | — | ok |
| `git diff --check` | — | clean |
| `python3 scripts/validate_docs.py` | — | passed |
| `pnpm lint` | — | unavailable |

## Known Non-Goals

- No execution
- No autonomous delegation
- No recursive tool loop
- No result return
- No result reinjection
- No receipt/artifact persistence
- No command bus dispatch
- No worker queue dispatch
- No release support

## Remaining Risks

| Risk | Future task |
|------|-------------|
| Dry-run acceptance could be mistaken for execution acceptance | C04 UI copy hardening (deferred) |
| Future persistence could confuse validation with invocation | Governance contract enforcement (C04-T018) |
| Future policy runtime could be introduced without ADR | Architecture review gate |
| `pnpm lint` unavailable — no automated frontend lint | Frontend tooling task (deferred) |

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C04-T018: Close C04 Pi/Coder invocation boundary campaign`
