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
