# Task 004 - Scope image generation to active project/thread
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-005
Risk: MED

Goal: remove hardcoded project/thread IDs and ensure generated images appear in the correct scoped gallery.

Allowed files:
- frontend/src/components/modals/ImageGenModal.tsx
- frontend/src/components/gallery/GalleryView.tsx
- frontend/src/App.tsx
- frontend/src/tests/image_gen_modal.spec.tsx

Dependencies/prereqs (commands):
- printenv IMAGE_GEN_PROVIDER >/dev/null
- printenv IMAGE_GEN_MODEL >/dev/null
- printenv GUARDIAN_API_KEY >/dev/null
- printenv VITE_GUARDIAN_API_KEY >/dev/null
- printenv OPENAI_API_KEY >/dev/null
- command -v pnpm
- command -v pytest

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-004-cleanup'
4. rg -n 'project_id: 1|thread_id: 1' frontend/src/components/modals/ImageGenModal.tsx frontend/src/tests/image_gen_modal.spec.tsx
5. rg -n 'project_id|thread_id|tag=generated' frontend/src/components/gallery/GalleryView.tsx guardian/routes/media.py
6. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(frontend/src/components/modals/ImageGenModal.tsx|frontend/src/components/gallery/GalleryView.tsx|frontend/src/App.tsx|frontend/src/tests/image_gen_modal.spec.tsx)$'
7. If step 6 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-004-out-of-scope'
8. pytest -q tests/routes/test_media_routes.py
9. pnpm -C frontend vitest run src/tests/image_gen_modal.spec.tsx
10. rg -n 'project_id: 1|thread_id: 1' frontend/src/components/modals/ImageGenModal.tsx frontend/src/tests/image_gen_modal.spec.tsx

Expected outputs:
- Step 2 returns no lines.
- Step 6 returns no lines (grep exit 1).
- Final step 10 returns no hardcoded ID matches.
- Pytest exits 0.
- Vitest exits 0.
- Generated image flow uses active scope context and remains visible in scoped gallery after reload.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-004'
- git restore --staged --worktree frontend/src/components/modals/ImageGenModal.tsx frontend/src/components/gallery/GalleryView.tsx frontend/src/App.tsx frontend/src/tests/image_gen_modal.spec.tsx

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any scope-model decision change must be captured in a dedicated Decision task artifact.