# Config and Ops

This page summarizes the operator truth surfaces that matter for local-first runtime work.

## Operational Posture

Codexify is currently described as local-first and locally operated.
That means the supported path is not inferred from a green service alone. It is inferred from the supported profile, health surfaces, and catalog truth taken together.

## Provider Governance Surfaces

Read these surfaces together:

- `/health`
- `/health/chat`
- `/api/health/llm`
- `/api/llm/catalog`

They answer different questions:

- `/health` reports overall runtime posture and supported-profile state.
- `/health/chat` reports queue and worker truth for chat execution.
- `/api/health/llm` reports the active provider runtime state.
- `/api/llm/catalog` reports discovered provider inventory and policy-shaped availability.

No single one of those surfaces proves release support on its own.

## Operator Rule

The provider registry, catalog, health, and supported-profile contract are distinct truths.
Operators should not collapse them into one yes/no answer.

If catalog presence, provider reachability, and supported-profile posture disagree, that is drift evidence, not a clean support signal.

## Local-Only Rule

The current guide set preserves the local-only posture as the supported path.
Cloud-capable config, discovered inventory, or experimental runtime wiring do not widen support unless the current-state docs say they do.

## Failure Interpretation

- green health does not equal full release support
- catalog visibility does not equal supported posture
- backend startup success does not equal end-to-end chat proof
- operator proof requires reading multiple surfaces together
