# TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy

## Title

Frontend sends X-API-Key consistently (no reliance on Vite proxy injection)

## Audit Link / Finding

- FINDING-2026-02-04-002

## Allowed Files List (ONLY)

- frontend/src/lib/api.ts
- frontend/src/vite.config.ts (only if simplifying dev proxy behavior)
- frontend/.env.example or root env templates if frontend expects variables (align with Task 001)
- README.md (only to document required env vars)

## Command Checklist

Preflight:

- git status --porcelain -uall

Locate current behavior:

- rg -n "axios|create\\(" frontend/src/lib/api.ts
- rg -n "X-API-Key" frontend/src || true
- rg -n "proxy" frontend/src/vite.config.ts

Implement:

- Add `X-API-Key` header injection in the Axios client using a configured env value:
  - prefer `import.meta.env.VITE_GUARDIAN_API_KEY`
- Ensure it works in dev and production builds.

Verify:

- npm test/build if present, else:
  - (frontend) npm run build
  - (runtime) verify requests include X-API-Key (devtools or server logs)

## Expected Outputs (Success Criteria)

- Frontend HTTP client includes `X-API-Key` on API requests
- App core calls succeed without relying on Vite proxy header injection

## Rollback / Cleanup Commands

- git restore --staged <paths>
- git restore <paths>

## Dependencies / Prereqs

- VITE_GUARDIAN_API_KEY set in local runtime (not committed)

## Commit Plan (MANUAL — Two Phase)

### Commit A message EXACT

"TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy: send X-API-Key in client"

Commands:

- git add frontend/src/lib/api.ts frontend/src/vite.config.ts README.md
- git commit --no-verify -m "TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy: send X-API-Key in client"
Record CommitA=c08e50a1

### Docs Commit message EXACT

"TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy: finalize task docs and campaign mapping"

Commands:

- git add docs/work/tasks/2026/02/TASK_2026_02_04_003_auth_frontend_attach_x_api_key_without_dev_proxy.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy: finalize task docs and campaign mapping"
Record DocsCommit=987e34ee

Campaign mapping update EXACT:

- TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy -> [<commitA>] DocsCommit=<docsCommit>

## Stop Conditions

- Dirty tree with out-of-scope files => STOP.
