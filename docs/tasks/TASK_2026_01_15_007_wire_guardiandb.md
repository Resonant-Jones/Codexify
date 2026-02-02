# TASK-2026-01-15-007 — Wire GuardianDB configuration at app startup

## Task Prompt
- **Context:** Ensure GuardianDB-backed routers are configured at app startup in the local Codexify repo.
- **Instructions:** Edit only `guardian/guardian_api.py`, `guardian/server/app.py`, and `guardian/core/db.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Initialize GuardianDB from environment configuration and wire it into routers that depend on it during app startup.
- **Expected Output:** GuardianDB is configured at startup and routed to document/share endpoints, with passing `pytest -v`.

## Summary
- Changed files: `guardian/core/db.py` (added env loader helper), `guardian/guardian_api.py` (startup wiring for documents/share), `guardian/server/app.py` (startup wiring for documents).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit mode: two-phase
- Implementation hash: `bf12fcb4489d144353d72e51d1d5037755343bad`
- Finalize-artifact hash: `63e65b4a31159b38dbd9da7af0e280cdd9face09`