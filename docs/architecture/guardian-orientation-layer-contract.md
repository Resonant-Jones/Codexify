# Guardian Orientation Layer Contract

Last updated: 2026-07-01

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/kb-validity-matrix.md
- docs/architecture/guardian-role-and-delegation-boundary.md
- docs/architecture/guardian-operator-index.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/system-overview.md
- docs/architecture/flows.md
- docs/architecture/config-and-ops.md
- docs/architecture/modules-and-ownership.md
- docs/architecture/data-and-storage.md
- docs/architecture/router-decision-table.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/self-extending-agent-plugin-system.md

## Classification

- Classification: Aligned with existing ADR(s) / architecture contracts.
- Governing docs and contracts:
  - Guardian Role and Delegation Boundary
  - Guardian Operator Index
  - Agent Protocol Operations Index
  - Retrieval Router Decision Table
  - KB Validity Matrix
  - Runtime Protocol Token Contract
  - Chat Runtime Contract
  - Pi Invocation Boundary Contract
  - Agent Tool Loop Contract
  - Self-Extending Agent Plugin System
- Reason:
  - This contract defines a docs-first orientation doctrine for Guardian. It clarifies how docs are prioritized, retrieved, and proven before Guardian governs work or prepares delegation packets, without changing runtime behavior or release support.

## 1. Purpose

The Guardian Orientation Layer is the doctrine for how Guardian becomes aware of Codexify's canonical documentation before it explains system state, judges what is current, or prepares delegation packets.

This is a docs-only architecture contract. It does not implement runtime behavior, docs ingestion, codebase indexing, retrieval-router behavior, context injection, Pi/Codex/Claude execution, command execution, worker orchestration, or release support.

## 2. Problem Statement

A repository can be mounted into Docker, present on disk, or readable to a process without Guardian being able to retrieve, prioritize, cite, or reason over those documents during chat.

The important distinctions are:

- filesystem visibility
- document ingestion
- chunking and indexing
- retrieval
- context injection
- answer grounding and citation
- runtime proof

Those stages are related, but they are not interchangeable. A later stage cannot be assumed from an earlier one.

## 3. Relationship to Guardian Boundary

This contract refines the docs-first awareness that the [Guardian Role and Delegation Boundary](./guardian-role-and-delegation-boundary.md) already requires.

That boundary says Guardian is the governing role and that docs ingestion is an orientation requirement, not an execution requirement. This contract defines the bounded corpus and priority rules that make that orientation concrete.

Orientation belongs to Guardian Composite operation, not to any single model identity. A model can participate in orientation, but it does not own the doctrine by itself.

## 4. Orientation Layer Definition

The Orientation Layer is the bounded set of docs, indexes, retrieval policy, freshness rules, and proof surfaces Guardian uses to answer:

- what is true
- what is safe
- what is current
- what is out of scope
- what should be delegated

The layer does not replace current-state truth, runtime evidence, or governed delegation. It organizes them.

## 5. Canonical Corpus Tiers

The canonical corpus is ordered by retrieval and authority priority. Some documents support more than one tier, but each tier has a primary use.

| Tier | Name | Primary purpose | Typical docs |
|---|---|---|---|
| Tier 0 | Current-state and release truth | Short-horizon operational truth and supported-path reality | `docs/architecture/00-current-state.md` |
| Tier 1 | KB routing and validity | Tell Guardian which docs are safe to trust and how to route into the corpus | `docs/architecture/README.md`, `docs/architecture/kb-validity-matrix.md`, `docs/architecture/router-decision-table.md` |
| Tier 2 | Runtime architecture and critical flows | Describe implemented components, flow order, config, seams, and storage | `docs/architecture/system-overview.md`, `docs/architecture/flows.md`, `docs/architecture/config-and-ops.md`, `docs/architecture/modules-and-ownership.md`, `docs/architecture/data-and-storage.md` |
| Tier 3 | Operator protocols and issue/task rituals | Map operator questions to docs, probes, and work rituals | `docs/architecture/guardian-operator-index.md`, `docs/architecture/agent-protocol-operations.md`, relevant `docs/tasks/` and `docs/Campaign/` artifacts |
| Tier 4 | Delegation and harness boundaries | Define authority, lineage, bounded harnesses, and result-return doctrine | `docs/architecture/guardian-role-and-delegation-boundary.md`, `docs/architecture/pi-invocation-boundary-contract.md`, `docs/architecture/agent-tool-loop-contract.md`, `docs/architecture/self-extending-agent-plugin-system.md` |
| Tier 5 | UI/design canon | Support UI work without becoming backend runtime truth | `docs/architecture/codexify_workspace_surface_spec_v_1.md`, `docs/architecture/persona-studio.md`, `docs/architecture/persona-studio-spec.md`, `docs/dev/ARTIFACT*.md` |
| Tier 6 | Supplementary or proof artifacts | Prove exact surfaces only; never replace governing docs | `docs/audits/`, `docs/tasks/`, `docs/Campaign/`, proof reports, generated proof artifacts |

