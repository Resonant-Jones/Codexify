# TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST: Verify memory init + ContextBroker integration test

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Ensure memory store is initialized correctly and add a deterministic ContextBroker integration test covering retrieval/memory hooks end-to-end (mock external services as needed).

### Expected Output
- Initialization path confirmed in code and documented.
- Integration test passes without external network calls.

## Allowed Files
- guardian/core/dependencies.py
- guardian/context/*.py
- guardian/memory/*.py
- guardian/tests/test_*.py
- docs/tasks/TASK_2026_01_23_008_memory_init_and_context_integration_test.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "Memory|memory store|MemoryStore|get_memory" guardian/core/dependencies.py guardian/memory guardian/context
- pytest -q -k "context and broker" || true

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST: add context broker integration test
- Commit B: TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST: finalize task summary

## Summary
- Confirmed memory store initialization via `guardian/core/dependencies.py` (`_memory_store`).
- Added a deterministic ContextBroker integration test covering deep-mode memory retrieval without external calls.

## Checks Run
- `rg -n "Memory|memory store|MemoryStore|get_memory" guardian/core/dependencies.py guardian/memory guardian/context`
- `pytest -q -k "context and broker" || true` (pass)

## Git Status
- `git status --porcelain -uall` shows only this task artifact pending finalize commit.

## Commits
- Commit A (implementation): `160d6c21`
- Commit B (finalize docs): TBD

## Mapping
- TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST -> [160d6c21, ]
