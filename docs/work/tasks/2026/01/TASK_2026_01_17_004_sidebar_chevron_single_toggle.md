# TASK-2026-01-17-004 — Sidebar Chevron Single Toggle

## Task Prompt

Codexify Task Prompt

TASK-ID
TASK-2026-01-17-004_SIDEBAR_CHEVRON_SINGLE_TOGGLE

Context
You’re operating on the local Codexify repo.

Guardian Chat currently has two competing sidebar controls:
- A chevron toggle on the chat surface (intended to dismiss/invoke the sidebar)
- A hamburger (Menu icon) toggle inside the sidebar header itself

This creates a broken UX: once the sidebar is dismissed via the sidebar’s hamburger, there’s no reliable way to bring it back. We want one source of truth: the chat chevron controls sidebar open/closed state. The sidebar should not have its own collapse toggle.

Objective
Remove the sidebar header hamburger collapse toggle and wire sidebar open/close behavior exclusively to the Guardian Chat chevron toggle.

Requirements
- Remove only the sidebar HEADER hamburger/collapse button in SidebarRoot (do NOT remove per-thread action menus like rename/archive/delete).
- Sidebar open/close must be controlled only by the chevron on the chat surface.
- When sidebar is closed, the chevron must still be visible and able to re-open it.
- Keep existing desktop/mobile behavior intact (desktop persistence via localStorage is fine).
- Do not change routing, thread selection behavior, project selection behavior, SSE/event behavior, or message rendering.
- Follow Runner_Protocol.md two-phase commit pattern:
  - Commit A: implementation
  - Commit B: finalize docs artifact
- Include TASK-ID in both commit messages.
- Record both commit hashes in the task artifact.

Files allowed to edit (only)
- frontend/src/components/sidebar/SidebarRoot.tsx
- frontend/src/features/chat/GuardianChat.tsx
- frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
- docs/work/tasks/2026/01/TASK_2026_01_17_004_sidebar_chevron_single_toggle.md

Implementation Notes
1) SidebarRoot.tsx
- Remove the sidebar HEADER collapse hamburger button and its related collapse plumbing.
- SidebarRoot must not own or manage sidebar open/close state after this change.
- Remove `Menu` import from lucide-react if unused after change.

2) GuardianChatWithSidebar.tsx
- Sidebar open state remains computed/owned here (single source of truth).
- Pass `isSidebarOpen` + `onToggleSidebar` (or equivalent) down to GuardianChat.
- Do not pass collapse toggles into SidebarRoot.

3) GuardianChat.tsx
- Ensure the chevron button:
  - Exists in an always-visible chat header region
  - Calls `onToggleSidebar`
  - Reflects open/closed state visually (ChevronLeft/ChevronRight or similar)

Checks to run
- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint (warnings ok, errors not ok)

Git steps (two-phase)

Commit A (implementation)
1) git status --porcelain (must show only expected changes)
2) pnpm --dir frontend/src test (must pass)
3) pnpm --dir frontend/src lint
4) git add \
   frontend/src/components/sidebar/SidebarRoot.tsx \
   frontend/src/features/chat/GuardianChat.tsx \
   frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
5) git commit -m "TASK-2026-01-17-004_SIDEBAR_CHEVRON_SINGLE_TOGGLE: make chevron the only sidebar toggle"

Commit B (finalize task artifact)
1) Create/update docs/work/tasks/2026/01/TASK_2026_01_17_004_sidebar_chevron_single_toggle.md with:
   - Task Prompt (copy this prompt)
   - Summary (files changed, commands run + pass/fail, git status)
   - Commit mode: two-phase
   - Implementation hash: <hash A>
   - Finalize-artifact hash: <hash B>
2) git add docs/work/tasks/2026/01/TASK_2026_01_17_004_sidebar_chevron_single_toggle.md
3) git commit -m "TASK-2026-01-17-004_SIDEBAR_CHEVRON_SINGLE_TOGGLE: finalize task summary"

Output required
- Summary of changes
- Commands run + pass/fail
- git status --porcelain must be empty
- Mapping:
  TASK-2026-01-17-004_SIDEBAR_CHEVRON_SINGLE_TOGGLE -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria
✅ Sidebar header hamburger/collapse control is removed  
✅ Chat chevron toggles sidebar closed/open reliably  
✅ Sidebar can always be reopened after being closed  
✅ Tests pass and working tree is clean after finalize commit

## Summary

- Files changed: frontend/src/components/sidebar/SidebarRoot.tsx, frontend/src/features/chat/GuardianChat.tsx
- Commands run: pnpm --dir frontend/src test (pass); pnpm --dir frontend/src lint (warnings only, no errors)
- git status --porcelain: clean
- Commit mode: two-phase
- Implementation hash: d4551779609c80ff6d3bc407c40801318e54b2a6
- Finalize-artifact hash: TBD (reported in final mapping / derived via git log --grep TASK-ID)
