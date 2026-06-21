# C04-T008c Closeout: Pi/Coder Dry-Run Route Proof

## Gate Decision

**`go`** — The dry-run route proof is closed. C04-T009 may proceed.

## Scope

This is a docs-only proof closeout. No code or test changes were made. The original C04-T008 was split into C04-T008a (inspection), C04-T008b (implementation + boundary proof), and C04-T008c (this closeout).

## Route Path

```
POST /api/agents/pi-invocation/dry-run
```

## Route Ownership

`guardian/routes/agent_orchestration.py` owns the route. This is the correct owner per C04-T008a: the module already owns `POST /api/agents/coding/execute` and imports `guardian.pi` contracts. Alternate owners (`codex.py`, `command_bus.py`) own different surfaces.

## Auth Pattern

The route follows the existing `require_api_key` router-level dependency. Unauthenticated requests return 401/403 — test-proven in C04-T008b-R1.

## Request Contract

- Accepts `PiInvocationEnvelope` from `guardian.pi.contracts`.
- Validates using `validate_invocation_envelope()` from `guardian.pi.validation`.
- **Accepted means accepted for dry-run validation only** — not accepted for execution.

## Response Contract

| Field | Value | Proven |
|-------|-------|--------|
| `dry_run` | `true` | Test-proven |
| `accepted` | `true` or `false` | Test-proven |
| `execution_performed` | `false` | Test-proven |
| `persistence_performed` | `false` | Test-proven |
| `release_support` | `unsupported` | Test-proven |

No raw payloads, execution controls, or completion verdicts in response — test-proven.

## Test Evidence

| Suite | Tests | Result |
|-------|-------|--------|
| Route tests (`test_pi_invocation_dry_run_route.py`) | 14 | passed |
| Pi contract tests (`tests/pi/`) | 90 | passed |
| `guardian.pi` import | — | ok |
| `git diff --check` | — | clean |
| `python3 scripts/validate_docs.py` | — | passed |

## Side-Effect Boundary Proof

| Boundary | Proof | Source |
|----------|-------|--------|
| No Pi SDK behavior | Source-verified | Route imports only Pi contracts + validators |
| No Coder execution | Source-verified | Route imports only Pi contracts + validators |
| No command bus execution | Source-verified | Separate module, not imported |
| No worker enqueue | Source-verified | No queue/worker imports |
| No transcript persistence | Source-verified | No chat worker or message write |
| No receipt creation | Source-verified | No receipt model/store imported |
| No artifact creation | Source-verified | No artifact model exists (C04-T001) |
| No database write | Source-verified + test-proven | No _store calls |
| No `_store` call | Test-proven (monkeypatch) | C04-T008b-R1 |
| No `_event_publisher` call | Test-proven | C04-T008b-R1 |
| No frontend import | Source-verified | No frontend modules in route |
| No frontend execution controls | Source-verified | Response contract prohibits |
| No operator UI | Source-verified | No frontend code changed |

## What Is Now True

- One validation-only dry-run route exists at `POST /api/agents/pi-invocation/dry-run`.
- It is authenticated via the existing `require_api_key` dependency.
- It validates `PiInvocationEnvelope` using `validate_invocation_envelope()`.
- It returns a safe, bounded dry-run response with explicit `dry_run: true`, `execution_performed: false`, `persistence_performed: false`, `release_support: unsupported`.
- It performs no execution, no persistence, no side effects.

## What Is Still Not True

- No Pi SDK invocation.
- No Coder execution.
- No command bus execution.
- No worker enqueue.
- No result return runtime.
- No result reinjection.
- No transcript persistence.
- No receipt persistence.
- No artifact persistence.
- No receipt linkage.
- No operator UI for Pi/Coder evidence.
- No autonomous delegation.
- No recursive tool loops.
- No release support widening.

## Risks Closed

| Risk | Status |
|------|--------|
| Route owner ambiguity | Closed — `agent_orchestration.py` |
| Auth ambiguity | Closed — `require_api_key` |
| Response shape ambiguity | Closed — bounded contract |
| `_store` hazard | Closed — not called, test-proven |
| `_event_publisher` hazard | Closed — not called, test-proven |
| Raw payload leak | Closed — response contract prohibits |
| Execution-control leak | Closed — response contract prohibits |
| Completion-verdict collapse | Closed — response contract prohibits |
| `/coding/execute` semantic inheritance | Closed — different path + different contract |

## Risks Remaining

- Future implementation could accidentally convert dry-run acceptance into execution acceptance.
- Future UI could imply execution exists before governance.
- Future persistence could confuse validation with invocation.
- Future policy runtime could be introduced without an ADR.
- Future result return runtime could be confused with transcript write.

## Next Task

**C04-T009: Define Pi/Coder dry-run operator read surface**

## Release Boundary

- No runtime execution added.
- No Pi SDK behavior added.
- No Coder behavior added.
- No command bus behavior changed.
- No worker behavior changed.
- No chat completion behavior changed.
- No persistence schema changed.
- No frontend controls added.
- No operator UI added.
- No release support widened.

## Documentation Follow-Through

- `00-current-state.md` unchanged.
- ADRs unchanged.
- Backend route code unchanged in this closeout.
- Tests unchanged in this closeout.
- Frontend unchanged.
- Dry-run route closeout created.
- Proof-pack updated.
- Decision-log updated.
- Backlog updated.
