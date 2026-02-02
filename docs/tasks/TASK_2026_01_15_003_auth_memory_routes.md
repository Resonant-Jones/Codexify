# TASK-2026-01-15-003 — Require API key for memory routes

## Task Prompt
- **Context:** Prevent unauthenticated access to memory read/write endpoints in the local Codexify repo.
- **Instructions:** Edit only `guardian/routes/memory.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Require API key authentication across memory routes.
- **Expected Output:** Memory routes enforce `require_api_key`, with passing `pytest -v`.

## Summary
- Changed files: `guardian/routes/memory.py` (wired `require_api_key` into memory routers and imported core dependency).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit mode: two-phase
- Implementation hash: `3720288dec0fce1e76d907a9af339b78c8b3eeb9`
- Finalize-artifact hash: `e2872f2a5f527a8e2ff8f80132010fde5f0d0d1d`