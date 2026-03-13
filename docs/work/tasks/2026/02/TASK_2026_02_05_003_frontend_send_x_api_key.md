# TASK-2026-02-05-003_frontend_send_x_api_key: frontend consistently sends X-API-Key

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-003_frontend_send_x_api_key
Task title: frontend consistently sends X-API-Key
Task artifact path: docs/work/tasks/2026/02/TASK_2026_02_05_003_frontend_send_x_api_key.md
Risk: HIGH
Allowed files list:
- frontend/src/lib/**
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "X-API-Key" frontend/src
- rg -n "axios|fetch" frontend/src/lib
- npm --prefix frontend install
- npm --prefix frontend run build
- git status --porcelain -uall
Expected outputs:
- All frontend API requests include X-API-Key when VITE_GUARDIAN_API_KEY is set.
- No reliance on the Vite dev proxy for auth headers.
- Frontend build completes or failure is documented in task summary.
Rollback/cleanup commands:
- git checkout -- frontend/src/lib
Dependencies/Prereqs (commands):
- npm --prefix frontend install

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-003_frontend_send_x_api_key: send x-api-key from client"
Commit B message EXACT:
"TASK-2026-02-05-003_frontend_send_x_api_key: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-003_frontend_send_x_api_key -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add frontend/src/lib
- git commit --no-verify -m "TASK-2026-02-05-003_frontend_send_x_api_key: send x-api-key from client"
- git log -1 --oneline
- git add docs/work/tasks/2026/02/TASK_2026_02_05_003_frontend_send_x_api_key.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-003_frontend_send_x_api_key: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.

## Summary
- Status: DONE (already satisfied by prior implementation).
- Implementation: c08e50a1 (frontend API client injects X-API-Key and normalizes /api paths).
- Tests: Not run (no code changes for this task).
