# TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT: Verify embeddings endpoint used by frontend

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Confirm the embeddings endpoint exists, matches frontend usage, and functions (returns success + predictable shape). If missing/mismatched, implement/correct it.

### Scope
- Identify frontend call sites and expected route/path.
- Ensure backend route exists and is wired into FastAPI app.
- Add/adjust a minimal backend test for endpoint contract.

### Expected Output
- One clear embeddings route used by frontend.
- Test passes for the endpoint contract.

## Allowed Files
- guardian/guardian_api.py
- guardian/routes/*.py
- guardian/tests/test_*.py
- frontend/src/**/*.ts
- frontend/src/**/*.tsx
- docs/tasks/TASK_2026_01_23_002_verify_embeddings_endpoint.md
- docs/Campaign/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "/api/embeddings|embeddings" frontend/src
- rg -n "embeddings|/api/embeddings" guardian/routes guardian/guardian_api.py
- pytest -q guardian/tests -k "embedding or embeddings" || true

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT: verify embeddings endpoint contract
- Commit B: TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT: finalize task summary

## Summary
- Located frontend references to the embeddings route and confirmed the canonical path is **/api/embeddings**.
- Implemented a minimal FastAPI route at `guardian/routes/embeddings.py` and wired it into the main app in `guardian/guardian_api.py`.
- Added a focused contract test in `guardian/tests/test_embeddings_endpoint.py` to validate a successful response and stable JSON shape.

### Checks run
- `rg -n "/api/embeddings|embeddings" frontend/src`
- `rg -n "embeddings|/api/embeddings" guardian/routes guardian/guardian_api.py`
- `pytest -q guardian/tests -k "embedding or embeddings" || true` *(collection failed due to Neo4j test seed: `neomodel.exceptions.NodeClassAlreadyDefined`)*
- `pytest -q guardian/tests/test_embeddings_endpoint.py` *(pass: 1 test)*

### Commits
- Commit A (implementation): `9f9b1c3b`
- Commit B (finalize docs): `0efbb2fb`
