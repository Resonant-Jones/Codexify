# ADR-056: Document Lifecycle Graph Control Plane

## Status

Accepted.

## Date

2026-08-07

## Acceptance

- Accepted: 2026-08-07
- Human approver: Resonant Jones

## Context

Codexify's repository contains current-state authority, accepted ADRs, normative contracts, structural maps, operator guidance, design canon, product specifications, proofs, generated reports, task packets, campaign material, compatibility pointers, and historical archives. These artifacts have different authority, lifecycle, freshness, evidence, and retrieval semantics, but most share the same Markdown namespace.

Axis Node already defines source authority, evidence labels, source identifiers, a static source map, and an Orientation Receipt. ADR-042 and the Canonical Audit Evidence Contract already require orthogonal authority, proof, freshness, disposition, and lineage semantics for audit evidence. Neither surface currently provides a repository-wide document identity graph, deterministic source resolver, or graph-aware retrieval implementation.

Paths alone are not durable identity. Modification time is not freshness. Document volume is not authority. A generated report is not proof, and a graph projection must not become a second owner of repository truth.

## Decision

Codexify adopts the Document Lifecycle Graph (DLG): a repository-native, schema-governed property graph over governed documents.

The DLG uses stable document identities independent of file paths, orthogonal lifecycle axes, typed directed relationships, scope-specific authority profiles, and bounded Agent Reading Packets. Git remains the canonical persistence layer for hand-reviewed document metadata. Aggregate graphs, reports, vector metadata, relational views, RDF exports, in-memory graphs, and Neo4j projections remain derived, disposable, and reconstructable.

The normative design is the [Document Lifecycle Graph Contract](../document-lifecycle-graph-contract.md). Its two Draft 2020-12 schemas define document-graph records and Agent Reading Packets. Acceptance establishes the architecture and governance model only; it does not implement the future tooling, projections, retrieval integration, or runtime surfaces described by the contract.

## Authority and truth boundary

- `docs/architecture/00-current-state.md` retains short-horizon release-truth authority.
- Accepted ADRs retain decision authority inside their declared scopes.
- Current code, focused tests, and live proof retain implementation-evidence roles; graph metadata cannot replace or manufacture them.
- Authority is scope-specific and query-specific. The DLG defines no universal truth score and no LLM-generated authority score.
- Axis Node remains a portable reasoning interface. The DLG evolves its source-map model without creating a parallel truth store or granting an Axis instance execution or approval authority.
- Human review remains required for future ADR acceptance, canonicalization, supersession, contradiction resolution, quarantine, and destructive migration decisions.

## Canonical persistence decision

Future hand-reviewed node records will live at `docs/knowledge-graph/nodes/<stable-document-id>.json`. Generated aggregate and report files will live under `docs/knowledge-graph/generated/`. Agent Reading Packets will be transient by default and may be committed only when a workflow requires an inspectable source-selection receipt.

Machine-critical DLG schemas, nodes, generated projections, and persisted packets must remain ordinary Git text so agents and connector APIs can read them without Git LFS hydration. External graph or retrieval stores may cache or project the records but may not become their sole owner.

This task creates schemas and illustrative examples only. It does not create the node corpus or generated output directories.

## Consequences

- Renames and moves can preserve document identity and graph lineage.
- Lifecycle, freshness, disposition, authority, and evidence remain independently inspectable.
- Compatibility pointers, superseded sources, contradictions, and historical proofs can remain visible without polluting ordinary retrieval.
- Future resolvers can explain every selection, exclusion, pointer resolution, conflict, stale warning, and proof gap within a bounded reading budget.
- The corpus can be inventoried and classified incrementally before any rewrite, move, or canonicalization.
- Future validators must detect ID/path collisions, ADR-number collisions, invalid edges and cycles, LFS pointers, stale anchors, authority conflicts, orphaned nodes, and prohibited metadata.
- The control plane adds governance overhead and requires maintained hashes, anchors, ownership, and human review.

## Alternatives rejected for v1

- File paths as durable identity.
- A single overloaded document `status` or scalar authority score.
- Modification timestamps as freshness authority.
- Markdown headings as an independently maintained metadata graph.
- Vector similarity or document volume as authority resolution.
- Automatically accepting inferred edges or model-selected canonical truth.
- Neo4j, Postgres, a vector store, RDF, or JSON-LD as the canonical v1 persistence layer.
- Destructive first-pass corpus migration or mass rewriting.

## Rollout posture

The contract defines phases from read-only inventory through classification, explicit connection, validation/generation, human canonicalization, later canonical rewrites, duplicate-authority retirement, retrieval integration, and optional projections. Each implementation phase requires a separately approved task and proof surface.

## Compatibility and upgrades

Schema changes require versioned review and migration guidance. Stable document IDs survive path moves and rewrites of the same concept. Splits, merges, replacements, corrections, retirements, and tombstones preserve explicit lineage. Generated projections remain rebuildable across schema versions, and consumers must declare supported schema versions.

## Non-goals

This ADR does not implement a corpus inventory, node-record corpus, graph validator, generator, CLI, CI workflow, automatic document classification, automatic authority decision, source-manifest migration, Agent Reading Packet generator, RAG behavior, chunk metadata, runtime ingestion, database schema, Neo4j writes, vector-index changes, agent harness loading, UI, document moves, archival work, duplicate cleanup, or release claim.

It does not repair the pre-existing ADR-number collisions visible in the current index.

## Acceptance record

Resonant Jones accepted ADR-056 on 2026-08-07. This acceptance approves the DLG docs/control-plane architecture; repository presence, schema validation, documentation validation, or an illustrative example still does not constitute tooling, runtime, retrieval, database-projection, release, or other implementation proof.
