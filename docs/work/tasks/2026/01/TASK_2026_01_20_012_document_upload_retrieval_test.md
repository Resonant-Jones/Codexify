# TASK-2026-01-20-012_DOCUMENT_UPLOAD_RETRIEVAL_TEST: Document Upload Retrieval Test

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-003_MVP_LOOP_CLOSURE_DOCUMENT_UPLOAD_PARSING.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-012_DOCUMENT_UPLOAD_RETRIEVAL_TEST.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Add a deterministic test proving upload -> parse -> chunk -> embed -> retrieve for an uploaded document. The test should stub embedding/vector store as needed and avoid external services. It should validate parsed_text, chunk determinism (for long inputs), simulated embedding/storage, and retrieval of uploaded content.

### Expected Output
- A focused test proves the document upload path results in retrievable knowledge.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- guardian/routes/media.py
- guardian/routes/documents.py
- guardian/services/document_parsers/pdf_text_extractor.py
- guardian/services/document_parsers/docx_text_extractor.py
- guardian/services/document_chunking.py
- guardian/tests/test_document_upload_retrieval.py
- docs/work/tasks/2026/01/TASK_2026_01_20_012_document_upload_retrieval_test.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md

## Checks to Run
- pytest -v

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): TASK-2026-01-20-012_DOCUMENT_UPLOAD_RETRIEVAL_TEST: add upload→retrieve proof test
- Commit B (finalize artifact): TASK-2026-01-20-012_DOCUMENT_UPLOAD_RETRIEVAL_TEST: finalize task summary

## Summary
- Updated `guardian/routes/media.py` to chunk parsed document text before embedding and attach chunk metadata.
- Added `guardian/tests/test_document_upload_retrieval.py` to prove upload → parse → chunk → embed → retrieve with faked vector store/embeddings.
- Tests: `pytest -v` (560 passed, 1 skipped, 33 xfailed, 11 xpassed), `pytest -v guardian/tests/test_document_upload_retrieval.py` (1 passed; explicit run because pytest.ini ignores guardian/tests).
- Git status: `git status --porcelain` clean.
- Commit mode: two-phase.
- Implementation commit: `ea1b57bd`.
- Finalize commit: reported in campaign mapping.
- Campaign mapping: `TASK-2026-01-20-012_DOCUMENT_UPLOAD_RETRIEVAL_TEST -> [ea1b57bd, <finalize_hash>]`.
