# Pi Invocation Boundary Contract

Purpose: define a Codexify-native boundary for future Pi-like external coding-agent harness invocation while preserving Guardian ownership of policy, lineage, provenance, command authority, and result return.
Last updated: 2026-05-08
Source anchors:
- docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md
- docs/architecture/adr/010-self-extending-agent-plugin-system.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/config-and-ops.md

## Classification

- Architecture-impacting documentation contract.
- Aligned with existing ADRs and contracts.
- Defines boundary doctrine only; no runtime implementation is introduced.

## Governing ADRs and Contracts

- ADR-020: Guardian Mediated Coding Agent Execution Contract
- ADR-010: Self-Extending Agent Plugin System
- Agent Tool Loop Contract
- Chat Runtime Contract
- Runtime Protocol Token Contract
- Account Export + Restore Contract
- Existing identity/IDDB policy and Persona Studio boundary rules

## A) Purpose and Problem Statement

Codexify needs a bounded Pi Invocation Boundary before any Pi SDK or Pi-like harness integration so external coding execution cannot silently become a second runtime authority.

Pi-like harnesses must be treated as external or mediated execution harnesses, not as unrestricted self-modifying runtime control planes. Guardian remains the owner of:

- request policy
- transcript lineage
- provenance
- command authority
- result return

Minimax, if used, is a provider/model lane only. It must not be hardwired into Pi invocation governance.

## B) Canonical Terminology

Use these terms exactly and consistently:

- `Pi Invocation Boundary`: the bounded Codexify contract for mediated invocation of a Pi-like harness.
- `Pi-like Harness`: an external or adapter-mediated coding-agent execution substrate.
- `Guardian-Mediated Invocation`: a Pi invocation path that is authorized, enveloped, and validated by Guardian.
- `Invocation Receipt`: structured execution receipt returned from a harness run.
- `Invocation Artifact`: bounded result artifact reference or payload returned by the harness.
- `Harness Result`: the harness output bundle, including receipt, artifact references, and terminal status.
- `Result Return Path`: the Guardian-owned path that reenters Codexify runtime and transcript flow.
- `Provider Lane`: the model/provider path used by execution components.
- `Minimax Provider Lane`: the Minimax-specific provider lane, if selected.
- `Guardian Ownership Boundary`: the non-bypass ownership boundary for policy, lineage, provenance, and return.

## C) Boundary Model

Codexify may later delegate one bounded request to a Pi-like harness.

Non-negotiable boundary rules:

- Pi-like harnesses must not bypass Guardian policy, command-bus authority, transcript ownership, provenance, or export/restore obligations.
- Pi-like harnesses must not directly mutate IDDB / Identity Mirror.
- Pi-like harnesses must not directly mutate persona ownership rules.
- Pi-like harnesses must not directly redefine runtime protocol tokens.
- Pi-like harnesses must not directly alter message-versus-attempt semantics.
- Pi-like harnesses must not silently write to core runtime state.
- This contract must not create an autonomous recursive execution loop.

## D) Invocation Lifecycle

Canonical future lifecycle:

1. Guardian receives an authored request.
2. Guardian resolves whether Pi invocation is permitted.
3. Guardian creates a bounded invocation envelope.
4. Pi-like harness executes externally or in a mediated adapter lane.
5. Harness returns a result artifact and receipt.
6. Guardian validates the result.
7. Guardian returns the result through the existing reinjection/reentry path or an explicitly future-compatible return path.
8. Guardian preserves lineage and auditability.

### Phase Contract Matrix

| Phase | Entry condition | Required artifact or metadata | Allowed side effects | Prohibited side effects | Proof / observability expectation |
|---|---|---|---|---|---|
| 1. Request intake | Authored user request exists in a Guardian-owned thread | `thread_id`, `source_message_id`, requester identity, request intent summary | Intake validation and policy precheck metadata | Direct harness execution, transcript mutation by harness | Request accepted with Guardian-owned lineage anchors |
| 2. Permission resolution | Intake metadata complete and policy engine reachable | permission decision, requested vs granted scope, boundary flags | Decision record creation | Scope widening by harness, silent policy bypass | Inspectable granted-vs-requested decision surface |
| 3. Envelope creation | Invocation permitted | `invocation_id`, `harness_id`, bounded instructions, context scope summary, permission posture, request/attempt identity | Creation of bounded invocation envelope | Runtime token mutation, identity writes, command execution side effects | Envelope inspection surface with canonical fields |
| 4. Harness execution | Valid envelope delivered to adapter lane | adapter/harness execution metadata, harness version, optional provider lane | External/mediated execution inside granted scope | Direct writes to Codexify core state, autonomous recursion | Terminal execution status plus harness identity/version evidence |
| 5. Receipt + artifact return | Harness reaches terminal state | `Invocation Receipt`, `Invocation Artifact` references, failure classification | Result packaging only | Assistant-visible continuation before Guardian ingest | Receipt/artifact linkage to `invocation_id` |
| 6. Guardian validation | Harness result returned to Guardian | schema validation outcome, provenance checks, policy conformance checks | Validation report, acceptance/rejection decision | Silent acceptance of malformed or out-of-scope output | Validation outcome with explicit failure class when rejected |
| 7. Result return | Validation succeeded or explicitly failed | `Harness Result`, `Result Return Path` metadata, reinjection/reentry compatibility markers | Reinjection/reentry metadata emission | Collapsing authored turn into attempt identity, bypassing return path | Reentry status plus source-message/attempt linkage |
| 8. Lineage preservation | Return path completed or terminal failure recorded | lineage chain (`thread_id`, `source_message_id`, request/attempt, `invocation_id`, receipt/artifact refs) | Durable lineage/provenance recording when persisted | Silent lineage drop, export-unsafe references | Audit-ready lineage report and traceable invocation closure |

