# CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md

## Campaign-ID

CAMPAIGN-2026-02-06-LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION

## Purpose

Close the “tests-before-commit” reliability gap by:

- making test prerequisites deterministic (pytest/venv),
- adding a repeatable preflight checklist,
- adding a deterministic validation for the chat-embed queue/worker loop,
- preventing future “BLOCKER_PROMPT due to missing tooling” cycles.

This campaign is **DX + Loop Integrity**, not feature work.

## Global Rules

- STOP if `git status --porcelain -uall` is not empty (clean tree required).
- Two-phase commits (A implementation, B docs finalize + mapping).
- Manual commits only (index.lock workaround).

## Task List (Ordered)

1) TASK-2026-02-06-001_env_preflight_contract
2) TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path
3) TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist
4) TASK-2026-02-06-004_validate_chat_embed_queue_loop

## Mapping (placeholders)

- TASK-2026-02-06-001_env_preflight_contract -> [7ddc7b49, fd6fa3ea]
- TASK-2026-02-06-002_fix_make_test_target_and_pytest_install_path -> [<commitA>, <commitB>]
- TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist -> [<commitA>, <commitB>]
- TASK-2026-02-06-004_validate_chat_embed_queue_loop -> [<commitA>, <commitB>]

## Completion Criteria

Campaign is DONE when all tasks are DONE or explicitly DEFERRED with a documented decision.
