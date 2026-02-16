# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 003
- Title: Make uploader auth work without Vite proxy header injection
- Finding: FINDING-2026-02-10-006
- Risk: HIGH

## Allowed Files
- frontend/src/hooks/useUploader.ts
- frontend/src/lib/api/client.ts
- frontend/src/tests/playwright/doc_upload_auth.spec.ts
- tests/routes/test_media_routes.py

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. test -n ${VITE_GUARDIAN_API_KEY:-} || { echo 'Missing VITE_GUARDIAN_API_KEY'; exit 1; }
5. rg -n '/api/media/upload/document|/api/media/upload/image' frontend/src/hooks/useUploader.ts
6. pytest tests/routes/test_media_routes.py -q
7. cd frontend && npx playwright test src/tests/playwright/doc_upload_auth.spec.ts
8. for f in $(git diff --name-only); do case $f in frontend/src/hooks/useUploader.ts|frontend/src/lib/api/client.ts|frontend/src/tests/playwright/doc_upload_auth.spec.ts|tests/routes/test_media_routes.py) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Upload requests include API key auth in non-proxy deployment mode.
- Backend media route tests still pass.
- Playwright upload auth test passes without relying on dev proxy header injection.

## Rollback / Cleanup
- git restore --staged frontend/src/hooks/useUploader.ts frontend/src/lib/api/client.ts frontend/src/tests/playwright/doc_upload_auth.spec.ts tests/routes/test_media_routes.py || true
- git restore frontend/src/hooks/useUploader.ts frontend/src/lib/api/client.ts frontend/src/tests/playwright/doc_upload_auth.spec.ts tests/routes/test_media_routes.py || true
- rm -f frontend/src/tests/playwright/doc_upload_auth.spec.ts

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
- command -v npx >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
- test -n ${VITE_GUARDIAN_API_KEY:-} || { echo 'Missing VITE_GUARDIAN_API_KEY'; exit 1; }


---

# Task 003 — Backend: Make `/media` Serving Reliable on Fresh Runtime (FINDING-2026-02-16-005)

Preflight: git status --porcelain -uall must be empty

## STOP Conditions
1) If preflight is not empty, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

2) If any out-of-scope files appear at any point, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

## Finding
- ID: `FINDING-2026-02-16-005`
- Severity: `WARN` (map to task risk: MED)
- Title: Media URLs depend on conditional `/media` static mount that may be absent on fresh runtime

## Outcome (must be observable)
- A fresh `docker compose up` reliably serves media URLs returned by the API (no manual directory creation required).
- The conditional mount behavior is removed or made safe by ensuring the base directory exists before the mount decision.

## Allowed Files (strict)
- `guardian/guardian_api.py`
- `guardian/core/storage.py`
- `docker-compose.yml`
- `docs/**/*.md`

## Dependencies / Prereqs (deterministic checks)
- `docker --version`
- `docker compose version`

## Command Checklist
1) Preflight:
- `git status --porcelain -uall`

2) Inspect current behavior (audit context):
- Review static mount logic in `guardian/guardian_api.py` (audit evidence lines L442-L450).
- Review storage base path defaults / directory creation in `guardian/core/storage.py` (audit evidence lines L485-L508).

3) Implement:
- Ensure the storage base directory exists before app startup static mounting decisions.
- Make `/media` serving deterministic for fresh runtimes (either always mount + create dir, or mount after ensuring dir exists).
- If behavior changes, document it in `docs/`.

4) Validate (basic service startup and route visibility):
- `docker compose up -d db redis backend`
- `curl -sS http://localhost:8888/openapi.json | rg -n "\/api\/media\/upload\/image|\/api\/media\/upload\/document|\/api\/media\/images|\/media" || true`

5) Scope check:
- `git status --porcelain -uall`

## Expected Outputs (success signals)
- Fresh backend startup does not depend on a pre-existing host/container directory for `/media` serving.
- Media upload/list routes continue to exist (OpenAPI grep finds expected endpoints).
- `git status --porcelain -uall` shows modifications only within Allowed Files.

## Rollback / Cleanup Commands
- `git restore --source=HEAD --staged --worktree -- guardian/guardian_api.py guardian/core/storage.py docker-compose.yml`
- `git restore --source=HEAD --staged --worktree -- docs`
- `git clean -fd`
