# TASK-2026-01-20-019_PLAYWRIGHT_CONFIG_ENV_SWITCHING: Playwright Env Switching

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-005_PRODUCTION_GRADE_DOCKER_E2E_HARNESS.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-019_PLAYWRIGHT_CONFIG_ENV_SWITCHING.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Update Playwright config so: baseURL uses PW_BASE_URL, reuseExistingServer is configurable via env, webServer is optional via PW_START_WEBSERVER=0, and local path remains valid. Keep changes minimal and backwards compatible.

### Expected Output
- `pnpm --dir frontend/src exec playwright test --list` succeeds.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- frontend/src/playwright.config.ts
- docs/tasks/TASK_2026_01_20_019_playwright_config_env_switching.md
- docs/Campaign/CAMPAIGN_2026_01_20.md

## Checks to Run
- pnpm --dir frontend/src exec playwright test --list

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-20-019_PLAYWRIGHT_CONFIG_ENV_SWITCHING: env-driven playwright config
- Commit B: TASK-2026-01-20-019_PLAYWRIGHT_CONFIG_ENV_SWITCHING: finalize task summary

## Summary
- Added Playwright env toggles for baseURL, reuseExistingServer, and optional webServer in `frontend/src/playwright.config.ts`.
- Checks:
  - `pnpm --dir frontend/src exec playwright test --list` (reported by user: 8 tests / 4 files).
- Git status: `git status --porcelain` shows only allowed docs files pending finalize commit.
- Commit mode: two-phase.
- Implementation commit: `e9fc445a`.
- Finalize commit: reported in campaign mapping.
- Campaign mapping requirement: `TASK-2026-01-20-019_PLAYWRIGHT_CONFIG_ENV_SWITCHING -> [e9fc445a, <finalize_hash>]`.
