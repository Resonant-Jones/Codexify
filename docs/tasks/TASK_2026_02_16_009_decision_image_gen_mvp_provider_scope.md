Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-009"
- git status --porcelain -uall

# TASK-2026-02-16-009  Decision: MVP image-gen provider scope
- Risk: MED
- Findings: FINDING-2026-02-16-005, FINDING-2026-02-16-013
- Allowed files:
  - docs/codexify-mvp-roadmap.md
  - docs/codexify-mvp-roadmap-2026-02-15.md
  - README.md
  - .env.template
- Dependencies/Prereqs:
  - command -v rg
  - test -n "${OPENAI_API_KEY:-}" || true
- Command checklist:
  1. rg -n "openai|local|stability|Not implemented|IMAGE_GEN_PROVIDER" guardian/image_gen docs/codexify-mvp-roadmap.md README.md .env.template
  2. Document explicit MVP provider scope and deferred-provider acceptance criteria.
  3. Ensure docs/config text does not present deferred providers as ready.
  4. rg -n "openai|local|stability|IMAGE_GEN_PROVIDER" docs/codexify-mvp-roadmap.md docs/codexify-mvp-roadmap-2026-02-15.md README.md .env.template
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - Docs scope MVP providers explicitly and mark deferred providers as follow-up.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- docs/codexify-mvp-roadmap.md docs/codexify-mvp-roadmap-2026-02-15.md README.md .env.template
  - git status --porcelain -uall