# Campaign Runner Pi Adapter Contract

## Purpose

Define Pi as the lightweight provider-broker adapter seam for Campaign Runner and Guardian-owned coding-agent execution.

## Scope

This contract covers the Pi broker boundary used by Campaign Runner for:

- route resolution
- backend invocation
- backend receipt preservation
- schema-aware structured output expectations
- explicit failure, retry, and fallback behavior

## Non-goals

- redefining Pi as Campaign Runner core
- redefining Pi as ResonantOS runtime
- replacing Codexify-wide provider governance
- proving that every current runtime path already returns complete broker receipts

## Boundary model

- Pi is not Campaign Runner core.
- Pi is not ResonantOS runtime.
- Pi is not a provider fabric replacement for all of Codexify.
- Pi is an execution broker layer.
- Campaign Runner depends only on the Pi adapter contract, not Pi internals.

## Pi posture

- Pi is the preferred provider-broker adapter for this module when available.
- Pi is preferred, not globally mandatory.
- Pi internals remain replaceable.
- Campaign Runner should only observe Pi through explicit contract fields and receipts.

## Route resolution

Pi may resolve:

- downstream provider
- downstream model
- broker-local fallback order
- provider-specific capability matching

Campaign Runner must not infer those details from Pi naming alone. Downstream identity becomes visible only through explicit receipt metadata.

## Backend receipts

The Pi adapter should preserve a backend receipt with at least:

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

`dependency_mode` values:

- `brokered`
- `direct-forbidden`
- `manual`
- `noop`

## Provider transparency

- Campaign Runner must not know whether Pi used Codex, Claude, a local model, OpenRouter, HTTP JSON, or another backend except through explicit receipt fields.
- Backend/provider switching must never be silent.
- Pi receipts are the transparency surface; Pi internals are not runner truth.

## Schema enforcement expectations

- Pi adapter output is expected to be schema-aware when Campaign Runner requests structured output.
- Schema-invalid responses must be rejected by the adapter or by Campaign Runner validation before they can advance orchestration state.
- Partial output must not be treated as valid success unless the receipt and result contract explicitly mark it as partial and bounded.

## Dependency and footprint rationale

- Avoiding direct Codex/Claude binaries reduces contributor setup cost.
- Avoiding heavy CLI assumptions reduces runtime image bloat.
- A lightweight broker seam improves contributor accessibility for local-first workflows.
- Pi can preserve provider plurality without forcing Campaign Runner to depend on many heavy CLIs directly.

## Failure behavior

| Failure | Expected adapter action | Receipt or error metadata | Retry allowed | Fallback allowed | Reject output |
| --- | --- | --- | --- | --- | --- |
| provider unavailable | fail closed or move to explicit fallback chain | `error_code=provider_unavailable`, `fallback_chain` updated | yes | yes, if declared | yes unless a later attempt succeeds |
| schema-invalid response | reject response | `error_code=schema_invalid` | yes | yes | yes |
| route resolution failure | stop before execution | `error_code=route_resolution_failed` | yes | yes, if alternate route declared | yes |
| backend mismatch | reject mismatched receipt | `error_code=backend_mismatch` | no until config changes | no silent fallback | yes |
| timeout | return bounded failure | `error_code=timeout` | yes | yes | yes |
| partial output | mark partial and reject as success | `error_code=partial_output` or explicit partial marker | maybe | maybe | yes unless orchestration explicitly supports partials |
| direct Codex binary requested | refuse | `dependency_mode=direct-forbidden`, `error_code=direct_codex_forbidden` | no | yes, only through declared Pi route | yes |
| direct Claude binary requested | refuse | `dependency_mode=direct-forbidden`, `error_code=direct_claude_forbidden` | no | yes, only through declared Pi route | yes |
| missing Pi adapter | fail closed | `error_code=missing_pi_adapter` | no until runtime fixed | no | yes |
| Pi route resolves to unsupported backend | fail closed | `error_code=unsupported_broker_backend` | no until route/config fixed | yes, if alternate supported route declared | yes |

## Replaceability rules

- Pi is replaceable as an adapter implementation.
- Replacing Pi must not change Campaign Runner core semantics.
- Any replacement broker must preserve explicit backend receipts and the same no-silent-switch rule set.

## Codex/Claude treatment

- Codex and Claude are not direct dependencies of Campaign Runner.
- Codex and Claude are not direct provider choices for Campaign Runner.
- Codex and Claude may be contacted only through Pi as resolved downstream provider/model identities.
- Direct Codex/Claude binaries, packages, or required CLIs are forbidden for this module.

## Open questions

- What is the smallest proven receipt contract that Pi can emit on the supported local-first path without overclaiming live SDK coverage?
- Should Pi route labels be user-configurable per stage, or stay as a single adapter-level route declaration until receipt persistence hardens?
- How should Pi communicate broker-level fallback versus downstream provider-level retry so Guardian logs remain explicit and non-ambiguous?
