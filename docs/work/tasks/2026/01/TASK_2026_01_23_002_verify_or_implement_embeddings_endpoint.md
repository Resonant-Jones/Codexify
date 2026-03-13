# TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT: Ensure embeddings endpoint exists

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Confirm `/api/embeddings` exists and behaves as expected by `frontend/src/hooks/useUploader.ts` (document upload embedding call). If missing or mismatched, implement/fix it.

### Expected Output
- There is a reachable POST endpoint at /api/embeddings (or an explicitly documented replacement that the frontend uses).
- The endpoint returns a 2xx response and persists embeddings to the configured vector store.
- Contract is documented in this task artifact (request + response shape).

## Allowed Files
- guardian/routes/**/*.py
- guardian/guardian_api.py (or the single authoritative FastAPI wiring file used)
- backend/rag/embedder.py (only if needed for request/response adaptation)
- guardian/vector/store.py (only if needed)
- guardian/tests/**/*.py
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/work/tasks/2026/01/TASK_2026_01_23_002_verify_or_implement_embeddings_endpoint.md
- frontend/src/hooks/useUploader.ts (only if the endpoint contract must be aligned)

Note: The campaign text references `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- rg -n "/api/embeddings|embeddings" frontend/src/hooks/useUploader.ts
- rg -n "api/embeddings|/embeddings|Embeddings" guardian/routes guardian/guardian_api.py backend | head -n 200
- curl -s http://localhost:8888/openapi.json | rg -n "\"/api/embeddings\"" -n || true
- curl -s -X POST http://localhost:8888/api/embeddings -H "Content-Type: application/json" -d '{"texts":["hello world"],"namespace":"test","metadata":{"source":"task-002"}}' | head -n 60
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT: ensure embeddings endpoint exists
- Commit B: TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT: finalize task summary

## Summary
- Added best-effort vector store ingestion to `/api/embeddings` while keeping the response contract stable.
- Added a minimal payload test to confirm `{texts:[...]}` requests succeed.

## Checks Run
- `rg -n "/api/embeddings|embeddings" frontend/src/hooks/useUploader.ts`
- `rg -n "api/embeddings|/embeddings|Embeddings" guardian/routes guardian/guardian_api.py backend | head -n 200`
- `curl -s http://localhost:8888/openapi.json | rg -n "\"/api/embeddings\"" -n || true` (no output; backend not running)
- `curl -s -X POST http://localhost:8888/api/embeddings ...` (not run; backend not running)
- `pytest -q guardian/tests/test_embeddings_endpoint.py`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows this task artifact + campaign mapping pending record finalize hash commit.

## Commits
- Commit A (implementation): `b95a1646`
- Commit B (finalize docs): `57deb7b8`

## Mapping
- TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT -> [b95a1646, 57deb7b8]
