# TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR: Show document embedding status in UI

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Show document embedding readiness in the Documents UI with a visible status indicator (including a short hint for failed items).

### Expected Output
- A visible status indicator exists for each document tile/card.
- Newly uploaded docs start at pending/processing then become ready after pipeline completes.
- Failed embeddings show a short hint.

## Allowed Files
- frontend/src/components/documents/**/*.tsx
- frontend/src/hooks/**/*.ts
- guardian/routes/media.py (only if list payload lacks status)
- guardian/db/models.py (only if serialization needs adjustment)
- frontend/src/tests/**/*.ts(x) (optional)
- docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_005_documents_ui_embed_status_indicator.md

Note: The campaign text references `docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- rg -n "DocumentsView|DocumentTile|UploadedDocument|embedding" frontend/src/components/documents -S
- rg -n "/api/media|documents|upload/document" frontend/src/hooks -S
- rg -n "list.*documents|GET.*documents|UploadedDocument" guardian/routes/media.py -S
- rg -n "\"type-check\"|\"lint\"|vitest|playwright" frontend/src/package.json
- pnpm --dir frontend/src lint
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR: show document embedding status in UI
- Commit B: TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR: finalize task summary

## Summary
- Added failure hints to document embedding status badges and passed through embedding errors to tiles.
- Added a test for failed status hint rendering.

## Checks Run
- `rg -n "DocumentsView|DocumentTile|UploadedDocument|embedding" frontend/src/components/documents -S`
- `rg -n "/api/media|documents|upload/document" frontend/src/hooks -S`
- `rg -n "list.*documents|GET.*documents|UploadedDocument" guardian/routes/media.py -S`
- `rg -n "\"type-check\"|\"lint\"|vitest|playwright" frontend/src/package.json`
- `pnpm --dir frontend/src lint` (warnings only: existing lint warnings in repo)
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows this task artifact + campaign mapping pending record finalize hash commit.

## Commits
- Commit A (implementation): `66501b7b`
- Commit B (finalize docs): `06a50a84`

## Mapping
- TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR -> [66501b7b, 06a50a84]