## E) Minimax Provider Separation

Minimax separation is explicit:

- Minimax may be a model/provider option used by a harness or by Codexify provider routing.
- Minimax is not the Pi boundary.
- This contract must not assume Minimax.
- Any Minimax adapter or provider validation task is separate from Pi invocation governance.
- Provider catalog, health, and supported-profile truth remain governed by existing provider and config contracts.

## F) Command Authority and Command-Bus Relationship

Pi-like harnesses may not invent a second command universe.

- Any Codexify-owned action must pass through the existing command bus or a future explicitly governed adapter.
- Pi output may include proposed commands, patches, summaries, or artifacts.
- Guardian decides whether and how those proposals become Codexify actions.
- Any future live invocation must preserve command-bus provenance and idempotency posture.

## G) Result Return and Transcript Integrity

Pi results must return as bounded artifacts and receipts before any assistant-facing continuation.

Result return must preserve:

- `source_thread_id`
- `source_message_id`
- request/attempt identity where applicable
- `invocation_id`
- `harness_id`
- provider lane when relevant
- result artifact id/reference

This contract aligns with message-versus-attempt doctrine and must not collapse authored turns into execution attempts.

This contract must remain compatible with existing reinjection and one-turn reentry contracts without claiming that live Pi execution exists today.

## H) Identity and Sovereignty Boundaries

Identity remains user-owned.

- Personas do not own identity.
- Pi invocation must not write identity traits.
- Pi invocation must not infer durable identity from coding behavior.
- Pi invocation may consume only explicitly permitted project/thread/workspace context.
- Any future identity-affecting output must be proposed for user review, never silently persisted.

## I) Export/Restore and Lineage Obligations

If future Pi invocation records become user-owned durable state, they must be exportable/restorable.

- Durable invocation records, receipts, artifacts, and references must preserve lineage across export/restore.
- Restore must not silently drop invocation lineage.
- If artifacts cannot be restored faithfully, restore must fail closed or report explicit loss.
- This document defines obligations only and does not implement new entities.

## J) Observability and Proof Surface

Future proof expectations include:

- invocation envelope inspection
- requested vs granted permissions
- harness id and harness version
- provider lane when used
- command-bus linkage when any Codexify action is proposed or executed
- result artifact and receipt linkage
- failure classification
- result return status
- explicit no-autonomous-recursion evidence

Diagnostics should align with current Codexify observability posture. Noisy harness internals should not be pushed into the primary chat lane.

## K) Explicit Non-Goals

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
- replace ADR-020

## L) Recommended First Implementation Slice

Recommended first implementation slice:

- backend-only Pi invocation envelope contract
- no live Pi SDK call
- no Minimax provider change
- no command execution
- no worker orchestration
- no transcript persistence
- pure validation of envelope shape, provenance, permission posture, and receipt shape

## ADR Impact

Classification: aligned with existing ADRs.

Governing ADRs/contracts:

- ADR-020 Guardian Mediated Coding Agent Execution Contract
- ADR-010 Self-Extending Agent Plugin System
- Agent Tool Loop Contract
- Chat Runtime Contract
- Runtime Protocol Token Contract
- Account Export + Restore Contract
- existing identity/IDDB and Persona Studio boundary doctrine

Reason:

This contract defines a new architecture boundary for Pi-like harness invocation and clarifies provider separation for Minimax. It does not implement runtime behavior.

## Current-Truth Anchors

What is true now:

- Codexify is in late beta hardening on `main`.
- The supported release anchor remains local Docker Compose.
- Guardian remains the runtime boundary for result return, lineage, and trace persistence.
- The command bus remains the canonical command/tooling layer.
- The self-extending campaign has bounded backend seams through proposal, gate, registry, binding, resolution, activation, manual dispatch, reinjection, and one-turn reentry.
- Minimax appears as provider/config lane, not as a Pi invocation boundary.

What is not true now:

- No Pi SDK integration is implemented by this task.
- No live Pi invocation exists by this task.
- No Minimax provider change is made by this task.
- No autonomous coding-agent runtime is enabled by this task.
- No worker orchestration or sandbox execution is added by this task.

## Documentation Follow-Through and Deferrals

Updated by this task:

- `docs/architecture/pi-invocation-boundary-contract.md`
- `docs/architecture/self-extending-agent-plugin-system.md` (minimal cross-reference)
- `docs/architecture/README.md` (routing guidance)

Explicitly deferred by this task:

- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- provider implementation docs
- command-bus runtime docs
