# TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA: Add embedding status tracking for uploaded documents

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Add durable embedding status tracking (pending/processing/ready/failed) for uploaded documents, expose status via API, and add minimal tests.

### Expected Output
- Model contains embedding status fields.
- Migration exists and is consistent with existing migration conventions.
- API returns status field (documented in task summary).
- Tests pass (or new tests pass in isolation).

## Allowed Files
- guardian/db/models.py
- backend/migrations/versions/*.py
- guardian/routes/*.py
- guardian/tests/test_*.py
- docs/work/tasks/2026/01/TASK_2026_01_23_003_doc_embed_status_schema.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "class UploadedDocument|uploaded_document" guardian/db/models.py
- rg -n "UploadedDocument|/api/documents" guardian/routes
- pytest -q -k "uploaded_document or document and status" || true

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA: add embedding status fields
- Commit B: TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA: finalize task summary

## Summary
- Added embedding status fields (status/error/timestamps) to `UploadedDocument` and enforced allowed status values.
- Added a migration to persist the new columns and the status check constraint.
- Updated `/api/media/upload/document` to initialize status and update it after embedding, and `/api/media/documents` to return status fields.
- Added `guardian/tests/test_uploaded_document_status.py` to confirm status fields are present in the list API response.

## Checks Run
- `rg -n "class UploadedDocument|uploaded_document" guardian/db/models.py`
- `rg -n "UploadedDocument|/api/documents" guardian/routes`
- `pytest -q -k "uploaded_document or document and status" || true` (exit 0; no output)

## Git Status
- `git status --porcelain -uall` shows only this task artifact pending finalize commit.

## Commits
- Commit A (implementation): `f2e6acdd`
- Commit B (finalize docs): `b097a557`

## Mapping
- TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA -> [f2e6acdd, b097a557]
