# TASK-2026-01-15-001 — Remove /api/chat api-bypass alias

## Task Prompt
- **Context:** Close the explicit auth bypass path on `/api/chat` in the local Codexify repo.
- **Instructions:** Edit only `guardian/routes/chat.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Remove the `/api/chat` api-bypass behavior by requiring normal API key verification.
- **Expected Output:** A single scoped code change in `guardian/routes/chat.py` with passing `pytest -v`.

## Summary
- Changed files: `guardian/routes/chat.py` (api_chat_root now depends on `require_api_key` instead of hardcoded bypass).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit hash: `48d4747dd805891e3c7c74f62f9522149dc7dc8e`
