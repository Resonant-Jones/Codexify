# Guardian Orientation Layer Contract

## Purpose

The Guardian Orientation Layer is the doctrine for how Guardian becomes aware of Codexify's canonical docs before governing work, explaining system state, or preparing delegation packets.

This is a docs-only architecture contract. It does not implement runtime behavior, docs ingestion, codebase indexing, retrieval-router behavior, Pi/Codex/Claude execution, command execution, worker orchestration, sandboxing, or release support.

## Problem Statement

A repository mounted into Docker or present on disk does not automatically mean Guardian can retrieve, prioritize, cite, or reason over those files during chat.

Filesystem visibility, ingestion, indexing, retrieval, context injection, and proof are separate stages. Treating them as equivalent causes false confidence: a file can be mounted without being indexed, indexed without being retrievable, retrievable without being injected, and injected without being proven in an operator-visible way.

## Relationship to Guardian Boundary

This contract is subordinate to [`Guardian Role and Delegation Boundary`](./guardian-role-and-delegation-boundary.md).

Orientation belongs to Guardian Composite operation, not to any single model identity. A provider or model may participate in orientation, but the governing boundary is the composite operational role that combines docs, retrieval, policy, and operator-facing explanation.

## Orientation Layer Definition

The Orientation Layer is the bounded set of docs, indexes, retrieval policy, freshness rules, and proof surfaces Guardian uses to answer:

- what is true
- what is safe
- what is current
- what is out of scope
- what should be delegated

The layer is intentionally narrower than the whole repository. It is the curated knowledge boundary Guardian may consult before reasoning over codebase seams or preparing a task packet.

## Canonical Corpus Tiers

Guardian should treat the corpus as tiered, not flat:

- Tier 0: Current-state and release truth
- Tier 1: KB routing and validity
- Tier 2: Runtime architecture and critical flows
- Tier 3: Operator protocols and issue/task rituals
- Tier 4: Delegation and harness boundaries
- Tier 5: UI/design canon
- Tier 6: Supplementary or proof artifacts

Tier order expresses orientation priority, not storage layout. Higher tiers may exist on disk without being authoritative for a given question.

## Initial Required Documents

The first orientation corpus should include:

- `/docs/architecture/00-current-state.md`
- `/docs/architecture/README.md`
- `/docs/architecture/kb-validity-matrix.md`
- `/docs/architecture/guardian-operator-index.md`
- `/docs/architecture/agent-protocol-operations.md`
- `/docs/architecture/system-overview.md`
- `/docs/architecture/flows.md`
- `/docs/architecture/config-and-ops.md`
- `/docs/architecture/modules-and-ownership.md`
- `/docs/architecture/data-and-storage.md`
- `/docs/architecture/router-decision-table.md`
- `/docs/architecture/guardian-role-and-delegation-boundary.md`
- `/docs/architecture/pi-invocation-boundary-contract.md`
- `/docs/architecture/agent-tool-loop-contract.md`
- `/docs/architecture/self-extending-agent-plugin-system.md`

## Source Priority Rules

- `/docs/architecture/00-current-state.md` wins for short-horizon release truth.
- `/docs/architecture/README.md` and `/docs/architecture/kb-validity-matrix.md` route readers to the right doc class.
- Operator indexes route questions but do not prove runtime behavior.
- Proof artifacts prove only the exact surfaces they tested.
- Docs-only contracts do not imply implementation.

## Ingestion vs Retrieval vs Injection vs Proof

- Filesystem visibility: the docs exist on disk or inside a mounted repository path.
- Document ingestion: the system has accepted the docs into an ingestible corpus.
- Chunking/indexing: the docs have been broken into retrievable units and indexed.
- Retrieval: Guardian can select the right docs for a question or task.
- Context injection: retrieved docs are placed into the executed completion context.
- Answer grounding/citation: the answer is explicitly grounded in the retrieved docs and can name or cite them.
- Runtime proof: an operator-visible surface demonstrates the executed path actually used the docs and obeyed source-priority rules.

Later stages cannot be assumed from earlier stages. Each stage needs its own evidence.

## Codebase Reasoning Boundary

Guardian may need read-only codebase reasoning to locate seams, estimate blast radius, and create delegation packets.

That reasoning is separate from write/execute authority. Reads may inform planning, but writes, tests, patches, and commits belong to a separate governed harness lane.

## Delegation Readiness Gate

Before preparing a Pi/Codex/Claude delegation packet, Guardian should have at minimum:

- current-state doc retrieved
- relevant subsystem doc retrieved
- relevant operator/delegation boundary retrieved
- target files or directories identified from architecture docs or read-only code search
- proof commands identified
- non-goals and release boundaries preserved

## Non-Goals

- No runtime implementation.
- No docs ingestion implementation.
- No repo scanner implementation.
- No vector-store migration.
- No retrieval-router behavior change.
- No Pi/Codex/Claude integration.
- No command execution.
- No release promise expansion.

## Proof Surfaces

Future proof classes for this contract are:

- Docs existence proof: contract and README route exist.
- Filesystem proof: backend container can read selected docs paths.
- Ingestion proof: selected docs appear as indexed documents with ready embedding status.
- Retrieval proof: Guardian can retrieve current-state and operator docs for an operator question.
- Injection proof: retrieved docs enter the executed completion context bundle.
- Answer proof: Guardian answers with correct source priority and cites or names the governing docs.
- Delegation packet proof: Guardian creates a task packet that uses the orientation corpus without requiring write authority.

## Required Language

Filesystem visibility is not orientation. Guardian is oriented only when canonical docs are ingested or otherwise retrievable, prioritized by current-truth rules, injected into the executed context when needed, and proven through operator-visible evidence.
