# Task 005 - Rehydrate generated documents from backend thread links
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-006
Risk: MED

Goal: UI must read thread-document links from backend on load/thread switch so generated docs persist across refresh/session boundaries.

Allowed files:
- frontend/src/App.tsx
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/lib/api.ts
- frontend/src/tests/thread_documents_rehydration.spec.tsx

Dependencies/prereqs (commands):
- printenv GUARDIAN_API_KEY >/dev/null
- printenv VITE_GUARDIAN_API_KEY >/dev/null
- pg_isready
- command -v pnpm
- command -v pytest

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-005-cleanup'
4. rg -n '/documents/generate|cfy:documents:add|cfy:documents:open' frontend/src/App.tsx
5. rg -n '/media/documents|threads/.*/documents' frontend/src/components/persona/layout/AppShell.tsx frontend/src
6. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(frontend/src/App.tsx|frontend/src/components/persona/layout/AppShell.tsx|frontend/src/lib/api.ts|frontend/src/tests/thread_documents_rehydration.spec.tsx)$'
7. If step 6 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-005-out-of-scope'
8. pytest -q guardian/tests/test_document_gen_persist_and_link.py tests/routes/test_thread_documents.py
9. pnpm -C frontend vitest run src/tests/thread_documents_rehydration.spec.tsx

Expected outputs:
- Step 2 returns no lines.
- Step 6 returns no lines (grep exit 1).
- Backend tests exit 0.
- Frontend rehydration test exits 0.
- Generated docs are visible after refresh and thread switches.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-005'
- git restore --staged --worktree frontend/src/App.tsx frontend/src/components/persona/layout/AppShell.tsx frontend/src/lib/api.ts frontend/src/tests/thread_documents_rehydration.spec.tsx
- git clean -fd frontend/src/tests/thread_documents_rehydration.spec.tsx

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any API contract decision change must be captured in a dedicated Decision task artifact.