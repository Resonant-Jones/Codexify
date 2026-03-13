Codexify Task Prompt

TASK-ID
TASK-2026-01-19-011_DOCKER_PLAYWRIGHT_E2E_HARNESS

Context
You’re operating on the local Codexify repo.

Playwright tests fail when run inside the existing frontend Docker container because the container is Alpine (musl) and Playwright’s downloaded Chromium expects glibc (missing loader /lib/ld-linux-aarch64.so.1). We want a production-grade Docker E2E harness that runs reliably in containers without requiring the frontend image to switch away from Alpine.

Objective
Add a dedicated Docker Compose E2E service that uses the official Playwright (glibc) image and can execute frontend Playwright tests against the running frontend dev server.

Requirements

- Do NOT change the existing frontend container base image.
- Add a new docker-compose service (e.g., `e2e`) using an official Playwright image (Ubuntu/glibc).
- E2E service must:
  - Install deps (pnpm install) and run Playwright tests from the repo.
  - Reuse an existing dev server instead of trying to start a second server on port 5173.
  - Use an internal network baseURL that works in Docker (prefer `http://frontend:5173`).
- Update Playwright config so it supports:
  - Local: baseURL defaults to http://localhost:5173
  - Docker harness: baseURL becomes http://frontend:5173
  - WebServer reuse behavior is controlled via env vars (do not break local usage).
  - Playwright artifact output must NOT dirty the git working tree by default (configure outputs under a dedicated ignored directory, or ignore the default Playwright output folders).
- Provide stable commands the developer can run:
  - Host (recommended): `docker compose run --rm e2e pnpm --dir frontend/src exec playwright test`
  - Inside the frontend container is NOT supported for Playwright browsers (Alpine/musl); use the `e2e` service instead.

Files allowed to edit (only)

- docker-compose.yml
- frontend/src/playwright.config.ts
- docs/work/tasks/2026/01/TASK_2026_01_19_011_docker_playwright_e2e_harness.md
- .gitignore

Implementation Notes

1) docker-compose.yml
Add a new service named `e2e`:

- image: use an official Playwright image (example tag is acceptable; pick a stable one)
- Optional (Apple Silicon): set `platform: linux/arm64` if Docker does not automatically pick an arm64 Playwright image.
- working_dir: /work
- volumes: mount repo into /work
- environment:
  - CI=1
  - DOCKER=1
  - PW_START_WEBSERVER=0
  - PW_REUSE_EXISTING_SERVER=1
  - PW_BASE_URL=http://frontend:5173
- depends_on:
  - frontend (and backend if required by UI)
- command should be a safe default (e.g. sleep infinity) but the expected usage is `docker compose run --rm e2e ...`

2) frontend/src/playwright.config.ts

- Use env overrides:
  - `const baseURL = process.env.PW_BASE_URL ?? 'http://localhost:5173'`
  - `const startWebServer = parseEnvBool(process.env.PW_START_WEBSERVER, true)`
  - `const reuseExistingServer = parseEnvBool(process.env.PW_REUSE_EXISTING_SERVER, true)`
  - In Docker harness, the e2e service sets `PW_START_WEBSERVER=0` so Playwright must NOT attempt to bind/start a second server.
- Ensure webServer logic remains correct:
  - IMPORTANT: the exported config must contain exactly ONE `webServer` property (avoid defining both `webServer: {...}` and `webServer,`). Compute a single `webServer` object (or `undefined`) and assign it once.
  - Local: startWebServer true by default (cold start friendly)
  - Docker: startWebServer false by default (reuse existing)
- Playwright outputs (git cleanliness)
  - Configure Playwright to write artifacts into a single directory under `frontend/src/.playwright/` (recommended), e.g. set:
    - `outputDir: '.playwright/test-results'`
    - `reporter: [['html', { outputFolder: '.playwright/playwright-report', open: 'never' }]]`
    - If your screenshot tests write to `frontend/src/screenshots/`, update them (if easy) to write under `.playwright/screenshots/`; otherwise, add ignores in `.gitignore` (see below).

3) Verification
From host:

- Ensure frontend is running via docker compose (5173 exposed).
- Run:
  - `docker compose run --rm e2e pnpm --dir frontend/src exec playwright test`
Expected: Playwright runs in the e2e container and passes (or at minimum launches browser successfully and executes tests; failures must be functional, not “missing browser binary/loader”).

Git hygiene requirements

- Ensure Playwright artifacts do not dirty the working tree by default.
- Update `.gitignore` to ignore Playwright output directories used by this repo, at minimum:
  - `frontend/src/test-results/`
  - `frontend/src/playwright-report/`
  - `frontend/src/screenshots/`
  - `frontend/src/.playwright/`
- The goal: after running the Docker E2E command, `git status --porcelain` should remain clean (aside from the intentional code/config changes).

Checks to run (required)

- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint
- docker compose run --rm e2e pnpm --dir frontend/src exec playwright test
- git status --porcelain (must be empty)

Git steps (two-phase)

Commit A (implementation)

1) git status --porcelain (must show only expected changes)
2) pnpm --dir frontend/src test (must pass)
3) pnpm --dir frontend/src lint (warnings ok, errors not ok)
4) docker compose run --rm e2e pnpm --dir frontend/src exec playwright test (must run; should pass)
5) git add docker-compose.yml frontend/src/playwright.config.ts
6) git commit -m "TASK-2026-01-19-011_DOCKER_PLAYWRIGHT_E2E_HARNESS: add glibc e2e runner service and baseURL overrides"

Commit B (finalize task artifact)

1) Create/update docs/work/tasks/2026/01/TASK_2026_01_19_011_docker_playwright_e2e_harness.md with:
   - Task Prompt (copy this prompt in)
   - Summary:
     - Changed files
     - Commands run + pass/fail
     - git status confirmation
     - Commit mode: two-phase (no amend)
     - Implementation hash: <hash A>
     - Finalize-artifact hash: (reported in final mapping)
     - How to run: docker compose run --rm e2e pnpm --dir frontend/src exec playwright test
2) git add docs/work/tasks/2026/01/TASK_2026_01_19_011_docker_playwright_e2e_harness.md
3) git commit -m "TASK-2026-01-19-011_DOCKER_PLAYWRIGHT_E2E_HARNESS: finalize task summary"

Output required
After finishing, output:

- Summary of changes
- Commands run + pass/fail (include docker compose run invocation)
- git status --porcelain (must be empty)
- Mapping:
  TASK-2026-01-19-011_DOCKER_PLAYWRIGHT_E2E_HARNESS -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria
✅ Playwright runs successfully inside Docker (no missing loader / browser ENOENT)  
✅ Harness targets running frontend via http://frontend:5173 in Docker  
✅ Local Playwright workflow remains valid (localhost baseURL + optional webServer start)  
✅ Repo remains clean after finalize commit  

Draft Summary (Blocked)
- Status: blocked on required check `pnpm --dir frontend/src test`.
- Failure: Vite could not resolve import "axios" from `frontend/src/lib/api.ts`, indicating missing deps outside the allowed file list.
- Commands run (latest attempt):
  - node -v
  - pnpm -v
  - uname -a
  - pnpm install --force
  - pnpm --dir frontend/src install --force
  - pnpm --dir frontend/src test (failed with axios resolution error)
- Scope note: dependency fixes likely require `frontend/src/package.json` and lockfile changes, which are not allowed in this task.
- Working tree: reverted changes to `docker-compose.yml`, `frontend/src/playwright.config.ts`, and `.gitignore` before writing this draft.
