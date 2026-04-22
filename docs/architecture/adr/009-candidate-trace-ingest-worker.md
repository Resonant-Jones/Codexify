# ADR-009: Candidate Trace Ingest Worker Scaffold

Status: accepted
Date: 2026-04-19

## Context

Codexify already exposes `candidate_trace` as a backend-only, non-canonical runtime surface. The system now needs a safe asynchronous seam that can consume those transient records without making graph/entity extraction part of the completion critical path.

Without an explicit decision here, candidate ingestion could drift into one of three bad states:

- becoming a hidden persistence path
- blocking completion on optional downstream work
- creating a second authoritative representation of candidate outputs

## Decision

Codexify may enqueue `candidate_trace` ingest tasks into Redis and drain them with a dedicated worker, but that worker must remain:

- non-blocking from the completion path
- log-only for the initial scaffold
- independent from canonical chat persistence
- subordinate to the transient candidate-trace surface

The worker may normalize and inspect the ingest payload, but it must not write to Postgres, the vector store, or Neo4j in this phase.

## Rationale

This preserves the current runtime contracts:

- Postgres remains the source of truth
- `candidate_trace` stays non-canonical and ephemeral
- completion success does not depend on optional ingestion work
- future graph/entity extraction can attach to a stable seam

The ingest task carries explicit request and thread identity so future downstream consumers can preserve scope boundaries without guessing.

## Alternatives Considered

### 1. Write graph entities directly from the completion service

Rejected.

That would couple optional enrichment to the completion critical path and make the assistant loop harder to reason about.

### 2. Keep `candidate_trace` only in memory with no queue seam

Rejected for now.

That would leave no durable handoff point for later ingestion work and make future graph/entity extraction more invasive.

### 3. Add a dedicated ingestion queue and worker that logs normalized payloads

Chosen.

This creates the smallest safe seam for future enrichment without changing canonical behavior.

## Consequences

### Positive

- completion remains non-blocking
- ingestion has an explicit worker boundary
- future enrichment can be layered without reworking chat output
- task payloads remain replayable and identity-scoped

### Negative

- an additional queue and worker need operational monitoring
- the ingest path still needs backpressure and retry semantics in later phases
- the initial scaffold does not yet produce durable graph artifacts

## Invariants Created by This Decision

- ingestion must not mutate `chat_messages`
- ingestion must not become authoritative
- ingestion must not alter retrieval behavior
- ingestion must not raise into chat completion
- candidate trace and ingest task identities must preserve thread/request scope

## Governing Contracts

- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Candidate Trace Surface](../candidate-trace-surface.md)
- [Candidate Trace Ingestion Pipeline](../candidate-ingest-pipeline.md)

## Related Notes

- [Account Export + Restore Contract](../account-export-restore-contract.md)
- [Data and Storage](../data-and-storage.md)
- [00-current-state](../00-current-state.md)

