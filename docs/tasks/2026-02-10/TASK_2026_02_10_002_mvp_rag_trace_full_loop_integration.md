# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 002
- Title: Deterministic RAG completion to trace retrieval integration
- Finding: FINDING-2026-02-10-005
- Risk: MED

## Allowed Files
- tests/integration/test_rag_integration_loop.py
- tests/integration/test_chat_completion_context.py
- guardian/routes/chat.py
- guardian/workers/chat_worker.py

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. test -n ${REDIS_URL:-} || { echo 'Missing REDIS_URL'; exit 1; }
5. test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
6. test -n ${CODEXIFY_VECTOR_STORE:-} || { echo 'Missing CODEXIFY_VECTOR_STORE'; exit 1; }
7. rg -n 'rag-trace|task.completed|_thread_latest_task' guardian/routes/chat.py guardian/workers/chat_worker.py tests/integration/test_chat_completion_context.py
8. pytest tests/integration/test_rag_integration_loop.py tests/integration/test_chat_completion_context.py -q
9. for f in $(git diff --name-only); do case $f in tests/integration/test_rag_integration_loop.py|tests/integration/test_chat_completion_context.py|guardian/routes/chat.py|guardian/workers/chat_worker.py) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Integration path executes API -> queue -> worker completion without synthetic trace injection.
- /api/chat/debug/rag-trace/{thread_id}/latest returns real trace for completed task.
- Integration suite passes deterministically.

## Rollback / Cleanup
- git restore --staged tests/integration/test_rag_integration_loop.py tests/integration/test_chat_completion_context.py guardian/routes/chat.py guardian/workers/chat_worker.py || true
- git restore tests/integration/test_rag_integration_loop.py tests/integration/test_chat_completion_context.py guardian/routes/chat.py guardian/workers/chat_worker.py || true

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v pytest >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
- test -n ${REDIS_URL:-} || { echo 'Missing REDIS_URL'; exit 1; }
- test -n ${DATABASE_URL:-} || { echo 'Missing DATABASE_URL'; exit 1; }
- test -n ${CODEXIFY_VECTOR_STORE:-} || { echo 'Missing CODEXIFY_VECTOR_STORE'; exit 1; }
