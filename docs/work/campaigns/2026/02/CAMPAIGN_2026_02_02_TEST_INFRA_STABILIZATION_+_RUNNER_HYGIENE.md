# CAMPAIGN_2026_02_02 — Test Infra Stabilization + Runner Hygiene

## Campaign Intent

Stabilize local test runs for `guardian/tests/test_chat_memory.py` by fixing two root causes:

1) the in-test Redis stub (`_InMemoryRedis`) lacks required methods for turn locks (`set`, `delete`)  
2) `chatlog_db` is not initialized during tests because `GUARDIAN_DATABASE_URL` / `DATABASE_URL` is not set early enough

Secondarily: fix one Runner Protocol hygiene issue in an older campaign file (allowed-files list points at a non-existent sidebar file).

## Global Notes

- Apply the Runner Protocol strictly:
  - one task = one change set
  - only edit allowed files
  - run checks/tests before commit
  - produce a task artifact in `docs/work/tasks/` for each task
  - clean tree between tasks

---

## TASK_2026_02_02_000_campaign_allowed_files_sidebar_fix

### Goal / Objective

Fix the allowed-files list in the existing campaign section so it references the correct sidebar file. Prevents scope ambiguity in future runs.

### Allowed Files (only)

- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md
- docs/work/tasks/2026/02/TASK_2026_02_02_000_campaign_allowed_files_sidebar_fix.md

### Checks to Run

```bash
rg -n "CAMPAIGN_2026_01_20_004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION|TASK-2026-01-20-013_DOCUMENT_GEN_MODAL_UI|Files allowed to edit" docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md
git diff --check

Commit Mode

one-commit

Commit Message Template
 • TASK_2026_02_02_000: fix campaign allowed-files sidebar path

Task Prompt (for docs/work/tasks artifact)

Update docs/work/campaigns/2026/01/CAMPAIGN_2026_01_20.md, in section:
## CAMPAIGN_2026_01_20_004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION →
### TASK-2026-01-20-013_DOCUMENT_GEN_MODAL_UI →
Files allowed to edit (only)

Edits:
 • Delete bullet: - frontend/src/components/Sidebar.tsx (if present)
 • Ensure bullet: - frontend/src/components/SidebarRoot.tsx exists
 • Leave - frontend/src/components/AppShell.tsx unchanged

⸻

TASK_2026_02_02_001_inmemoryredis_support_turn_locks

Goal / Objective

Implement the minimal Redis API required by the new per-thread turn-lock logic in tests.
Fixes the current failure: '_InMemoryRedis' object has no attribute 'set' and ... 'delete'.

Allowed Files (only)
 • guardian/queue/redis_queue.py
 • docs/work/tasks/2026/02/TASK_2026_02_02_001_inmemoryredis_support_turn_locks.md

Checks to Run

pytest -q guardian/tests/test_chat_memory.py::test_chat_turn_lock_rejects -vv -s
pytest -q guardian/tests/test_chat_memory.py::test_chat_crud -vv -s

Commit Mode

one-commit

Commit Message Template
 • TASK_2026_02_02_001: add InMemoryRedis set/delete for turn locks

Task Prompt (for docs/work/tasks artifact)

In guardian/queue/redis_queue.py, locate the in-test Redis stub class (commonly _InMemoryRedis).
Add minimal method support:
 • set(key, value, ex=None, nx=False):
 • implement NX semantics (don’t overwrite if key exists) when nx=True
 • implement TTL behavior using ex seconds (expire keys)
 • return truthy success like Redis (True/1) and falsy on NX failure
 • delete(key):
 • delete key if present (respect expiry)
 • return integer count of deleted keys (0 or 1)

Do not change production Redis behavior—only the in-memory stub.

⸻

TASK_2026_02_02_002_seed_chatlog_db_env_for_tests

Goal / Objective

Ensure chatlog_db initializes during pytest runs by setting GUARDIAN_DATABASE_URL or DATABASE_URL
early enough (before app import). Fixes current warning/error:
 • [db] No chatlog DB configured (GUARDIAN_DATABASE_URL or DATABASE_URL must be set)
 • chatlog_db is not initialised
 • NoneType has no attribute ensure_chat_thread/list_messages

Allowed Files (only)
 • guardian/tests/conftest.py
 • docs/work/tasks/2026/02/TASK_2026_02_02_002_seed_chatlog_db_env_for_tests.md

Checks to Run

pytest -q guardian/tests/test_chat_memory.py::test_chat_crud -vv -s
pytest -q guardian/tests/test_chat_memory.py::test_memory_crud_and_health -vv -s

Commit Mode

one-commit

Commit Message Template
 • TASK_2026_02_02_002: seed chatlog DB env for pytest bootstrap

Task Prompt (for docs/work/tasks artifact)

In guardian/tests/conftest.py, set a deterministic SQLite DB URL for chatlog before importing/creating the FastAPI app.
Requirements:
 • Must run at import time in conftest (top-level), not inside a fixture that runs after the app is imported.
 • Use a local sqlite file path under guardian/temp/ or a .pytest_* file in repo root.
 • Set one of:
 • GUARDIAN_DATABASE_URL=sqlite:///...
 • or DATABASE_URL=sqlite:///...
whichever the chatlog initializer expects (prefer GUARDIAN_DATABASE_URL if chatlog warns about that).

No Docker dependencies. The tests must pass locally.

⸻

TASK_2026_02_02_003_make_test_chat_memory_pass_end_to_end

Goal / Objective

After Redis stub + DB env are fixed, make the entire guardian/tests/test_chat_memory.py pass.
This task is explicitly for any remaining failures (status codes, pagination shape, auth headers, lock release).

Allowed Files (only)
 • guardian/tests/test_chat_memory.py
 • guardian/tests/conftest.py
 • guardian/core/dependencies.py
 • guardian/routes/chat.py
 • guardian/routes/memory.py
 • docs/work/tasks/2026/02/TASK_2026_02_02_003_make_test_chat_memory_pass_end_to_end.md

Checks to Run

pytest -q guardian/tests/test_chat_memory.py -vv -s

Commit Mode

one-commit

Commit Message Template
 • TASK_2026_02_02_003: make test_chat_memory pass

Task Prompt (for docs/work/tasks artifact)

Run pytest -q guardian/tests/test_chat_memory.py -vv -s and fix remaining failures while staying in the allowed file list.

Typical fixes that are allowed under this task:
 • ensure TestClient uses X-API-Key consistently (either by default headers or dependency override)
 • ensure chat/memory routes return expected status codes and shapes (ok, pagination fields)
 • ensure turn-lock is acquired/released correctly across success/failure paths (avoid lock leaks)

Do not refactor unrelated code. Keep changes minimal and directly tied to failing assertions.

⸻

Completion Mapping Requirement

After completing all tasks, output a mapping:
 • TASK_... -> <commit_hash>

If any task uses two-phase mode, output:
 • TASK_... -> [impl_hash, finalize_hash]

