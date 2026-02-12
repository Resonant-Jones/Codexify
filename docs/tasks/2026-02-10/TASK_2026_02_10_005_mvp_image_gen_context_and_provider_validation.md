# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 005
- Title: Use active context for image-gen and validate one real provider path
- Finding: FINDING-2026-02-10-008
- Risk: MED

## Allowed Files
- frontend/src/components/modals/ImageGenModal.tsx
- guardian/image_gen/router.py
- guardian/image_gen/providers/local.py
- guardian/image_gen/providers/stability.py
- tests/routes/test_media_routes.py
- frontend/src/tests/image_gen_modal.spec.tsx
- tests/integration/test_image_gen_provider_path.py

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. test -n ${IMAGE_GEN_PROVIDER:-} || { echo 'Missing IMAGE_GEN_PROVIDER'; exit 1; }
5. test -n ${IMAGE_GEN_MODEL:-} || { echo 'Missing IMAGE_GEN_MODEL'; exit 1; }
6. test -n ${OPENAI_API_KEY:-} || { echo 'Missing OPENAI_API_KEY'; exit 1; }
7. rg -n 'project_id: 1|thread_id: 1|not implemented' frontend/src/components/modals/ImageGenModal.tsx guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py
8. pytest tests/routes/test_media_routes.py -q
9. cd frontend && npx vitest run src/tests/image_gen_modal.spec.tsx
10. pytest tests/integration/test_image_gen_provider_path.py -q
11. for f in $(git diff --name-only); do case $f in frontend/src/components/modals/ImageGenModal.tsx|guardian/image_gen/router.py|guardian/image_gen/providers/local.py|guardian/image_gen/providers/stability.py|tests/routes/test_media_routes.py|frontend/src/tests/image_gen_modal.spec.tsx|tests/integration/test_image_gen_provider_path.py) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Frontend image generation payload uses active project/thread context.
- At least one provider path is validated without provider execution mocks.
- Generated images remain queryable via backend list/tag pathways.

## Rollback / Cleanup
- git restore --staged frontend/src/components/modals/ImageGenModal.tsx guardian/image_gen/router.py guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py tests/routes/test_media_routes.py frontend/src/tests/image_gen_modal.spec.tsx tests/integration/test_image_gen_provider_path.py || true
- git restore frontend/src/components/modals/ImageGenModal.tsx guardian/image_gen/router.py guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py tests/routes/test_media_routes.py frontend/src/tests/image_gen_modal.spec.tsx tests/integration/test_image_gen_provider_path.py || true
- rm -f tests/integration/test_image_gen_provider_path.py

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
- command -v npx >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
- test -n ${IMAGE_GEN_PROVIDER:-} || { echo 'Missing IMAGE_GEN_PROVIDER'; exit 1; }
- test -n ${IMAGE_GEN_MODEL:-} || { echo 'Missing IMAGE_GEN_MODEL'; exit 1; }
- test -n ${OPENAI_API_KEY:-} || { echo 'Missing OPENAI_API_KEY'; exit 1; }
