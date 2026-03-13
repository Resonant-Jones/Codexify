# TASK-2026-01-19-010_SIDEBAR_PROJECT_CONTEXT_PERSIST_ON_THREAD_SELECT

## Task Prompt
Codexify Task Prompt

TASK-ID
TASK-2026-01-19-010_SIDEBAR_PROJECT_CONTEXT_PERSIST_ON_THREAD_SELECT

Context
You’re operating on the local Codexify repo.

In the sidebar selection workflow, selecting a Project and then selecting a Thread currently boots the user out of context: the UI returns to an empty Threads view with no project selected. This makes switching threads painful and defeats the Project→Thread UX.

We want the selection state to persist:
- If the user is browsing within a Project and selects a Thread, the Project context should remain selected.
- The sidebar should not “reset” to no-project / empty threads state.

Objective
Fix the sidebar state management so Project context persists when selecting a thread from within a project, and add a Playwright regression test covering the workflow (mobile viewport).

Requirements
- Preserve existing desktop behavior.
- On mobile and desktop:
  - Selecting Project → then Thread must NOT clear the selected project context.
  - The sidebar should remain in a consistent state after navigation (no “booted out”).
- Add a Playwright test that fails on the current buggy behavior and passes after the fix.
- Follow Runner_Protocol.md two-phase commit pattern:
  - Commit A: implementation (code + test)
  - Commit B: finalize docs artifact
- Include TASK-ID in BOTH commit messages.
- Record BOTH commit hashes in the task artifact.

Files allowed to edit (only)
- frontend/src/components/sidebar/SidebarRoot.tsx
- frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
- frontend/src/tests/playwright/sidebar_project_context_persist.spec.ts
- docs/work/tasks/2026/01/TASK_2026_01_19_010_sidebar_project_context_persist_on_thread_select.md

Implementation Notes
1) Bug Fix
- Identify where selected project state is stored (likely in SidebarRoot and/or derived from active thread).
- Ensure selecting a thread does NOT clear project selection state.
- If the UI needs both:
  - "selectedProjectId" (or similar)
  - "activeThreadId"
  then keep them independent so thread navigation doesn’t reset project selection.
- If SidebarRoot currently auto-switches tabs or resets state on activeId changes, adjust logic so it preserves the last user-intended context.

2) Playwright Test (regression)
Your Playwright config is at frontend/src/playwright.config.ts with testDir = ./tests/playwright.

Create:
- frontend/src/tests/playwright/sidebar_project_context_persist.spec.ts

Test requirements:
- Run in a mobile viewport via in-test override:
  - viewport around 390x844
- Steps:
  1) Navigate to baseURL (http://localhost:5173)
  2) Open sidebar (use chevron toggle)
  3) Switch to Projects tab
  4) Click a project that has at least one thread
  5) Click a thread inside that project
  6) Assert that after thread selection:
     - The project context still appears selected (project name visible/active)
     - The threads list is not “empty booted out”
- Use stable selectors if available (data-testid preferred).
- If there are no stable selectors, add minimal data-testid attributes in SidebarRoot ONLY where needed:
  - data-testid="sidebar-projects-tab"
  - data-testid="sidebar-threads-tab"
  - data-testid="sidebar-project-item"
  - data-testid="sidebar-thread-item"
  - data-testid="sidebar-selected-project"
(Keep changes minimal and scoped.)

Checks to run
Run:
- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint
- pnpm --dir frontend/src playwright test

Git steps (two-phase)

Commit A (implementation)
1) git status --porcelain (must show only expected changes)
2) pnpm --dir frontend/src test (must pass)
3) pnpm --dir frontend/src lint (warnings ok, errors not ok)
4) pnpm --dir frontend/src playwright test (must pass)
5) git add \
   frontend/src/components/sidebar/SidebarRoot.tsx \
   frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx \
   frontend/src/tests/playwright/sidebar_project_context_persist.spec.ts
6) git commit -m "TASK-2026-01-19-010_SIDEBAR_PROJECT_CONTEXT_PERSIST_ON_THREAD_SELECT: persist project context on thread select + add e2e"

Commit B (finalize task artifact)
1) Create/update: docs/work/tasks/2026/01/TASK_2026_01_19_010_sidebar_project_context_persist_on_thread_select.md with:
   - Task Prompt (copy this prompt in)
   - Summary:
     - Changed files
     - Commands run + pass/fail
     - git status confirmation
     - Commit mode: two-phase
     - Implementation hash: <hash A>
     - Finalize-artifact hash: <hash B>
2) git add docs/work/tasks/2026/01/TASK_2026_01_19_010_sidebar_project_context_persist_on_thread_select.md
3) git commit -m "TASK-2026-01-19-010_SIDEBAR_PROJECT_CONTEXT_PERSIST_ON_THREAD_SELECT: finalize task summary"

Output required
After finishing, output:
- Summary of changes
- Commands run + pass/fail
- git status --porcelain (must be empty)
- Mapping:
  TASK-2026-01-19-010_SIDEBAR_PROJECT_CONTEXT_PERSIST_ON_THREAD_SELECT -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria
✅ Selecting Project → Thread does not clear Project context  
✅ Sidebar remains usable (no boot-out to empty Threads view)  
✅ Playwright test covers the workflow at mobile viewport and passes  
✅ Tests pass; lint has no errors; working tree clean after finalize commit

## Summary
- Changed files: `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` (persist selected project in parent), `frontend/src/components/sidebar/SidebarRoot.tsx` (stable tab test IDs), `frontend/src/tests/playwright/sidebar_project_context_persist.spec.ts` (mobile regression test)
- Commands run: `pnpm --dir frontend/src test` (pass), `pnpm --dir frontend/src lint` (pass, warnings only), `pnpm --dir frontend/src playwright test` (fail: pnpm command not found), `pnpm --dir frontend/src exec playwright test` (fail: EPERM binding in sandbox), `pnpm --dir frontend/src exec playwright test` (fail: test timeout), `pnpm --dir frontend/src exec playwright test` (pass)
- git status --porcelain: clean after implementation commit; only task artifact modified during finalize
- Commit mode: two-phase
- Implementation hash: d2a3e7d7e6f2aea241f24c54d2cce416cfd5556e
- Finalize-artifact hash: reported in final mapping (commit hash cannot be embedded pre-commit)
