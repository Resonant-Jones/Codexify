# TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS: Add doc type selector and refresh events

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Add the missing product ergonomics to document generation:
- doc_type selector: code / literature / diagram
- event emission or refetch so documents list refreshes immediately after generation

### Expected Output
- Modal includes doc_type selector with explicit options.
- Payload includes doc_type (or maps to backend contract).
- After generation, documents list refreshes (event or refetch) with no manual reload.

## Allowed Files
- frontend/src/components/DocumentGenModal.tsx
- frontend/src/components/documents/**/*.tsx (only if event wiring is here)
- frontend/src/App.tsx
- frontend/src/tests/document_gen_modal.spec.tsx (if payload assertions need updating)
- guardian/routes/documents.py (only if doc_type contract needs alignment)
- docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_008_document_gen_add_doc_type_and_events.md

## Checks to Run
- rg -n "doc_type|diagram|mermaid|code|literature" frontend/src/components/DocumentGenModal.tsx guardian/routes/documents.py -S
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS: add doc type selector and refresh events
- Commit B: TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS: finalize task summary

## Summary
- Added a doc_type selector to DocumentGenModal and included doc_type in the generate payload.
- Updated the modal test to assert the doc_type field.
- Existing document-add event emission remains the refresh mechanism after generation.

## Checks Run
- `rg -n "doc_type|diagram|mermaid|code|literature" frontend/src/components/DocumentGenModal.tsx guardian/routes/documents.py -S`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows App.tsx, DocumentGenModal.tsx, document_gen_modal.spec.tsx, the task artifact, and the campaign file pending commits.

## Commits
- Commit A (implementation): `e0c4b588`
- Commit B (finalize docs): `c37392de`

## Mapping
- TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS -> [e0c4b588, c37392de]
