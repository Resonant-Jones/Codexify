# TASK-2026-01-20-010_ADD_DOCX_TEXT_EXTRACTION: Add DOCX text extraction

## Task Prompt
### Context
You are operating in the Codexify repo to extend the document upload pipeline for the
`CAMPAIGN-2026-01-20-003_MVP_LOOP_CLOSURE_DOCUMENT_UPLOAD_PARSING` campaign.

### Instructions
1. Implement DOCX text extraction using a server-side library.
2. Populate `parsed_text` for uploaded DOCX files and handle failures gracefully.
3. Keep scope limited to the allowed files and run `pytest -v`.
4. Use two-phase commits with the provided commit messages.

### Task Description
Goal: Add a DOCX parsing library and extraction path in the upload pipeline.

Constraints / Requirements
- Prefer a backend DOCX text extraction library suitable for server-side use.
- Populate `parsed_text` for uploaded DOCX files so they become searchable knowledge.
- Keep extraction pragmatic (plain text is fine; styling/layout fidelity is not required).
- Handle empty/failed extraction gracefully with a clear error message and without crashing the upload flow.
- No unrelated refactors.

### Expected Output
- Uploaded DOCX files have `parsed_text` populated.
- A focused test proves DOCX text extraction works.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- `guardian/routes/media.py`
- `guardian/routes/documents.py`
- `guardian/services/document_parsers/docx_text_extractor.py`
- `guardian/services/document_parsers/__init__.py`
- `guardian/tests/test_docx_text_extraction.py`
- `docs/work/tasks/2026/01/TASK_2026_01_20_010_add_docx_text_extraction.md`
- `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md`

## Checks to Run
- `pytest -v`

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): `TASK-2026-01-20-010_ADD_DOCX_TEXT_EXTRACTION: extract DOCX text on upload`
- Commit B (finalize artifact): `TASK-2026-01-20-010_ADD_DOCX_TEXT_EXTRACTION: finalize task summary`

## Summary
- Changes: added DOCX extractor with python-docx preference and XML fallback; wired `/upload/document` to extract DOCX `parsed_text`; added focused extraction test.
- Tests: `pytest -v` (pass: 560 passed, 1 skipped, 33 xfailed, 11 xpassed, 23 warnings).
- Git status --porcelain: `M docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md`, `?? docs/work/tasks/2026/01/TASK_2026_01_20_010_add_docx_text_extraction.md`
- Commit mode: two-phase
- Implementation commit: 94b69395
- Finalize commit: reported in campaign mapping
- Campaign mapping: `TASK-2026-01-20-010_ADD_DOCX_TEXT_EXTRACTION -> [94b69395, reported in campaign mapping]`
