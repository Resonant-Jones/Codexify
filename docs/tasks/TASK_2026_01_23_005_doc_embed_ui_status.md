# TASK-2026-01-23-005_DOC_EMBED_UI_STATUS: Display document embedding status in UI

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-005_DOC_EMBED_UI_STATUS.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Expose embedding readiness to users:
- show status badge (Pending / Processing / Ready / Failed)
- optionally prevent use for retrieval until Ready (only if already implied by UX)

### Expected Output
- UI shows embedding status label/badge.
- No Playwright report/test-results artifacts are committed.

## Allowed Files
- frontend/src/**/*.tsx
- frontend/src/**/*.ts
- frontend/src/components/**/*
- frontend/src/tests/**/*
- docs/tasks/TASK_2026_01_23_005_doc_embed_ui_status.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "DocumentTile|DocumentsView|UploadedDocument" frontend/src
- pnpm --dir frontend/src test || true
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-005_DOC_EMBED_UI_STATUS: show embedding status in UI
- Commit B: TASK-2026-01-23-005_DOC_EMBED_UI_STATUS: finalize task summary

## Summary
- Added document embed status fields to the frontend document model and normalized API payloads for local state.
- Rendered an embedding status badge on document tiles and passed status through the documents list.
- Added a unit test to assert status badge rendering.

## Checks Run
- `rg -n "DocumentTile|DocumentsView|UploadedDocument" frontend/src`
- `pnpm --dir frontend/src test || true` (pass; warnings from existing tests about act() and WebSocket errors)
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows only this task artifact pending finalize commit.

## Commits
- Commit A (implementation): `97da98ff`
- Commit B (finalize docs): TBD

## Mapping
- TASK-2026-01-23-005_DOC_EMBED_UI_STATUS -> [97da98ff, ]
