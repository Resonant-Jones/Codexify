# TASK-2026-01-20-009_ADD_PDF_TEXT_EXTRACTION: Add PDF text extraction

## Task Prompt
### Context
You are operating in the Codexify repo to extend the document upload pipeline for the
`CAMPAIGN-2026-01-20-003_MVP_LOOP_CLOSURE_DOCUMENT_UPLOAD_PARSING` campaign.

### Instructions
1. Implement PDF text extraction using a server-side library.
2. Populate `parsed_text` for uploaded PDFs and handle failures gracefully.
3. Keep scope limited to the allowed files and run `pytest -v`.
4. Use two-phase commits with the provided commit messages.

### Task Description
Goal: Add a PDF parsing library and extraction path in the upload pipeline.

Constraints / Requirements
- Prefer a backend PDF text extraction library suitable for server-side use (no headless browser requirement).
- Populate `parsed_text` for uploaded PDFs so they become searchable knowledge.
- Keep extraction pragmatic (plain text is fine; layout-perfect fidelity is not required).
- Handle empty/failed extraction gracefully with a clear error message and without crashing the upload flow.
- No unrelated refactors.

### Expected Output
- Uploaded PDFs have `parsed_text` populated.
- A focused test proves PDF text extraction works.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- `guardian/routes/media.py`
- `guardian/routes/documents.py`
- `guardian/services/document_parsers/pdf_text_extractor.py`
- `guardian/services/document_parsers/__init__.py`
- `guardian/tests/test_pdf_text_extraction.py`
- `docs/work/tasks/2026/01/TASK_2026_01_20_009_add_pdf_text_extraction.md`
- `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md`

## Checks to Run
- `pytest -v`

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): `TASK-2026-01-20-009_ADD_PDF_TEXT_EXTRACTION: extract PDF text on upload`
- Commit B (finalize artifact): `TASK-2026-01-20-009_ADD_PDF_TEXT_EXTRACTION: finalize task summary`

## Summary
- Changes: added PDF text extractor with fallback parsing and error handling; wired `/upload/document` to extract PDF `parsed_text`; added focused extraction test.
- Tests: `pytest -v` (pass: 560 passed, 1 skipped, 33 xfailed, 11 xpassed, 23 warnings).
- Git status --porcelain: `M docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md`, `?? docs/work/tasks/2026/01/TASK_2026_01_20_009_add_pdf_text_extraction.md`
- Commit mode: two-phase
- Implementation commit: 3b5c0e5e
- Finalize commit: reported in campaign mapping
- Campaign mapping: `TASK-2026-01-20-009_ADD_PDF_TEXT_EXTRACTION -> [3b5c0e5e, reported in campaign mapping]`
