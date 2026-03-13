Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-004"
- git status --porcelain -uall

# TASK-2026-02-16-004  Deterministic RAG memory-loop selector fix
- Risk: HIGH
- Findings: FINDING-2026-02-16-001
- Allowed files:
  - tests/integration/test_rag_integration_loop.py
  - guardian/routes/chat.py
  - guardian/workers/chat_worker.py
  - guardian/context/broker.py
  - guardian/cognition/identity_policy.py
- Dependencies/Prereqs:
  - command -v pytest
  - command -v rg
  - docker compose up -d db redis
  - docker compose ps db redis
- Command checklist:
  1. pytest -q tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop
  2. rg -n "depth_mode|downgraded depth_mode=deep|has_memory_context" tests/integration/test_rag_integration_loop.py guardian/routes/chat.py guardian/workers/chat_worker.py guardian/context/broker.py
  3. Fix deterministic context path so memory context is present.
  4. for i in 1 2 3; do pytest -q tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop || exit 1; done
  5. pytest -q tests/integration/test_rag_integration_loop.py -k memory -vv
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - Selector passes repeatedly from clean environment.
  - Assistant output includes persisted memory recall text.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- tests/integration/test_rag_integration_loop.py guardian/routes/chat.py guardian/workers/chat_worker.py guardian/context/broker.py guardian/cognition/identity_policy.py
  - git status --porcelain -uall