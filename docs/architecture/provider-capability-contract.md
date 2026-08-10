# Provider Capability Contract

## Purpose

This note defines how Codexify represents what each provider, runtime, or model path can actually do.

It is contract planning only. It does not implement provider discovery, routing, validation, UI, health probes, or capability enforcement.

## Governing Sources

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/providers.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/router-decision-table.md`
- `docs/architecture/model-chain-workflows-and-cloud-escalation-policy.md`
- `docs/architecture/whooshd-model-profiles.md`
- `docs/architecture/flow-builder-validation-issue-taxonomy.md`
- `docs/architecture/flow-builder-testrun-activation-contract.md`
- `docs/architecture/adr/039-network-profile-topology-resolution-contract.md`
- `docs/architecture/self-extending-agent-plugin-system.md`

## Interpretation Rules

- Capability selection is declarative.
- Provider name alone is not enough to decide routing.
- The workflow engine and UI should route by capability, not by hardcoded provider name.
- A provider may be valid without being suitable for a specific step.
- Capability claims are not the same thing as runtime proof.
- Effective capability is always shaped by policy, credentials, and environment.
- This note does not claim any new runtime support on `main`.

## Core Idea

Codexify should ask:

> What capabilities does this provider expose?

That question is more useful than:

> What is the provider called?

The same provider family may expose different capabilities depending on the runtime, model, deployment environment, or support posture.

## Capability Model

A capability is a named, declarative statement about what a provider can do for Codexify.

Capabilities should be treated as routing and compatibility signals, not as general marketing labels.

### Capability State Split

The contract should distinguish three layers:

| Layer | Meaning |
|---|---|
| `declared_capabilities` | What the provider or runtime says it can do. |
| `verified_capabilities` | What Codexify has checked with discovery, health, or probe evidence. |
| `effective_capabilities` | What the workflow engine may rely on after applying policy, credentials, and environment rules. |

Routing should use effective capabilities.

UI should show declared, verified, and effective state separately when possible.

### Candidate Capability Vocabulary

The current candidate vocabulary includes:

- `chat_completion`
- `streaming`
- `embeddings`
- `tool_calling`
- `artifact_generation`
- `health_check`
- `queue_metrics`
- `model_lifecycle`
- `memory_pressure`
- `wake_sleep`
- `remote_admin`
- `structured_output`
- `vision`
- `file_ingestion`
- `local_only`
- `cloud_provider`

The vocabulary is declarative and may grow over time, but new terms should be introduced deliberately rather than ad hoc.

### Capability Classes

Some capabilities are execution features.

Examples:

- `chat_completion`
- `streaming`
- `embeddings`
- `tool_calling`
- `artifact_generation`
- `structured_output`
- `vision`
- `file_ingestion`

Some capabilities are operational or diagnostic surfaces.

Examples:

- `health_check`
- `queue_metrics`
- `model_lifecycle`
- `memory_pressure`
- `wake_sleep`
- `remote_admin`

Some capabilities are posture or boundary labels.

Examples:

- `local_only`
- `cloud_provider`

Those posture labels are especially important because they help Codexify separate "what can this do" from "what trust boundary does this live in."

## Proposed Capability Record

A provider capability record should be able to capture at least:

| Field | Meaning |
|---|---|
| `provider_id` | Canonical provider identity. |
| `runtime_id` | Optional runtime family or backend family. |
| `model_id` | Optional model identity if the capability set is model-specific. |
| `declared_capabilities` | Capabilities advertised by the provider or runtime. |
| `verified_capabilities` | Capabilities proven by discovery, health, or probe evidence. |
| `effective_capabilities` | Capabilities available after policy and environment filtering. |
| `discovery_source` | Where the capability data came from. |
| `last_checked_at` | When the record was last checked. |
| `policy_scope` | The policy or posture that shaped the effective view. |
| `notes` | Human-readable explanation or caveat text. |

The record is conceptual only. It does not prescribe the final storage layer.

## Routing Rules

- Workflow steps should declare required capabilities.
- The router should only consider providers whose effective capabilities satisfy those requirements.
- A provider name may be used as a lookup key, but not as the sole routing rule.
- If a capability is missing, the router should fail closed unless the workflow explicitly allows a safe fallback.
- If a capability is declared but not verified, the UI should make that distinction visible.
- If a capability is verified but policy-disallowed, it should still be excluded from effective routing.

## Whoosh'd Position

Whoosh'd is a first-class local provider family because it can expose richer operational and runtime capabilities than a generic OpenAI-compatible endpoint.

That richness matters because it lets Codexify distinguish a local provider that can report health and lifecycle state from a provider that can only answer chat requests.

Whoosh'd may expose capabilities such as:

```json
{
  "chat_completion": true,
  "streaming": true,
  "health_check": true,
  "queue_metrics": true,
  "model_lifecycle": true,
  "memory_pressure": true,
  "wake_sleep": true,
  "local_only": true
}
```

That is a representative capability shape, not a runtime proof claim.

## Generic Provider Position

A generic OpenAI-compatible endpoint is still valid, but it may expose a smaller capability surface.

Example:

```json
{
  "chat_completion": true,
  "streaming": true,
  "health_check": false,
  "queue_metrics": false,
  "model_lifecycle": false,
  "local_only": false,
  "cloud_provider": true
}
```

That does not make it worse. It makes it narrower.

Codexify should treat narrower providers as valid when they satisfy the step or workflow requirements.

## Why This Matters

Capability-based routing lets Codexify support many providers without flattening them into the same abstraction.

It also keeps Whoosh'd first-class for the right reason:

- not because the app hardcodes special cases everywhere
- but because Whoosh'd can truthfully expose more operational capability

This matters for:

- model chains
- cloud escalation policy
- workflow compatibility checks
- UI capability displays
- provider/runtime selection

## Example Compatibility Logic

Step requirements:

- `chat_completion`
- `streaming`
- `structured_output`
- `local_only`

Candidate provider:

- Whoosh'd local runtime

Expected result:

- compatible if the effective capability record proves all four requirements

Candidate provider:

- generic cloud OpenAI-compatible endpoint

Expected result:

- incompatible for that step if `local_only` is required

Candidate provider:

- generic OpenAI-compatible endpoint with structured output support

Expected result:

- compatible for a cloud-allowed step that only requires `chat_completion`, `streaming`, and `structured_output`

## Observability and UI Requirements

The UI should display capability information as a first-class surface.

It should show:

- declared capabilities
- verified capabilities
- effective capabilities
- why a capability is missing
- why a provider is filtered out
- which workflow step required the capability
- whether the limitation is runtime, policy, or trust-boundary related

Capability displays should not collapse into a single green/red availability dot.

## Follow-Up Implementation Specs

This note intentionally stops before implementation.

## Cross-Provider Capability Boundaries

For the DeepSeek provider, capability is relatively homogeneous: one native
transport has been test-proven against the canonical tool-turn contract
(Stage 2B). For Whoosh'd, which is a single provider identity containing
heterogeneous model/runtime targets, tool-capability qualification occurs
below the provider level at the exact target/runtime/template boundary.
That boundary is governed by
[`whooshd-model-tool-capability-boundary.md`](./whooshd-model-tool-capability-boundary.md).
Provider capability records under this contract describe ability; they do
not grant Guardian command authority.

### Provider-specific qualification evidence

An effective capability may consume provider-specific evidence without making
that evidence a provider-neutral wire requirement. For the identity-pinned
Whoosh'd strict-structured path, a future effective tool capability requires a
future qualification record and a current runtime-attestation `MATCH` for the
exact resolved execution target, in addition to readiness, permitted
provider/model capability, and Guardian authority. The detailed local-runtime
attestation boundary is governed by
[`whooshd-runtime-qualification-attestation-contract.md`](./whooshd-runtime-qualification-attestation-contract.md).

That attestation does not itself declare or grant a capability, and it does
not authorize Guardian commands. It is evidence consumed below this generic
capability layer. Other providers may use different trustworthy proof and
lifecycle evidence; they are not required to implement Whoosh'd artifact,
tokenizer, template, or decoder identity fields.

### 1. Runtime Discovery Spec

Should define:

- how provider capability data is discovered
- how discovery differs for local runtimes, cloud providers, and model inventories
- how capability records are refreshed
- how evidence confidence is represented

Suggested future name:

- `provider-capability-discovery-contract.md`

### 2. UI Display Spec

Should define:

- capability badges and detail panels
- declared versus verified versus effective display
- provider comparison views
- step compatibility warnings

Suggested future name:

- `provider-capability-ui-contract.md`

### 3. Workflow Compatibility Spec

Should define:

- how a workflow step declares required capabilities
- how the router filters candidate providers
- how fallback and fail-closed behavior works
- how capability mismatch is reported to validation and receipts

Suggested future name:

- `provider-capability-compatibility-contract.md`

## Implemented Provider-Specific Effective Capability (Stage 2G)

This note remains planning-only for the generic provider capability
framework. One narrow provider-specific effective capability has been
implemented and is documented separately at the exact-target level:

- Provider: `whooshd`
- Target: the exact Stage 2D qualified execution identity
- Surface: parsed current Whoosh'd runtime inventory
  (`whooshd.runtime.v1` / `ModelInfo` payload, full bounded attestation
  when the adapter-loaded path is active)
- Comparator: `guardian/providers/whooshd_qualification.py`
  (`compare_whooshd_inventory_qualification`), re-using the existing
  `whooshd.qualification-attestation.canonical-json.v1` canonicalizer
- Projection: `guardian/providers/whooshd_tool_capability.py`
  (`project_whooshd_tool_capability`)
- Snapshot fields: `outcome`, `invocation_model_id`, `runtime_kind`,
  `adapter_name`, `qualification_outcome`, `runtime_ready`,
  `exposure_allowed`, `reason`, `qualification_reason`

This implementation does **not** turn into the generic provider capability
registry/routing framework implied above. The projection answers only the
narrow Stage 2G question for one target; a future Stage 2H convergence
proof and a separate Stage 2I capability advertisement layer would
generalize any of these decisions. Effective eligibility is
evidence-aware and distinct from a runtime's `supports_tools` field —
`supports_tools=True` without matching attestation cannot qualify a
target, and `supports_tools=False` on the exact qualified target does
not disqualify it.

## Non-Goals

- No runtime discovery implementation
- No UI implementation
- No health endpoint implementation
- No provider registry implementation
- No routing implementation
- No billing logic
- No credential management changes
- No release-surface expansion

## Relationship to Provider/Tool-Turn Boundary

Provider capability records produced under this contract may describe whether
and how a provider can transport the canonical model/tool-turn contract from
[`provider-tool-turn-boundary-contract.md`](./provider-tool-turn-boundary-contract.md).
They do not define Guardian authority, the canonical `ModelTurn` shape, the
tool-call correlation identity, the normalized tool-result shape, or the
provider-continuation-state boundary. Those definitions live in the boundary
contract, not in capability records.

In other words, this contract is cross-cutting with, not subordinate to, the
provider/tool-turn boundary contract. Capability records describe what a
provider can transport; the boundary contract defines what a tool turn is.

This contract remains planning-only and is not current runtime truth.
