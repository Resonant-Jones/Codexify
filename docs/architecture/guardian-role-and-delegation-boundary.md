# Guardian Role and Delegation Boundary

## 1. Purpose

The Guardian name needs a precise architecture boundary because Codexify uses it across several related surfaces: a backend/runtime namespace, a governing AI/operator role, and the composite operational entity formed when runtime systems cooperate under one authority boundary. This contract separates those meanings so future docs ingestion, codebase reasoning, and Pi/Codex/Claude-style delegation can be discussed without widening current release support or blurring authority.

This is a docs-only architecture contract. It does not implement runtime behavior, docs ingestion, codebase indexing, Pi/Codex/Claude execution, command execution, worker orchestration, sandboxing, SDK integration, transcript persistence, or release support.

## 2. Problem Statement

"Guardian" can ambiguously mean a code namespace, an AI role, a runtime system, or a delegated harness acting on a task. That ambiguity is risky because directory membership, model behavior, runtime cooperation, and external-harness activity each carry different authority and proof requirements.

The ambiguity matters before Codexify expands docs ingestion, codebase reasoning, and Pi/Codex/Claude delegation. A delegated harness may act under Guardian direction, but it must not silently become Guardian identity, bypass policy, redefine runtime tokens, own transcripts, mutate release posture, or treat request acceptance as completion.

## 3. Canonical Guardian Layers

Codexify uses four canonical Guardian layers:

1. **Guardian Directory**: the concrete backend/runtime namespace and code ownership surface.
2. **Guardian Role**: the governing operator role responsible for policy-aware interpretation and delegation decisions.
3. **Guardian Composite**: the operational entity formed when approved Codexify runtime components cooperate under the Guardian authority boundary.
4. **Guardian-operative delegated harness**: an external or internal harness acting only inside a Guardian-issued envelope with bounded scope, permissions, lineage, and return expectations.

These layers are related, but none of the lower-level surfaces automatically inherits the full authority of another layer.

## 4. Guardian Directory

Guardian Directory means the concrete backend/runtime namespace and code ownership surface where Guardian-owned application responsibilities live. Examples include `guardian/routes`, `guardian/core`, `guardian/context`, `guardian/workers`, `guardian/command_bus`, `guardian/db`, and related runtime modules.

Directory membership is implementation ownership, not role sovereignty. A module under the Guardian namespace may participate in Guardian behavior, but directory placement alone does not define the full Guardian Role, prove release readiness, or authorize delegation semantics.

## 5. Guardian Role

Guardian Role means the governing operator role responsible for orientation, policy, retrieval posture, task framing, delegation decisions, and operator-facing interpretation. The role is the authority boundary for deciding what a task means, what evidence is required, what permissions apply, and how results should be explained back to the operator.

The Guardian Role may be occupied by different models or providers without changing the role contract. Provider substitution does not change Guardian's policy obligations, lineage obligations, release-truth constraints, or operator-facing explanation duties.

## 6. Guardian Composite

Guardian Composite means the operational entity formed when the Guardian backend namespace, active model, indexed docs, retrieval stack, context broker, workers, command bus, storage, and approved harnesses cooperate under the Guardian authority boundary.

The composite is an operational/entity concept similar to a legal or agentic entity. It describes coordinated authority and responsibility across components; it is not a claim of consciousness, sentience, personhood, supernatural status, or unbounded agency.

## 7. Delegated Harness Semantics

Pi, Codex, Claude, or another harness is Guardian-operative only when it acts inside a Guardian-issued envelope with bounded scope, permissions, lineage, and return expectations. The envelope must identify what the harness may inspect or change, what proof it must return, and how its result flows back to Guardian-owned validation and operator-facing explanation.

A harness may act as Guardian's operative hand, but it does not inherit Guardian sovereignty. Acting under Guardian scope means the harness is subordinate to Guardian policy, provenance, transcript lineage, command authority, and receipt requirements.

Guardian is the governing role. Pi, Codex, Claude, workers, tools, and retrieval systems may become Guardian-operative components only when acting under Guardian-scoped authority, with preserved lineage, bounded permissions, and operator-visible receipts.

## 8. Sovereignty Boundary

Guardian retains:

- policy decision authority
- permission scope
- source-thread/source-message lineage
- transcript ownership
- result validation
- operator-facing explanation
- receipt/proof expectations

Delegated harnesses must not directly redefine identity, runtime tokens, export/restore lineage, queue semantics, acceptance semantics, or release posture. They must return bounded artifacts, receipts, and evidence for Guardian-owned validation rather than treating their own execution as user-visible completion.

## 9. Documentation Ingestion Requirement

Guardian must ingest or retrieve architecture and operator docs before it can reliably govern Codexify work. The first critical docs class includes `00-current-state.md`, `README.md`, `guardian-operator-index.md`, `config-and-ops.md`, `flows.md`, `modules-and-ownership.md`, and related architecture contracts.

Docs ingestion is an orientation/retrieval requirement, not a coding-agent execution requirement. It helps Guardian frame tasks, cite current truth, and avoid stale release claims; it does not itself implement autonomous execution, delegation, command routing, or runtime proof.

## 10. Codebase Reasoning Requirement

Guardian needs codebase reasoning when locating implementation seams, estimating blast radius, or preparing delegation packets. Codebase reasoning may help identify likely files, relevant tests, ownership boundaries, and validation surfaces.

Full write or execute authority belongs to a separate governed harness lane. Reasoning about the codebase does not imply direct mutation authority, release support, command execution, or a shipped autonomous coding-agent loop.

## 11. Non-Goals

This contract does not provide:

- runtime implementation
- docs ingestion implementation
- Pi/Codex/Claude integration
- command execution
- worker orchestration
- sandboxing
- SDK integration
- transcript persistence
- autonomous coding-agent loop
- release promise expansion
- claims of consciousness, sentience, personhood, or supernatural entity status

## 12. Proof Surfaces

- Documentation proof: this contract exists and is linked from the architecture README.
- Future docs-ingestion proof: Guardian can retrieve and cite current-state/operator docs during chat.
- Future delegation proof: a harness returns a bounded artifact/receipt under Guardian scope.
- Future codebase reasoning proof: Guardian can identify likely code seams without write authority.

## 13. Required Language

Guardian is the governing role. Pi, Codex, Claude, workers, tools, and retrieval systems may become Guardian-operative components only when acting under Guardian-scoped authority, with preserved lineage, bounded permissions, and operator-visible receipts.
