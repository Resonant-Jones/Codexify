# TASK-2026-01-16-004 — Deduplicate “Loose Threads” at the DB source of truth

## Task Prompt
- **Context:** Guardian chat sidebar polish campaign; ensure a canonical Loose Threads project row and avoid hardcoded IDs in migration.
- **Instructions:** Edit only `backend/scripts/seed_defaults.py` and `backend/rag/chatgpt_migration.py`. Run `pytest -v`. Use two-phase commits and record both commit hashes in the Summary.
- **Task Description:** Enforce a canonical “Loose Threads” project row (idempotent). If duplicates exist, migrate threads to the canonical project and remove redundant rows. Ensure ChatGPT migration resolves the canonical project dynamically (avoid hardcoding project_id=1).
- **Expected Output:** Dedupe logic in place, migration resolves canonical project, `pytest -v` passes, and the task artifact records both commit hashes with a clean `git status --porcelain`.

## Summary
- Changed files: `backend/scripts/seed_defaults.py`, `backend/rag/chatgpt_migration.py` (canonicalize Loose Threads + dynamic resolution in migration).
- Commands: `pytest -v` (timeout, then pass); `git status --porcelain` (clean).
- Commit mode: two-phase
- Implementation hash: `741e28019b23fa5a92165c6a7989f40a2fe1d2f5`
- Finalize-artifact hash: (this commit; see git log / final mapping)
