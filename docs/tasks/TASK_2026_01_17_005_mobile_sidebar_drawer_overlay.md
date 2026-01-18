# TASK-2026-01-17-005 — Mobile Sidebar Drawer Overlay

## Task Prompt

Codexify Task Prompt

TASK-ID
TASK-2026-01-17-005_MOBILE_SIDEBAR_DRAWER_OVERLAY

Context
You’re operating on the local Codexify repo.

Desktop sidebar behavior is correct (sidebar column beside chat). On mobile, opening the sidebar currently behaves like a full-page overlay/blanket. We want a standard mobile drawer pattern:

- Sidebar becomes a fixed left drawer with constrained width
- A scrim/backdrop covers the rest of the screen
- Clicking the scrim closes the drawer
- Chat becomes inert while the drawer is open
- The chat chevron remains the only toggle

Objective
Implement a polished mobile “drawer overlay” sidebar behavior (Option A) while preserving existing desktop behavior.

Requirements
- Desktop behavior unchanged (grid two-column layout stays as-is).
- Mobile behavior:
  - Sidebar renders as a fixed drawer anchored left (NOT full-width, NOT inset-0).
  - Drawer width is constrained: min(360px, 90vw).
  - Drawer occupies full height.
  - A scrim covers the rest of the viewport.
  - Clicking scrim closes the drawer.
  - Chat is non-interactive while drawer is open (no click/scroll).
- Layout rule must be explicit:
  - On mobile, the base layout remains a single-column chat grid (gridTemplateColumns: "1fr") even when the drawer is open.
- Keep existing state logic intact:
  - Desktop uses persistent localStorage preference (cfy.sidebarVisible).
  - Mobile uses isMobileSidebarOpen (no persistence required).
- Follow Runner_Protocol.md two-phase commit pattern (impl commit + finalize docs artifact).
- Include TASK-ID in BOTH commit messages.
- Record BOTH commit hashes in the task artifact.

Files allowed to edit (only)
- frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
- docs/tasks/TASK_2026_01_17_005_mobile_sidebar_drawer_overlay.md

Implementation Notes (GuardianChatWithSidebar.tsx)

1) Grid / base layout
- Desktop:
  - Keep existing two-column grid behavior when sidebar is open.
- Mobile:
  - Force the grid to remain "1fr" at all times (even when the drawer is open).
  - The mobile sidebar must NOT participate in grid flow.

2) Mobile drawer + scrim (render only when !isDesktopLayout && isSidebarOpen)
- Render a scrim element that blocks interaction:
  - class: fixed inset-0
  - z-index below the drawer, above the chat
  - onClick: toggleSidebar (close)
- Render the drawer container:
  - class: fixed top-0 left-0 h-full
  - width: w-[min(360px,90vw)]
  - z-index above the scrim
  - The drawer content should reuse the existing PanelShell + SidebarRoot composition.
  - Do NOT use absolute inset-0 w-full for the drawer container.

3) Prevent click-through / inert chat
- While the drawer is open on mobile:
  - The chat panel must not receive pointer events (existing PanelShell disabled pointerEvents is fine).
  - Scrim must capture clicks (no click-through to chat).

4) Cleanup
- Remove or replace any mobile sidebar wrapper logic that sets the sidebar to absolute inset-0 ... w-full.
- Keep changes narrowly scoped to mobile drawer behavior (no refactors unrelated to layout).

Checks to run
- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint

Git steps (two-phase)

Commit A (implementation)
1) git status --porcelain (must show only expected changes)
2) pnpm --dir frontend/src test (must pass)
3) pnpm --dir frontend/src lint (warnings ok, errors not ok)
4) git add frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
5) git commit -m "TASK-2026-01-17-005_MOBILE_SIDEBAR_DRAWER_OVERLAY: implement mobile sidebar drawer"

Commit B (finalize task artifact)
1) Create/update: docs/tasks/TASK_2026_01_17_005_mobile_sidebar_drawer_overlay.md with:
   - Task Prompt (copy this prompt in)
   - Summary:
     - Changed files
     - Commands run + pass/fail
     - git status confirmation
     - Commit mode: two-phase
     - Implementation hash: <hash A>
     - Finalize-artifact hash: <hash B>
2) git add docs/tasks/TASK_2026_01_17_005_mobile_sidebar_drawer_overlay.md
3) git commit -m "TASK-2026-01-17-005_MOBILE_SIDEBAR_DRAWER_OVERLAY: finalize task summary"

Output required
- Summary of changes
- Commands run + pass/fail
- git status --porcelain must be empty
- Mapping:
  TASK-2026-01-17-005_MOBILE_SIDEBAR_DRAWER_OVERLAY -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria
✅ Desktop unchanged  
✅ Mobile grid remains 1fr (chat is base layout)  
✅ Mobile sidebar is a constrained left drawer (not full-width)  
✅ Scrim closes drawer on click  
✅ Chat cannot be interacted with while drawer is open  
✅ Tests pass, lint has no errors, working tree clean after finalize commit

## Summary

- Changed files: frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
- Commands run: pnpm --dir frontend/src test (pass); pnpm --dir frontend/src lint (warnings only, no errors)
- git status --porcelain: clean
- Commit mode: two-phase
- Implementation hash: 9c7a038c35269d8becb9d0212a502caeed37bc3f
- Finalize-artifact hash: TBD (reported in final mapping / derived via git log --grep TASK-ID)
