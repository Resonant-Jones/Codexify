# TASK-2026-01-20-016_DOCUMENT_GEN_OPEN_IN_EDITOR: Open Generated Doc in Editor

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-016_DOCUMENT_GEN_OPEN_IN_EDITOR.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
After a successful generation request and persistence/linking, the UI must navigate/open the existing document editor view with the generated document loaded. Use the persisted document identifier returned by the generate endpoint to open the editor. Keep UI changes minimal and focused to wiring/navigation only. Do not introduce new editor UX. If the editor route/component lives outside the allowed files list, stop and report the exact path(s) required so the campaign can be updated.

### Expected Output
- After generation, the editor opens with the generated document content loaded.
- A focused UI test asserts navigation/open behavior deterministically.
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- frontend/src/components/DocumentGenModal.tsx
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/components/sidebar/SidebarRoot.tsx
- frontend/src/App.tsx
- frontend/src/tests/document_gen_open_in_editor.spec.tsx
- docs/tasks/TASK_2026_01_20_016_document_gen_open_in_editor.md
- docs/Campaign/CAMPAIGN_2026_01_20.md

## Checks to Run
- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): TASK-2026-01-20-016_DOCUMENT_GEN_OPEN_IN_EDITOR: open generated doc in editor
- Commit B (finalize artifact): TASK-2026-01-20-016_DOCUMENT_GEN_OPEN_IN_EDITOR: finalize task summary

## Summary
- Wired document generation to call `/documents/generate` and dispatch open/add events in `frontend/src/App.tsx`.
- Added a listener to open generated docs in the documents workspace in `frontend/src/components/persona/layout/AppShell.tsx`.
- Added a focused UI test for open-in-editor behavior in `frontend/src/tests/document_gen_open_in_editor.spec.tsx`.
- Tests:
  - `pnpm --dir frontend/src test`
  - `pnpm --dir frontend/src lint` (warnings only)
- Git status: `git status --porcelain` shows only allowed docs files pending finalize commit.
- Commit mode: two-phase.
- Implementation commit: `e2c7dd75`.
- Finalize commit: reported in campaign mapping.
- Campaign mapping requirement: `TASK-2026-01-20-016_DOCUMENT_GEN_OPEN_IN_EDITOR -> [e2c7dd75, <finalize_hash>]`.
