# C04-T008a Inspection: Pi/Coder Dry-Run Route Seam

## Gate Decision

**`go`** — C04 may proceed to C04-T008b.

## Scope

This is a docs-only route seam inspection. No route was implemented. This inspection exists because the original C04-T008 was too large for one atomic commit.

## Inputs Read

All 26 required pre-reads and 18 inspection targets available. No missing inputs.

## Existing Route Ownership

### Inspected modules

| Module | Owns | Notes |
|--------|------|-------|
| `guardian/routes/agent_orchestration.py` | `POST /api/agents/coding/execute`, plans, deployments, runs, events, cancel | Directly owns the coding-agent invocation surface. Uses `require_api_key`, `_store`, `_event_publisher`. |
| `guardian/routes/codex.py` | Codex entry CRUD + lineage | Not Pi/Coder-specific. Not the correct owner. |
| `guardian/routes/command_bus.py` | Command bus manifest, invoke, run readback, tool-turn observability | Not Pi/Coder-specific. Not the correct owner for Pi invocation. |

### Decision

**`guardian/routes/agent_orchestration.py` is the correct owner** for a future Pi/Coder dry-run route. It already owns `POST /api/agents/coding/execute` and the imported `guardian.pi` contracts. The `codex.py` and `command_bus.py` modules own different surfaces (codex entries, command bus commands) — routing Pi invocation there would confuse ownership.

### Alternate owners not selected

- `guardian/routes/codex.py` — owns codex entries, not invocation.
- `guardian/routes/command_bus.py` — owns command bus, not Pi invocation.
- New `guardian/routes/pi_invocation.py` — could be created, but splitting the coding-agent surface across two route modules would complicate auth, dependency, and test patterns. Adding to the existing module is cleaner.

## Existing Authentication and Dependency Pattern

### Auth

- Both routers (`router` and `chat_router`) use `dependencies=[Depends(require_api_key)]`.
- `require_api_key` is a FastAPI dependency from `guardian.core.dependencies`.
- Route handlers do not manually call `require_api_key` — it's a router-level dependency.

### Dependencies

- `_store: AgentStore = store` — module-level store instance.
- `_event_publisher: AgentEventPublisher = publisher` — module-level event publisher.
- `configure_db(db)` — callable to inject DB after import.

### Rule for C04-T008b

- The future dry-run route MUST use the same `require_api_key` dependency (router-level).
- The future dry-run route MUST NOT call `_store` for writes.
- The future dry-run route MUST NOT call `_event_publisher.emit()`.
- The future dry-run route MUST use existing `guardian.pi` validators, not store methods.

## Existing Response and Error Pattern

### Response shape

Routes return `dict[str, Any]` with `{"ok": true, ...}` or `{"ok": false, ...}` pattern.

### Error handling

- `HTTPException` is used for 4xx/5xx errors.
- Validation failures return structured dicts, not raw exceptions.

### Rule for C04-T008b

- The future dry-run response MUST include `dry_run: true` early in the response.
- The future dry-run response MUST include `execution_performed: false`.
- The future dry-run response MUST NOT leak raw request payloads or internal errors.

## Existing Coding-Agent Route Stub Posture

### `POST /api/agents/coding/execute`

- Accepts `CodingAgentTaskEnvelope`.
- Creates a **deployment record** via `_store.create_deployment()`.
- Creates a **run record** via `_store.create_run()`.
- Emits **events** via `_event_publisher.emit()`.
- Returns `run_id` — the code returns immediately, execution is deferred to a worker.
- Does **NOT** call Pi SDK.
- Does **NOT** call Coder.
- Does **NOT** execute adapters directly.

### Danger zones for C04-T008b

| Danger | Mitigation |
|--------|------------|
| Copying the `/coding/execute` pattern | The dry-run route must not create deployment/run records, emit events, or defer execution |
| Importing `CodingAgentTaskEnvelope` instead of Pi contracts | Use `guardian.pi.contracts` directly, not coding_agent_contracts |
| Accidentally wiring `_store` or `_event_publisher` | Must be explicitly absent from the dry-run handler |
| Returning `run_id` implying execution | Must not return run_id or any execution-tracker |

## Existing Store and Event Publisher Hazards

### Hazards

