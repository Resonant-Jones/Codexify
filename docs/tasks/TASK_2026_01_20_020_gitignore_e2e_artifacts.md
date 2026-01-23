# TASK-2026-01-20-020_GITIGNORE_E2E_ARTIFACTS: Ignore Playwright Artifacts

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-005_PRODUCTION_GRADE_DOCKER_E2E_HARNESS.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-020_GITIGNORE_E2E_ARTIFACTS.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Ignore Playwright artifacts (test-results/, screenshots, traces, playwright-report/) or redirect output to a known ignored directory.

### Expected Output
- Playwright artifacts are ignored or redirected to ignored paths.
- Task artifact recorded with commands + results + hashes.

## Allowed Files
- .gitignore
- frontend/src/playwright.config.ts
- docs/tasks/TASK_2026_01_20_020_gitignore_e2e_artifacts.md
- docs/Campaign/CAMPAIGN_2026_01_20.md

## Checks to Run
- pnpm --dir frontend/src exec playwright test --list

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-20-020_GITIGNORE_E2E_ARTIFACTS: ignore playwright artifacts
- Commit B: TASK-2026-01-20-020_GITIGNORE_E2E_ARTIFACTS: finalize task summary

## Summary
- Added Playwright artifact ignores for traces and .last-run.json under `frontend/src` in `.gitignore`.
- Checks:
  - `pnpm --dir frontend/src exec playwright test --list` (passed: 8 tests / 4 files).
- Git status: `git status --porcelain` clean after finalize commit.
- Commit mode: two-phase.
- Implementation commit: `9f445e63`.
- Finalize commit: `556bedd5`.
- Campaign mapping requirement: `TASK-2026-01-20-020_GITIGNORE_E2E_ARTIFACTS -> [9f445e63, 556bedd5]`.
