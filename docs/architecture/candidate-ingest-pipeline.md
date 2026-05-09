# Candidate Trace Ingestion Pipeline

Purpose: describe the backend-only ingestion seam that consumes transient `candidate_trace` records and prepares them for future entity or graph extraction without changing canonical chat behavior.
Last updated: 2026-05-08
Source anchors:
- guardian/core/chat_completion_service.py
- guardian/core/graph_write_inspection_store.py
- guardian/workers/candidate_ingest_worker.py
- guardian/workers/graph_write_worker.py
- guardian/tasks/types.py
- guardian/queue/redis_queue.py
- guardian/queue/graph_write_receipts.py
- guardian/memory_graph/graph_write_identity.py
- docs/architecture/candidate-trace-surface.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/adr/009-candidate-trace-ingest-worker.md
- docs/architecture/adr/011-graph-write-task-seam-and-worker-scaffold.md
- docs/architecture/adr/018-graph-write-inspection-surface.md

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

## Graph-Candidate Mapping Step

Normalized candidate entities now feed a pure graph-candidate mapping seam.

This mapping remains:

- deterministic
- non-persistent
- provenance-preserving
- outside export/restore lineage
- outside retrieval consumption

The mapper produces derived graph candidates for future graph/entity work, but
it does not create canonical records or semantic truth.

## Worker Inspection Summary

The ingest worker now performs two pure derived steps in sequence:

1. normalization
2. graph-candidate mapping

Both steps remain deterministic and non-persistent. The graph-candidate output
is only summarized inside the worker for inspection and diagnostics.

Graph candidates remain transient derived artifacts and are not:

- exported
- restored
- persisted as canonical records
- used by retrieval
- written to Neo4j in this phase

Future graph persistence remains explicitly deferred.

## Graph-Write Inspection Snapshot Surface

The graph-write worker now emits a latest-per-thread inspection snapshot after
receipt handling.

This surface is intentionally operational and summary-oriented:

- it records whether the task was first-seen or duplicate-skipped
- it preserves thread-scoped identity plus node, edge, and warning counts
- it remains backend-only and debug-only
- it does not create canonical graph truth

The inspection snapshot is not:

- exported
- restored
- used by retrieval
- written to Neo4j in this phase
- promoted into canonical chat or memory state

The debug route reads the latest snapshot for a thread, or an explicit empty
state when no snapshot exists.

## Graph Backend Adapter Contract

The graph-write worker now also mounts a bounded graph backend adapter after
receipt claim and inspection snapshot emission.

This adapter seam is deliberately inert in the current phase:

- the default backend implementation is no-op
- adapter output is derived, not canonical
- adapter results do not alter receipt semantics
- adapter results do not feed retrieval, export, or canonical graph state

The adapter contract exists so later graph persistence can attach to a stable
typed seam without changing the current inspection-only behavior.

### Runtime gate for graph backend selection

Graph backend selection is runtime-gated and default-off on the supported
Docker Compose path. The factory in
`guardian/memory_graph/graph_backend_factory.py` returns
`NoopGraphBackendAdapter` unless both:

- `CODEXIFY_ENABLE_GRAPH_WRITES=true`
- `CODEXIFY_GRAPH_BACKEND=neo4j`

Neo4j container presence alone does not enable graph writes. Invalid backend
values or missing flags fail closed to noop.

## Graph-Write Task Hand-Off

Candidate ingest now hands non-empty graph candidates to a dedicated
`GRAPH_WRITE_QUEUE` as a derived `GraphWriteTask`.

The graph-write worker now resolves a bounded backend adapter via
`get_graph_backend()`:

- default path is `NoOpGraphBackend`
- `Neo4jGraphBackend` is selected only when `CODEXIFY_ENABLE_GRAPH_WRITES=true`
  and `CODEXIFY_GRAPH_BACKEND=neo4j`
- backend selection is operational and derived-only; it does not promote graph
  artifacts to canonical truth

The worker keeps the existing contract:

- receipt claim happens before backend invocation
- duplicate tasks exit before backend invocation
- inspection snapshot semantics stay upstream of the backend call
- backend failures are contained and do not affect chat acceptance semantics

Graph-write tasks remain deterministic derived artifacts and are not:

- exported
- restored
- persisted as canonical records
- used by retrieval
- consumed by retrieval in this phase

Neo4j persistence now exists behind an explicit default-off runtime gate.

## Graph Identity and Receipt Semantics

Graph-write tasks now carry deterministic graph-lane identity derived from the
candidate trace boundary plus the canonicalized graph payload.

Before the graph-write worker inspects or writes a task, it claims an ephemeral receipt
for the task's idempotency key. That receipt is Redis-backed operational dedupe
only:

- it is not exported
- it is not restored
- it is not persisted as canonical state
- it is not used by retrieval
- it is not consumed by retrieval in this phase

The receipt claim only makes the inspection-only lane replay-safe. It does not
turn graph tasks into graph truth.

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
