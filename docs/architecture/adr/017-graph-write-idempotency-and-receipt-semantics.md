---
tags:
* architecture
* adr
* memory-graph
* graph-write
* idempotency
* receipts
  aliases:
* ADR-017
* Graph Write Idempotency and Receipt Semantics
---

# ADR-017: Graph Write Idempotency and Receipt Semantics

## Status

Accepted

## Date

2026-04-28

## Context

ADR-007 established the derived graph write hook.
ADR-008 established the candidate_trace diagnostic surface.
ADR-009 established the candidate_trace ingest worker scaffold.
ADR-011 established the dedicated graph-write task seam and inspection-only
worker scaffold.

That topology is useful, but it still leaves one replay-safety gap: the graph
lane had no explicit operational identity or receipt claim semantics. Without
that seam, repeated graph-write tasks can only be treated as ad hoc duplicates,
which is brittle even when no graph persistence exists yet.

The purpose of this ADR is to close that gap before any Neo4j persistence is
added.

## Problem Statement

The graph lane is derived, transient, and inspection-only in the current phase.
Even so, it still needs a bounded replay contract so worker runs are stable
when the same derived payload is replayed more than once.

Without explicit identity and receipt semantics, the lane risks:

- replaying the same derived task with no clear first-seen boundary
- treating duplicate payloads as novel inspection work
- leaking the illusion of canonical graph truth into an inspection-only path
- making future persistence assumptions harder to reason about

This matters even before graph writes exist because the identity seam will
shape later persistence behavior.

## Decision

Codexify defines deterministic graph-write identity plus ephemeral receipt
claims as the replay-safety contract for the inspection-only graph lane.

The lane now behaves as follows:

- candidate traces are normalized and mapped to graph candidates
- graph-write identity is built from the candidate-trace boundary plus the
  canonicalized graph payload
- a `GraphWriteTask` carries that identity when it is enqueued
- the graph-write worker claims an ephemeral receipt before inspection
- first-seen tasks produce inspection summaries
- repeated tasks within the receipt window degrade to duplicate/replay
  handling and skip further graph-lane work

This is an operational control-plane seam only. It does not create graph truth.

## Canonical Terms

| Term | Canonical meaning |
|---|---|
| Graph-write identity | The deterministic operational identity for a derived graph task. It is derived from the candidate-trace boundary and the canonicalized node/edge/warning payload. |
| Graph-write fingerprint | The stable digest of a canonicalized graph payload. It is insensitive to payload ordering when the graph meaning is unchanged. |
| Graph-write task identity | The combined identity fields carried on `GraphWriteTask`, including `graph_write_id` and `idempotency_key`. |
| Receipt claim | An ephemeral Redis-backed claim that marks the first inspection of a graph-write idempotency key for the duration of the TTL. |
| Duplicate/replay handling | The bounded worker path taken when a receipt already exists. Duplicate/replayed tasks are logged and skipped, not promoted to truth. |
| Operational receipt state | Non-canonical state used only to make the inspection-only lane replay-safe. It is not exportable, restorable, or authoritative. |

## Decision Details

The graph lane must remain replay-safe without becoming a persistence layer.

Required behavior:

- identical graph payloads on the same candidate trace should produce the same
  graph-write identity
- different graph shapes should change the fingerprint and therefore the
  idempotency key
- distinct candidate traces must remain distinct even when payload shape is
  similar
- the worker must claim an ephemeral receipt before inspecting the task
- duplicate claims must skip further graph-lane work
- malformed tasks and receipt-claim failures must remain isolated from the
  worker loop

## Non-Negotiable Invariants

- receipts are operational and ephemeral, not canonical truth
- graph-write tasks remain derived artifacts
- no Neo4j writes occur in this phase
- no Postgres writes occur in this phase
- no vector writes occur in this phase
- no retrieval path may consume graph-write tasks or receipts in this phase
- no export or restore payload may participate in graph-write receipt state
- no chat completion behavior may depend on graph-write enqueue or receipt
  success

## Relationship to Existing Architecture

This ADR is constrained by:

- ADR-007 for derived graph write hook provenance
- ADR-008 for candidate_trace diagnostic lineage
- ADR-009 for candidate_trace ingest worker behavior
- ADR-011 for the dedicated graph-write task seam and inspection-only worker
- the account export/restore contract for provenance boundaries
- the data and storage contract for canonical truth boundaries

Current runtime truth remains unchanged: graph persistence is still deferred.

## Implementation Boundaries

This ADR does not implement:

- real Neo4j writes
- durable idempotent persistence semantics
- graph retrieval consumption
- Postgres receipts
- vector receipts
- export/restore participation
- UI coupling
- canonical graph truth claims

The receipt seam exists only to make the inspection-only lane replay-safe.

## Deferred Work

The following are explicitly left for later tasks:

- real graph persistence in Neo4j or a compatible projection
- durable write idempotency for graph materialization
- graph retrieval consumption
- any export/restore support for graph-derived structures

## Consequences

### Positive

- replay behavior is bounded before persistence exists
- the worker can distinguish first-seen from duplicate inspection work
- later persistence work has a stable identity seam to build on
- graph tasks stay clearly derived and non-canonical

### Negative

- the graph lane now carries another explicit control-plane concept
- later persistence work must honor the receipt and identity semantics instead
  of inventing a new uniqueness story
- the inspection-only path still needs careful docs so no one reads it as graph
  truth

## Links

- [[ADR Index]]
- [[007-Memory-Graph-Derived-Write-Hook|ADR-007 Memory Graph Derived Write Hook]]
- [[008-Candidate-Trace-Surface|ADR-008 Candidate Trace Surface]]
- [[009-Candidate-Trace-Ingest-Worker|ADR-009 Candidate Trace Ingest Worker Scaffold]]
- [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|ADR-011 Graph Write Task Seam and Worker Scaffold]]
- [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
- [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
- [[account-export-restore-contract|Account Export + Restore Contract]]
- [[data-and-storage|Data and Storage]]
- [[00-current-state]]

## Notes

This ADR intentionally stops at replay safety. It does not introduce graph
truth, graph retrieval, or durable persistence.
