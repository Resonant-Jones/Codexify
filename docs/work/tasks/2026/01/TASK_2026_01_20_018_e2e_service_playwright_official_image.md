# TASK-2026-01-20-018_E2E_SERVICE_PLAYWRIGHT_OFFICIAL_IMAGE: Docker E2E Service

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-005_PRODUCTION_GRADE_DOCKER_E2E_HARNESS.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-018_E2E_SERVICE_PLAYWRIGHT_OFFICIAL_IMAGE.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Introduce/repair a docker-compose e2e service using Playwright’s official image with a stable working directory and volume mounts so `frontend/src` tests can run. Ensure baseURL and networking work inside Docker (no localhost confusion). Do not break local non-docker Playwright usage.

### Expected Output
- `docker compose run --rm e2e pnpm --dir frontend/src exec playwright test --list` succeeds inside the container.
- Task artifact recorded with commands + results + hashes.

## Allowed Files
- docker-compose.yml
- frontend/src/playwright.config.ts
- frontend/src/package.json
- .dockerignore
- docs/work/tasks/2026/01/TASK_2026_01_20_018_e2e_service_playwright_official_image.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md

## Checks to Run
- docker compose run --rm e2e pnpm --dir frontend/src exec playwright test --list

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-20-018_E2E_SERVICE_PLAYWRIGHT_OFFICIAL_IMAGE: add docker e2e service
- Commit B: TASK-2026-01-20-018_E2E_SERVICE_PLAYWRIGHT_OFFICIAL_IMAGE: finalize task summary

## Summary
- Added an `e2e` Playwright service in `docker-compose.yml` using the official image with stable mounts and `PW_BASE_URL` for container networking.
- Checks:
  - `docker compose run --rm e2e pnpm --dir frontend/src exec playwright test --list`
- Git status: `git status --porcelain` shows only allowed docs files pending finalize commit.
- Commit mode: two-phase.
- Implementation commit: `6fa78eb5`.
- Finalize commit: reported in campaign mapping.
- Campaign mapping requirement: `TASK-2026-01-20-018_E2E_SERVICE_PLAYWRIGHT_OFFICIAL_IMAGE -> [6fa78eb5, <finalize_hash>]`.
