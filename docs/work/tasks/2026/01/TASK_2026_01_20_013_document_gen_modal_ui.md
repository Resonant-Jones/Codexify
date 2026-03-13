# TASK-2026-01-20-013_DOCUMENT_GEN_MODAL_UI: Document Generation Modal UI

## Task Prompt

### Context
Active campaign: CAMPAIGN-2026-01-20-004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-20-013_DOCUMENT_GEN_MODAL_UI.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Prefer deterministic tests and minimal scope.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages.

### Task Description
Create DocumentGenModal and the UI trigger to open it. Implement only frontend UI for opening/closing the modal and capturing user inputs. Do not implement backend calls in this task. Modal must be accessible (keyboard dismiss, focus trap if the existing modal system supports it). UI should be non-blocking and minimal.

### Expected Output
- A DocumentGenModal can be opened from the UI and dismissed.
- The modal captures user inputs and returns them to caller state (no backend invocation).
- Task artifact recorded with prompt verbatim, commands + results, clean git status, and hashes.

## Allowed Files
- frontend/src/components/DocumentGenModal.tsx
- frontend/src/components/AppShell.tsx
- frontend/src/components/SidebarRoot.tsx
- frontend/src/App.tsx
- frontend/src/tests/document_gen_modal.spec.tsx
- docs/work/tasks/2026/01/TASK_2026_01_20_013_document_gen_modal_ui.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md

## Checks to Run
- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint

## Commit Mode
- Two-phase (implementation commit + finalize task artifact commit)

## Commit Messages
- Commit A (implementation): TASK-2026-01-20-013_DOCUMENT_GEN_MODAL_UI: add modal shell + open trigger
- Commit B (finalize artifact): TASK-2026-01-20-013_DOCUMENT_GEN_MODAL_UI: finalize task summary

## Summary
TBD
