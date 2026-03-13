# TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING: Wire DocumentGenModal submit to backend + add UI entry point

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Close the document generation loop by ensuring a visible UI entry point exists and DocumentGenModal submits to POST /api/documents/generate, with a visible outcome in the UI.

### Expected Output
- A button opens DocumentGenModal.
- Submitting the modal triggers POST /api/documents/generate.
- UI does something observable with the returned content.

## Allowed Files
- frontend/src/**/*.tsx
- frontend/src/**/*.ts
- frontend/src/tests/**/*
- docs/work/tasks/2026/01/TASK_2026_01_23_007_document_gen_ui_wiring.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "DocumentGenModal|DocumentsView|/api/documents/generate" frontend/src
- pnpm --dir frontend/src test || true
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING: wire document gen modal to endpoint
- Commit B: TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING: finalize task summary

## Summary
- Added a Documents header action to trigger document generation via a shared event.
- Wired App to open DocumentGenModal on the event, reusing the existing `/api/documents/generate` submit flow.
- Added a focused unit test to verify the event dispatch from DocumentsView.

## Checks Run
- `rg -n "DocumentGenModal|DocumentsView|/api/documents/generate" frontend/src`
- `pnpm --dir frontend/src test || true` (pass; warnings from existing tests about act() and WebSocket errors)
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows task artifact + campaign mapping pending record finalize hash commit.

## Commits
- Commit A (implementation): `7d9b52ae`
- Commit B (finalize docs): `bc52c143`

## Mapping
- TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING -> [7d9b52ae, bc52c143]
