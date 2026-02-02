# TASK-2026-01-20-021_E2E_SMOKE_TEST_CANARY: E2E Smoke Canary

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-005_PRODUCTION_GRADE_DOCKER_E2E_HARNESS.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-021_E2E_SMOKE_TEST_CANARY.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Add a tiny, deterministic Playwright smoke test that boots the app, loads the root page, and asserts a stable element exists. The test must run both locally and in the Docker harness; keep selectors stable (role-based or data-testid if already present).

### Expected Output
- Smoke canary test passes locally.
- Task artifact recorded with commands + results + hashes.

## Allowed Files
- frontend/src/tests/playwright/e2e_smoke_canary.spec.ts
- frontend/src/playwright.config.ts
- docs/tasks/TASK_2026_01_20_021_e2e_smoke_test_canary.md
- docs/Campaign/CAMPAIGN_2026_01_20.md

## Checks to Run
- pnpm --dir frontend/src exec playwright test e2e_smoke_canary.spec.ts

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-20-021_E2E_SMOKE_TEST_CANARY: add smoke canary test
- Commit B: TASK-2026-01-20-021_E2E_SMOKE_TEST_CANARY: finalize task summary

## Summary
- Added a Playwright smoke canary test that loads the app and asserts the Guardian tab is visible.
- Checks:
  - `pnpm --dir frontend/src exec playwright test e2e_smoke_canary.spec.ts` (passed: 1 test; Vite proxy ECONNREFUSED to backend :8888 noted but non-fatal).
- Git status: `git status --porcelain` clean after docs reconciliation commit.
- Commit mode: two-phase.
- Implementation commit: `d822a735`.
- Finalize commit: `33ee566d`.
- Campaign mapping requirement: `TASK-2026-01-20-021_E2E_SMOKE_TEST_CANARY -> [d822a735, 33ee566d]`.
