Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-005"
- git status --porcelain -uall

# TASK-2026-02-16-005  Migration real-stack closure harness + runbook
- Risk: MED
- Findings: FINDING-2026-02-16-002
- Allowed files:
  - scripts/verification/migration_loop_validation.sh
  - docs/guardian/migration_loop_validation.md
  - tests/routes/test_migration_routes.py
  - guardian/guardian_api.py
  - guardian/routes/migration.py
  - docs/reports/mvp-core-loop-closure-matrix.md
- Dependencies/Prereqs:
  - command -v docker
  - command -v curl
  - command -v jq
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}"
  - docker compose up -d db backend
- Command checklist:
  1. pytest -q tests/routes/test_migration_routes.py::test_migration_route_executes_real_ingest_and_embeds
  2. rg -nF "include_router(migration.router)" guardian/guardian_api.py
  3. Add/refresh migration non-proxy validator script with auth + persistence read/list checks.
  4. Add/refresh migration runbook with exact deterministic command sequence.
  5. bash scripts/verification/migration_loop_validation.sh
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - Authenticated migration flow is reproducible from repo scripts/docs.
  - Validator exits 0 and proves persistence through backend list/read.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- scripts/verification/migration_loop_validation.sh docs/guardian/migration_loop_validation.md tests/routes/test_migration_routes.py guardian/guardian_api.py guardian/routes/migration.py docs/reports/mvp-core-loop-closure-matrix.md
  - git status --porcelain -uall