Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-007"
- git status --porcelain -uall

# TASK-2026-02-16-007  Decision: canonical frontend API-key contract
- Risk: MED
- Findings: FINDING-2026-02-16-004, FINDING-2026-02-16-008
- Allowed files:
  - docs/reference/security/auth-boundary-decision.md
  - README.md
  - .env.template
  - docs/codexify-mvp-roadmap.md
- Dependencies/Prereqs:
  - command -v rg
- Command checklist:
  1. rg -n "VITE_GUARDIAN_DEV_API_KEY|VITE_GUARDIAN_API_KEY|forceApiKey" frontend/src/lib/api.ts frontend/src/main.tsx frontend/src/vite.config.ts README.md .env.template
  2. Record explicit MVP canonical env contract decision in docs/reference/security/auth-boundary-decision.md.
  3. Define compatibility shim semantics/timeline in docs.
  4. Align README/.env.template/roadmap language to that decision.
  5. rg -n "VITE_GUARDIAN_DEV_API_KEY|VITE_GUARDIAN_API_KEY" docs/reference/security/auth-boundary-decision.md README.md .env.template docs/codexify-mvp-roadmap.md
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - One canonical frontend auth env contract is documented.
  - No conflicting docs statements remain in touched files.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- docs/reference/security/auth-boundary-decision.md README.md .env.template docs/codexify-mvp-roadmap.md
  - git status --porcelain -uall