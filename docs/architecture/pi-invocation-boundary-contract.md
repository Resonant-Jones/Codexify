# Pi Invocation Boundary Contract

Implementation status (2026-05-08): backend-only Pi invocation boundary contracts now exist under `guardian/pi` for `PiInvocationEnvelope`, `PiInvocationReceipt`, `PiInvocationArtifact`, `PiHarnessResult`, and `PiInvocationValidationResult`, with pure deterministic validation helpers for envelope, receipt, and harness-result provenance/permission checks.

This seam is contract and validation only:
- no live Pi SDK call exists
- no Minimax provider behavior changed
- no provider routing changed
- no command execution was added
- no worker orchestration was added
- no sandboxing was added
- no runtime dispatch/autonomous execution was added
- no transcript persistence was added
- no HTTP routes were added

Deferred in this task:
- `/docs/architecture/00-current-state.md`
- `/docs/architecture/system-overview.md`
- `/docs/architecture/flows.md`
- provider implementation docs
- command-bus runtime docs
Purpose: Define Codexify's bounded architecture contract for future Pi-like coding-agent harness invocation while preserving Guardian authority, lineage, and sovereignty boundaries.
Last updated: 2026-05-08
Source anchors:
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/config-and-ops.md
- docs/architecture/modules-and-ownership.md
- docs/architecture/self-extending-agent-plugin-system.md

# Pi Invocation Boundary Contract

## Classification

- Classification: Aligned with existing ADR(s)
- Governing ADRs/contracts:
  - ADR-010 Self-Extending Agent Plugin System
  - Guardian-mediated coding-agent execution doctrine (ADR-020 when present in this repo lineage)
  - Bounded tool-augmented completion contract
  - Agent tool-loop contract
  - Chat runtime contract
  - Runtime protocol token contract
  - Account export + restore contract
  - Existing identity/IDDB policy and Persona Studio identity-boundary rules
- Brief reason:
  - This contract defines a bounded architecture seam for future Pi-like harness invocation and clarifies provider-lane separation (including Minimax) without implementing runtime execution.

Implementation status: backend-only Pi invocation envelope, receipt, artifact, harness-result, and pure validation contracts now exist under `guardian/pi/`. They perform shape, provenance, and permission-posture validation only. No live Pi SDK call exists, no Minimax provider behavior changed, and no command execution, worker orchestration, sandboxing, runtime dispatch, or transcript persistence was added by this seam.

## Purpose and Problem Statement

Codexify needs a bounded Pi Invocation Boundary before any Pi-like integration so external coding-agent harnesses cannot quietly redefine runtime authority.

Pi-like harnesses are treated as external or mediated execution harnesses, not unrestricted self-modifying runtimes. Guardian remains the owner of request policy, transcript lineage, provenance, command authority, and result return.

Minimax, if used, is a Provider Lane concern only. Provider/model choice must not be hardwired into Pi invocation governance.

## Canonical Terminology

| Term | Meaning |
|---|---|
| `Pi Invocation Boundary` | The Codexify-native contract seam that governs bounded invocation of a Pi-like harness. |
| `Pi-like Harness` | Any external or mediated coding-agent harness that can execute a bounded authored request and return outputs. |
| `Guardian-Mediated Invocation` | Invocation path where Guardian evaluates policy, creates the invocation envelope, and owns result return. |
| `Invocation Receipt` | Structured record that invocation occurred, including invocation identity, permission posture, and completion status. |
| `Invocation Artifact` | Result payload returned from the harness (for example proposed patch, command plan, summary, or diagnostics artifact). |
| `Harness Result` | The harness-produced output bundle containing at minimum an Invocation Artifact reference plus Invocation Receipt metadata. |
| `Result Return Path` | The governed path that returns Harness Result into Codexify continuation semantics. |
| `Provider Lane` | Provider/model routing lane governed by existing provider/config contracts. |
| `Minimax Provider Lane` | A specific Provider Lane value for Minimax when configured and allowed by provider governance. |
| `Guardian Ownership Boundary` | Non-bypass boundary where Guardian retains policy, authority, lineage, and return control. |

