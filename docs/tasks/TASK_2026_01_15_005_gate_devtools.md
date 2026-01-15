# TASK-2026-01-15-005 — Gate devtools routes behind dev mode and API key

## Task Prompt
- **Context:** Ensure devtools endpoints are not reachable outside explicit dev mode in the local Codexify repo.
- **Instructions:** Edit only `guardian/routes/devtools.py` and `guardian/core/config.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Gate devtools routes behind a dev-mode configuration flag and API key requirement.
- **Expected Output:** Devtools routes require API key auth and reject access unless dev mode is enabled, with passing `pytest -v`.

## Summary
- Changed files: `guardian/routes/devtools.py` (devtools access dependency enforcing API key + dev mode), `guardian/core/config.py` (added `GUARDIAN_DEV_MODE` setting).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit hash: `76346184e91c65a6d36aa5bb5a16ecbdebdec124`
