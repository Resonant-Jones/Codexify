Codexify Task Prompt

TASK-ID
TASK-2026-01-20-002_VECTOR_STORE_HEALTH_ENDPOINT

Context
You are operating on the local Codexify repo on branch chore/post-skip-hook-fixes as part of
CAMPAIGN-2026-01-20-001_MVP_LOOP_CLOSURE_RAG.

We need a vector store health endpoint in the canonical backend entrypoint to verify
connectivity and basic add/search behavior.

Instructions
- Edit only the allowed files listed below.
- Add a health endpoint that checks the vector store by performing a simple add + search.
- Use the canonical backend app (guardian/guardian_api.py includes guardian/routes/health.py).
- Keep behavior minimal; do not alter embedding logic or unrelated RAG flows.
- Run `pytest -v`.
- Follow docs/Ops/Runner_Protocol.md two-phase commit flow and record hashes.

Task Description
Add a vector store health endpoint that verifies connectivity and basic add/query capability.
Add a backend test that exercises the endpoint in the canonical app.

Expected Output
- A GET health endpoint returns JSON with ok/error status and vector store details.
- The endpoint performs a minimal add + search probe without breaking existing behavior.
- `pytest -v` passes.

Files allowed to edit (only)
- guardian/routes/health.py
- tests/routes/test_metrics.py
- docs/tasks/TASK_2026_01_20_002_vector_store_health_endpoint.md

Checks to run (required)
- pytest -v

Commit mode: two-phase
Commit message (implementation): TASK-2026-01-20-002_VECTOR_STORE_HEALTH_ENDPOINT: add vector store health endpoint
Commit message (finalize): TASK-2026-01-20-002_VECTOR_STORE_HEALTH_ENDPOINT: finalize task summary

## Summary
- Added `GET /health/vector` probe in `guardian/routes/health.py`, including add+search checks and a chroma-safe probe path.
- Added coverage in `tests/routes/test_metrics.py`.
- Tests: `pytest -v` (pass).
- git status --porcelain: `docs/tasks/TASK_2026_01_20_002_vector_store_health_endpoint.md`.
- Commit mode: two-phase.
- Implementation hash: `55503fabebd7fadadbe519e3ea0f8c5b7e214d82`.
- Finalize-artifact hash: reported in campaign mapping.
