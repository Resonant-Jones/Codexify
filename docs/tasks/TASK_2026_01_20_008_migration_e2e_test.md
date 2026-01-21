# TASK-2026-01-20-008_MIGRATION_E2E_TEST: Migration E2E Test

## Context
You’re operating on the local Codexify repo on branch `chore/post-skip-hook-fixes`.

Migration is **asynchronous** by design:
- `POST /api/upload-chatgpt-export` queues an import.
- Processing may complete after the current UI session ends.
- On startup, Codexify scans for pending/unprocessed imports and processes them in the background.

This E2E must be deterministic and must **not** assume synchronous completion.

Canonical backend entrypoint: `guardian/guardian_api.py`.
Canonical migration endpoint: `POST /api/upload-chatgpt-export` (legacy `/upload-chatgpt-export` preserved).

## Instructions
1. Perform the described edit only in the specified files.
2. Run the appropriate test suite based on what was modified:
   - Frontend-only changes:
     - Run:
       - `pnpm --dir frontend/src test`
       - `pnpm --dir frontend/src lint`
       - `pnpm --dir frontend/src exec playwright test migration_e2e_import.spec.ts`
3. If tests pass:
   - Stage modified files with `git add`.
   - Commit using the commit messages defined below (two-phase commits).
4. Output:
   - Summary of what changed (files + key selectors/assertions).
   - Test / lint results.
   - The git commit hash(es).

## Task Description
Update the Playwright E2E for ChatGPT migration to be deterministic by using **network stubbing** and by asserting the **async** queue/resume/notify behavior.

### What the test must verify
**A. Queue (same session):**
1) UI navigation to Settings → Data → ChatGPT Migration → Import flow is stable.
2) Clicking “Upload & Migrate” results in a request to the canonical endpoint:
   - `POST /api/upload-chatgpt-export`
3) The UI reaches a *queued / processing-in-background* state (do not require completion).

**B. Resume (simulated next session):**
4) On page reload (simulating a new session), Codexify performs the pending-import scan.
5) The UI receives a passive completion signal (banner/toast/notification) when the job completes.

### Determinism requirements
- Do **not** rely on real ingestion time or background workers.
- Do **not** assert immediate “Migration Successful” right after click.
- Use Playwright `page.route()` to stub:
  - `**/api/upload-chatgpt-export` to return JSON indicating queued (e.g. `{ ok: true, jobId: 'job_1', status: 'queued' }`).
  - The “pending import scan” call(s) that run on startup (route-match by URL once identified in the repo; prefer the minimal set that makes the UI show the queued job).
  - The “job status” call(s) so the test can deterministically flip from `processing` to `complete` on reload.

### Assertions
- Assert the canonical `POST /api/upload-chatgpt-export` request happened (method + URL match).
- Assert that a refresh/resume occurred on reload by observing at least one startup scan request OR job status request.
- Assert the UI shows a *non-blocking* notification on completion (toast/banner). If there is no stable selector, prefer an accessible role-based selector (`role=status`, `role=alert`) over exact text.

### Selector strategy
Use stable, accessibility-based selectors and add a “mount gate”:
- Click global `Settings` first.
- Wait for a Settings/Data surface anchor (e.g. heading or text like `ChatGPT Migration`) before clicking the `Data` tab/button.
- Prefer regex accessible names when the exact label can vary.

If selectors remain flaky due to ambiguous roles/names, propose adding **minimal** `data-testid` attributes *only* to the Settings/Data/Migration controls. If adding test IDs is required, document the exact IDs and files needed and keep the change minimal.

## Allowed Files
- `frontend/src/tests/playwright/migration_e2e_import.spec.ts` (new or modify)
- `playwright.config.ts` (only if needed)
- `docs/tasks/TASK_2026_01_20_008_migration_e2e_test.md`

If (and only if) deterministic selectors cannot be achieved with role/label anchors, request a campaign constraint update to allow minimal `data-testid` additions for:
- Settings nav button
- Data tab/button
- Migration import panel
- Upload button
- Toast/banner container

## Checks to Run
- `pnpm --dir frontend/src test`
- `pnpm --dir frontend/src lint`
- `pnpm --dir frontend/src exec playwright test migration_e2e_import.spec.ts`

## Commit Mode
Two-phase commits:
1) Commit the task artifact / spec alignment first.
2) Commit the Playwright E2E implementation second.

## Commit Messages
1) `docs(tasks): specify async-deterministic migration E2E requirements`
2) `test(playwright): make migration E2E deterministic with stubs + async assertions`

## Expected Output
- Confirmation of code changes.
- Passing tests / checks summary (or explicit note if none apply).
- Git commit hash(es).

## Summary
- Updated `frontend/src/tests/playwright/migration_e2e_import.spec.ts` to gate the upload while asserting processing state, treat `/api/events` as the resume scan and `/api/chat/threads` as the status poll after reload, and emit a toast on completion.
- Tests:
  - `pnpm --dir frontend/src test` (pass; baseline-browser-mapping warning)
  - `pnpm --dir frontend/src lint` (warnings only)
  - `pnpm --dir frontend/src exec playwright test migration_e2e_import.spec.ts` (pass)
- `git status --porcelain`: clean after commits (Playwright artifacts restored to HEAD).
- Commit mode: follow-up fix after prior two-phase.
- Commit hashes:
  - spec: e6e76956
  - implementation: 0bede14d
  - follow-up fix: 519b128e
