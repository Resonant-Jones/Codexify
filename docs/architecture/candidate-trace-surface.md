# Candidate Trace Surface

Purpose: define the backend-only `candidate_trace` runtime surface for pre-answer completion candidates.
Last updated: 2026-04-19
Source anchors:
- guardian/core/chat_completion_service.py
- guardian/core/candidate_trace_store.py
- guardian/routes/chat.py
- guardian/services/account_export.py
- docs/architecture/chat-runtime-contract.md
- docs/architecture/account-export-restore-contract.md

## Purpose

`candidate_trace` is a diagnostic, ephemeral, non-canonical runtime surface for candidate outputs produced during completion assembly. It exists so backend operators and tests can inspect pre-answer completion candidates without promoting them into chat history.

## Contract

- `candidate_trace` is attempt-scoped, not message-scoped.
- `candidate_trace` must not mutate canonical chat state.
- `candidate_trace` must not appear as a `chat_messages` row.
- `candidate_trace` must not participate in export, restore, or lineage replay.
- `candidate_trace` must remain backend-only; there is no UI exposure.

## Relationship to RAG Trace

`rag_trace` describes retrieval evidence for a completion run.

`candidate_trace` describes the candidate outputs assembled before the final assistant answer is selected.

They are related, but they are not the same surface:

- `rag_trace` explains why the runtime retrieved what it did.
- `candidate_trace` explains what candidate output the completion pipeline was considering.

`candidate_trace` is intentionally non-canonical. It does not widen the retrieval corpus and it does not replace the canonical assistant message.

## Lifecycle

- Stored in a short-lived transient backend cache keyed by `thread_id` plus `request_id`.
- TTL-bound and replay-safe.
- Safe to miss: an empty diagnostic response is a valid state.
- Safe to lose: expiration does not affect canonical chat state.

## Export Boundary

`candidate_trace` is intentionally excluded from account export and restore.

It is derived runtime diagnostic data, not durable user content.
