# TASK-2026-01-18-008_MOBILE_SIDEBAR_RENDER_SCRIM_AND_OUTSIDE_CLOSE

## Task Prompt
Codexify Task Prompt

TASK-ID
TASK-2026-01-18-008_MOBILE_SIDEBAR_RENDER_SCRIM_AND_OUTSIDE_CLOSE

Context
You’re operating on the local Codexify repo.

Mobile sidebar drawer is mounting (mobile-sidebar-drawer exists), but the overlay and scrim are missing in the DOM (mobile-sidebar-overlay and mobile-sidebar-scrim query as null). Therefore:
- “tap outside to close” cannot work
- scrim cannot intercept pointer events
- visual dimming may be coming from chat-disabled styling instead of a real overlay

Objective
Make mobile overlay fully real and reliable:
- Always render overlay wrapper + scrim whenever the mobile drawer is open
- Scrim must close the drawer on click/tap
- Prevent click-through to chat while open
- Keep desktop behavior unchanged

Requirements
- Desktop behavior unchanged.
- Mobile only (non-desktop layout):
  - When sidebar is open, render THREE elements via portal:
    1) overlay wrapper (data-testid="mobile-sidebar-overlay")
    2) scrim/backdrop (data-testid="mobile-sidebar-scrim")
    3) drawer container (data-testid="mobile-sidebar-drawer")
  - Scrim covers full viewport (fixed inset-0) and visibly dims background.
  - Scrim captures pointer events and closes drawer: setSidebarOpen(false)
  - Drawer stops propagation so clicks inside do not close it.
  - ESC closes the drawer.
  - Lock body scroll while open.
- No unrelated refactors.

Runner Protocol / Commit Paradox Rule
Follow Runner_Protocol.md two-phase commit pattern (impl + finalize docs).
Do NOT use git commit --amend.
Artifact may include:
  Finalize-artifact hash: (reported in final mapping)

Files allowed to edit (only)
- frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
- docs/tasks/TASK_2026_01_18_008_mobile_sidebar_render_scrim_and_outside_close.md

Implementation Notes (must-do)
In GuardianChatWithSidebar.tsx:
1) In the mobile portal block, ensure the portal returns a single wrapper that contains:
   - <div data-testid="mobile-sidebar-overlay" style={{ position:'fixed', inset:0, zIndex: 10000 }}>
   - Inside it:
     a) <div data-testid="mobile-sidebar-scrim" style={{ position:'absolute', inset:0, background:'rgba(0,0,0,0.45)' }} onClick={() => setSidebarOpen(false)} />
     b) <aside data-testid="mobile-sidebar-drawer" style={{ position:'absolute', top:0, left:0, height:'100%', width:'min(360px, 90vw)', zIndex: 10001 }} onClick={(e)=>e.stopPropagation()} />
2) Ensure overlay/scrim are rendered only when: isSidebarOpen && !isDesktopLayout
3) Ensure there is no path where the drawer renders without scrim.
4) Keep existing desktop grid layout untouched.

Checks to run
- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint

Git steps (two-phase)

Commit A (implementation)
1) git status --porcelain (must show only expected changes)
2) pnpm --dir frontend/src test (must pass)
3) pnpm --dir frontend/src lint (warnings ok, errors not ok)
4) git add frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
5) git commit -m "TASK-2026-01-18-008_MOBILE_SIDEBAR_RENDER_SCRIM_AND_OUTSIDE_CLOSE: render scrim + outside click close"

Commit B (finalize task artifact)
1) Create/update: docs/tasks/TASK_2026_01_18_008_mobile_sidebar_render_scrim_and_outside_close.md with:
   - Task Prompt (copy this prompt in)
   - Summary:
     - Changed files
     - Commands run + pass/fail
     - git status confirmation
     - Commit mode: two-phase (NO amend)
     - Implementation hash: <hash A>
     - Finalize-artifact hash: (reported in final mapping)
2) git add docs/tasks/TASK_2026_01_18_008_mobile_sidebar_render_scrim_and_outside_close.md
3) git commit -m "TASK-2026-01-18-008_MOBILE_SIDEBAR_RENDER_SCRIM_AND_OUTSIDE_CLOSE: finalize task summary"

Output required
After finishing, output:
- Summary of changes
- Commands run + pass/fail
- git status --porcelain (must be empty)
- Mapping:
  TASK-2026-01-18-008_MOBILE_SIDEBAR_RENDER_SCRIM_AND_OUTSIDE_CLOSE -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria
✅ In DevTools console, all three return non-null when sidebar open:
  - document.querySelector('[data-testid="mobile-sidebar-overlay"]')
  - document.querySelector('[data-testid="mobile-sidebar-scrim"]')
  - document.querySelector('[data-testid="mobile-sidebar-drawer"]')
✅ Clicking scrim closes drawer
✅ No click-through / chat inert while open
✅ Desktop unchanged
✅ Tests pass, lint no errors, tree clean

## Summary
- Changed files: `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` (portal wrapper now contains overlay + scrim + drawer in a single fixed container with absolute children)
- Commands run: `pnpm --dir frontend/src test` (first attempt timed out; second attempt passed), `pnpm --dir frontend/src lint` (pass, warnings only)
- git status --porcelain: clean after implementation commit; only task artifact modified during finalize
- Commit mode: two-phase (no amend)
- Implementation hash: 68324f1e804e9012cbc638c35569b8ad9cdbc550
- Finalize-artifact hash: reported in final mapping
