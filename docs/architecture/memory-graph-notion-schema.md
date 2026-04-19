# Codexify Memory Graph Schema (Notion Export)

Purpose: define a Notion-ready export schema for offline inspection of Memory Graph content, retrieval traces, and relationship data.

Last updated: 2026-04-19

Source anchors:
- docs/architecture/data-and-storage.md
- docs/architecture/system-overview.md
- docs/architecture/flows.md
- docs/architecture/completion_pipeline.md
- docs/architecture/account-export-restore-contract.md

## 1. Database: Memory Nodes

Purpose: store graph-materialized nodes derived from canonical runtime sources.

Fields:

- `node_id` (string)
- `type` (`Message` | `Document` | `MemoryFact` | `Project`)
- `source_id` (Postgres ID)
- `embedding_id` (optional)
- `created_at`
- `thread_id`
- `project_id`

Notes:

- `node_id` is the graph-side identifier.
- `source_id` preserves the canonical relational origin.
- `embedding_id` should be left empty when a node has no vector backing.

## 2. Database: Relationships

Purpose: store explicit graph edges between memory nodes.

Fields:

- `edge_id`
- `from_node`
- `to_node`
- `relationship_type`
- `weight` (optional)
- `created_at`

Notes:

- `relationship_type` should be constrained to the graph edge vocabulary used in the indexing plan.
- `weight` is optional because not every edge needs a ranked score.
- edge rows must preserve directionality.

## 3. Database: Embeddings

Purpose: store offline inspection records for vector-backed memory chunks.

Fields:

- `embedding_id`
- `source_id`
- `vector_ref`
- `chunk_index`
- `score_metadata`

Notes:

- `source_id` links embeddings back to the canonical source record.
- `vector_ref` should identify the vector-store object or external reference used during export.
- `score_metadata` should preserve retrieval or ranking context needed for debugging.

## 4. Database: Retrieval Logs (Offline RAG)

Purpose: preserve offline retrieval traces for audit and inspection.

Fields:

- `query`
- `source_mode`
- `widen_reason`
- `semantic_hits`
- `memory_hits`
- `graph_hits`
- `timestamp`

Runtime alignment:

- this log shape must align with the RAG trace fields proven in runtime
- if the runtime exports a richer retrieval provenance envelope, this database should preserve the meaningful subset needed for offline reconstruction

## 5. Offline RAG Workflow

Offline reconstruction flow:

1. Export data from Postgres + vector store
2. Rehydrate into Notion databases
3. Reconstruct graph relationships
4. Run offline queries:
   - semantic
   - memory
   - graph traversal
5. Validate against runtime RAG trace

Operational rule:

- offline export is for inspection and audit
- it does not replace the canonical runtime storage contract

## 6. Use Cases

- memory debugging
- retrieval auditing
- cross-thread insight mapping
- export inspection

This schema is intended for practical review, not for speculative workflow design.

