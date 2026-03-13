# TASK-2026-01-20-017_DOCUMENT_GEN_TEST: Document Generation Pipeline Test

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-017_DOCUMENT_GEN_TEST.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Add deterministic automated coverage for the document generation pipeline using an LLM stub/mock (no external network calls). Cover at minimum: happy path (generate -> returns content -> persists document -> links to thread) and an error path (LLM failure OR DB failure returns a user-safe error). Prefer a backend test at the Guardian layer (FastAPI test client) and stub the LLM call via dependency injection or monkeypatch. No unrelated refactors.

### Expected Output
- A deterministic test validates document generation behavior with an LLM stub.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- guardian/routes/documents.py
- guardian/guardian_api.py
- guardian/services/llm.py
- guardian/core/llm.py
- guardian/core/llm_client.py
- guardian/tests/test_document_gen_pipeline.py
- docs/work/tasks/2026/01/TASK_2026_01_20_017_document_gen_test.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md

## Checks to Run
- pytest -v

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): TASK-2026-01-20-017_DOCUMENT_GEN_TEST: add deterministic generation pipeline test
- Commit B (finalize artifact): TASK-2026-01-20-017_DOCUMENT_GEN_TEST: finalize task summary

## Summary
TBD
