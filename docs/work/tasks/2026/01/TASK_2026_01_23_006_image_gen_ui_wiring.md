# TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: Wire Image Generation UI to backend endpoint

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Close the Image Generation core loop by adding a Gallery trigger, a modal with prompt + model selection, and wiring to POST `/api/media/generate/image`.

### Expected Output
- Gallery has a visible button to open the modal.
- Modal submit triggers correct POST with required payload fields (including model).
- Generated images are added to the gallery view.

## Allowed Files
- frontend/src/components/gallery/GalleryView.tsx
- frontend/src/components/modals/*.tsx
- frontend/src/lib/**/*.ts (if there’s a centralized API client)
- frontend/src/tests/**/*.ts(x) (optional)
- guardian/routes/media.py (only if endpoint payload/response needs alignment)
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/work/tasks/2026/01/TASK_2026_01_23_006_image_gen_ui_wiring.md

Note: The campaign text references `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- rg -n "/api/media/generate/image|generate_image" guardian/routes/media.py
- rg -n "GalleryView|Generate" frontend/src/components/gallery/GalleryView.tsx
- ls -1 frontend/src/components/modals || true
- rg -n "\"type-check\"|\"lint\"|vitest" frontend/src/package.json
- pnpm --dir frontend/src lint
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: add image generation modal and gallery trigger
- Commit B: TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: finalize task summary

## Summary
- Added model selection to ImageGenModal and included model in the request payload.
- Added a GalleryView trigger + event listener to append generated images to the grid.
- Updated the modal test to assert the model value in the request.

## Checks Run
- `rg -n "/api/media/generate/image|generate_image" guardian/routes/media.py`
- `rg -n "GalleryView|Generate" frontend/src/components/gallery/GalleryView.tsx`
- `ls -1 frontend/src/components/modals || true`
- `rg -n "\"type-check\"|\"lint\"|vitest" frontend/src/package.json`
- `pnpm --dir frontend/src lint` (warnings only: existing lint warnings in repo)
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows this task artifact + campaign mapping pending finalize commit.

## Commits
- Commit A (implementation): `97dc31dc`
- Commit B (finalize docs): `006f2622`

## Mapping
- TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING -> [97dc31dc, 006f2622]
