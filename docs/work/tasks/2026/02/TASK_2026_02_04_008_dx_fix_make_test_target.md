# TASK-2026-02-04-008_dx_fix_make_test_target

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-008_dx_fix_make_test_target

## Title

Fix Makefile test target to run pytest (remove missing tests/run_tests.py reference)

## Audit Link / Finding

- FINDING-2026-02-04-010

## Allowed Files List (ONLY)

- Makefile
- README.md
- tests/*or guardian/tests/* (only if needed to adjust invocation)

## Command Checklist

Preflight:

- git status --porcelain -uall

Locate:

- rg -n "run_tests\\.py" Makefile tests || true

Implement:

- Update `make test` to call pytest directly (consistent with README)
- Ensure command works in repo root

Verify:

- make test

## Expected Outputs (Success Criteria)

- `make test` runs and exits with pytest status code
- No references to missing tests/run_tests.py remain

## Rollback / Cleanup Commands

- git restore --staged Makefile README.md
- git restore Makefile README.md

## Dependencies / Prereqs

- pytest installed in active environment

## Commit Plan (MANUAL — Two Phase)

### Commit A message EXACT

"TASK-2026-02-04-008_dx_fix_make_test_target: make test runs pytest"

Commands:

- git add Makefile README.md
- git commit --no-verify -m "TASK-2026-02-04-008_dx_fix_make_test_target: make test runs pytest"
Record CommitA=f1e69a81

### Docs Commit message EXACT

"TASK-2026-02-04-008_dx_fix_make_test_target: finalize task docs and campaign mapping"

Commands:

- git add docs/work/tasks/2026/02/TASK_2026_02_04_008_dx_fix_make_test_target.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-008_dx_fix_make_test_target: finalize task docs and campaign mapping"
Record DocsCommit=84ce843e

Campaign mapping update EXACT:

- TASK-2026-02-04-008_dx_fix_make_test_target -> [f1e69a81] DocsCommit=84ce843e

## Stop Conditions

- Dirty tree with out-of-scope files => STOP.