| Dependency | Used by `/coding/execute` | Must be used by dry-run? |
|------------|--------------------------|-------------------------|
| `_store.create_deployment()` | ✅ | ❌ |
| `_store.create_run()` | ✅ | ❌ |
| `_event_publisher.emit()` | ✅ | ❌ |

### Rule for C04-T008b

- The future dry-run route MUST NOT call `_store` read methods that depend on database state.
- The future dry-run route MUST NOT call `_event_publisher.emit()`.
- The future dry-run route MUST NOT import task_events or enqueue workers.
- `_store` and `_event_publisher` may remain module-level for other routes, but the dry-run handler MUST NOT reference them.

## Existing Pi Contract and Validator Surface

### Available contracts

| Contract | Location | Usable in dry-run? |
|----------|----------|---------------------|
| `PiInvocationEnvelope` | `guardian.pi.contracts` | ✅ — primary request type |
| `PiGuardianBoundary` | `guardian.pi.contracts` | ✅ — embedded in envelope |
| `PiPermissionGrant` | `guardian.pi.contracts` | ✅ — permission posture |
| `PiInvocationReceipt` | `guardian.pi.contracts` | ✅ (optional preview) |
| `PiInvocationArtifact` | `guardian.pi.contracts` | ✅ (optional preview) |
| `PiInvocationPolicyDecision` | `guardian.pi.contracts` | ✅ — policy decision preview |
| `PiInvocationResultReturn` | `guardian.pi.contracts` | ✅ — result return preview |
| `PiInvocationOperatorEvidence` | `guardian.pi.contracts` | ✅ — operator evidence preview |

### Available validators

| Validator | Location | Usable in dry-run? |
|-----------|----------|---------------------|
| `validate_invocation_envelope()` | `guardian.pi.validation` | ✅ — primary validation |
| `validate_pi_invocation_policy_decision()` | `guardian.pi.validation` | ✅ — policy preview validation |
| `validate_pi_invocation_result_return()` | `guardian.pi.validation` | ✅ — result preview validation |
| `validate_pi_invocation_operator_evidence()` | `guardian.pi.validation` | ✅ — evidence preview validation |

### Rule for C04-T008b

- The future dry-run route MUST use `validate_invocation_envelope()` as the primary validator.
- Optional: derive safe previews for policy, result, and evidence using the respective validators.
- The route MUST NOT duplicate validator logic — call the existing helpers.

## Existing Route Test Conventions

### FastAPI test pattern

- `from fastapi.testclient import TestClient` — standard.
- `TestClient(app)` is used.
- `monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")` for auth.
- `monkeypatch.setenv("DEBUG", "1")` for debug mode.
- `configure_db(None)` to inject null DB.

### Auth test pattern

- API key is set via environment variable in monkeypatch.
- Headers are handled by the FastAPI dependency system — no manual header construction needed in tests when `GUARDIAN_API_KEY` is set.

### Side-effect test pattern

- Monkeypatch to mock or replace forbidden functions (e.g., `_store`, `_event_publisher`).
- Assert that forbidden functions were NOT called.

### Rule for C04-T008b

- Future tests MUST follow the existing TestClient pattern.
- Future tests MUST monkeypatch `GUARDIAN_API_KEY`.
- Future tests MUST assert no `_store` write, no `_event_publisher.emit()`, no database call.

## Future C04-T008b Dry-Run Route Contract

### Route

```
POST /api/agents/pi-invocation/dry-run
```

The prefix `/api/agents` is the existing agent orchestration router prefix. The path `pi-invocation/dry-run` clearly signals this is a Pi/Coder dry-run endpoint, not a coding-agent execution endpoint.

### Request

Accepts a `PiInvocationEnvelope` payload.

### Response contract

| Field | Value | Notes |
|-------|-------|-------|
| `dry_run` | `true` | Always — this is a dry-run route |
| `accepted` | `true` or `false` | Dry-run validation accepted only, NOT execution accepted |
| `state` | Bounded string | Matches envelope validation outcome |
| `validation_status` | `valid` or `failed_closed` | Per `PiInvocationValidationResult` |
| `errors` | List of strings | From validator failure reasons |
| `warnings` | List of strings | From validator warnings if applicable |
| `redaction_state` | String | Safe summary of redactions |
| `release_support` | `unsupported` | Always — no Pi/Coder release support |
| `execution_performed` | `false` | Always — no execution |
| `persistence_performed` | `false` | Always — no database writes |
| `policy_decision_preview` | Object or null | Optional safe preview |
| `result_return_preview` | Object or null | Optional safe preview |
| `operator_evidence_preview` | Object or null | Optional safe preview |

