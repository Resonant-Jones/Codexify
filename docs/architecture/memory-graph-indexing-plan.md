# Memory Graph Indexing Plan

Purpose: define the canonical indexing blueprint for a Memory Graph layer that unifies relational memory, vector memory, and optional graph enrichment without changing the runtime source of truth.

Last updated: 2026-04-19

Source anchors:
- docs/architecture/data-and-storage.md
- docs/architecture/system-overview.md
- docs/architecture/flows.md
- docs/architecture/completion_pipeline.md
- docs/architecture/router-decision-table.md
- docs/architecture/account-export-restore-contract.md

## 1. Purpose and Scope

Memory Graph is the indexing and linkage layer that makes Codexify memory inspectable across three existing storage shapes:

- `chat_messages`
- `memory_entries` and higher-level fact records
- documents and document-link tables
- embeddings and semantic chunks
- graph relationships

The purpose of this layer is to give the system a consistent way to answer:

- what was said
- what was remembered
- what artifact or document supported that memory
- how those pieces relate across threads, projects, and time

The useful draft idea to preserve here is identity-aware partitioning at every layer:

- account scope
- project scope
- thread scope
- source-family scope

That idea survives only when expressed in the repo's actual identity model, not as persona-specific storage assumptions.

Non-goals:

- no runtime mutation of canonical Postgres truth
- no speculative retrieval features
- no replacement for the current completion pipeline
- no hidden widening of retrieval scope
- no claim that graph context outranks relational or semantic truth

This document describes an indexing plan, not a new product surface.

## 2. Current State Anchors

The current architecture already establishes the following truths:

- Postgres is the source of truth for messages, memory, and documents.
- The vector store powers semantic retrieval for messages and documents.
- Neo4j exists as an optional graph context layer.
- Retrieval happens through the `ContextBroker` assembly pipeline before completion.

Those truths matter because Memory Graph must remain derived from them. It may index, correlate, and enrich, but it must not become a competing authority.

## 3. Memory Layers Model

### Layer A: Relational Memory

Relational Memory is the durable base layer in Postgres.

Primary entities:

- `chat_messages`
- `memory_entries`
- `personal_facts`
- `personal_fact_evidence`
- `documents`
- document linkage tables such as `thread_documents` and `project_document_links`

Responsibilities:

- preserve canonical rows and ordering
- preserve ownership and thread/project boundaries
- preserve provenance and deletion semantics
- provide the restoreable truth set for export and rehydration

### Layer B: Vector Memory

Vector Memory is the semantic retrieval layer built from embeddings and chunks.

Primary entities:

- semantic message chunks
- semantic document chunks
- vector references for searchable content

Responsibilities:

- support similarity search for completion context assembly
- surface retrieval scores and ranking signals
- expose enough metadata for RAG trace inspection and debugging

### Layer C: Graph Memory

Graph Memory is the relationship layer in Neo4j or a compatible graph projection.

Primary entities:

- message nodes
- document nodes
- memory fact nodes
- project nodes

Responsibilities:

- represent entity relationships
- track cross-thread linkage
- retain provenance chains between source rows and derived graph edges

Graph Memory is optional and feature-flagged. It enriches context; it does not define canonical truth.

## 4. Canonical Identity Model

Memory Graph must preserve three distinct identity concepts:

- `node_id`: graph identity inside the graph layer
- `source_id`: the originating Postgres identifier
- `embedding_id`: the vector-layer reference for the chunk or embedding

Identity rules:

- `messageId` and `requestId` separation must remain intact.
- `source_id` always wins as the origin pointer for rehydration and provenance.
- `node_id` must be stable within the graph index, but it must not replace the originating relational ID.
- `embedding_id` links semantic retrieval back to the chunk or source record that produced it.
- graph projection jobs must preserve the same account/project/thread boundaries that the relational layer already enforces

This separation is what prevents graph or vector layers from silently collapsing distinct runtime identities.

## 5. Indexing Strategy

### 5.1 Postgres Indexing

Postgres indexing is lineage-first.

Thread to artifact lineage should preserve:

- thread
- message
- derived artifact
- document link
- memory/fact link

Document linking should continue to flow through:

- `thread_documents`
- `project_document_links`

The indexer should preserve both direct thread attachment and project-level scope because `ContextBroker` may widen through either path.

### 5.2 Vector Indexing

Vector indexing should operate on chunkable source text only.

Chunking rules:

- chunk by source type and structural boundaries where possible
- keep chunk provenance tied to the originating message, document, or fact
- preserve chunk order within a source object
- avoid chunking schemes that erase the source family

Embedding triggers:

- when a message is persisted
- when a document is parsed and ready for embedding

