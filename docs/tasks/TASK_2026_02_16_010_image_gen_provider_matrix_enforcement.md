Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-010"
- git status --porcelain -uall

# TASK-2026-02-16-010  Image-gen provider matrix runtime enforcement
- Risk: MED
- Findings: FINDING-2026-02-16-005
- Allowed files:
  - guardian/image_gen/router.py
  - guardian/image_gen/providers/local.py
  - guardian/image_gen/providers/stability.py
  - tests/routes/test_media_routes.py
- Dependencies/Prereqs:
  - command -v rg
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}" || true
- Command checklist:
  1. rg -n "Not implemented|status_code=503|IMAGE_GEN_PROVIDER" guardian/image_gen
  2. Align runtime messages/validation with documented MVP provider scope.
  3. Add/update tests for supported-provider success and unsupported-provider fail-closed behavior.
  4. pytest -q tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_success
  5. pytest -q tests/routes/test_media_routes.py -k provider
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - Runtime provider contract matches docs.
  - Provider tests exit 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- guardian/image_gen/router.py guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py tests/routes/test_media_routes.py
  - git status --porcelain -uall