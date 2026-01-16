# TASK-2026-01-16-002 — Sidebar tab focus persists (Threads/Projects doesn’t flip)

## Task Prompt
- **Context:** Guardian chat sidebar polish campaign; keep last interacted tab unless the user explicitly switches tabs.
- **Instructions:** Edit only `frontend/src/components/sidebar/SidebarRoot.tsx`. Run `pnpm test`. Use two-phase commits and record both commit hashes in the Summary.
- **Task Description:** Prevent the sidebar from defaulting to Projects after selecting a thread. UX rule: keep last interacted tab, unless there’s a deliberate user click to switch.
- **Expected Output:** Tab focus persists, `pnpm test` passes, and the task artifact records both commit hashes with a clean `git status --porcelain`.

## Summary
- Changed files: `frontend/src/components/sidebar/SidebarRoot.tsx` (removed auto-switch to Threads on active thread changes).
- Commands: `pnpm test` (pass); `git status --porcelain` (clean).
- Commit mode: two-phase
- Implementation hash: `1e1707217c32bc7c22992c77920e8c73561eb564`
- Finalize-artifact hash: (this commit; see git log / final mapping)
