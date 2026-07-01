# RAG and Document Retrieval

## Document Lifecycle Status Contract

Every `UploadedDocument` carries an `embedding_status` governed by the
`EmbeddingLifecycleStatus` enum in `guardian/protocol_tokens.py`:

| Status | Meaning | Retrieval Eligible |
|--------|---------|-------------------|
| `pending` | Upload accepted; queued for embedding. | No |
| `processing` | Worker is chunking and embedding the document. | No |
| `ready` | All chunks embedded successfully. | **Yes** |
| `failed` | Embedding failed unrecoverably. | No |

The status is set by the document embed worker (`guardian/workers/document_embed_worker.py`),
which follows a strict transition sequence:

```
upload → pending → processing → ready
                              → failed
```

### Status fields on UploadedDocument

```
embedding_status       VARCHAR(32)   — one of {pending, processing, ready, failed}
embedding_error        TEXT          — error detail when status=failed
embedding_started_at   TIMESTAMPTZ   — when the worker began processing
embedding_completed_at TIMESTAMPTZ   — when the worker finished (success or failure)
```

A CHECK constraint at the database level enforces the allowed status values.

## Retrieval Readiness Gate

The context broker (`guardian/context/broker.py`) loads uploaded documents for
chat context through `_load_doc_by_type`. This method filters `UploadedDocument`
queries by `embedding_status == 'ready'`, so:

- **Only embedded documents** contribute to retrieval evidence.
- Documents stuck in `pending`, `processing`, or `failed` are silently excluded
  from chat context.
- If no documents are ready, retrieval returns empty — chat works without
  document context.

Document filtering happens at the SQL query level, not in post-processing,
so indexing state is cheap to enforce regardless of document count.

## Operator-Visible Status

The documents list API (`GET /api/media/documents`) returns `embedding_status`
and `embedding_error` for every document. The thread documents API
(`GET /api/threads/{thread_id}/documents`) also exposes these fields.

The frontend `DocumentTile` component renders a color-coded status badge:

- **Pending** — grey badge, document queued
- **Processing** — yellow badge, embedding in progress
- **Ready** — green badge, available for retrieval
- **Failed** — red badge, with a short error hint (e.g. "Failed - No text")

## "Atlas" Background Re-Indexing

No background re-indexing loop for documents was found in the local Docker
Compose path. The `embedding_backfill_worker.py` handles **chat message**
embeddings only, and its scope does not extend to `UploadedDocument` rows.

Document embedding is purely queue-driven: the upload route enqueues
`enqueue_document_embed(doc_id)` and the `document_embed_worker` dequeues
and processes one document at a time. No silent, unscoped re-processing
of all documents occurs in the current supported path.

If a future at-scale re-index capability is needed, it should:
- Be gated behind an explicit feature flag (default off).
- Operate on a per-document basis with surfaced status (reuse the
  existing `embedding_status` column).
- Not run silently in the local Docker Compose path.

## Separation from Completion Context

Document retrieval operates on top of the bounded completion context
(see `docs/architecture/completion_pipeline.md`). The readiness gate
described here narrows *which* documents enter retrieval — it does not
widen the total context window for model execution.
