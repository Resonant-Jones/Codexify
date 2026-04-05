# Import Enrichment Decoupling

Date: 2026-04-05

## Problem Statement

The historical ChatGPT import path was too tightly coupled to enrichment work. In practice, the import request lane was doing canonical persistence and heavyweight follow-up work in the same flow:

- Postgres writes were interleaved with embedding work.
- Embedding initialization could repeatedly load FAISS and the sentence-transformer model during small import batches.
- Import completion and normal API responsiveness were affected by enrichment latency and CPU load.

That coupling made the backend behave as though enrichment were required for basic import durability, which is the wrong dependency order.

## Sequencing Contract

The import pipeline now follows this order:

1. Persist canonical records to Postgres.
2. Mark optional graph projection as pending.
3. Enqueue embedding catch-up work for background processing.

The import request lane only guarantees durable source-of-truth persistence. Enrichment is decoupled from import success.

## Source of Truth

Postgres is the canonical store for imported threads and messages.

Requirements:

- Imported rows must be written durably before any enrichment is attempted.
- Resume and rerun behavior must remain idempotent.
- Item-level failure tracking must remain intact.
- Corrupted placeholder content must not be stored as a substitute for missing enrichment.

The import path may attach metadata that describes enrichment state, but that metadata does not replace the canonical row content.

## Graph Projection

Graph / Neo4j is treated as a derived projection, not part of the critical import path.

Current contract:

- Imported records are marked `graph_status=pending` or equivalent.
- Graph work is optional and may be skipped cleanly when graph is disabled.
- Import completion does not wait on graph availability.
- A later graph pass can reconstruct projection state from durable Postgres data.

The future Settings toggle for Graph is intentionally deferred. This task only establishes the sequencing so that a toggle can be added later without changing import durability semantics.

## Embedding Catch-Up

Embeddings are background catch-up work, not inline import work.

Current contract:

- Import enqueues backlog items onto the deferred embedding queue.
- Imported rows are marked with an embedding pending state.
- A worker drains the backlog until empty and then stops naturally.
- New live content can append to the same backlog without blocking normal interaction.

The background worker processes the deferred import queue ahead of the regular live embed queue, but both remain outside the import request lane.

## Worker Ownership

The import path now hands off to:

- `guardian.queue.redis_queue.enqueue_chat_import_embed(...)`
- `guardian.queue.redis_queue.dequeue_chat_import_embed(...)`
- `guardian.workers.chat_embedding_worker.process_chat_embed_task(...)`

The worker runtime reuses a single vector store instance per process, so the model / FAISS setup is not repeated for every small import batch.

### Remaining Boundary

This task stops at process-level reuse in the embedding worker. A larger refactor could further centralize embedder lifecycle management across worker types, but that is intentionally out of scope here.

## Resume and Idempotency

The import flow must be safe to rerun.

Expected behavior:

- Re-importing the same historical export does not duplicate canonical rows.
- Existing rows with completed enrichment are not reprocessed unnecessarily.
- Pending or failed enrichment can be retried from durable state.
- Queue handoff is best-effort and does not corrupt canonical import state if background enqueueing fails.

## Failure Modes

The main failure cases and their handling:

- Postgres write failure: import fails before canonical durability is claimed.
- Graph unavailable or disabled: import still completes, graph remains pending.
- Embedding queue unavailable: canonical import still completes, enrichment is degraded and retryable.
- Worker failure during embedding: the worker marks the item failed without mutating the source-of-truth row.
- Restart during backlog processing: pending enrichment can be resumed from durable state and queued backlog.

## Deferred Work

Explicitly deferred from this task:

- Graph Settings UI toggle
- Frontend import/progress redesign
- Chat completion queue priority changes
- Provider routing changes
- Any broad schema redesign beyond the minimal enrichment state needed here

## Practical Result

Normal chat and core API routes remain usable while historical imports continue to enqueue enrichment work in the background. The backend no longer needs to finish heavy embedding initialization in the same lane that performs durable import writes.
