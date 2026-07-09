# RAG and Retrieval

Last updated: 2026-07-01

Source anchors:
- `guardian/routes/media.py`
- `guardian/workers/document_embed_worker.py`
- `guardian/context/broker.py`
- `guardian/routes/documents.py`
- `frontend/src/components/documents/DocumentTile.tsx`
- `frontend/src/components/documents/DocumentsView.tsx`
- `frontend/src/components/dashboard/DashboardView.tsx`
- `docs/architecture/flows.md`
- `docs/architecture/data-and-storage.md`

## Purpose

This note describes the uploaded-document retrieval contract for Codexify's local-room document pipeline.

The contract is intentionally narrow:
- uploaded documents flow through parse -> chunk -> embed -> ready/failed
- the context broker only retrieves uploaded documents once the lifecycle is `ready`
- the UI must show the lifecycle honestly while the document is still pending, processing, or failed

This doc does not broaden the supported surface to shared-room KB sync, federation, or opaque background reindexing.

## Lifecycle Contract

The canonical lifecycle tokens are:
- `pending`
- `processing`
- `ready`
- `failed`

The upload route seeds `pending` for supported documents when parsed text exists. The embed worker then advances the row through `processing` and ends at `ready` or `failed`.

When text extraction fails or embedding fails, the row remains visible with the failure state and error detail. That is an operator-facing truth surface, not a retrieval grant.

## Retrieval Gate

The broker treats `uploaded_documents.embedding_status` as the source of truth for document availability.

Rules:
- `ready` documents may be serialized into project/thread document buckets
- `pending`, `processing`, and `failed` documents are excluded from broker-visible document retrieval
- semantic hits that point at uploaded document chunks are fail-closed unless the backing row is `ready`
- if the broker cannot verify readiness, it should act as though the document is not ready

That means a document can exist in storage, appear in the UI, and still be intentionally absent from the model context until the lifecycle says it is ready.

## UI Visibility

The UI should expose the same lifecycle state the backend uses.

Current surfaces:
- `DocumentTile` shows the lifecycle badge for desktop document cards
- the mobile document row in `DocumentsView` shows the same badge
- the mobile recent-document row in `DashboardView` shows the same badge
- failed documents keep their error hint visible so operators can tell whether the failure came from missing parsed text, an embed failure, or another runtime error

## Failure Modes

Top failure modes for the local-room document path:

1. `parsed_text_missing`
   - Upload succeeded, but no extractable text was available
   - The row should go to `failed`
   - The broker should not retrieve it

2. Queue or worker failure
   - The document was parsed, but the embed job could not complete
   - The row should go to `failed`
   - The broker should not retrieve it

3. Row / vector mismatch
   - The vector store contains chunks, but the document row is missing or not `ready`
   - Retrieval should fail closed

4. Stale or partial metadata
   - If the broker cannot verify readiness, it must not guess
   - Fail closed and keep the mismatch visible in logs/tests

## Explicit Non-Goals

This contract does not:
- implement shared-room KB synchronization
- change federation behavior
- add participant-node document handoff
- claim that `/api/obsidian/index` is a hidden fallback for uploaded document retrieval
- widen the release promise beyond the local-room document path

## Anchors

- Upload path: `guardian/routes/media.py`
- Embed worker: `guardian/workers/document_embed_worker.py`
- Context broker gate: `guardian/context/broker.py`
- Document detail visibility: `guardian/routes/documents.py`
- UI lifecycle badge: `frontend/src/components/documents/DocumentTile.tsx`
