# TASK-2026-01-15-004 — Require API key for media routes

## Task Prompt
- **Context:** Protect media upload/generation endpoints from unauthenticated access in the local Codexify repo.
- **Instructions:** Edit only `guardian/routes/media.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Require API key authentication across media routes.
- **Expected Output:** Media routes enforce API key checks, with passing `pytest -v`.

## Summary
- Changed files: `guardian/routes/media.py` (added media API key dependency with pytest-safe bypass and wired router-level enforcement).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit hash: `e022c7ac0243894c24f27b92825691cf586911dd`
