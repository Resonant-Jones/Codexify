# C04-T013 Route-to-Operator Evidence Seam

## Purpose

Define the seam between the Pi/Coder dry-run route response and the operator-visible evidence model so future implementation can map the existing backend dry-run route response into the existing operator evidence surface without implying live Pi/Coder execution, persistence, result return, receipt creation, artifact creation, worker dispatch, or release support.

## Scope

This is a docs-only seam definition. It does **not** implement the adapter, add backend routes, modify frontend code, create tests, alter runtime behavior, or widen release claims.

## Non-Goals

- No implementation of a route-to-evidence adapter.
- No new backend routes.
- No new frontend components.
- No persistence behavior.
- No receipt/artifact creation.
- No result return runtime.
- No transcript writes.
- No worker enqueue.
- No release support widening.

## Current Truth

### Existing Route

```
POST /api/agents/pi-invocation/dry-run
```
Owned by `guardian/routes/agent_orchestration.py`. Authenticated via `require_api_key`. Accepts `PiInvocationEnvelope`. Validates via `validate_invocation_envelope()`. Returns safe bounded dry-run response.

### Existing Response Semantics

| Field | Value | Meaning |
|-------|-------|---------|
| `dry_run` | `true` | Always — no execution |
| `accepted` | `true` or `false` | Dry-run validation accepted only |
| `state` | `validated` or `validation_failed` | Envelope validation outcome |
| `validation_status` | `valid` or `failed_closed` | Per `PiInvocationValidationResult` |
| `errors` | List of strings | Validator failure reasons |
| `warnings` | List of strings | Validator warnings |
| `redaction_state` | `clean` | Safe summary |
| `release_support` | `unsupported` | Always — no release support |
| `execution_performed` | `false` | Always — no execution |
| `persistence_performed` | `false` | Always — no persistence |

### Existing Frontend

- **Helper**: `validatePiCoderDryRun()` at `frontend/src/api/piCoderDryRun.ts`
- **Card**: `GuardianWorkspacePiCoderDryRunCard` at `frontend/src/features/commandCenter/components/GuardianWorkspacePiCoderDryRunCard.tsx`
- **Flow**: Card accepts envelope JSON, calls helper on "Validate dry-run" button, renders safe response fields.

### Existing Operator Evidence Contract

`PiInvocationOperatorEvidence` in `guardian/pi/contracts.py`. Evidence states: `unavailable`, `available`, `partial`, `blocked`, `deferred`, `validation_failed`.

## Existing Inputs

| Input | Location | Status |
|-------|----------|--------|
| Dry-run route | `POST /api/agents/pi-invocation/dry-run` | ✅ Proven |
| `PiInvocationEnvelope` | `guardian/pi/contracts.py` | ✅ Contract-only |
| `validate_invocation_envelope()` | `guardian/pi/validation.py` | ✅ Deterministic |
| `validatePiCoderDryRun()` | `frontend/src/api/piCoderDryRun.ts` | ✅ Typed |
| `GuardianWorkspacePiCoderDryRunCard` | `frontend/src/features/commandCenter/components/GuardianWorkspacePiCoderDryRunCard.tsx` | ✅ Interactive |
| `PiInvocationOperatorEvidence` | `guardian/pi/contracts.py` | ✅ Contract-only |
| Evidence state model | C04-T007 | ✅ 6 states |

## Proposed Seam

A future implementation (C04-T014 or later) may:

1. Accept a dry-run route response (from `validatePiCoderDryRun()` or from the raw route response).
2. Map it to a `PiInvocationOperatorEvidence` state:
   - `accepted === true` and safe summary present → `available`
   - `accepted === false` → `validation_failed`
   - Route call failed or timed out → `unavailable`
   - Partial safe fields only → `partial`
   - Blocked by permission/posture → `blocked`
   - Not yet executed → `deferred`
3. Render the operator evidence in the existing card using safe fields only.

The adapter must be **pure** — no side effects, no persistence, no global state.

## Field Mapping

| Dry-run response field | Operator evidence field | Mapping rule |
|------------------------|------------------------|--------------|
| `dry_run` | `evidence_state` derivation | `true` does not change state — state derives from `accepted` and result availability |
| `accepted` | `evidence_state` | `true` + safe summary → `available`; `false` → `validation_failed` |
| `state` | `evidence_state` | Informational — used alongside `accepted` for state derivation |
| `validation_status` | `validation_status` | Direct mapping |
| `errors` | Failure context for `validation_failed` | Do not expose raw error payloads |
| `warnings` | Safe metadata | Optional |
| `redaction_state` | `redaction_state` | Direct mapping |
| `release_support` | Unsafe | Do not map as evidence — always `unsupported` |
| `execution_performed` | `evidence_state` | Must be `false` — used to prevent `available` without verification |
| `persistence_performed` | `evidence_state` | Must be `false` — used to prevent `available` without verification |
| `invocation_id` | `invocation_id` | Safe reference |
| `source_thread_id` | `source_thread_id` | Safe reference |
| `source_message_id` | `source_message_id` | Safe reference |
| `harness_id` | `harness_id` | Safe reference |
| `permission_posture` | `permission_posture` | Safe summary |