Retrieval alignment:

- semantic retrieval must remain compatible with `ContextBroker` assembly
- vector hits should carry enough metadata to explain why they were selected
- trace visibility must expose the semantic layer separately from graph enrichment

### 5.3 Graph Indexing (Neo4j)

Graph indexing should materialize explicit node and edge types.

Node types:

- `Message`
- `Document`
- `MemoryFact`
- `Project`

Edge types:

- `REFERENCES`
- `DERIVED_FROM`
- `PART_OF`
- `MENTIONS`

Graph indexing rules:

- create graph nodes only from validated relational sources
- derive graph edges from explicit provenance, not inference alone
- keep edge directionality deterministic
- store enough metadata to recover the source row and the reason the edge exists

### 5.4 Current Implementation Path

The current derived pipeline now includes a pure graph-candidate mapper between
normalized candidate entities and any future graph write path.

That mapper is deliberately conservative:

- provenance-first
- deterministic
- side-effect free
- non-persistent

Semantic relationship inference is explicitly deferred. The mapper may only
emit structurally justified candidates from explicit metadata and scope
signals.

## 6. Invariants

The Memory Graph layer must preserve these invariants:

- no loss of provenance
- thread isolation remains intact
- retrieval remains deterministic for a given input and policy
- the graph layer must not override relational truth
- export and restore contracts remain satisfiable

The export contract matters here because graph-derived knowledge must not become impossible to rehydrate or inspect later.

## 7. Retrieval Integration

Graph is enrichment, not primary retrieval source.

Integration rule:

- semantic retrieval happens first
- memory retrieval may follow when policy allows
- graph enrichment is eligible only when intent permits widening or lineage tracing

This must align with the retrieval router doctrine. In practice, graph context belongs behind policy decisions, not in prompt text or ad hoc UI toggles.

Allowed use cases for graph enrichment:

- provenance explanation
- relationship tracing
- cross-thread linkage inspection
- context augmentation when semantic and memory evidence already justify widening

Not allowed:

- graph-only widening that bypasses retrieval policy
- graph context that replaces semantic ranking
- graph edges that appear as authoritative truth without source linkage

## 8. RAG + Graph Convergence Model

The convergence order is:

1. semantic retrieval
2. memory retrieval
3. graph enrichment

That order matters because graph should annotate and connect evidence, not outrank it.

Convergence rules:

- graph never replaces semantic ranking
- graph may add provenance or relationship context after semantic selection
- graph output should be readable as enrichment over an already-assembled retrieval set
- graph contribution should be visible in diagnostics, not silently merged into unrelated context
- the practical tradeoff is still the same as the draft: Postgres preserves fidelity, vectors preserve recall, and graph preserves relationship structure

## 9. Observability + Diagnostics

Graph edges must be visible in diagnostics surfaces, not in the normal chat UI.

Diagnostic requirements:

- expose source node identity
- expose edge type and direction
- expose graph contribution separately from semantic hits
- expose whether graph data was missing, partial, or feature-flagged off

This must respect the Cognitive Diagnostics Canon separation:

- chat UI shows user-facing answer surfaces
- diagnostics surfaces show evidence, provenance, and retrieval composition

## 10. Failure Modes

Top failure modes to design against:

- orphaned embeddings
- graph drift from Postgres truth
- cross-thread leakage
- replay ambiguity
- partial graph availability

Mitigations:

- keep source IDs attached to every derived node and edge
- make graph writes idempotent
- require thread and project scoping on graph projection jobs
- record retrieval provenance separately from graph materialization state
- treat graph unavailability as enrichment degradation, not completion failure

## 11. Phased Rollout Plan

### Phase 1: Documentation only

- define the canonical indexing model
- align terminology with current storage and retrieval docs
- avoid runtime behavior changes

### Phase 2: Graph write hooks

- add non-blocking graph write hooks in ingestion and completion paths
- preserve current completion behavior if graph writes fail
- keep graph writes idempotent

### Phase 3: Graph read enrichment

- add a graph retrieval adapter in `ContextBroker`
- gate graph enrichment behind retrieval policy
- ensure graph output remains subordinate to semantic ranking

### Phase 4: Diagnostics surface exposure

- expose graph inspection in diagnostics surfaces
- keep the chat UI free of low-level graph clutter
- show provenance and edge metadata for debugging

## 12. Next Steps Checklist

- [ ] Define graph schema in code
- [ ] Add graph write hooks in ingestion + completion paths
- [ ] Add graph retrieval adapter in `ContextBroker`
- [ ] Add diagnostics surface for graph inspection
- [ ] Validate against export/restore contract
