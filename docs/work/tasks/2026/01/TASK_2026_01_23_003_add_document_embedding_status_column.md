# TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN: Add embedding status to uploaded documents

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Add durable embedding status tracking to `UploadedDocument` so the UI and pipeline can reflect pending/processing/ready/failed.

### Expected Output
- UploadedDocument includes a persisted status field.
- A migration exists and applies cleanly.
- New uploads can set status to an initial value deterministically.

## Allowed Files
- guardian/db/models.py
- backend/migrations/versions/*.py
- guardian/routes/media.py (only if required to set initial status)
- guardian/tests/**/*.py (optional)
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/work/tasks/2026/01/TASK_2026_01_23_003_add_document_embedding_status_column.md

Note: The campaign text references `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- rg -n "class UploadedDocument|UploadedDocument" guardian/db/models.py
- ls -1 backend/migrations/versions | tail -n 20
- rg -n "alembic|migrations" Makefile README.md pyproject.toml
- docker compose up -d postgres (if used)
- alembic upgrade head (if used)
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN: add embedding status to uploaded documents
- Commit B: TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN: finalize task summary

## Summary
- Verified `UploadedDocument` already includes embedding status fields with a check constraint for pending/processing/ready/failed.
- Confirmed existing migration `7c2a8e6d1f4b_add_embedding_status_to_uploaded_documents.py`; no new schema changes required.

## Checks Run
- `rg -n "class UploadedDocument|UploadedDocument" guardian/db/models.py`
- `ls -1 backend/migrations/versions | tail -n 20`
- `rg -n "alembic|migrations" Makefile README.md pyproject.toml`
- `docker compose up -d postgres` (not run; no migration changes)
- `alembic upgrade head` (not run; no migration changes)
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows this task artifact + campaign mapping pending record finalize hash commit.

## Commits
- Commit A (implementation): `700c7c27`
- Commit B (finalize docs): `ad15e46e`

## Mapping
- TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN -> [700c7c27, ad15e46e]
