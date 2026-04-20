# Candidate Trace Ingestion Pipeline

Purpose: describe the backend-only ingestion seam that consumes transient `candidate_trace` records and prepares them for future entity or graph extraction without changing canonical chat behavior.
Last updated: 2026-04-20
Source anchors:
- guardian/core/chat_completion_service.py
- guardian/workers/candidate_ingest_worker.py
- guardian/queue/redis_queue.py
- docs/architecture/candidate-trace-surface.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/adr/009-candidate-trace-ingest-worker.md

## Purpose

`candidate_trace` is a non-canonical runtime artifact. The ingestion pipeline exists so the backend can accept those transient records, normalize their identity scope, and expose a clean seam for later graph or entity extraction.

This pipeline is intentionally narrow:

- it does not persist canonical chat state
- it does not create or mutate `chat_messages`
- it does not write to Postgres, the vector store, or Neo4j
- it does not surface in the UI

## Pipeline Shape

1. The completion service emits a `candidate_trace` after candidate assembly.
2. A non-blocking enqueue step pushes a `CandidateTraceIngestTask` into Redis.
3. `candidate_ingest_worker` consumes the task and normalizes the payload with the pure `normalize_candidate_trace(...)` helper.
4. The worker logs a structured normalization summary and any derived warnings for diagnostics.
5. Future phases may attach graph/entity extraction to the same seam.

The current implementation is log-only. It is a scaffold, not a durable ingest path.

## Normalization Step

Normalization now occurs inside the ingest worker, but it remains a pure inspection step:

- normalization is deterministic and pure with respect to the candidate payload
- normalized entities are transient derived artifacts
- normalized output is not exported, restored, persisted as canonical state, or used by retrieval
- the worker remains inspection-only in this phase
- future graph/entity persistence remains explicitly deferred

## Non-Canonical Constraint

The ingest task is derived runtime data.

It must remain:

- ephemeral
- replay-safe
- identity-scoped
- excluded from export/restore lineage
- derived-only and non-canonical even after normalization

If the queue drops a task, canonical chat behavior must remain unchanged.

## Relationship to `candidate_trace`

`candidate_trace` is the transient diagnostic surface for pre-answer candidates.
The ingestion pipeline consumes that surface but does not replace it.

- `candidate_trace` answers: what candidate output existed for this completion attempt?
- candidate ingestion answers: what normalized payload is available for future enrichment?

The two surfaces share request/thread identity, but they serve different layers of the runtime.

## Extension Points

Future work may attach:

- entity extraction
- graph node/edge materialization
- replay-safe deduplication
- queue backpressure and dead-letter handling

Those concerns belong to later phases. They are deliberately absent from this scaffold.

## Failure Policy

- Completion must not wait on ingestion.
- Ingestion failures must be logged and isolated.
- Missing or malformed ingest tasks must not affect canonical chat state.
- Empty-state behavior remains valid when no candidate trace exists.
