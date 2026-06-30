# Guardian Role and Delegation Boundary

Purpose: Define the boundary between Guardian as a backend directory, Guardian as a governing role, Guardian as a composite operational entity, and Guardian-operative delegated harnesses so the name stays precise as delegation and retrieval surfaces grow.

Last updated: 2026-06-30

Classification: docs-only architecture contract. It defines naming, authority, and delegation semantics only. It does not implement runtime behavior, docs ingestion, codebase indexing, provider execution, command execution, worker orchestration, or transcript persistence.

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/modules-and-ownership.md
- docs/architecture/system-overview.md
- docs/architecture/config-and-ops.md
- docs/architecture/data-and-storage.md

## 1. Purpose

Guardian needs a precise boundary because the same name is used for multiple related surfaces:

- a concrete backend directory and runtime namespace
- a governing operator role
- a composite operational entity that coordinates multiple subsystems under one authority boundary

Without that boundary, later docs can blur directory ownership, role ownership, and delegated execution ownership into one implied sovereignty claim.

## 2. Problem Statement

The word "Guardian" can currently point to several different things:

- a code namespace in the backend tree
- the role that interprets policy and decides how work should proceed
- the operational system that combines backend modules, retrieval, workers, storage, and approved harnesses
- a delegated harness acting under Guardian-issued scope

That ambiguity matters before docs ingestion, codebase reasoning, and Pi/Codex/Claude delegation expand because each surface has different authority and proof expectations.

If the layers are not separated, a delegated harness can be mistaken for Guardian itself, and a directory can be mistaken for the full role or the full composite.

## 3. Canonical Guardian Layers

The canonical layers are:

- Guardian Directory
- Guardian Role
- Guardian Composite
- Guardian-operative delegated harness

Read them in that order.

## 4. Guardian Directory

Guardian Directory is the concrete backend/runtime namespace and code ownership surface.

It includes modules such as:

- `guardian/routes`
- `guardian/core`
- `guardian/context`
- `guardian/workers`
- `guardian/command_bus`
- `guardian/db`
- related runtime modules under the Guardian tree

Directory membership alone does not define the full Guardian role.

A directory can host implementation seams without carrying authority to interpret policy, approve delegation, or own transcript lineage.

## 5. Guardian Role

Guardian Role is the governing operator role responsible for:

- orientation
- policy
- retrieval posture
- task framing
- delegation decisions
- operator-facing interpretation

The role may be occupied by different models or providers without changing the role contract.

The role is the authority boundary, not the directory and not any single harness implementation.

## 6. Guardian Composite

Guardian Composite is the operational entity formed when the Guardian backend namespace, active model, indexed docs, retrieval stack, context broker, workers, command bus, storage, and approved harnesses cooperate under the Guardian authority boundary.

This is an operational and entity concept similar to a legal or agentic entity.

It is not a claim of consciousness, sentience, or supernatural status.

The composite may span multiple components, but the composite remains governed by the Guardian Role rather than dissolving into whichever component is active at the moment.

## 7. Delegated Harness Semantics

Pi, Codex, Claude, or another harness is Guardian-operative when it acts only inside a Guardian-issued envelope with bounded scope, permissions, lineage, and return expectations.

In that mode, the harness may function as Guardian's operative hand.

It does not inherit Guardian sovereignty.

A Guardian-operative harness is still a delegated component, not the authority source.

## 8. Sovereignty Boundary

Guardian retains:

- policy decision authority
- permission scope
- source-thread and source-message lineage
- transcript ownership
- result validation
- operator-facing explanation
- receipt and proof expectations

Delegated harnesses must not directly redefine:

- identity
- runtime tokens
- export/restore lineage
- queue semantics
- acceptance semantics
- release posture

Any harness output that changes one of those surfaces must still be mediated by Guardian authority and visible receipts.

## 9. Documentation Ingestion Requirement

Guardian must ingest or retrieve architecture and operator docs before it can reliably govern Codexify work.

The first critical docs class is:

- `00-current-state.md`
- `README.md`
- `guardian-operator-index.md`
- `config-and-ops.md`
- `flows.md`
- `modules-and-ownership.md`
- related architecture contracts

This is an orientation and retrieval requirement, not a coding-agent execution requirement.

## 10. Codebase Reasoning Requirement

Guardian only needs codebase reasoning when it is:

- locating implementation seams
- estimating blast radius
- preparing delegation packets

Full write and execute authority belongs to a separate governed harness lane.

That lane may be under Guardian direction, but it is still a distinct execution boundary.

## 11. Non-Goals

This contract does not:

- implement runtime behavior
- implement docs ingestion
- implement Pi/Codex/Claude integration
- implement command execution
- implement an autonomous coding-agent loop
- widen the release promise
- claim consciousness, sentience, or supernatural entity status

## 12. Proof Surfaces

Documentation proof:

- this contract exists and is linked from `README.md`

Future docs-ingestion proof:

- Guardian can retrieve and cite current-state and operator docs during chat

Future delegation proof:

- a harness returns a bounded artifact or receipt under Guardian scope

Future codebase reasoning proof:

- Guardian can identify likely code seams without write authority

## 13. Required Language

Guardian is the governing role. Pi, Codex, Claude, workers, tools, and retrieval systems may become Guardian-operative components only when acting under Guardian-scoped authority, with preserved lineage, bounded permissions, and operator-visible receipts.
