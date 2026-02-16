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


---

# Task 005 — Fullstack: Align Async Chat Completion Contract + Trace Retrieval (FINDING-2026-02-16-003)

Preflight: git status --porcelain -uall must be empty

## STOP Conditions
1) If preflight is not empty, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

2) If any out-of-scope files appear at any point, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

## Finding
- ID: `FINDING-2026-02-16-003`
- Severity: `WARN` (map to task risk: MED)
- Title: RAG loop uses async queue; frontend expects completion context that backend does not return

## Outcome (must be observable)
- RAG completion has a single documented contract:
  - `/chat/{thread_id}/complete` does NOT require synchronous RAG context to be returned for the frontend to function.
  - Either the endpoint returns explicit pointers/fields describing how to retrieve messages and trace (preferred for determinism), OR the frontend deterministically fetches trace from `/api/chat/debug/rag-trace/{thread_id}/latest`.
- Frontend no longer assumes `response.data.context` exists when calling `/chat/{id}/complete`.

## Allowed Files (strict)
- `guardian/routes/chat.py`
- `frontend/src/features/chat/GuardianChat.tsx`
- `frontend/src/**/*.ts`
- `frontend/src/**/*.tsx`
- `docs/**/*.md`

## Command Checklist
1) Preflight:
- `git status --porcelain -uall`

2) Inspect current mismatch (audit evidence):
- Review backend completion route and response in `guardian/routes/chat.py` (audit evidence L720-L870).
- Review frontend expectation in `frontend/src/features/chat/GuardianChat.tsx` (audit evidence L344-L373).
- Review debug trace endpoint in `guardian/routes/chat.py` (audit evidence L1265-L1313).

3) Implement (choose a deterministic contract and encode it in code + docs):
- Update backend and/or frontend so the async nature is first-class:
  - Backend: include explicit response fields (e.g., `task_id`, `depth_mode`, and trace/messages retrieval hints) OR
  - Frontend: after `/complete`, fetch the assistant message via the messages endpoint and fetch trace via debug endpoint.
- Remove any direct reliance on `response.data.context` in the frontend.
- Document the contract in `docs/` so it’s not dependent on tribal knowledge.

4) Verify (static verification):
- `rg -n "response\.data\.context" frontend/src/features/chat/GuardianChat.tsx -S || true`

5) Optional live verification hooks (do not require changing files beyond Allowed Files):
- `curl -sS http://localhost:8888/openapi.json | rg -n "\/chat\/\{thread_id\}\/complete|\/api\/chat\/debug\/rag-trace" || true`

6) Scope check:
- `git status --porcelain -uall`

## Expected Outputs (success signals)
- Frontend code has zero required dependency on `response.data.context` for the `/complete` call.
- The completion/trace retrieval contract is documented (and matches backend behavior).
- `git status --porcelain -uall` shows modifications only within Allowed Files.

## Rollback / Cleanup Commands
- `git restore --source=HEAD --staged --worktree -- guardian/routes/chat.py`
- `git restore --source=HEAD --staged --worktree -- frontend/src/features/chat/GuardianChat.tsx`
- `git restore --source=HEAD --staged --worktree -- frontend/src`
- `git restore --source=HEAD --staged --worktree -- docs`
- `git clean -fd`


## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_COMPILED_AUDIT

- Task ID: 005

- Head before: 95e291d2b93090dcefb41196be3e13bfe1780853
