# TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING: Wire document generation modal

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Close the Generate Documents loop:
- Add a "Generate Document" button in Documents view.
- Wire DocumentGenModal submit to POST `/api/documents/generate`.
- Show success/failure and add the new document into the list view.

### Expected Output
- Documents view exposes a visible "Generate Document" action.
- Submitting the modal calls `/api/documents/generate` and results in a new document visible in the UI.
- Failure cases surface an error message (no silent no-op submit).

## Allowed Files
- frontend/src/components/documents/DocumentsView.tsx
- frontend/src/components/DocumentGenModal.tsx
- frontend/src/lib/**/*.ts (if API client used)
- guardian/routes/documents.py (only if response contract adjustment needed)
- frontend/src/tests/**/*.ts(x) (optional)
- docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_007_document_gen_ui_button_and_submit_wiring.md

Note: The campaign text references `docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- rg -n "DocumentGenModal" frontend/src/components -S
- rg -n "DocumentsView" frontend/src/components/documents/DocumentsView.tsx
- rg -n "/api/documents/generate|generate" guardian/routes/documents.py
- rg -n "\"type-check\"|\"lint\"" frontend/src/package.json
- pnpm --dir frontend/src lint (if listed in package.json)
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING: wire document generation modal
- Commit B: TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING: finalize task summary

## Summary
- No code changes required; existing UI already dispatches the generate event and submits to `/api/documents/generate`.
- Captured verification checks and prepared docs updates for two-phase flow.

## Checks Run
- `rg -n "DocumentGenModal" frontend/src/components -S`
- `rg -n "DocumentsView" frontend/src/components/documents/DocumentsView.tsx`
- `rg -n "/api/documents/generate|generate" guardian/routes/documents.py`
- `rg -n "\"type-check\"|\"lint\"" frontend/src/package.json`
- `pnpm --dir frontend/src lint` (warnings only: existing repo warnings)
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows only this task artifact pending finalize commit.

## Commits
- Commit A (implementation): `b20caad9`
- Commit B (finalize docs): TBD

## Mapping
- TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING -> [b20caad9, ]
