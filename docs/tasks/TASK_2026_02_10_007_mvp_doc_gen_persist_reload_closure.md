# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 007
- Title: Deterministic doc-gen closure via backend retrieval after reload
- Finding: FINDING-2026-02-10-009
- Risk: MED

## Allowed Files
- guardian/tests/test_document_gen_persist_and_link.py
- guardian/tests/test_document_gen_pipeline.py
- guardian/routes/documents.py
- frontend/src/App.tsx
- frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. test -n ${AI_BACKEND:-} || { echo 'Missing AI_BACKEND'; exit 1; }
5. test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
6. rg -n 'thread_id is required|/api/documents/generate|cfy:documents:add' guardian/routes/documents.py frontend/src/App.tsx
7. pytest guardian/tests/test_document_gen_persist_and_link.py guardian/tests/test_document_gen_pipeline.py -q
8. cd frontend && npx playwright test src/tests/playwright/doc_gen_reload_persistence.spec.ts
9. for f in $(git diff --name-only); do case $f in guardian/tests/test_document_gen_persist_and_link.py|guardian/tests/test_document_gen_pipeline.py|guardian/routes/documents.py|frontend/src/App.tsx|frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Deterministic test proves generate -> persist -> thread-link -> backend retrieval after reload.
- Authenticated non-proxy behavior remains valid.
- Pipeline and persistence tests pass alongside reload assertion.

## Rollback / Cleanup
- git restore --staged guardian/tests/test_document_gen_persist_and_link.py guardian/tests/test_document_gen_pipeline.py guardian/routes/documents.py frontend/src/App.tsx frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts || true
- git restore guardian/tests/test_document_gen_persist_and_link.py guardian/tests/test_document_gen_pipeline.py guardian/routes/documents.py frontend/src/App.tsx frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts || true
- rm -f frontend/src/tests/playwright/doc_gen_reload_persistence.spec.ts

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
- command -v npx >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
- test -n ${AI_BACKEND:-} || { echo 'Missing AI_BACKEND'; exit 1; }
- test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
