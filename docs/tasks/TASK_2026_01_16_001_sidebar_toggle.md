# TASK-2026-01-16-001 — Sidebar dismiss chevron truly collapses sidebar

## Task Prompt
- **Context:** Guardian chat sidebar polish campaign; ensure the sidebar toggle controls the parent layout collapse state.
- **Instructions:** Edit only `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`. Run `pnpm test`. Use two-phase commits and record both commit hashes in the Summary.
- **Task Description:** Ensure the internal sidebar toggle callback is bound to the parent layout’s collapse state so clicking the dismiss/chevron/hamburger collapses the sidebar container.
- **Expected Output:** Sidebar toggle collapses/expands the entire sidebar, `pnpm test` passes, and the task artifact records both commit hashes with a clean `git status --porcelain`.

## Summary
- Changed files: `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` (binds sidebar toggle to parent open state).
- Commands: `pnpm test` (pass); `git status --porcelain` (clean).
- Commit mode: two-phase
- Implementation hash: `df984427e95823d27301ba6bc0dd1fe443797ae9`
- Finalize-artifact hash: (this commit; see git log / final mapping)
