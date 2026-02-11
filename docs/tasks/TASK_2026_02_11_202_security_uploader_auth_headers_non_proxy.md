# Task 001 - Add explicit auth headers to uploader media requests
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-003
Risk: HIGH

Goal: remove dev-proxy auth dependency by ensuring uploader requests to media endpoints carry explicit auth headers in direct-backend deployments.

Allowed files:
- frontend/src/hooks/useUploader.ts
- frontend/src/lib/api.ts
- frontend/src/tests/uploader_document_auth.spec.ts

Dependencies/prereqs (commands):
- printenv GUARDIAN_API_KEY >/dev/null
- printenv VITE_GUARDIAN_API_KEY >/dev/null
- redis-cli ping
- pg_isready
- pgrep -fl worker-document-embed
- command -v pnpm
- command -v pytest

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-001-cleanup'
4. rg -n '/api/media/upload/document|/api/media/upload/image|X-API-Key' frontend/src/hooks/useUploader.ts frontend/src/lib/api.ts
5. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(frontend/src/hooks/useUploader.ts|frontend/src/lib/api.ts|frontend/src/tests/uploader_document_auth.spec.ts)$'
6. If step 5 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-001-out-of-scope'
7. pnpm -C frontend vitest run src/tests/uploader_document_auth.spec.ts
8. pytest -q tests/routes/test_media_routes.py guardian/tests/test_document_embed_worker.py

Expected outputs:
- Step 2 returns no lines.
- Step 5 returns no lines (grep exit 1).
- Vitest command exits 0.
- Pytest command exits 0.
- Upload requests to media endpoints include explicit auth header behavior in direct-backend mode.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_SECURITY_BOUNDARY-001'
- git restore --staged --worktree frontend/src/hooks/useUploader.ts frontend/src/lib/api.ts frontend/src/tests/uploader_document_auth.spec.ts
- git clean -fd frontend/src/tests/uploader_document_auth.spec.ts

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any architecture/policy decision must be handled in a dedicated Decision task, not as a follow-up question.