# TASK-2026-01-15-006 — Fail closed when cloud providers are disallowed

## Task Prompt
- **Context:** Enforce sovereignty by blocking cloud LLM calls when disallowed in the local Codexify repo.
- **Instructions:** Edit only `guardian/workers/chat_worker.py` and `guardian/core/config.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Ensure chat worker fails closed if a cloud provider is requested while `ALLOW_CLOUD_PROVIDERS` is false.
- **Expected Output:** Chat worker blocks cloud providers when disallowed, with passing `pytest -v`.

## Summary
- Changed files: `guardian/workers/chat_worker.py` (fail closed when cloud provider requested), `guardian/core/config.py` (added cloud provider helper).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit mode: two-phase
- Implementation hash: `a1df5b2a7b2c71cab4b566240c91ec056b54f114`
- Finalize-artifact hash: `1cadd1b8b1d90b1b94086120f07fa2eb533a0a85`