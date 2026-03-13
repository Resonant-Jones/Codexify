# TASK-2026-02-05-004_fix_chatgpt_import_path_auth: fix ChatGPT import path and auth

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-004_fix_chatgpt_import_path_auth
Task title: fix ChatGPT import path and auth
Task artifact path: docs/work/tasks/2026/02/TASK_2026_02_05_004_fix_chatgpt_import_path_auth.md
Risk: HIGH
Allowed files list:
- frontend/src/components/modals/ChatGPTImportModal.tsx
- frontend/src/lib/api.ts
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "upload-chatgpt-export" frontend/src/components/modals/ChatGPTImportModal.tsx
- npm --prefix frontend install
- npm --prefix frontend run build
- git status --porcelain -uall
Expected outputs:
- ChatGPT import uses /api/upload-chatgpt-export.
- Requests include X-API-Key via the shared API client.
- Frontend build completes or failure is documented in task summary.
Rollback/cleanup commands:
- git checkout -- frontend/src/components/modals/ChatGPTImportModal.tsx frontend/src/lib/api.ts
Dependencies/Prereqs (commands):
- npm --prefix frontend install

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-004_fix_chatgpt_import_path_auth: fix chatgpt import auth path"
Commit B message EXACT:
"TASK-2026-02-05-004_fix_chatgpt_import_path_auth: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-004_fix_chatgpt_import_path_auth -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add frontend/src/components/modals/ChatGPTImportModal.tsx frontend/src/lib/api.ts
- git commit --no-verify -m "TASK-2026-02-05-004_fix_chatgpt_import_path_auth: fix chatgpt import auth path"
- git log -1 --oneline
- git add docs/work/tasks/2026/02/TASK_2026_02_05_004_fix_chatgpt_import_path_auth.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-004_fix_chatgpt_import_path_auth: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.

## Summary
- Status: DONE (already satisfied by prior implementation).
- Implementation: e472ea71 (ChatGPT import uses /api/upload-chatgpt-export via shared API client).
- Tests: Not run (no code changes for this task).
