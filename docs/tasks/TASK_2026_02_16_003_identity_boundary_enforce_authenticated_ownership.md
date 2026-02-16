Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-003"
- git status --porcelain -uall

# TASK-2026-02-16-003  Identity boundary enforcement on mutating routes
- Risk: HIGH
- Findings: FINDING-2026-02-16-010
- Allowed files:
  - guardian/core/dependencies.py
  - guardian/routes/migration.py
  - guardian/routes/media.py
  - guardian/routes/chat.py
  - tests/routes/test_migration_routes.py
  - tests/routes/test_media_routes.py
  - tests/routes/test_identity_boundary.py
- Dependencies/Prereqs:
  - command -v rg
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}"
- Command checklist:
  1. rg -n "get_current_user|user_id" guardian/core/dependencies.py guardian/routes/migration.py guardian/routes/media.py guardian/routes/chat.py
  2. Derive mutating ownership from authenticated context or explicit single-user invariant.
  3. Reject caller-injected ownership ids when mismatched.
  4. Add/update mismatch rejection tests.
  5. pytest -q tests/routes/test_migration_routes.py
  6. pytest -q tests/routes/test_media_routes.py
  7. pytest -q tests/routes/test_identity_boundary.py
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - Mutating routes no longer trust arbitrary user_id values.
  - Identity tests exit 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- guardian/core/dependencies.py guardian/routes/migration.py guardian/routes/media.py guardian/routes/chat.py tests/routes/test_migration_routes.py tests/routes/test_media_routes.py tests/routes/test_identity_boundary.py
  - git status --porcelain -uall