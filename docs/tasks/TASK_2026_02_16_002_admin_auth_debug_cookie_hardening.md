Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-002"
- git status --porcelain -uall

# TASK-2026-02-16-002  Admin auth boundary and cookie hardening
- Risk: HIGH
- Findings: FINDING-2026-02-16-009
- Allowed files:
  - guardian/routes/admin.py
  - tests/routes/test_admin.py
  - .env.template
  - README.md
- Dependencies/Prereqs:
  - command -v rg
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}"
- Command checklist:
  1. rg -n "DEBUG_MODE|secure=False|GUARDIAN_ADMIN_TOKEN" guardian/routes/admin.py .env.template README.md
  2. Constrain/remove unconditional DEBUG admin bypass (explicit local opt-in only).
  3. Make cookie security flags environment-aware with secure defaults.
  4. Set docs/template default to DEBUG=false.
  5. pytest -q tests/routes/test_admin.py
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - No ambient DEBUG admin bypass.
  - No hardcoded secure=False cookie.
  - tests/routes/test_admin.py exits 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- guardian/routes/admin.py tests/routes/test_admin.py .env.template README.md
  - git status --porcelain -uall

## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_SECURITY_MVP_FOLLOWUP_EXECUTION

- Task ID: TASK-2026-02-16-002

- Head before: 0a2c08d3dbf5e9a7080e86865cb18a1d441d87aa
