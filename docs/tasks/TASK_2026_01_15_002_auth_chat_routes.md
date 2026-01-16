# TASK-2026-01-15-002 — Require API key for chat routes

## Task Prompt
- **Context:** Establish a consistent auth boundary on core chat routes in the local Codexify repo.
- **Instructions:** Edit only `guardian/routes/chat.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Require API key authentication on `/chat/*` and `/api/chat/*` routes.
- **Expected Output:** Chat routes enforce `require_api_key`, with passing `pytest -v`.

## Summary
- Changed files: `guardian/routes/chat.py` (added `require_api_key` dependencies across chat and alias endpoints, including debug trace endpoint).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit mode: two-phase
- Implementation hash: `268584a3d71e86f2d179a53cebba748a48a22a27`
- Finalize-artifact hash: `52b5c8f6479cc3c3ff75573bd89092a27baa7aac`