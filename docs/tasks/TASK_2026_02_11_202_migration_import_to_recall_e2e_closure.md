# Task 002 - Migration import recall closure
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-002
Risk: MED

Goal: automated migration E2E imports a sample export and verifies subsequent chat completion retrieves an imported fact.

Allowed files:
- guardian/routes/migration.py
- backend/rag/chatgpt_migration.py
- tests/routes/test_migration_routes.py
- guardian/tests/migration/test_chatgpt_ingest.py
- frontend/src/components/modals/ChatGPTImportModal.tsx
- frontend/src/tests/playwright/migration_e2e_import.spec.ts
- frontend/src/tests/playwright/fixtures/chatgpt_export_sample.json

Dependencies/prereqs (commands):
- printenv GUARDIAN_API_KEY >/dev/null
- printenv VITE_GUARDIAN_API_KEY >/dev/null
- printenv CODEXIFY_VECTOR_STORE >/dev/null
- redis-cli ping
- pg_isready
- command -v npx
- npx playwright --version
- command -v pytest

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-002-cleanup'
4. rg -n 'upload-chatgpt-export|ingest_chatgpt_export' guardian/routes/migration.py backend/rag/chatgpt_migration.py frontend/src/components/modals/ChatGPTImportModal.tsx
5. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(guardian/routes/migration.py|backend/rag/chatgpt_migration.py|tests/routes/test_migration_routes.py|guardian/tests/migration/test_chatgpt_ingest.py|frontend/src/components/modals/ChatGPTImportModal.tsx|frontend/src/tests/playwright/migration_e2e_import.spec.ts|frontend/src/tests/playwright/fixtures/chatgpt_export_sample.json)$'
6. If step 5 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-002-out-of-scope'
7. pytest -q tests/routes/test_migration_routes.py guardian/tests/migration/test_chatgpt_ingest.py
8. npx playwright test frontend/src/tests/playwright/migration_e2e_import.spec.ts

Expected outputs:
- Step 2 returns no lines.
- Step 5 returns no lines (grep exit 1).
- Pytest exits 0.
- Playwright exits 0 and includes assertion that imported fact is recalled in post-import chat completion.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-002'
- git restore --staged --worktree guardian/routes/migration.py backend/rag/chatgpt_migration.py tests/routes/test_migration_routes.py guardian/tests/migration/test_chatgpt_ingest.py frontend/src/components/modals/ChatGPTImportModal.tsx frontend/src/tests/playwright/migration_e2e_import.spec.ts frontend/src/tests/playwright/fixtures/chatgpt_export_sample.json
- git clean -fd frontend/src/tests/playwright/fixtures/chatgpt_export_sample.json

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any unresolved product/UX decision must be moved to a dedicated Decision task artifact.