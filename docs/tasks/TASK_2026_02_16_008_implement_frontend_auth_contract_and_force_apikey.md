Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-008"
- git status --porcelain -uall

# TASK-2026-02-16-008  Implement frontend auth contract + forceApiKey behavior
- Risk: MED
- Findings: FINDING-2026-02-16-004, FINDING-2026-02-16-008
- Allowed files:
  - frontend/src/lib/api.ts
  - frontend/src/lib/authState.ts
  - frontend/src/main.tsx
  - frontend/src/vite.config.ts
  - frontend/src/tests/gallery_auth.spec.tsx
  - frontend/src/tests/uploader_document_auth.spec.ts
- Dependencies/Prereqs:
  - command -v pnpm
  - command -v rg
  - pnpm -C frontend install
- Command checklist:
  1. rg -n "VITE_GUARDIAN_DEV_API_KEY|VITE_GUARDIAN_API_KEY|forceApiKey|void options" frontend/src/lib/api.ts frontend/src/main.tsx frontend/src/vite.config.ts
  2. Apply Task 007 decision in runtime/proxy paths and remove no-op forceApiKey handling.
  3. Implement deterministic forceApiKey header behavior and keep credential handling consistent.
  4. Update/add frontend tests for token/dev-key/force-api-key cases.
  5. pnpm -C frontend test
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - buildAuthenticatedFetchInit uses options and no longer contains void options.
  - Frontend test suite exits 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- frontend/src/lib/api.ts frontend/src/lib/authState.ts frontend/src/main.tsx frontend/src/vite.config.ts frontend/src/tests/gallery_auth.spec.tsx frontend/src/tests/uploader_document_auth.spec.ts
  - git status --porcelain -uall