Repeated contract-bearing values must use canonical tokens or future bounded registries, not ad hoc literals.

## Boundary Model

Codexify may later delegate one bounded request to a Pi-like harness through a Guardian-Mediated Invocation.

The Pi Invocation Boundary enforces these invariants:

- Pi-like harnesses must not bypass Guardian policy decisions.
- Pi-like harnesses must not bypass command-bus authority for Codexify-owned actions.
- Pi-like harnesses must not bypass transcript ownership, provenance, or export/restore obligations.
- Pi-like harnesses must not directly mutate IDDB / Identity Mirror.
- Pi-like harnesses must not directly mutate persona ownership rules.
- Pi-like harnesses must not redefine runtime protocol tokens.
- Pi-like harnesses must not alter message-versus-attempt semantics.
- Pi-like harnesses must not silently write core runtime state.
- Pi-like harnesses must not become an autonomous recursive execution loop through this contract.

## Invocation Lifecycle

### Canonical lifecycle

1. Guardian receives an authored request.
2. Guardian resolves whether Pi invocation is permitted.
3. Guardian creates a bounded invocation envelope.
4. Pi-like harness executes externally or in a mediated adapter lane.
5. Harness returns a result artifact and receipt.
6. Guardian validates the result.
7. Guardian returns the result through the existing reinjection/reentry path or an explicitly future-compatible return path.
8. Guardian preserves lineage and auditability.

### Phase contract table

| Phase | Entry condition | Required artifact / metadata | Allowed side effects | Prohibited side effects | Proof / observability expectation |
|---|---|---|---|---|---|
| `1. Authored request received` | A user-authored turn is persisted and identity-scoped. | source thread id, source message id, request identity where applicable. | None beyond normal authored-turn persistence. | Creating autonomous execution attempts without policy decision. | Request lineage is recoverable from current chat/runtime records. |
| `2. Invocation permission resolved` | Guardian has enough policy context to evaluate invocation eligibility. | policy decision, requested permission set, granted permission set, Guardian policy source. | Record decision metadata. | Hidden policy overrides or implicit broadening of permissions. | Requested-vs-granted permissions are inspectable. |
| `3. Invocation envelope created` | Invocation is explicitly permitted for this authored request. | invocation id, harness id, bounded scope, allowed context references, permission posture, provider lane if relevant. | Construct bounded invocation envelope artifact. | Direct runtime mutation, command execution, identity writes. | Envelope inspection shows bounded scope and provenance linkage. |
| `4. Harness execution` | A valid invocation envelope exists. | harness id/version, invocation id, execution start/stop metadata. | External or mediated harness processing only. | Direct IDDB writes, persona rule mutation, token mutation, command-bus bypass, recursive self-dispatch. | Execution surface records harness id/version and invocation linkage. |
| `5. Harness result return` | Harness execution completed or failed terminally. | Invocation Artifact reference, Invocation Receipt, failure classification when failed, provider lane if used. | Return bounded Harness Result bundle. | Silent continuation without receipt, silent state writes. | Artifact-receipt linkage is explicit and queryable. |
| `6. Guardian validation` | Harness Result bundle is available. | validation outcome, schema/conformance checks, permission conformance checks. | Accept/reject result for continuation. | Trusting harness output as self-authorizing execution. | Validation verdict and reasons are observable. |
| `7. Result return path` | Guardian validated result for continuation. | result return metadata including source thread/message, request/attempt identity, invocation id, harness id, provider lane (if relevant), artifact reference. | Controlled reinjection/reentry through existing or explicitly future-compatible path. | Collapsing authored-turn identity into execution-attempt identity; bypassing transcript semantics. | Return status is visible without requiring harness-internal logs. |
| `8. Lineage preservation` | Result return phase completed. | end-to-end lineage references from authored turn through invocation and return. | Persist bounded lineage metadata where contract-governed state exists. | Orphaning invocation records from export/restore lineage obligations. | Auditability shows no autonomous recursion and preserves ownership chain. |

