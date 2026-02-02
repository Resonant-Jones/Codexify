# TASK-2026-01-14-CLEAN-002 — Personal facts / message guard / capability index

## Task Prompt
- **Context:** Package the personal facts and message guard backend feature slice in the local Codexify repo while following `docs/Ops/Runner_Protocol.md`.
- **Instructions:** Allowed files: `guardian/core/message_guard.py`, `guardian/routes/personal_facts.py`, `guardian/graph/capability_index.py`, migrations `guardian/db/migrations/versions/a1b2c3d4e5f6_add_temporal_and_personal_facts.py` and `c7a253a50757_merge_guardian_heads.py`, tests `tests/core/test_capability_index.py`, `tests/routes/test_personal_facts_routes.py`, `tests/test_chat_message_guard.py`, `tests/test_chat_worker_blank_output.py`, `tests/test_personal_facts_crud.py`, `tests/test_temporal_facts_migration.py`. Do not include unrelated config changes. Test loop: `pytest -v`. Commit message: `Add personal facts, message guard, and capability index`. Record artifact summary + commit hash.
- **Task Description:** Add the personal facts API routes, message guard helper, capability index tracking, supporting migrations, and related tests.
- **Expected Output:** One commit containing only the allowed backend/test files plus this artifact, with passing `pytest -v` noted.

## Summary
- Changed files: `guardian/core/message_guard.py`, `guardian/routes/personal_facts.py`, `guardian/graph/capability_index.py`, migrations under `guardian/db/migrations/versions/`, tests under `tests/` for capability index, personal facts, and message guard behavior.
- Tests: Pending.
- git status: TODO
- Commit hash: TODO