### Forbidden Mappings

| Forbidden field | Must not appear in evidence |
|----------------|---------------------------|
| Raw args | ❌ |
| Raw command payloads | ❌ |
| Raw `extra_meta` | ❌ |
| Raw `result_json` | ❌ |
| Raw event payloads | ❌ |
| Stack traces | ❌ |
| Hidden prompts | ❌ |
| System prompts | ❌ |
| Secrets | ❌ |
| Credentials | ❌ |
| Unredacted payloads | ❌ |
| Execution controls | ❌ |
| Completion verdicts | ❌ |

## Safe Rendering Rules

### Allowed in Operator Evidence

- Validation state (available/unavailable/partial/blocked/deferred/validation_failed)
- Safe summaries (validation_status, errors bounded, redaction_state)
- Safe references (invocation_id, source_thread_id, source_message_id, harness_id)
- Route path (`POST /api/agents/pi-invocation/dry-run`)
- Unsupported release posture (`release_support: unsupported`)
- No-execution status (`execution_performed: false`)
- No-persistence status (`persistence_performed: false`)
- Permission summary (if available)
- Validation errors (bounded — no stack traces, no secrets, no raw payloads)

### Prohibited in Operator Evidence

- Raw payloads of any kind
- Hidden prompts or system prompts
- Secrets or credentials
- Chain-of-thought content
- Raw document bodies
- Raw message bodies beyond safe references
- Execution controls (dispatch, execute, retry, replay, approve, complete)
- Completion verdicts (completed, merge_status, execution_success)
- Receipt claims
- Artifact claims
- Runtime support claims
- Release support claims beyond "unsupported"

## Prohibited Claims

This seam does **not** prove:

- Live Pi SDK behavior.
- Coder execution.
- Command bus execution.
- Worker enqueue.
- Transcript persistence.
- Result return runtime.
- Result reinjection.
- Receipt creation.
- Artifact creation.
- Database writes.
- Release support.
- Autonomous delegation.
- Recursive tool loops.

## Failure and Partial Evidence States

| Condition | Evidence state |
|-----------|---------------|
| Route call succeeds, `accepted: true`, safe summary present | `available` |
| Route call succeeds, `accepted: false` | `validation_failed` |
| Route call fails (network, timeout, auth) | `unavailable` |
| Route call succeeds but only partial safe fields available | `partial` |
| Invocation blocked by permission/posture | `blocked` |
| Not yet attempted | `deferred` |

State transitions must be deterministic for the same input.

## Proof Requirements

Future implementation must prove:

- Helper calls only `POST /api/agents/pi-invocation/dry-run`.
- Card renders only safe evidence fields.
- No direct fetch in card.
- No execution controls in card.
- No raw payload rendering.
- Dry-run response maps deterministically to evidence state.
- Validation failures map to `validation_failed`.
- Missing route response maps to `unavailable`.
- Partial safe evidence maps to `partial`.
- Unsupported release posture remains visible.
- Route remains side-effect-free.
- No `_store` calls.
- No `_event_publisher` calls.
- No migrations.
- No receipt/artifact creation.
- No command bus invocation.
- No worker enqueue.

## Implementation-Ready Acceptance Criteria

A future implementation task (C04-T014 or later) must:

- Be named explicitly with target files in the task prompt.
- Keep the route-to-evidence mapping pure and deterministic.
- Keep the UI validation-only and dry-run-only.
- Preserve `release_support: unsupported`.
- Prove no execution/persistence controls are introduced.
- Prove no raw payloads are rendered.
- Prove no forbidden mappings occur.
- Reuse existing contracts, validators, helpers, and cards — no parallel types.

C04-T013 does **not** implement this. It defines the seam contract only.

## Release Boundary

- No runtime behavior changed.
- No backend route behavior changed.
- No frontend behavior changed.
- No persistence or migrations added.
- No receipt/artifact creation added.
- No result return runtime added.
- No transcript persistence added.
- No worker enqueue added.
- No release claim widened.
- No autonomous delegation claimed.
- No Pi/Coder execution claimed.
- No recursive tool loops claimed.

## Open Questions

1. Should the mapping be a backend helper (pure function) or a frontend utility?
   - Backend helper is safer — centralizes evidence derivation. Frontend utility would duplicate field extraction in the card.
2. Should the adapter produce a `PiInvocationOperatorEvidence` instance or a lighter-weight dict?
   - `PiInvocationOperatorEvidence` is the canonical contract type. Producing it directly ensures downstream consumers use the same safe shape.
3. Should the mapping be called from the dry-run route or from the card?
   - The mapping is a pure function — it can be called from either. Calling it from the route would produce evidence alongside the dry-run response. Calling it from the card keeps the route response unchanged.

Resolved by future C04-T014 task prompt.

## Gate Decision

- **Decision**: `go`
- **Next task by name only**: `C04-T014: Implement Pi/Coder dry-run route-to-operator evidence adapter`
