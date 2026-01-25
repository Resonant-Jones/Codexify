# TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT: Verify memory store wiring

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Verify the memory store is actually initialized and wired into ContextBroker creation, per audit.

### Expected Output
- Clear, code-evidenced path showing memory store initialization and injection into ContextBroker.
- If broken, fixed wiring is merged and documented in this task.

## Allowed Files
- guardian/core/dependencies.py
- guardian/memory/**/*.py
- guardian/context/broker.py (only if wiring fix needed)
- guardian/routes/chat.py (only if wiring fix needed)
- guardian/tests/**/*.py (optional)
- docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_009_verify_memory_store_init.md

Note: The campaign text references `docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- rg -n "_memory_store|MemoryStore|memoryos|dependencies" guardian/core/dependencies.py guardian/memory guardian/context/broker.py guardian/routes/chat.py -S
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT: verify memory store wiring
- Commit B: TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT: finalize task summary

## Summary
- Verified memory store initialization in `guardian/memory/query_memory.py` and injection via `guardian/core/dependencies.py` into ContextBroker usage.
- No wiring changes required.

## Checks Run
- `rg -n "_memory_store|MemoryStore|memoryos|dependencies" guardian/core/dependencies.py guardian/memory guardian/context/broker.py guardian/routes/chat.py -S`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows only this task artifact pending finalize commit.

## Commits
- Commit A (implementation): `9a462cf8`
- Commit B (finalize docs): `2b1029ad`

## Mapping
- TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT -> [9a462cf8, 2b1029ad]
