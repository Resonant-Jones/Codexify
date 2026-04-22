---

tags:

* architecture
* adr
* memory-graph
* queue
* worker
  aliases:
* ADR-011
* Graph Write Task Seam and Worker Scaffold

---

# ADR-011: Graph Write Task Seam and Worker Scaffold

## Status

Accepted

## Date

2026-04-21

## Context

Codexify already has a derived candidate-ingest lane that normalizes
`candidate_trace` payloads and maps them into conservative graph candidates.
The system now needs a dedicated asynchronous handoff point for those graph
candidates so the topology is explicit before any Neo4j persistence exists.

Without a bounded seam here, graph write preparation could drift into one of
three bad states:

* remaining hidden inside candidate ingest logs
* becoming a silent second authority for graph truth
* jumping directly from derived candidates to persistence without an
  inspection-only staging lane

## Decision

Codexify may enqueue derived graph-write tasks into a dedicated Redis queue
and drain them with a dedicated worker scaffold, but that worker must remain
inspection-only in this phase.

The graph-write task seam must remain:

* derived from normalized graph candidates
* non-canonical
* non-restorable
* non-blocking for candidate ingest
* isolated from canonical chat persistence

The worker may summarize nodes, edges, and warnings, but it must not write to
Neo4j, Postgres, the vector store, or export payloads in this phase.

## Rationale

This preserves the current runtime contracts:

* Postgres remains the source of truth
* candidate ingest remains an enrichment scaffold, not a canonical writer
* graph candidates can be staged independently of graph persistence
* future persistence can add idempotency and backpressure without changing the
  graph-candidate contract

The queue-backed seam makes the future control plane explicit while keeping the
current implementation honest about what it does and does not persist.

## Alternatives Considered

### 1. Write graph candidates directly in the candidate-ingest worker

Rejected.

That would entangle inspection and persistence in the same lane and make the
derived topology harder to reason about.

### 2. Keep graph candidates only in logs with no queue handoff

Rejected for now.

That would leave no bounded asynchronous seam for future graph persistence and
would make backpressure harder to introduce later.

### 3. Add a queue-backed graph-write task seam and inspection-only worker

Chosen.

This creates the smallest stable boundary for future graph persistence while
preserving the current derived-only posture.

## Consequences

### Positive

* graph-write preparation has a dedicated queue and worker boundary
* candidate ingest can remain focused on normalization and candidate shaping
* future persistence can be introduced behind a stable task contract
* inspection logs can validate topology without changing runtime truth

### Negative

* one more queue and worker need operational awareness
* the initial worker still does not create durable graph artifacts
* later persistence work must keep the task contract stable

## Invariants Created by This Decision

* graph-write tasks must not mutate canonical chat state
* graph-write tasks must not change retrieval behavior
* graph-write tasks must preserve request/thread identity boundaries
* graph-write worker failures must not affect candidate-ingest success
* graph persistence remains deferred until a later decision

## Governing Contracts

* [Memory Graph Derived Write Hook](../adr/007-memory-graph-derived-write-hook.md)
* [Candidate Trace Surface](../adr/008-candidate-trace-surface.md)
* [Candidate Trace Ingest Worker Scaffold](../adr/009-candidate-trace-ingest-worker.md)
* [Candidate Trace Ingestion Pipeline](../candidate-ingest-pipeline.md)
* [Memory Graph Indexing Plan](../memory-graph-indexing-plan.md)
* [Chat Runtime Contract](../chat-runtime-contract.md)
* [Account Export + Restore Contract](../account-export-restore-contract.md)

## Related Notes

* [00-current-state](../00-current-state.md)
* [Data and Storage](../data-and-storage.md)

## Notes

Future work may wire this task seam into:

* idempotent Neo4j persistence
* graph-write retry semantics
* graph diagnostics surfaces

Those are follow-on decisions, not part of this ADR.
