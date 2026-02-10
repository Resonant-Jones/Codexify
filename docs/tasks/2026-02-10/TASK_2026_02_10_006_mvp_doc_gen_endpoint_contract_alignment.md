# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 006
- Title: Fix document generation endpoint contract drift in tests
- Finding: FINDING-2026-02-10-010
- Risk: MED

## Allowed Files
- guardian/tests/test_document_gen_endpoint.py
- guardian/routes/documents.py

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. rg -n 'thread_id|/api/documents/generate' guardian/tests/test_document_gen_endpoint.py guardian/routes/documents.py
4. pytest guardian/tests/test_document_gen_endpoint.py -q
5. for f in $(git diff --name-only); do case $f in guardian/tests/test_document_gen_endpoint.py|guardian/routes/documents.py) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Success test cases include required thread_id.
- Negative test explicitly asserts 400 when thread_id is missing.
- Endpoint contract tests pass.

## Rollback / Cleanup
- git restore --staged guardian/tests/test_document_gen_endpoint.py guardian/routes/documents.py || true
- git restore guardian/tests/test_document_gen_endpoint.py guardian/routes/documents.py || true

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
