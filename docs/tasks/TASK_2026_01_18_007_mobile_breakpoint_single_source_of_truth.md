# TASK-2026-01-18-007_MOBILE_BREAKPOINT_SINGLE_SOURCE_OF_TRUTH

## Task Prompt
Codexify Task Prompt

TASK-ID
TASK-2026-01-18-007_MOBILE_BREAKPOINT_SINGLE_SOURCE_OF_TRUTH

Context

You’re operating on the local Codexify repo.

We have a recurring mobile sidebar bug where the chat “dims” as if the sidebar is open, but the mobile drawer/scrim sometimes does not render, and DOM queries like:
	•	document.querySelector('[data-testid="mobile-sidebar-overlay"]')

return null.

This strongly suggests a breakpoint mismatch: Tailwind/CSS is using lg (min-width: 1024px), but the React logic that computes isDesktopLayout may be using a different signal (e.g. a hook that doesn’t match CSS, hydration timing, or inconsistent breakpoint mapping). When isDesktopLayout is wrong, the mobile portal overlay never mounts.

Objective

Make desktop/mobile detection maximally reliable by using one source of truth that matches Tailwind’s lg breakpoint:
	•	Desktop if: window.matchMedia("(min-width: 1024px)").matches === true
	•	Mobile if: false

This should make the mobile overlay mount reliably whenever the sidebar is opened on mobile.

Requirements
	•	Replace breakpoint logic so isDesktopLayout is determined exclusively by:
	•	window.matchMedia("(min-width: 1024px)")
	•	subscribed to "change" events (with Safari fallback addListener/removeListener)
	•	Ensure the existing mobile overlay logic still uses the same isMobileOverlayActive conditions and continues to mount via portal when:
	•	!isDesktopLayout && isSidebarOpen
	•	Desktop behavior unchanged.
	•	Do not refactor unrelated UI logic.
	•	Follow Runner_Protocol.md two-phase commit pattern (impl + finalize docs).
	•	Do NOT use git commit --amend (commit hash paradox rule).
	•	Task artifact may include: Finalize-artifact hash: (reported in final mapping)

Files allowed to edit (only)
	•	frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
	•	docs/tasks/TASK_2026_01_18_007_mobile_breakpoint_single_source_of_truth.md

Implementation Notes

In GuardianChatWithSidebar.tsx:
	1.	Remove/stop using any desktop detection that is not guaranteed to match Tailwind lg (e.g. useBreakpoint() or derived bp strings).
	2.	Implement:

	•	const [isDesktopLayout, setIsDesktopLayout] = useState(() => matchMedia("(min-width: 1024px)").matches) (guard for SSR)
	•	useEffect that:
	•	creates mq = window.matchMedia("(min-width: 1024px)")
	•	updates state initially and on change
	•	uses mq.addEventListener("change", ...) when available
	•	falls back to mq.addListener(...) for older Safari

	3.	Ensure the mobile overlay portal condition remains:

	•	const isSidebarOpen = isDesktopLayout ? isSidebarVisible : isMobileSidebarOpen;
	•	const isMobileOverlayActive = !isDesktopLayout && isSidebarOpen;

	4.	No console spam. If debugging is needed, use minimal data attributes already in place.

Checks to run

Run:
	•	pnpm --dir frontend/src test
	•	pnpm --dir frontend/src lint

Git steps (two-phase)

Commit A (implementation)
	1.	git status --porcelain (must show only expected changes)
	2.	pnpm --dir frontend/src test (must pass)
	3.	pnpm --dir frontend/src lint (warnings ok, errors not ok)
	4.	git add frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
	5.	git commit -m "TASK-2026-01-18-007_MOBILE_BREAKPOINT_SINGLE_SOURCE_OF_TRUTH: matchMedia-based desktop detection"

Commit B (finalize task artifact)
	1.	Create/update: docs/tasks/TASK_2026_01_18_007_mobile_breakpoint_single_source_of_truth.md with:
	•	Task Prompt (copy this prompt in)
	•	Summary:
	•	Changed files
	•	Commands run + pass/fail
	•	git status --porcelain confirmation
	•	Commit mode: two-phase (NO amend)
	•	Implementation hash: <hash A>
	•	Finalize-artifact hash: (reported in final mapping)
	2.	git add docs/tasks/TASK_2026_01_18_007_mobile_breakpoint_single_source_of_truth.md
	3.	git commit -m "TASK-2026-01-18-007_MOBILE_BREAKPOINT_SINGLE_SOURCE_OF_TRUTH: finalize task summary"

Output required

After finishing, output:
	•	Summary of changes
	•	Commands run + pass/fail
	•	git status --porcelain (must be empty)
	•	Mapping:
TASK-2026-01-18-007_MOBILE_BREAKPOINT_SINGLE_SOURCE_OF_TRUTH -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria

✅ window.matchMedia("(min-width: 1024px)").matches is the sole determinant for isDesktopLayout
✅ On mobile widths (<1024), opening sidebar mounts the portal elements reliably:
	•	[data-testid="mobile-sidebar-overlay"] exists
	•	[data-testid="mobile-sidebar-scrim"] exists
	•	[data-testid="mobile-sidebar-drawer"] exists
✅ Desktop layout unaffected
✅ Tests pass; lint has no errors; working tree clean

## Summary
- Changed files: `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` (matchMedia-based desktop detection)
- Commands run (pass): `pnpm --dir frontend/src test`, `pnpm --dir frontend/src lint` (warnings only)
- git status --porcelain: clean after implementation commit; only task artifact modified during finalize
- Commit mode: two-phase (no amend)
- Implementation hash: a6bd21d06c392fe0efe8be026a3a92621cf1af1e
- Finalize-artifact hash: reported in final mapping
