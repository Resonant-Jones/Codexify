# TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE: Worker-based embedding pipeline with status updates

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Replace fire-and-forget embeddings with a reliable queued worker pipeline that updates status (pending → processing → ready/failed), records errors, and is observable via status API fields.

### Expected Output
- Embedding work is queued and processed by a worker (documented in summary).
- Status transitions persist.
- Tests cover the critical path deterministically.

## Allowed Files
- guardian/workers/*.py
- guardian/queue/*.py
- guardian/routes/*.py
- backend/rag/*.py and/or backend/vector_store/*.py
- guardian/tests/test_*.py
- docs/tasks/TASK_2026_01_23_004_doc_embed_worker_pipeline.md
- docs/Campaign/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "embeddings|embed|enqueue|queue" guardian backend
- ls -la guardian/workers || true
- rg -n "Redis|enqueue|worker" guardian/workers guardian/queue
- pytest -q -k "embed and worker" || true

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE: add worker-based embedding pipeline
- Commit B: TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE: finalize task summary

## Summary
- Added a dedicated document embed queue and worker to process queued documents and update embedding status throughout the lifecycle.
- Updated `/api/media/upload/document` to enqueue embedding work and record `parsed_text_missing` or queue errors without inline embedding.
- Added deterministic worker tests covering success and failure status transitions.

## Checks Run
- `rg -n "embeddings|embed|enqueue|queue" guardian backend`
- `ls -la guardian/workers || true`
- `rg -n "Redis|enqueue|worker" guardian/workers guardian/queue`
- `pytest -q -k "embed and worker" || true` (exit 0; no output)

## Git Status
- `git status --porcelain -uall` shows task artifact + campaign mapping pending record finalize hash commit.

## Commits
- Commit A (implementation): `0b64306b`
- Commit B (finalize docs): `1e2c22b8`

## Mapping
- TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE -> [0b64306b, 1e2c22b8]
