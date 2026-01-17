# TASK-2026-01-17-001 — Sidebar Toggle Single Source

## Task Prompt

Codexify Task Prompt

TASK-ID: TASK-2026-01-17-001_SIDEBAR_TOGGLE_SINGLE_SOURCE

Context

You are operating on the local Codexify repo. The Guardian Chat sidebar currently has two competing toggle controls:
	•	A Chevron on the Guardian Chat surface (desired single control)
	•	A Hamburger inside the Sidebar (undesired; it can dismiss the sidebar but leaves no way to bring it back)

We want to simplify UX: remove the Sidebar hamburger toggle pathway and make the Chevron the single source of truth for dismissing/invoking the sidebar. Also fix the mismatch where GuardianChat receives isSidebarVisible instead of the actual computed open state (desktop vs mobile).

Instructions
	1.	Perform the described edit only in the specified allowed file.
	2.	Run checks/tests listed below.
	3.	Commit using the two-phase commit workflow per docs/Ops/Runner_Protocol.md:
	•	Commit A (Implementation)
	•	Commit B (Docs finalize) updating the task artifact with both hashes.
	4.	Output:
	•	Summary (what changed, files touched)
	•	Checks/tests run and results
	•	git status --porcelain confirmation
	•	Both commit hashes (impl + finalize)

⸻

🧩 Task Description

Goal

Make the Guardian Chat chevron the only sidebar toggle, and remove the Sidebar hamburger toggle pathway by removing the collapse handler wiring into SidebarRoot.

Required Changes (Implementation)

In frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx:
	1.	Stop passing collapse props into SidebarRoot
	•	Remove onToggleCollapse={toggleSidebar}
	•	Remove collapsed={!isSidebarOpen}
	This should prevent SidebarRoot from rendering its internal hamburger toggle (if it’s gated on these props), and ensures sidebar visibility can’t be lost permanently via sidebar-only controls.
	2.	Wire the chevron correctly across desktop + mobile
	•	Ensure GuardianChat receives the actual sidebar open state:
	•	Change isSidebarVisible={isSidebarVisible} to isSidebarVisible={isSidebarOpen}
	•	Keep onSidebarToggle={toggleSidebar} unchanged (Chevron triggers this)

Acceptance Criteria
	•	✅ Sidebar hamburger toggle no longer dismisses sidebar (or no longer exists if it was conditional on collapse props)
	•	✅ Chevron on Guardian Chat dismisses sidebar
	•	✅ Chevron can bring the sidebar back
	•	✅ Works on both:
	•	Desktop layout (sidebar visibility persisted via cfy.sidebarVisible)
	•	Mobile layout (sidebar open state via isMobileSidebarOpen)
	•	✅ No other files modified

⸻

Allowed Files (only)
	•	frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx

⸻

Checks / Tests to Run

Run:

pnpm --dir frontend/src test
pnpm --dir frontend/src lint
git status --porcelain

⸻

Git Steps (Two-phase)

Commit A — Implementation

git add frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
git commit -m "TASK-2026-01-17-001: unify sidebar toggle on chat chevron"

Task Artifact

Create/update:
	•	docs/tasks/TASK_2026_01_17_001_sidebar_toggle_single_source.md

Include:
	•	Task Prompt (this prompt)
	•	Summary (changes, tests, git status)
	•	Commit mode: two-phase
	•	Implementation hash: <hash A>
	•	Finalize-artifact hash: <hash B>

Commit B — Finalize Artifact

git add docs/tasks/TASK_2026_01_17_001_sidebar_toggle_single_source.md
git commit -m "docs(task): finalize TASK-2026-01-17-001 summary"

⸻

✅ Expected Output
	•	Sidebar toggle behavior is unified under the chat chevron
	•	Hamburger toggle pathway is removed/disabled
	•	Tests/lint pass
	•	Working tree clean
	•	Task artifact records both commit hashes

## Summary

- Changes: Removed SidebarRoot collapse wiring and passed computed sidebar open state to GuardianChat.
- Files: frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx.
- Tests: pnpm --dir frontend/src test (pass); pnpm --dir frontend/src lint (warnings only, no errors).
- git status --porcelain: M docker-compose.yml.
- Commit mode: two-phase.
- Implementation hash: bf006a92125d4bba5412aa363a678668605d1660.
- Finalize-artifact hash: TBD (recorded in campaign mapping / final output).