## 6. Initial Required Documents

The first orientation corpus must explicitly include:

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/kb-validity-matrix.md`
- `docs/architecture/guardian-operator-index.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/router-decision-table.md`
- `docs/architecture/guardian-role-and-delegation-boundary.md`
- `docs/architecture/pi-invocation-boundary-contract.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `docs/architecture/self-extending-agent-plugin-system.md`

These are the first documents Guardian should try to retrieve and prioritize before it governs work or prepares a delegation packet. The list can grow, but the priority rules below do not change.

## 7. Source Priority Rules

- `docs/architecture/00-current-state.md` wins for short-horizon release truth.
- `docs/architecture/README.md` and `docs/architecture/kb-validity-matrix.md` route readers to the right document class and tell Guardian which docs are safe to treat as evidence.
- Operator indexes route questions, but they do not prove runtime behavior.
- Proof artifacts prove only the exact surfaces they tested.
- Docs-only contracts do not imply implementation.

If sources conflict, the higher-priority current-state or validity source wins.

## 8. Ingestion vs Retrieval vs Injection vs Proof

### Filesystem visibility

Guardian can see that a file exists on disk or in a mounted repository.

### Document ingestion

The document is imported into a system that can track it as a known source.

### Chunking and indexing

The document is broken into retrievable units and recorded in an index or store.

### Retrieval

Guardian selects the document or chunk because it is relevant to the current question, corpus tier, and freshness rules.

### Context injection

Retrieved material is inserted into the executed context bundle used to answer the question or prepare a packet.

### Answer grounding and citation

The answer is constrained by the retrieved material and names or cites the governing sources.

### Runtime proof

The executed path shows operator-visible evidence that the intended stage actually happened.

Filesystem visibility is not orientation. Guardian is oriented only when canonical docs are ingested or otherwise retrievable, prioritized by current-truth rules, injected into the executed context when needed, and proven through operator-visible evidence.

Later stages cannot be assumed from earlier stages.

## 9. Codebase Reasoning Boundary

Guardian may use read-only codebase reasoning to locate seams, estimate blast radius, and prepare delegation packets.

That reasoning is separate from write or execute authority.

Writes, tests, patches, and commits belong to a separate governed harness lane. The orientation layer can point to the work, but it does not perform the mutation.

## 10. Delegation Readiness Gate

Before Guardian prepares a Pi/Codex/Claude delegation packet, it should have:

- the current-state doc retrieved
- the relevant subsystem doc retrieved
- the relevant operator or delegation boundary retrieved
- target files or directories identified from architecture docs or read-only code search
- proof commands identified
- non-goals and release boundaries preserved

If any of those are missing, the packet is still draft-only and should not be treated as ready for delegated execution.

## 11. Non-Goals

This contract does not provide:

- runtime implementation
- docs ingestion implementation
- repo scanner implementation
- vector-store migration
- retrieval-router behavior change
- Pi/Codex/Claude integration
- command execution
- release promise expansion

## 12. Proof Surfaces

Future proof classes are intentionally separate:

- Docs existence proof: the contract and README route exist.
- Filesystem proof: the backend container can read selected docs paths.
- Ingestion proof: selected docs appear as indexed documents with ready embedding status.
- Retrieval proof: Guardian can retrieve current-state and operator docs for an operator question.
- Injection proof: retrieved docs enter the executed completion context bundle.
- Answer proof: Guardian answers with the correct source priority and cites or names the governing docs.
- Delegation packet proof: Guardian creates a task packet that uses the orientation corpus without requiring write authority.

These proof classes are ordered, but each one proves only its own layer.

## 13. Required Language

Filesystem visibility is not orientation. Guardian is oriented only when canonical docs are ingested or otherwise retrievable, prioritized by current-truth rules, injected into the executed context when needed, and proven through operator-visible evidence.
