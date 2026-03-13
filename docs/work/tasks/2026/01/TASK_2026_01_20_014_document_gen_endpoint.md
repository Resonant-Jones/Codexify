# TASK-2026-01-20-014_DOCUMENT_GEN_ENDPOINT: Document Generation Endpoint

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-014_DOCUMENT_GEN_ENDPOINT.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Implement the backend endpoint POST /api/documents/generate using existing LLM/chat completion infrastructure. The request schema should accept the modal payload (title/type/prompt/context) and return generated text plus any metadata needed for follow-on tasks. Add clear, user-safe error messages on failure (400 for bad input, 500 for server issues). Add a focused test that covers the happy path and at least one error path. No unrelated refactors.

### Expected Output
- POST /api/documents/generate returns 200 with generated content for a valid request.
- A focused unit/integration test covers the happy path and at least one error path.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- guardian/guardian_api.py
- guardian/routes/documents.py
- guardian/routes/media.py
- guardian/services/llm.py
- guardian/core/llm.py
- guardian/core/llm_client.py
- guardian/tests/test_document_gen_endpoint.py
- docs/work/tasks/2026/01/TASK_2026_01_20_014_document_gen_endpoint.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md

## Checks to Run
- pytest -v

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): TASK-2026-01-20-014_DOCUMENT_GEN_ENDPOINT: add documents generate endpoint
- Commit B (finalize artifact): TASK-2026-01-20-014_DOCUMENT_GEN_ENDPOINT: finalize task summary

## Summary
- Added /api/documents/generate request/response models and LLM-backed handler with validation + safe errors in `guardian/routes/documents.py`.
- Added focused endpoint tests (happy path + missing prompt) in `guardian/tests/test_document_gen_endpoint.py`.
- Tests:
  - `pytest -v`
  - `pytest -v guardian/tests/test_document_gen_endpoint.py`
- Git status: `git status --porcelain` shows only allowed docs files pending finalize commit.
- Commit mode: two-phase.
- Implementation commit: `5b6cfd6a`.
- Finalize commit: reported in campaign mapping.
- Campaign mapping requirement: `TASK-2026-01-20-014_DOCUMENT_GEN_ENDPOINT -> [5b6cfd6a, <finalize_hash>]`.
