---

tags:

* architecture
* adr
* memory-graph
* graph
* completion
  aliases:
* ADR-007
* Memory Graph Derived Write Hook

---

# ADR-007: Memory Graph Derived Write Hook

## Status

Accepted

## Date

2026-04-19

## Context

Codexify's chat worker already owns the post-persistence completion lifecycle.

The runtime truth remains:

* Postgres is the canonical system of record
* completion remains queue-backed and worker-owned
* retrieval is brokered through `ContextBroker`
* Neo4j / graph behavior is optional and feature-flagged

The system now needs a derived seam for future graph ingestion without changing
assistant success semantics or introducing blocking writes into the completion
path.

Without an explicit decision here, graph candidate emission could drift into
one of three bad states:

* becoming a hidden second persistence path
* blocking completion on optional graph availability
* creating non-idempotent graph inputs that are hard to replay safely

## Decision

Codexify may emit graph-write candidates after assistant message persistence,
but that emission must remain:

* non-blocking
* idempotent
* derived from canonical Postgres rows
* subordinate to the completion worker

The candidate generation seam is a pure structural helper plus a best-effort
worker log emission.

It does **not** mean:

* Neo4j writes are active in the completion loop
* graph persistence is authoritative
* retrieval behavior changes
* completion success depends on graph availability

## Rationale

This decision preserves the current contract boundaries:

* Postgres remains the source of truth
* graph is a derived layer, not an authority
* worker completion must not be delayed or failed by optional graph work
* future graph ingestion can consume stable replay-safe inputs

The `idempotency_key` must be derived from the assistant message identity so
replays do not create duplicate candidate streams.

The scope fields must preserve account, project, and thread boundaries so graph
materialization never collapses ownership context.

The export/restore contract matters because graph-derived artifacts must remain
traceable back to canonical source IDs and lineage boundaries.

## Alternatives considered

### 1. Write directly to Neo4j in the chat worker

Rejected.

This would make optional graph availability part of the critical completion
path and would increase blast radius.

### 2. Defer all graph work to a separate batch job with no candidate seam

Rejected for now.

This would be safe, but it would hide the derived shape that future ingestion
needs and make replay semantics less explicit.

### 3. Emit a pure graph-write candidate after persistence

Chosen.

This keeps the completion loop honest while preparing a clean seam for later
queue-backed or worker-backed graph ingestion.

## Consequences

### Positive

* no completion-path dependency on graph persistence
* replay-safe candidate generation from canonical rows
* explicit identity scoping in the write candidate
* future graph ingestion can be introduced behind a separate queue or worker

### Negative

* logs now carry an extra derived artifact signal
* candidate structure must stay aligned with relational truth
* future graph ingestion still needs its own durability and backpressure model

## Invariants created by this decision

* graph candidate emission must not raise into completion failure
* graph candidate emission must not mutate assistant message payloads
* graph candidate identity must remain stable for the same assistant message
* account/project/thread/source boundaries must remain explicit
* graph persistence and graph retrieval remain deferred

## Links

* [[ADR Index]]
* [[router-decision-table|Retrieval Router Decision Table]]
* [[account-export-restore-contract|Account Export + Restore Contract]]
* [[flows|Critical Flows]]
* [[data-and-storage|Data and Storage]]
* [[00-current-state]]

## Notes

Future work may wire this candidate into:

* a queue-backed graph ingestion worker
* graph persistence retry semantics
* graph inspection diagnostics

Those are follow-on decisions, not part of this ADR.
