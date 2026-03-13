# TASK-2026-01-16-005 — Fix “Create Project” modal (visible + functional submit)

## Task Prompt
- **Context:** Guardian chat sidebar polish campaign; fix Create Project modal visibility and submission flow.
- **Instructions:** Edit only `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/CreateProjectModal.tsx`, and `frontend/src/components/sidebar/useProjectsCache.ts`. Run `pnpm test`. Use two-phase commits and record both commit hashes in the Summary.
- **Task Description:** Fix the “Add Project” flow in Guardian Chat: ensure modal visibility (z-index/overlay, non-transparent surface), validate input, POST to the backend create endpoint, close + refresh on success, and surface errors on failure.
- **Expected Output:** Modal is visible, Save/Enter creates a project and updates UI, errors are shown, `pnpm test` passes, and the task artifact records both commit hashes with a clean `git status --porcelain`.

## Summary
- Changed files: `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/CreateProjectModal.tsx` (modal surface + error display; submit flow handles validation, errors, and refresh).
- Commands: `pnpm test` (timeout, then pass); `git status --porcelain` (clean).
- Commit mode: two-phase
- Implementation hash: `bdf3af558872e033a921dcbc38a1593a31ff4b8d`
- Finalize-artifact hash: (this commit; see git log / final mapping)
