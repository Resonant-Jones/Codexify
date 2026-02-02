# TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST: Add context broker integration test

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Add an integration test that verifies ContextBroker assembles context for a representative query and returns a trace structure consistent with the UI’s expectations.

### Expected Output
- A deterministic integration test exists and passes locally/CI.
- The test validates:
  - assemble() returns context + trace
  - at least one retrieval path is exercised (semantic results or recent messages)
  - no out-of-scope artifacts added

## Allowed Files
- guardian/tests/**/*.py
- guardian/context/broker.py (only if test reveals a bug needing minimal fix)
- guardian/routes/chat.py (only if needed for test harness)
- docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_010_context_broker_integration_test.md

## Checks to Run
- rg -n "ContextBroker|assemble\(" guardian/context/broker.py -S
- ls -1 guardian/tests | head -n 50
- rg -n "pytest" Makefile README.md pyproject.toml
- pytest -q guardian/tests/test_context_broker_integration.py
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST: add context broker integration test
- Commit B: TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST: finalize task summary

## Summary
- Added a deterministic ContextBroker integration test using dummy chatlog/vector inputs.
- Verified assembled context and trace structure for a representative query.
- Normalized Task 010 docs path in the campaign entry to the canonical filename.

## Checks Run
- `rg -n "ContextBroker|assemble\\(" guardian/context/broker.py -S`
- `ls -1 guardian/tests | head -n 50`
- `rg -n "pytest" Makefile README.md pyproject.toml`
- `pytest -q guardian/tests/test_context_broker_integration.py`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows the new test file, the task artifact, and the campaign file pending commits.

## Commits
- Commit A (implementation): `bd95789e`
- Commit B (finalize docs): `a0b0e2d1`

## Mapping
- TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST -> [bd95789e, a0b0e2d1]
