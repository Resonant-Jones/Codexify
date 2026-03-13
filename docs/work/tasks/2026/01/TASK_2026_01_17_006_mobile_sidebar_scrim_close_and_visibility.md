# TASK-2026-01-17-006_MOBILE_SIDEBAR_SCRIM_CLOSE_AND_VISIBILITY

## Task Prompt
Codexify Task Prompt

TASK-ID
TASK-2026-01-17-006_MOBILE_SIDEBAR_SCRIM_CLOSE_AND_VISIBILITY

Context
You’re operating on the local Codexify repo.

Mobile sidebar drawer behavior is unreliable:
- Sometimes the app enters “sidebar open” state (chat dims / disabled) but the drawer/scrim is not visibly present.
- Clicking/tapping outside does not reliably close the sidebar.

We want maximum-reliability mobile drawer behavior:
- Drawer is visibly rendered above chat
- Scrim covers the viewport, intercepts all interaction, and closes the drawer
- Chat is fully inert and does not scroll behind overlay
- Desktop layout remains unchanged

Objective
Make the mobile sidebar drawer + scrim reliable and interactive:
- Ensure the drawer always appears above chat on mobile when opened
- Ensure the scrim captures input and closes the drawer
- Prevent background scroll while mobile drawer is open

Requirements
- Desktop behavior unchanged.
- Mobile only:
  - Drawer must be visible above chat (no “state open but drawer invisible”)
  - Scrim must render and intercept pointer/tap
  - Tapping scrim closes the drawer: setSidebarOpen(false)
  - No click-through to chat while drawer is open
  - Prevent background scrolling while drawer is open (body scroll lock)
  - Drawer interaction must NOT close the drawer (stop propagation)
  - Optional reliability: ESC closes drawer (safe + accessible)
- Do not refactor unrelated logic.

Runner Protocol / Commit Paradox Rule
Follow Runner_Protocol.md two-phase commit pattern (impl + finalize docs).
IMPORTANT: Do NOT use git commit --amend.
Because a commit cannot contain its own hash, the artifact may use:
  Finalize-artifact hash: (reported in final mapping)
and the final response MUST include both hashes in the mapping.

Files allowed to edit (only)
- frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
- docs/work/tasks/2026/01/TASK_2026_01_17_006_mobile_sidebar_scrim_close_and_visibility.md

Implementation Notes

0) Baseline check (required)
- Confirm whether the mobile overlay is currently rendered via createPortal(..., document.body).
- If NOT, refactor ONLY the mobile overlay block to render via createPortal(document.body), to avoid clipping/stacking-context issues caused by parent containers (overflow-hidden, transforms, blur layers, etc.).

1) Portal overlay structure (mobile only, when isSidebarOpen && !isDesktopLayout)
- Render via createPortal into document.body:
  - Overlay root: <div data-testid="mobile-sidebar-overlay" className="fixed inset-0" style={{ zIndex: 10000 }} />
  - Scrim: <div data-testid="mobile-sidebar-scrim" className="fixed inset-0" style={{ background: "rgba(0,0,0,0.45)" }} />
    - Must close on BOTH onPointerDown and onClick: setSidebarOpen(false)
    - Must have role="button" and tabIndex={0}
    - Add onKeyDown: if key === "Escape" then close (optional but recommended)
  - Drawer: <aside data-testid="mobile-sidebar-drawer" className="fixed top-0 left-0 h-full overflow-hidden" style={{ zIndex: 10001, width: "min(360px, 80vw)" }} />
    - Must stop propagation onPointerDown and onClick to prevent accidental close

2) Body scroll lock (mobile only)
- When mobile drawer opens: document.body.style.overflow = "hidden"
- On close/unmount: restore previous overflow value
- Only apply this for !isDesktopLayout && isSidebarOpen

3) Stacking contract
- Use explicit inline zIndex numbers:
  - overlay root: 10000
  - scrim: 10000
  - drawer: 10001
- Do NOT rely solely on Tailwind z-classes.

4) Keep existing desktop/mobile state logic intact
- Desktop persistence via localStorage remains
- Mobile uses isMobileSidebarOpen (no persistence required)

Checks to run
- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint

Git steps (two-phase)

Commit A (implementation)
1) git status --porcelain (must show only expected changes)
2) pnpm --dir frontend/src test (must pass)
3) pnpm --dir frontend/src lint (warnings ok, errors not ok)
4) git add frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
5) git commit -m "TASK-2026-01-17-006_MOBILE_SIDEBAR_SCRIM_CLOSE_AND_VISIBILITY: fix mobile drawer scrim close + visibility"

Commit B (finalize task artifact)
1) Create/update: docs/work/tasks/2026/01/TASK_2026_01_17_006_mobile_sidebar_scrim_close_and_visibility.md with:
   - Task Prompt (copy this prompt in)
   - Summary:
     - Changed files
     - Commands run + pass/fail
     - git status confirmation
     - Commit mode: two-phase (NO amend)
     - Implementation hash: <hash A>
     - Finalize-artifact hash: (reported in final mapping)
2) git add docs/work/tasks/2026/01/TASK_2026_01_17_006_mobile_sidebar_scrim_close_and_visibility.md
3) git commit -m "TASK-2026-01-17-006_MOBILE_SIDEBAR_SCRIM_CLOSE_AND_VISIBILITY: finalize task summary"

Output required
After finishing, output:
- Summary of changes
- Commands run + pass/fail
- git status --porcelain (must be empty)
- Mapping:
  TASK-2026-01-17-006_MOBILE_SIDEBAR_SCRIM_CLOSE_AND_VISIBILITY -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria
✅ Mobile drawer is always visible above chat when opened
✅ Scrim appears, intercepts taps, and closes drawer on tap
✅ Chat does not receive clicks/scroll while drawer is open
✅ Background scroll is locked while drawer is open
✅ Desktop behavior unchanged
✅ Tests pass; lint has no errors; working tree clean

## Summary
- Changed files: `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` (portal-based mobile overlay, scrim close handling, body scroll lock, ESC close)
- Commands run (pass): `pnpm --dir frontend/src test`, `pnpm --dir frontend/src lint` (warnings only)
- git status --porcelain: clean after implementation commit; only task artifact modified during finalize
- Commit mode: two-phase (no amend)
- Implementation hash: 33c2b2ec8f2af40e9724516d1678737ac7536766
- Finalize-artifact hash: reported in final mapping
