Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-011"
- git status --porcelain -uall

# TASK-2026-02-16-011  Image-gen explicit scope, no default id fallback
- Risk: MED
- Findings: FINDING-2026-02-16-006
- Allowed files:
  - guardian/routes/media.py
  - frontend/src/components/modals/ImageGenModal.tsx
  - tests/routes/test_media_routes.py
  - frontend/src/tests/image_gen_modal.spec.tsx
- Dependencies/Prereqs:
  - command -v rg
  - command -v pytest
  - command -v pnpm
  - test -n "${GUARDIAN_API_KEY:-}" || true
  - docker compose up -d db
- Command checklist:
  1. rg -nF "project_id = request.project_id or 1" guardian/routes/media.py
  2. rg -nF "?? 1" frontend/src/components/modals/ImageGenModal.tsx
  3. Require explicit scope or authenticated derivation; fail fast when missing.
  4. Update backend/frontend tests for missing-scope failure and explicit-scope success.
  5. pytest -q tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_success -vv
  6. pnpm -C frontend test -- --run src/tests/image_gen_modal.spec.tsx
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - No implicit id=1 fallback remains in backend or modal.
  - Image-gen scope tests exit 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- guardian/routes/media.py frontend/src/components/modals/ImageGenModal.tsx tests/routes/test_media_routes.py frontend/src/tests/image_gen_modal.spec.tsx
  - git status --porcelain -uall