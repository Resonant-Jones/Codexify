# TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER: Document embed pipeline worker

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Implement a reliable document embedding pipeline with queueing, worker processing, and embedding status transitions.

### Expected Output
- A worker exists that can embed document text deterministically.
- Upload triggers queueing (or explicit endpoint triggers queueing).
- Status transitions are observable in DB and returned by relevant APIs.
- At least one automated test validates the pipeline behavior.

## Allowed Files
- guardian/routes/media.py
- guardian/workers/*.py
- guardian/queue/**/*.py
- guardian/db/models.py (only if needed beyond Task 003)
- backend/rag/embedder.py (only if needed)
- guardian/vector/store.py (only if needed)
- guardian/tests/**/*.py
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/work/tasks/2026/01/TASK_2026_01_23_004_document_embed_pipeline_worker.md

Note: The campaign text references `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- ls -1 guardian/workers || true
- rg -n "enqueue|Redis|queue|worker" guardian/queue guardian/workers guardian/routes | head -n 200
- rg -n "upload_document|/api/media/upload/document|UploadedDocument" guardian/routes/media.py frontend/src/hooks/useUploader.ts
- rg -n "pytest" Makefile README.md pyproject.toml
- pytest -q guardian/tests/test_document_embed_worker.py
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER: add document embedding worker pipeline
- Commit B: TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER: finalize task summary

## Summary
- Verified the document embed queue, worker, and upload enqueueing already exist (no code changes required).
- Confirmed status transitions are covered by `guardian/tests/test_document_embed_worker.py`.

## Checks Run
- `ls -1 guardian/workers || true`
- `rg -n "enqueue|Redis|queue|worker" guardian/queue guardian/workers guardian/routes | head -n 200`
- `rg -n "upload_document|/api/media/upload/document|UploadedDocument" guardian/routes/media.py frontend/src/hooks/useUploader.ts`
- `rg -n "pytest" Makefile README.md pyproject.toml`
- `pytest -q guardian/tests/test_document_embed_worker.py`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows this task artifact + campaign mapping pending record finalize hash commit.

## Commits
- Commit A (implementation): `b158a85c`
- Commit B (finalize docs): `a64b7d98`

## Mapping
- TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER -> [b158a85c, a64b7d98]
