Codexify Task Prompt

TASK-ID
TASK-2026-01-20-003_RAG_INTEGRATION_TEST_LOOP

Context
You are operating on the local Codexify repo on branch chore/post-skip-hook-fixes as part of
CAMPAIGN-2026-01-20-001_MVP_LOOP_CLOSURE_RAG.

We need an integration test that proves the RAG loop can store a memory item in the vector
store, complete embedding, retrieve it, and assert it is returned.

Instructions
- Edit only the allowed files listed below.
- Add an integration test that writes a memory item, forces embedding completion, retrieves via
  the ContextBroker memory path, and asserts the memory is returned.
- Use mock embeddings and avoid external network/model dependencies.
- Keep the test deterministic and fast; no new production behavior changes unless required for
  the test.
- Run `pytest -v`.
- Follow docs/Ops/Runner_Protocol.md two-phase commit flow and record hashes.

Task Description
Add a RAG integration test loop covering memory write -> embed -> retrieve -> assert.

Expected Output
- New integration test exists and passes.
- Test writes a memory item into the vector store, verifies embedding completion, retrieves via
  the RAG memory path, and asserts the memory item is returned.
- `pytest -v` passes.

Files allowed to edit (only)
- tests/integration/test_rag_integration_loop.py
- docs/tasks/TASK_2026_01_20_003_rag_integration_test_loop.md

Checks to run (required)
- pytest -v

Commit mode: two-phase
Commit message (implementation): TASK-2026-01-20-003_RAG_INTEGRATION_TEST_LOOP: add RAG integration test loop
Commit message (finalize): TASK-2026-01-20-003_RAG_INTEGRATION_TEST_LOOP: finalize task summary

## Summary
- Added integration coverage in `tests/integration/test_rag_integration_loop.py` for vector-store-backed memory retrieval via `ContextBroker`.
- Tests: `pytest -v` (pass).
- git status --porcelain: `docs/tasks/TASK_2026_01_20_003_rag_integration_test_loop.md`.
- Commit mode: two-phase.
- Implementation hash: `a7c8d18ce8c454639155e34075d83c893523e55d`.
- Finalize-artifact hash: reported in campaign mapping.
