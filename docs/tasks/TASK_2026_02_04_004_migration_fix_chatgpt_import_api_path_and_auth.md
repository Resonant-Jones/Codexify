# TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth

## Title

Fix ChatGPT import UI to use /api path and include API key

## Audit Link / Finding

- FINDING-2026-02-04-003

## Allowed Files List (ONLY)

- frontend/src/components/modals/ChatGPTImportModal.tsx
- guardian/routes/migration.py (only if backend path must be adjusted)
- README.md (only if docs are wrong)

## Command Checklist

Preflight:

- git status --porcelain -uall

Locate endpoints:

- rg -n "upload-chatgpt-export" frontend/src/components/modals/ChatGPTImportModal.tsx guardian/routes/migration.py
- rg -n "/api" frontend/src/vite.config.ts || true

Implement:

- UI should call `/api/upload-chatgpt-export` (or whatever canonical backend path is)
- Ensure `X-API-Key` is sent (prefer shared Axios client from Task 003, not bespoke fetch)

Verify:

- run frontend
- trigger import flow with a small export zip
- confirm request is proxied/correct and backend accepts auth

## Expected Outputs (Success Criteria)

- Import request goes to `/api/upload-chatgpt-export`
- Request includes X-API-Key
- Import completes (or reaches backend handler) without 401

## Rollback / Cleanup Commands

- git restore --staged <paths>
- git restore <paths>

## Dependencies / Prereqs

- Working GUARDIAN_API_KEY available locally (not committed)

## Commit Plan (MANUAL — Two Phase)

### Commit A message EXACT

"TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth: wire import to /api with auth"

Commands:

- git add frontend/src/components/modals/ChatGPTImportModal.tsx guardian/routes/migration.py README.md
- git commit --no-verify -m "TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth: wire import to /api with auth"
Record CommitA=e472ea71

### Docs Commit message EXACT

"TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth: finalize task docs and campaign mapping"

Commands:

- git add docs/tasks/TASK_2026_02_04_004_migration_fix_chatgpt_import_api_path_and_auth.md docs/Campaign/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth: finalize task docs and campaign mapping"
Record DocsCommit=0f14f6cd

Campaign mapping update EXACT:

- TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth -> [<commitA>] DocsCommit=<docsCommit>

## Stop Conditions

- Dirty tree with out-of-scope files => STOP.
