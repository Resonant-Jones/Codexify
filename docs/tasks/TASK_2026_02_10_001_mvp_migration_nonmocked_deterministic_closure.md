# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 001
- Title: Migration loop closure without route/network mocks
- Finding: FINDING-2026-02-10-004
- Risk: MED

## Allowed Files
- guardian/routes/migration.py
- guardian/routes/rag_upload.py
- guardian/guardian_api.py
- tests/routes/test_migration_routes.py
- guardian/tests/migration/test_chatgpt_ingest.py
- frontend/src/tests/playwright/migration_e2e_import.spec.ts
- frontend/src/components/modals/ChatGPTImportModal.tsx

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. test -n ${VITE_GUARDIAN_API_KEY:-} || { echo 'Missing VITE_GUARDIAN_API_KEY'; exit 1; }
5. test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
6. test -n ${CODEXIFY_VECTOR_STORE:-} || { echo 'Missing CODEXIFY_VECTOR_STORE'; exit 1; }
7. rg -n 'upload-chatgpt-export' guardian/routes/migration.py guardian/routes/rag_upload.py guardian/guardian_api.py
8. pytest tests/routes/test_migration_routes.py guardian/tests/migration/test_chatgpt_ingest.py -q
9. cd frontend && npx playwright test src/tests/playwright/migration_e2e_import.spec.ts
10. for f in $(git diff --name-only); do case $f in guardian/routes/migration.py|guardian/routes/rag_upload.py|guardian/guardian_api.py|tests/routes/test_migration_routes.py|guardian/tests/migration/test_chatgpt_ingest.py|frontend/src/tests/playwright/migration_e2e_import.spec.ts|frontend/src/components/modals/ChatGPTImportModal.tsx) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Backend migration tests execute real ingest path (no ingest monkeypatch).
- Playwright migration test avoids API interception and validates persisted backend visibility after reload.
- Import requests include API key auth outside dev proxy mode.

## Rollback / Cleanup
- git restore --staged guardian/routes/migration.py guardian/routes/rag_upload.py guardian/guardian_api.py tests/routes/test_migration_routes.py guardian/tests/migration/test_chatgpt_ingest.py frontend/src/tests/playwright/migration_e2e_import.spec.ts frontend/src/components/modals/ChatGPTImportModal.tsx || true
- git restore guardian/routes/migration.py guardian/routes/rag_upload.py guardian/guardian_api.py tests/routes/test_migration_routes.py guardian/tests/migration/test_chatgpt_ingest.py frontend/src/tests/playwright/migration_e2e_import.spec.ts frontend/src/components/modals/ChatGPTImportModal.tsx || true

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
- command -v npx >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
- test -n ${VITE_GUARDIAN_API_KEY:-} || { echo 'Missing VITE_GUARDIAN_API_KEY'; exit 1; }
- test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
- test -n ${CODEXIFY_VECTOR_STORE:-} || { echo 'Missing CODEXIFY_VECTOR_STORE'; exit 1; }
