---
tags:
* architecture
* adr
* providers
* capabilities
* operator-surface
  aliases:
* ADR-041
* Provider Capability Model Contract
---

# ADR-041: Provider Capability Model Contract

## Status

Proposed

## Date

2026-06-30

## Context

Codexify already has provider governance, catalog and health surfaces, a local-first beta posture, and new proposed topology language through the Operator/User and Network Profile ADRs.

Network Profiles answer how a client reaches a Codexify instance and related runtime services. They should not also decide what a provider can honestly do. Provider names are useful, but provider-name branching is too blunt for a system that may use Whoosh'd, Ollama, LM Studio, custom OpenAI-compatible runtimes, and later brokered execution paths.

Codexify needs a capability model so product and operator surfaces can adapt to evidence-backed provider behavior without hardcoding every surface around specific provider names.

## Decision

Codexify will model provider behavior through explicit capabilities rather than provider-name conditionals.

Provider identity remains useful for configuration, routing, inventory, and diagnostics. Supported behavior should be derived from capability evidence.

A provider may be first-class for a capability when it can prove that capability through a documented registry, live health surface, catalog response, adapter contract, or test-backed runtime seam.

## Capability Domains

Initial candidate domains:

| Domain | Purpose |
|---|---|
| `generation` | Text generation, streaming, structured output, cancellation support, and related completion behavior. |
| `retrieval_support` | Context injection support, context-budget behavior, and retrieval-diagnostics compatibility. |
| `embedding` | Embedding availability, vector dimensions, batching behavior, and local/offline posture. |
| `vision` | Image understanding or multimodal input support. |
| `audio` | TTS, speech recognition, voice lifecycle, or interruption support. |
| `runtime_health` | Liveness, readiness, warmup, model inventory, and first-token evidence. |
| `operator_observability` | Runtime state, model inventory, warmup state, queue state, and failure reason visibility. |
| `policy_posture` | Local-only compatibility, supported-profile allowance, and credential posture. |
| `network_profile_support` | Whether the provider can safely participate in Network Profile URL resolution and profile health display. |

These domains are a starting taxonomy, not runtime tokens yet.

## Capability Evidence Levels

Future implementation should distinguish at least these evidence levels:

| Evidence level | Meaning |
|---|---|
| `declared` | Capability is declared by static configuration or adapter metadata, but not live-proven in this session. |
| `catalog_proven` | Capability appears in provider catalog or inventory data. |
| `health_proven` | Capability is supported by a live health or readiness response. |
| `runtime_proven` | Capability has been exercised by a runtime path or test harness. |
| `release_supported` | Capability is allowed by the supported profile and current release truth. |

A provider can be capable but not release-supported. A provider can be visible in a catalog but not healthy. A provider can be healthy but not part of the current supported beta posture.

Those distinctions must not collapse.

## First-Class Does Not Mean Exclusive

Whoosh'd may receive the richest operator experience because it can expose more local runtime signals, especially on Apple Silicon.

That is capability depth, not artificial feature gating.

Correct posture:

```text
Whoosh'd is first-class because it can prove deeper local runtime capabilities.
Other providers receive the surfaces their capabilities can honestly support.
```

Incorrect posture:

```text
Only Whoosh'd gets rich provider surfaces because its name is Whoosh'd.
```

If Ollama, LM Studio, or a custom OpenAI-compatible runtime can provide equivalent evidence through an adapter, registry, or health contract, Codexify should be able to expose the corresponding capability surface without duplicating provider-name logic.

## Non-Goals

This ADR does not implement:

- provider registry schema changes
- frontend provider picker changes
- Settings UI changes
- Network Profile runtime resolution
- new runtime health endpoints
- provider adapter code
- cloud-provider beta support
- release-supported expansion
- Whoosh'd-specific feature work
- migration or storage changes

## Current-Truth Anchors

What is true now:

- Codexify remains local-first beta hardening on `main`.
- Local Docker Compose remains the supported install path.
- The supported provider posture remains local-only.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Provider catalog, supported-profile posture, and live health must be read together for beta operation.

What is not yet true:

- A general Provider Capability Model is not implemented.
- Capability evidence levels are not yet canonical runtime tokens.
- Settings does not yet present a capability-driven provider matrix.
- Network Profiles do not yet derive provider behavior from this contract.
- This ADR does not make cloud providers beta-supported.

What future tasks may assume:

- It is valid to introduce a bounded capability registry or adapter contract.
- It is valid to make UI/provider surfaces branch on capabilities rather than provider names.
- It is valid to distinguish `catalog_proven`, `health_proven`, `runtime_proven`, and `release_supported` behavior.
- It is valid to give Whoosh'd richer default presentation when the evidence supports it.

## Invariants

- Provider capability display must be evidence-backed.
- Catalog presence must not imply release support.
- Health must not imply supported-profile allowance.
- Supported-profile allowance must not imply live runtime availability.
- Provider-name checks must not become hidden product policy.
- Local-only beta posture remains bounded by `docs/architecture/00-current-state.md`.
- Capability vocabulary that becomes repeated or contract-bearing must follow canonical token discipline.

## Relationship To Network Profiles

Network Profiles answer:

```text
How does this client reach this Codexify instance and related runtime services?
```

Provider Capabilities answer:

```text
What can the selected provider or runtime prove it can do once reached?
```

A Network Profile should not invent provider support. It can surface provider health and capability evidence, but the capability model owns the meaning of those signals.

## Relationship To Operator/User Boundary

Provider capability surfaces are operator-facing when they affect runtime configuration, provider selection, model inventory, queue posture, or instance-wide behavior.

User-facing provider labels may summarize capability in friendly language, but they must not expose operator authority as ordinary user preference.

## Proof Surface For Future Implementation

A future implementation task must include proof for:

- capability registry or adapter unit tests
- catalog-to-capability mapping tests
- health-to-capability mapping tests when live health participates
- UI tests proving provider display branches on capability, not provider name, where applicable
- local-only posture tests proving unsupported capability display does not widen release claims
- docs updates that preserve `00-current-state.md` release boundaries

## Documentation Follow-Through

If accepted, this ADR should be linked from:

- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md` near provider, operator, and Network Profile entrypoints
- future provider registry or Settings docs

## Related Documents

- `docs/architecture/00-current-state.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/tech-debt-and-risks.md`
- `docs/architecture/adr/039-operator-user-access-boundary.md`
- `docs/architecture/adr/040-network-profile-topology-resolution-contract.md`