### Prohibited response fields

- Raw args, raw command payloads, raw `extra_meta`, raw `result_json`.
- Raw event payloads, stack traces, hidden prompts, system prompts.
- Secrets, credentials, unredacted payloads.
- Execution controls (dispatch, execute, retry, etc.).
- Completion verdicts (completed, merge_status, execution_success).

## Future C04-T008b Required Test Matrix

| Category | Count (minimum) | Key assertions |
|----------|---------|----------------|
| Valid dry-run | 3 | `dry_run: true`, `execution_performed: false`, `persistence_performed: false`, `release_support: unsupported`, no raw payload |
| Missing source lineage | 2 | Thread ID missing fails, message ID missing fails |
| Missing harness ID | 1 | Fails validation |
| Forbidden raw payload metadata | 1 | Rejected or warned |
| Forbidden execution-control metadata | 1 | Rejected |
| Forbidden completion-collapse metadata | 1 | Rejected |
| No Pi SDK call | 1 | Monkeypatched function NOT called |
| No Coder execution | 1 | Monkeypatched function NOT called |
| No command bus execution | 1 | Monkeypatched function NOT called |
| No worker enqueue | 1 | Monkeypatched function NOT called |
| No transcript write | 1 | Monkeypatched function NOT called |
| No receipt creation | 1 | Monkeypatched function NOT called |
| No artifact creation | 1 | Monkeypatched function NOT called |
| No database write | 1 | Monkeypatched function NOT called |
| No frontend import | 1 | No frontend module imported |
| Deterministic response | 1 | Same input → same output |
| **Minimum** | **15** | |

## Split Decision

The original C04-T008 was split because it spanned a backend route, route tests, and documentation — too large for one atomic commit.

### Split sequence

| Task | Purpose | Atomic? |
|------|---------|---------|
| C04-T008a | Inspect route conventions and document the dry-run contract | ✅ Docs-only |
| C04-T008b | Add the validation-only dry-run route with tests | ✅ Route + tests |
| C04-T008c | Validation closeout and proof consolidation | ✅ Docs-only |

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Accidentally wiring dry-run into `_store` | HIGH | Explicitly absent from handler |
| Accidentally publishing events | HIGH | No `_event_publisher.emit()` call |
| Accidentally inheriting `/coding/execute` semantics | HIGH | Different route path + different request type |
| Treating deployment/run records as Pi/Coder execution | MED | Already documented — dry-run must not |
| Bypassing `require_api_key` | MED | Use router-level dependency |
| Duplicating validator logic in the route | MED | Call existing `guardian.pi.validation` helpers |
| Leaking raw payloads | HIGH | Response contract prohibits |
| Exposing execution controls | HIGH | Response contract prohibits |
| Creating completion verdicts | HIGH | Response contract prohibits |
| Widening release claims | HIGH | `release_support: unsupported` always |
| Adding frontend controls before governance | HIGH | No frontend changes in C04-T008 |

## Release Boundary

- No backend route added.
- No runtime behavior changed.
- No command invocation semantics changed.
- No tool execution semantics changed.
- No Coder execution semantics changed.
- No Pi SDK behavior changed.
- No chat completion semantics changed.
- No persistence schema changed.
- No protocol tokens added or renamed.
- No receipt linkage implemented.
- No result reinjection implemented.
- No transcript persistence implemented.
- No release claim widened.
- No autonomous delegation claim added.
- No Pi/Coder execution claim added.
- No recursive tool-loop claim added.
- No artifact creation claim added.
- No receipt creation claim added.
- No work-order completion claim added.
- No successful merge claim added.

## Documentation Follow-Through

- `00-current-state.md` unchanged.
- ADRs unchanged.
- C03 files unchanged.
- C05 files unchanged.
- C06 closeout unchanged.
- No backend runtime files changed.
- No frontend files changed.
- No tests changed.
- C04 route seam inspection created.
- C04 proof-pack updated.
- C04 decision-log updated.
- C04 backlog updated.

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C04-T008b: Add Pi/Coder validation-only dry-run route`
