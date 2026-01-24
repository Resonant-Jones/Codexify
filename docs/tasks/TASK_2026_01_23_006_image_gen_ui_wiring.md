# TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: Wire Image Generation UI to backend endpoint

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Add the missing ImageGen UI entry point (button/modal) and wire it to the existing backend image generation endpoint.

### Expected Output
- UI has a visible button to open modal.
- Modal submit triggers correct POST with required payload fields.
- No unintended artifacts committed.

## Allowed Files
- frontend/src/**/*.tsx
- frontend/src/**/*.ts
- frontend/src/tests/**/*
- docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "media/generate|image/generate|Generate Image" frontend/src guardian/routes || true
- pnpm --dir frontend/src test || true
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: wire image gen modal to endpoint
- Commit B: TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: finalize task summary

## Summary
- Verified ImageGenModal posts to `/api/media/generate/image` with the expected payload and trims the prompt.
- Added a focused unit test to assert modal submit wiring and close behavior on success.

## Checks Run
- `rg -n "media/generate|image/generate|Generate Image" frontend/src guardian/routes || true`
- `pnpm --dir frontend/src test || true` (pass; warnings from existing tests about act() and WebSocket errors)
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows only this task artifact pending finalize commit.

## Commits
- Commit A (implementation): `94d8aee8`
- Commit B (finalize docs): TBD

## Mapping
- TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING -> [94d8aee8, ]
