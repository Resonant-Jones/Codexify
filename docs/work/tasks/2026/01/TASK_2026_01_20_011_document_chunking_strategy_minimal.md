# TASK-2026-01-20-011_DOCUMENT_CHUNKING_STRATEGY_MINIMAL: Add document chunking

## Task Prompt
### Context
You are operating in the Codexify repo to extend the document upload pipeline for the
`CAMPAIGN-2026-01-20-003_MVP_LOOP_CLOSURE_DOCUMENT_UPLOAD_PARSING` campaign.

### Instructions
1. Implement deterministic fixed-size chunking with overlap for long documents.
2. Only chunk when `parsed_text` exceeds the threshold; otherwise keep a single chunk.
3. Preserve ordering with explicit chunk indices.
4. Keep scope limited to allowed files and run `pytest -v`.
5. Use two-phase commits with the provided commit messages.

### Task Description
Goal: Implement pragmatic chunking (fixed-size + overlap) for long documents so embeddings are stable and retrieval is useful.

Constraints / Requirements
- Chunking must be deterministic and stable for the same input text.
- Use a simple fixed-size character window with overlap (no semantic chunking required).
- Define conservative defaults (e.g., `chunk_size` and `chunk_overlap`) and make them easy to tune.
- Only chunk when `parsed_text` exceeds a threshold (e.g., `> chunk_size`), otherwise store a single chunk.
- Preserve ordering (each chunk should carry an index).
- Do not break existing upload flows.
- No unrelated refactors.

### Expected Output
- Long document text is split into ordered, overlapping chunks.
- A focused unit test proves chunking behavior (size, overlap, determinism).
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- `guardian/routes/documents.py`
- `guardian/services/document_chunking.py`
- `guardian/services/document_parsers/__init__.py`
- `guardian/tests/test_document_chunking.py`
- `docs/work/tasks/2026/01/TASK_2026_01_20_011_document_chunking_strategy_minimal.md`
- `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md`

## Checks to Run
- `pytest -v`

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): `TASK-2026-01-20-011_DOCUMENT_CHUNKING_STRATEGY_MINIMAL: add fixed chunking for long docs`
- Commit B (finalize artifact): `TASK-2026-01-20-011_DOCUMENT_CHUNKING_STRATEGY_MINIMAL: finalize task summary`

## Summary
- Changes: added deterministic fixed-size chunking with overlap and indices; added focused chunking unit tests.
- Tests: `pytest -v` (pass: 560 passed, 1 skipped, 33 xfailed, 11 xpassed, 23 warnings).
- Git status --porcelain: `M docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md`, `?? docs/work/tasks/2026/01/TASK_2026_01_20_011_document_chunking_strategy_minimal.md`
- Commit mode: two-phase
- Implementation commit: 951e32f0
- Finalize commit: reported in campaign mapping
- Campaign mapping: `TASK-2026-01-20-011_DOCUMENT_CHUNKING_STRATEGY_MINIMAL -> [951e32f0, reported in campaign mapping]`
