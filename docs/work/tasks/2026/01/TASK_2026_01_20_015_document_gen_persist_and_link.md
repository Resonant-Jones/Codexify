# TASK-2026-01-20-015_DOCUMENT_GEN_PERSIST_AND_LINK: Document Generation Persist + Link

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-015_DOCUMENT_GEN_PERSIST_AND_LINK.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Persist the generated document content returned by TASK-014 into the database as a GeneratedDocument (or existing equivalent model). Create a link/association between the originating thread and the persisted document (e.g., ThreadDocument join/edge model). Do not change the modal UI or add new frontend flows. Keep changes minimal and localized to the documents pipeline. Use existing DB/session patterns. Return a stable identifier for the persisted document from the API response (e.g., document_id). Add clear, user-safe error handling for DB write failures. No unrelated refactors.

### Expected Output
- A generated document is persisted and linked to its originating thread.
- The generate endpoint response includes the persisted document identifier.
- A focused test covers happy path persistence + linking and at least one failure mode.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- guardian/routes/documents.py
- guardian/guardian_api.py
- guardian/routes/media.py
- guardian/db/models.py
- guardian/db/session.py
- guardian/models/generated_document.py
- guardian/models/thread_document.py
- guardian/tests/test_document_gen_persist_and_link.py
- docs/work/tasks/2026/01/TASK_2026_01_20_015_document_gen_persist_and_link.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md

## Checks to Run
- pytest -v

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): TASK-2026-01-20-015_DOCUMENT_GEN_PERSIST_AND_LINK: persist generated doc and link to thread
- Commit B (finalize artifact): TASK-2026-01-20-015_DOCUMENT_GEN_PERSIST_AND_LINK: finalize task summary

## Summary
- Persisted generated documents and thread links in `guardian/routes/documents.py`.
- Added persistence/linking tests in `guardian/tests/test_document_gen_persist_and_link.py`.
- Tests:
  - `pytest -v`
  - `pytest -v guardian/tests/test_document_gen_persist_and_link.py`
- Git status: `git status --porcelain` shows only allowed docs files pending finalize commit.
- Commit mode: two-phase.
- Implementation commit: `b51bc26f`.
- Finalize commit: reported in campaign mapping.
- Campaign mapping requirement: `TASK-2026-01-20-015_DOCUMENT_GEN_PERSIST_AND_LINK -> [b51bc26f, <finalize_hash>]`.
