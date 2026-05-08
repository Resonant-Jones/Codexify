---
tags:
* architecture
* adr
* memory-graph
* graph-backend
* adapter
  aliases:
* ADR-019
* Graph Backend Adapter Contract
---

# ADR-019: Graph Backend Adapter Contract

## Status

Accepted

## Date

2026-04-28

## Classification

This ADR is architecture-impacting.

## Governing ADRs

- ADR-007: Memory Graph Derived Write Hook
- ADR-011: Graph Write Task Seam and Worker Scaffold
- ADR-017: Graph Write Idempotency and Receipt Semantics
- ADR-018: Graph Write Inspection Surface

## Context

The graph lane now has deterministic task identity, receipt claims, and an
operator-facing inspection snapshot. What it still lacks is a bounded backend
contract that a real graph persistence implementation can attach to later.

Without a typed adapter seam, future persistence work would have to bolt onto
the worker ad hoc, which risks coupling the persistence decision to queue,
receipt, and inspection logic all at once.

This ADR introduces the smallest stable backend contract for that future
extension point.

## Decision

Codexify defines a typed graph backend adapter contract with a default no-op
implementation.

The contract exposes a single write method that receives the derived graph
task payload and returns a bounded write result with:

- a result status
- graph-write identity
- node and edge counts
- warnings
- metadata

The adapter is mounted into the graph-write worker after receipt claim and
inspection snapshot emission.

The current default implementation is no-op. It preserves the current
inspection-only runtime behavior and does not introduce canonical graph
persistence.

## Contract Vocabulary

| Token | Meaning |
| --- | --- |
| `noop` | The adapter accepted the task contract but intentionally performed no graph persistence work. |
| `skipped` | The adapter declined to process the task because the input was malformed or unsupported. |

## Non-Negotiable Invariants

- Postgres remains canonical truth
- Redis remains transport and coordination
- graph-write tasks remain derived artifacts
- inspection snapshots remain derived artifacts
- graph backend adapter results remain derived artifacts
- no Neo4j writes are introduced here
- no Postgres writes are introduced here
- no vector writes are introduced here
- no retrieval consumer may depend on adapter results
- no export or restore participation is introduced here
- no main-shell diagnostics UI is introduced here
- no chat completion success semantics depend on adapter success

## Consequences

### Positive

- future graph persistence can attach to a typed backend seam
- the worker can remain inspection-only while still mounting the adapter path
- adapter semantics are explicit before any real persistence lands

### Negative

- one more backend contract must be maintained and versioned
- later persistence work must honor the adapter contract instead of inventing a
  new write shape

## Deferred Items

The following remain explicitly out of scope:

- real Neo4j writes
- durable graph storage
- retrieval consumption
- export/restore participation
- product-shell diagnostics UI

## Route and Worker Note

The worker currently invokes the adapter only after receipt success and
inspection snapshot emission. The default implementation is no-op, so the
present runtime behavior remains inspection-only.

## Links

- [[ADR Index]]
- [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|ADR-011 Graph Write Task Seam and Worker Scaffold]]
- [[017-Graph-Write-Idempotency-and-Receipt-Semantics|ADR-017 Graph Write Idempotency and Receipt Semantics]]
- [[018-Graph-Write-Inspection-Surface|ADR-018 Graph Write Inspection Surface]]
- [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
- [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
- [[data-and-storage|Data and Storage]]
- [[modules-and-ownership|Modules and Ownership]]
- [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
- [[00-current-state]]
