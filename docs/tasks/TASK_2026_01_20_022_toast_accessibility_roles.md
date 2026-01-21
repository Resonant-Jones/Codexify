# TASK-2026-01-20-022_TOAST_ACCESSIBILITY_ROLES

## Context
You’re operating on the local Codexify repo.

We want the desktop toast/notification region to be:
- Accessible (proper ARIA live region semantics).
- Reliably selectable for E2E assertions (avoid brittle string matching).

This task supports the ChatGPT migration E2E, which currently asserts completion via a toast signal.

Campaign: `CAMPAIGN-2026-01-20-002_MVP_LOOP_CLOSURE_CHATGPT_MIGRATION`
Source-of-truth campaign file: `docs/Campaign/CAMPAIGN_2026_01_20.md`

## Instructions
1. Perform the described edit only in the specified files.
2. Run the appropriate test suite based on what was modified:
   - Frontend-only changes:
     - Run:
       - `pnpm --dir frontend/src test`
       - `pnpm --dir frontend/src lint` (warnings ok; errors not ok)
       - `pnpm --dir frontend/src exec playwright test migration_e2e_import.spec.ts`
3. If tests pass (or the relevant checks succeed):
   - Stage the modified files with `git add`.
   - Commit with the message(s) provided below.
4. Output:
   - A summary of what was changed (files + components).
   - Any new test results or warnings.
   - The git commit hash(es).

## Task Description
Implement toast accessibility semantics and update the ChatGPT migration Playwright E2E to assert toast completion via accessibility role.

### Requirements
#### A) Toast accessibility semantics (semantics only)
Update the toast container so it exposes a stable live region:
- Add `role="status"`
- Add `aria-live="polite"`
- Add `aria-atomic="true"`

Important:
- Semantics only — do not change toast behavior (timing, animations, layout, styling).
- Apply these attributes to the element that is actually mounted/visible when a toast is displayed.

Optional (only if trivial with existing structure):
- If there is an obvious error toast variant, error notifications may use:
  - `role="alert"`
  - `aria-live="assertive"`
If this is not trivial, skip variant branching and implement only the baseline `status/polite` live region.

#### B) Update migration E2E assertion
Update `frontend/src/tests/playwright/migration_e2e_import.spec.ts` to assert the completion notification using a role-based selector:
- Prefer `page.getByRole('status')` (or `getByRole('alert')` if testing an error case).
- Avoid relying on exact toast text.
- Keep the existing async queue/resume determinism (network stubs) intact.

## Allowed Files
- `frontend/src/imprint/ImprintZeroToast.tsx`
- `frontend/src/tests/playwright/migration_e2e_import.spec.ts`
- `docs/tasks/TASK_2026_01_20_022_toast_accessibility_roles.md`
- `docs/Campaign/CAMPAIGN_2026_01_20.md`

## Checks to Run (required)
- `pnpm --dir frontend/src test`
- `pnpm --dir frontend/src lint`
- `pnpm --dir frontend/src exec playwright test migration_e2e_import.spec.ts`

## Commit Mode
Two-phase commits:
1) Commit A: implementation (UI semantics + E2E assertion update).
2) Commit B: finalize task artifact summary (commands + results + hashes).

## Commit Messages
- Commit A (implementation): `TASK-2026-01-20-022_TOAST_ACCESSIBILITY_ROLES: add toast accessibility role`
- Commit B (finalize artifact): `TASK-2026-01-20-022_TOAST_ACCESSIBILITY_ROLES: finalize task summary`

## Expected Output
- Toast container is a proper ARIA live region.
- Migration E2E uses role-based toast assertion and remains deterministic.
- Task artifact includes the prompt verbatim, commands run + results, clean `git status`, and commit hash mapping.
