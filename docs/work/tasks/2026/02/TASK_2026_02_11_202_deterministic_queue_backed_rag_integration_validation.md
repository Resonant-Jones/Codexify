# Task 001 - Deterministic queue-backed RAG loop validation
Preflight: git status --porcelain -uall must be empty

Source finding: FINDING-2026-02-11-001
Risk: MED

Goal: assert one deterministic path: POST message -> enqueue completion -> worker completion -> retrieval-backed assistant output.

Allowed files:
- tests/integration/test_rag_integration_loop.py
- tests/routes/test_chat_routes.py
- tests/conftest.py
- guardian/routes/chat.py
- guardian/workers/chat_worker.py

Dependencies/prereqs (commands):
- printenv GUARDIAN_API_KEY >/dev/null
- printenv VITE_GUARDIAN_API_KEY >/dev/null
- redis-cli ping
- pg_isready
- pgrep -fl worker-chat
- pgrep -fl worker-chat-embed
- command -v pytest

Command checklist:
1. Preflight: git status --porcelain -uall must be empty
2. git status --porcelain -uall
3. If step 2 is non-empty, STOP and run: git stash push --include-untracked --message 'preflight-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-001-cleanup'
4. rg -n 'codexify:queue:chat|ContextBroker' guardian/routes/chat.py guardian/workers/chat_worker.py
5. rg -n 'Route may be synchronous|task_id' tests/routes/test_chat_routes.py
6. git status --porcelain -uall | awk '{print $2}' | grep -Ev '^(tests/integration/test_rag_integration_loop.py|tests/routes/test_chat_routes.py|tests/conftest.py|guardian/routes/chat.py|guardian/workers/chat_worker.py)$'
7. If step 6 prints any path, STOP and run: git stash push --include-untracked --message 'cleanup-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-001-out-of-scope'
8. pytest -q tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_success tests/integration/test_rag_integration_loop.py

Expected outputs:
- Step 2 returns no lines.
- Step 6 returns no lines (grep exit 1).
- Pytest exits 0.
- Integration assertion verifies retrieval-backed assistant content in queue-backed run.

Rollback/cleanup commands:
- git stash push --include-untracked --message 'rollback-CAMPAIGN_2026_02_11_MVP_LOOP_CLOSURE-001'
- git restore --staged --worktree tests/integration/test_rag_integration_loop.py tests/routes/test_chat_routes.py tests/conftest.py guardian/routes/chat.py guardian/workers/chat_worker.py

Runner constraints:
- Must not proceed with dirty tree.
- Must stop if out-of-scope files appear.
- Any new architectural decision must be split into a dedicated Decision task artifact.

## Completion Summary (Runner)

- Status: success

- Summary: Made the RAG loop test deterministic by explicitly controlling queue consumption and worker completion, then verified with the targeted pytest command.

- Implementation commit hash: afd3fff76079f2323cfde22b95bb074faf33fe9c

- Receipt update commit hash: (see campaign mapping)

- Tests ran: pytest -q tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_success tests/integration/test_rag_integration_loop.py (pass: 2 passed)

- Notes: Changes made:
- `tests/routes/test_chat_routes.py:356` now asserts a single deterministic async path for `/chat/{thread_id}/complete`: task is enqueued and `task_id` is returned.
- `tests/integration/test_rag_integration_loop.py:148` was rewritten to deterministic queue-backed flow:
  - post user message
  - dequeue/process chat-embed task
  - enqueue completion
  - dequeue/process chat completion worker
  - wait for `task.completed` event
  - assert assistant output includes retrieval-backed memory
- Added explicit queue drains and terminal-event wait helpers in `tests/integration/test_rag_integration_loop.py:114` and `tests/integration/test_rag_integration_loop.py:124`.
- Reset cached redis client (`redis_queue._CLIENT`) in test setup (`tests/integration/test_rag_integration_loop.py:199`) to prevent cross-test MagicMock leakage from route test fixtures.

<details>
<summary>Structured task_result.json</summary>

```json
{
  "status": "success",
  "summary": "Made the RAG loop test deterministic by explicitly controlling queue consumption and worker completion, then verified with the targeted pytest command.",
  "tests_ran": [
    "pytest -q tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_success tests/integration/test_rag_integration_loop.py (pass: 2 passed)"
  ],
  "commit_hash": "afd3fff76079f2323cfde22b95bb074faf33fe9c",
  "implementation_commit_hash": "afd3fff76079f2323cfde22b95bb074faf33fe9c",
  "receipt_update_commit_hash": "",
  "notes": "Changes made:\n- `tests/routes/test_chat_routes.py:356` now asserts a single deterministic async path for `/chat/{thread_id}/complete`: task is enqueued and `task_id` is returned.\n- `tests/integration/test_rag_integration_loop.py:148` was rewritten to deterministic queue-backed flow:\n  - post user message\n  - dequeue/process chat-embed task\n  - enqueue completion\n  - dequeue/process chat completion worker\n  - wait for `task.completed` event\n  - assert assistant output includes retrieval-backed memory\n- Added explicit queue drains and terminal-event wait helpers in `tests/integration/test_rag_integration_loop.py:114` and `tests/integration/test_rag_integration_loop.py:124`.\n- Reset cached redis client (`redis_queue._CLIENT`) in test setup (`tests/integration/test_rag_integration_loop.py:199`) to prevent cross-test MagicMock leakage from route test fixtures."
}
```

</details>
