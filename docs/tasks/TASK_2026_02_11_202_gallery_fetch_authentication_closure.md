# Task 003 - Authenticate gallery read/write calls
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-004
Risk: MED

Goal: gallery list/upload calls authenticate explicitly and behave consistently in proxied and direct-backend deployments.

Allowed files:
- frontend/src/components/gallery/GalleryView.tsx
- frontend/src/hooks/useUploader.ts
- frontend/src/lib/api.ts
- frontend/src/tests/gallery_auth.spec.tsx

Dependencies/prereqs (commands):
- printenv GUARDIAN_API_KEY >/dev/null
- printenv VITE_GUARDIAN_API_KEY >/dev/null
- pg_isready
- command -v pnpm
- command -v pytest
- command -v curl

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-003-cleanup'
4. rg -n '/api/media/images|/api/media/upload/image' frontend/src/components/gallery/GalleryView.tsx frontend/src/hooks/useUploader.ts
5. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(frontend/src/components/gallery/GalleryView.tsx|frontend/src/hooks/useUploader.ts|frontend/src/lib/api.ts|frontend/src/tests/gallery_auth.spec.tsx)$'
6. If step 5 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-003-out-of-scope'
7. pytest -q tests/routes/test_media_routes.py::TestUploadDedupeAndTagging::test_list_images_generated_tag_returns_generated
8. pnpm -C frontend vitest run src/tests/gallery_auth.spec.tsx
9. curl -i http://localhost:8888/api/media/images
10. curl -i -H X-API-Key:${GUARDIAN_API_KEY} http://localhost:8888/api/media/images

Expected outputs:
- Step 2 returns no lines.
- Step 5 returns no lines (grep exit 1).
- Pytest exits 0.
- Vitest exits 0.
- Curl without auth returns 401/403.
- Curl with auth header returns 200.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-003'
- git restore --staged --worktree frontend/src/components/gallery/GalleryView.tsx frontend/src/hooks/useUploader.ts frontend/src/lib/api.ts frontend/src/tests/gallery_auth.spec.tsx
- git clean -fd frontend/src/tests/gallery_auth.spec.tsx

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any decision that changes API contract must be moved to a dedicated Decision task artifact.