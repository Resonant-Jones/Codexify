# TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage

## Title

Doc-gen UI lists documents from backend (localStorage only as cache)

## Audit Link / Finding

- FINDING-2026-02-04-008

## Allowed Files List (ONLY)

- frontend/src/components/persona/layout/AppShell.tsx
- guardian/routes/documents.py
- frontend/src/lib/api.ts (if needed for API call consistency; prefer reuse from Task 003)
- tests/*or guardian/tests/* (only if adding a targeted API/list test)
- README.md (only if docs mention current behavior)

## Command Checklist

Preflight:

- git status --porcelain -uall

Locate localStorage behavior:

- rg -n "localStorage|cfy\\.documents" frontend/src/components/persona/layout/AppShell.tsx
Locate backend list endpoint:
- rg -n "threads\\/{thread_id\\}\\/documents" guardian/routes/documents.py

Implement:

- UI calls backend documents list endpoint
- localStorage becomes cache/fallback only (not source of truth)

Verify:

- Generate a document
- Reload app
- Document persists in UI after reload (via backend)

## Expected Outputs (Success Criteria)

- UI document list reflects backend persisted state across sessions
- localStorage is not the only source of truth

## Rollback / Cleanup Commands

- git restore --staged <paths>
- git restore <paths>

## Dependencies / Prereqs

- Postgres running for persistence tests
- API auth working (Task 003 is prerequisite if auth blocks UI)

## Commit Plan (MANUAL — Two Phase)

### Commit A message EXACT

"TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage: wire UI docs list to backend"

Commands:

- git add frontend/src/components/persona/layout/AppShell.tsx guardian/routes/documents.py frontend/src/lib/api.ts README.md tests guardian/tests
- git commit --no-verify -m "TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage: wire UI docs list to backend"
Record CommitA=7653f9f0

### Docs Commit message EXACT

"TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage: finalize task docs and campaign mapping"

Commands:

- git add docs/work/tasks/2026/02/TASK_2026_02_04_007_docgen_ui_use_backend_documents_list_not_localstorage.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage: finalize task docs and campaign mapping"
Record DocsCommit=b178f5d9

Campaign mapping update EXACT:

- TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage -> [<commitA>] DocsCommit=<docsCommit>

## Stop Conditions

- Dirty tree with out-of-scope files => STOP.
