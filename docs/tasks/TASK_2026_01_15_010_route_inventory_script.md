# TASK-2026-01-15-010 — Add script to print FastAPI route inventory

## Task Prompt
- **Context:** Provide a reproducible script to inventory mounted FastAPI routes in the local Codexify repo.
- **Instructions:** Edit only `scripts/list_routes.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Add a script that imports the Guardian FastAPI app and prints its route inventory.
- **Expected Output:** A new `scripts/list_routes.py` that prints routes, with passing `pytest -v`.

## Summary
- Changed files: `scripts/list_routes.py` (new route inventory script).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit hash: `15c870b8c8cb25476454577f503f3ca05b4d630e`
