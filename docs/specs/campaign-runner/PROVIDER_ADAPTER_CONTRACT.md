# Campaign Runner Provider Adapter Contract

## Purpose

Define the direct adapter boundary for Campaign Runner so core orchestration
stays provider-agnostic, receipts stay auditable, and direct Codex/Claude CLI
coupling is excluded from this module.

## Scope

- Campaign Runner core orchestration
- Guardian-mediated coding-worker execution for Campaign Runner tasks
- direct adapter classes used by this module
- required backend receipts for brokered execution claims

## Non-goals

- Pi SDK implementation details
- global Codexify provider routing redesign
- chat completion runtime changes outside Campaign Runner
- Tauri IPC changes
- cloud-provider support widening

## Boundary model

Nodes:
- Guardian backend and coding worker
- Campaign Runner core
- Pi broker adapter process
- downstream provider/model selected behind Pi
- Postgres/Redis evidence rails

Trust boundaries:
- Guardian remains the policy and lineage boundary
- the adapter boundary begins at prompt execution and backend invocation
- downstream provider identity is untrusted until returned in a backend receipt

Threat model:
- honest-but-buggy adapter process
- missing or malformed backend receipts
- schema-invalid outputs
- explicit unsupported direct-provider requests

## Responsibility split

Campaign Runner Core responsibilities:
- campaign lifecycle
- schema validation
- artifact isolation
- git safety
- checkpoint enforcement
- handoff generation
- forbidden-zone enforcement
- adapter selection by declared contract only
- rejection of schema-invalid outputs
- preservation of backend receipts

Provider Adapter responsibilities:
- prompt execution
- backend invocation
- backend metadata reporting
- retry policy
- structured output mode
- provider-specific configuration
- model routing behind the adapter boundary
- fallback reporting
- backend receipt generation

## Required backend receipt

Every brokered execution claim must preserve a backend receipt with at least:

```text
backend_provider:
backend_version:
resolved_provider:
resolved_model:
schema_mode:
execution_mode:
passes:
fallback_chain:
retry_count:
error_code:
```

## Dependency posture

- Campaign Runner must not require direct Codex binaries.
- Campaign Runner must not require direct Claude binaries.
- Campaign Runner must not pin Codex or Claude CLI executables.
- Campaign Runner must not expose direct `codex` or `claude` provider choices.
- Codex/Claude may appear only as resolved downstream provider/model identities through Pi receipts.
- Pi is the preferred provider-broker adapter for this module.

## Failure and retry rules

- Retry behavior must be explicit, bounded, and logged.
- Schema-invalid adapter output must be rejected.
- Missing backend receipts must fail closed when receipt enforcement is enabled.
- Direct unsupported adapter requests must fail closed rather than remap.
- Fallbacks must be recorded in `fallback_chain`.

## Adapter class policy

Recommended direct adapter classes for this module:
- `pi`
- `noop`
- `manual`

Legacy-compatible internal target allowed in this slice:
- `pi_codex_runner`
  - legacy-compatible name for the Pi broker runner
  - not a direct Codex CLI path

Explicitly excluded direct adapter classes:
- `codex`
- `claude`
- `claudecode`

## Implementation posture

- Guardian owns execution policy, lineage, and result return.
- Campaign Runner core must not branch on downstream provider identity.
- Adapter selection is by declared contract, not shell binary availability.
- Backend receipts are the proof surface for brokered provider/model identity.

## Open questions

- Should `pi_codex_runner` be renamed to `pi_runner` or `pi_broker` in a later narrow cleanup?
- Which receipt fields should become canonical protocol tokens versus module-local metadata?
- How much adapter-session telemetry should be preserved beyond the required receipt?
