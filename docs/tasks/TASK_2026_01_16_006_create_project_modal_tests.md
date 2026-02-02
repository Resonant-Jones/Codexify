# TASK-2026-01-16-006 — Add regression tests for Create Project modal flow

## Task Prompt
- **Context:** Guardian chat sidebar polish campaign; add regression tests for the Create Project modal flow.
- **Instructions:** Edit only frontend test files (and related components if needed). Run `pnpm test`. Use two-phase commits and record both commit hashes in the Summary.
- **Task Description:** Add tests that verify modal visibility, submit triggers create call, success closes + refreshes, and failure shows an error.
- **Expected Output:** Tests cover modal visibility and submit outcomes, `pnpm test` passes, and the task artifact records both commit hashes with a clean `git status --porcelain`.

## Summary
- Changed files: `frontend/src/components/sidebar/__tests__/CreateProjectModal.test.tsx` (new tests for modal visibility, success path, and error handling).
- Commands: `pnpm test` (fail, then pass); `git status --porcelain` (clean).
- Commit mode: two-phase
- Implementation hash: `0b50a1d4468fc16bb997689a3b76688a0db277a3`
- Finalize-artifact hash: (this commit; see git log / final mapping)
