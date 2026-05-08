---
tags:
* architecture
* adr
* memory-graph
* graph-write
* inspection
* diagnostics
  aliases:
* ADR-018
* Graph Write Inspection Surface
---

# ADR-018: Graph Write Inspection Surface

## Status

Accepted

## Date

2026-04-28

## Classification

This ADR is architecture-impacting.

## Governing ADRs

- ADR-008: Candidate Trace Surface
- ADR-009: Candidate Trace Ingest Worker Scaffold
- ADR-011: Graph Write Task Seam and Worker Scaffold
- ADR-017: Graph Write Idempotency and Receipt Semantics

## Context

Codexify already has a derived graph-lane path:

`candidate_trace -> normalize_candidate_trace(...) -> map_to_graph_write_candidates(...) -> build GraphWriteTask identity -> enqueue GraphWriteTask -> graph_write_worker claims receipt`

ADR-017 gave that lane explicit replay safety, but operators still had no
bounded surface for seeing the latest graph-lane outcome for a thread. Without
an inspection snapshot, the lane could only be inferred from logs, which makes
first-seen versus duplicate-skipped behavior harder to inspect without
promoting the graph lane into canonical truth.

This ADR adds a small operator-facing inspection seam before any Neo4j
persistence exists.

## Decision

Codexify now records a latest-per-thread graph-write inspection snapshot and
exposes it through a backend-only debug route.

The snapshot is:

- operational
- ephemeral
- thread-scoped
- summary-oriented
- non-canonical

The snapshot records:

- thread identity
- request identity
- candidate trace identity
- graph-write identity
- idempotency key
- receipt status
- node, edge, and warning counts
- node and edge type sets
- creation time

The route proves the latest graph-lane inspection outcome for a thread. It
does not prove durable graph persistence, canonical graph state, or
successful retrieval use.

## Non-Negotiable Invariants

- Postgres remains canonical truth
- Redis remains transport and coordination
- graph-write tasks remain derived artifacts
- inspection snapshots remain derived artifacts
- no Neo4j writes are introduced here
- no Postgres writes are introduced here
- no vector writes are introduced here
- no retrieval consumer may depend on inspection snapshots
- no export or restore participation is introduced here
- no main-shell diagnostics UI is introduced here
- duplicate graph tasks remain bounded by receipt semantics, not graph truth

## Consequences

### Positive

- operators can inspect the latest graph-lane outcome for a thread
- first-seen versus duplicate-skipped outcomes are visible without
  instrumenting canonical state
- the graph lane keeps a stable debug seam ahead of real persistence work

### Negative

- one more ephemeral diagnostic surface must be maintained
- later durable graph work must not misread the inspection snapshot as truth

## Deferred Items

The following remain explicitly out of scope:

- real Neo4j writes
- durable graph audit history
- product-shell diagnostics UI

## Route Contract

`GET /chat/{thread_id}/debug/graph-write/latest`

Compat alias:

`GET /api/chat/{thread_id}/debug/graph-write/latest`

What it proves:

- the latest graph-lane inspection outcome for the requested thread

What it does not prove:

- durable graph persistence
- canonical graph state
- retrieval consumption

## Links

- [[ADR Index]]
- [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|ADR-011 Graph Write Task Seam and Worker Scaffold]]
- [[017-Graph-Write-Idempotency-and-Receipt-Semantics|ADR-017 Graph Write Idempotency and Receipt Semantics]]
- [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
- [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
- [[data-and-storage|Data and Storage]]
- [[00-current-state]]