## Minimax Provider Separation

Minimax separation is explicit:

- Minimax may be a model/provider option used by a harness or by Codexify provider routing.
- Minimax is not the Pi Invocation Boundary.
- The Pi Invocation Boundary must not assume Minimax.
- Any Minimax adapter or provider validation work is separate from Pi invocation governance.
- Provider catalog, health, and supported-profile truth remain governed by existing provider/config contracts.

## Command Authority and Command-Bus Relationship

- Pi-like harnesses may not invent a second command universe.
- Any Codexify-owned action must pass through the existing command bus or a future explicitly governed adapter.
- Pi output may include proposed commands, patches, summaries, or other Invocation Artifacts, but Guardian decides whether and how those become Codexify actions.
- Any future live invocation must preserve command-bus provenance and idempotency posture.

## Result Return and Transcript Integrity

Pi results must return as bounded Invocation Artifacts and Invocation Receipts before any assistant-facing continuation.

Result Return Path metadata must preserve:

- source thread id
- source message id
- request/attempt identity where applicable
- invocation id
- harness id
- provider lane if relevant
- result artifact id or stable reference

This contract aligns with message-versus-attempt doctrine and must not collapse authored turns into execution attempts.

This contract is forward-compatible with existing reinjection and one-turn reentry doctrine and does not claim that Pi execution exists today.

## Identity and Sovereignty Boundaries

- Identity remains user-owned.
- Personas do not own identity.
- Pi invocation must not write identity traits.
- Pi invocation must not infer durable identity from coding behavior.
- Pi invocation may consume only explicitly permitted project/thread/workspace context.
- Any future identity-affecting output must be proposed for user review, not silently persisted.

## Export/Restore and Lineage Obligations

If future Pi invocation records, receipts, artifacts, or result references become user-owned durable state, they must be exportable/restorable under account export/restore guarantees.

Restore semantics:

- Restore must not silently drop invocation lineage.
- If invocation artifacts cannot be restored faithfully, restore must fail closed or report explicit loss.

This contract does not implement those entities.

## Observability and Proof Surface

Future proof expectations include:

- invocation envelope inspection
- requested vs granted permissions
- harness id and harness version
- provider lane if used
- command-bus linkage if any
- result artifact and receipt linkage
- failure classification
- result return status
- evidence that no autonomous recursion occurred

Diagnostics must align with Codexify's existing observability posture. Noisy harness internals do not belong in the primary chat lane.

## Explicit Non-Goals

This contract does not:

- implement Pi SDK integration
- implement Minimax provider integration
- implement a Pi adapter
- add runtime execution
- add autonomous dispatch
- add worker orchestration
- add sandbox execution
- add UI
- widen the supported beta release promise
- authorize direct identity mutation
- authorize command-bus bypass
- replace ADR-020 doctrine

## Current-Truth Anchors and Deferrals

What is true now:

- Codexify remains in late beta hardening on `main`.
- The supported release anchor remains the local Docker Compose path.
- Guardian remains the runtime boundary for result return, lineage, and trace persistence.
- The command bus remains the canonical command/tooling lane.
- The self-extending campaign remains bounded through proposal, gate, registry, binding, resolution, activation, manual dispatch, reinjection, and one-turn reentry seams.
- Minimax is currently a provider/config lane, not the Pi Invocation Boundary.

What is not yet true by this task:

- No Pi SDK integration is implemented.
- No live Pi invocation is implemented.
- No Minimax provider change is made.
- No autonomous coding-agent runtime is enabled.
- No worker orchestration or sandbox execution is added.

Explicit deferrals in this task:

- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- provider implementation docs
- command-bus runtime docs

## Recommended First Implementation Slice

Narrow first slice recommendation:

- backend-only Pi invocation envelope contract
- no live Pi SDK call
- no Minimax provider change
- no command execution
- no worker orchestration
- no transcript persistence
- pure validation of envelope shape, provenance, permission posture, and receipt shape
