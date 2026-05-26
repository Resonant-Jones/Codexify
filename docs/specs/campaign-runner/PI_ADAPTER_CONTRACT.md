# Campaign Runner Pi Adapter Contract

## Purpose

Define the Pi broker adapter contract for Campaign Runner so Pi is treated as a
bounded provider-broker seam rather than as a model identity or global
Codexify runtime truth.

## Scope

- Pi-backed Campaign Runner execution
- route selection and broker metadata
- required Pi backend receipts
- failure behavior for brokered execution

## Non-goals

- Pi internals redesign
- mandatory Pi adoption outside Campaign Runner
- chat-runtime provider-routing changes
- direct Codex/Claude CLI support

## Boundary model

Nodes:
- Guardian backend
- Campaign Runner core
- Pi broker adapter
- downstream provider/model selected by Pi

Trust boundaries:
- Guardian owns task identity, policy, receipts, and transcript lineage
- Pi owns brokered backend invocation only
- downstream provider/model identity is authoritative only when Pi returns it in a receipt

## Pi posture

- Pi is the preferred lightweight provider-broker adapter for Campaign Runner when available.
- Pi is not a model.
- Pi is not ResonantOS runtime truth.
- Pi is not a global replacement for all Codexify provider routing.

## Route resolution

- Pi route selection must be explicit.
- Route defaults may be configured, but no silent provider switching is allowed.
- Route resolution failure must be surfaced as an execution error with receipt-compatible metadata.

## Backend receipts

Pi-backed execution must preserve a backend receipt with at least:

```text
backend_provider: pi
backend_version:
pi_route:
resolved_provider:
resolved_model:
schema_mode:
execution_mode:
dependency_mode:
fallback_chain:
retry_count:
error_code:
```

## Provider transparency

- Resolved provider/model identity must come from the Pi receipt.
- Campaign Runner core must not infer provider identity from CLI flags or branch names.
- Fallback chains must be preserved when Pi retries or reroutes.

## Schema enforcement expectations

- Structured output mode must be explicit.
- Schema-invalid output must fail closed.
- Partial output without a valid receipt must not be treated as success.
- Backend mismatch between declared adapter and receipt must fail closed.

## Dependency and footprint rationale

- Pi keeps Campaign Runner from depending on direct Codex/Claude binaries.
- Pi reduces runtime image coupling by avoiding global Codex/Claude CLI installs for this module.
- Pi keeps downstream provider/model routing behind a bounded adapter seam.

## Failure behavior

- provider unavailable: fail closed and record receipt error metadata
- schema-invalid response: reject output and surface validation failure
- route resolution failure: fail closed with explicit route error
- backend mismatch: fail closed when receipt backend is not `pi`
- timeout: record timeout and preserve retry metadata
- partial output: reject unless schema-valid and receipt-valid
- direct Codex binary requested: fail closed as unsupported
- direct Claude binary requested: fail closed as unsupported
- missing Pi adapter: fail closed as unsupported configuration
- Pi route resolves to unsupported backend: fail closed and record the resolution error

## Replaceability rules

- Campaign Runner core must depend on the adapter contract, not Pi-specific internals.
- Pi may be replaced by another broker adapter only through a future ADR or contract update.
- Receipt requirements survive adapter replacement.

## Codex/Claude treatment

- Direct Codex execution is unsupported for Campaign Runner.
- Direct Claude or Claude Code execution is unsupported for Campaign Runner.
- Codex/Claude may appear only as downstream resolved provider/model identities in Pi receipts.

## Open questions

- Which Pi route names should be treated as stable operator-facing defaults?
- Should receipt enforcement always default on for Campaign Runner, or remain configurable for transitional environments?

### `dependency_mode` values

- `brokered`
- `direct-forbidden`
- `manual`
- `noop`
