# TASK-2026-02-05-009_doc_list_backend_source: source document list from backend

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-009_doc_list_backend_source
Task title: source document list from backend
Task artifact path: docs/tasks/TASK_2026_02_05_009_doc_list_backend_source.md
Risk: MED
Allowed files list:
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/lib/api.ts
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "documents" frontend/src/components/persona/layout/AppShell.tsx
- npm --prefix frontend install
- npm --prefix frontend run build
- git status --porcelain -uall
Expected outputs:
- Documents list is fetched from /api/media/documents.
- localStorage is used only as a cache, not the primary source of truth.
- Frontend build completes or failure is documented in task summary.
Rollback/cleanup commands:
- git checkout -- frontend/src/components/persona/layout/AppShell.tsx frontend/src/lib/api.ts
Dependencies/Prereqs (commands):
- npm --prefix frontend install

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-009_doc_list_backend_source: use backend docs list"
Commit B message EXACT:
"TASK-2026-02-05-009_doc_list_backend_source: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-009_doc_list_backend_source -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add frontend/src/components/persona/layout/AppShell.tsx frontend/src/lib/api.ts
- git commit --no-verify -m "TASK-2026-02-05-009_doc_list_backend_source: use backend docs list"
- git log -1 --oneline
- git add docs/tasks/TASK_2026_02_05_009_doc_list_backend_source.md docs/Campaign/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-009_doc_list_backend_source: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.

## Summary
- Status: DONE (already satisfied by prior implementation).
- Implementation: 7653f9f0 (documents list sourced from backend with local cache).
- Tests: Not run (no code changes for this task).
