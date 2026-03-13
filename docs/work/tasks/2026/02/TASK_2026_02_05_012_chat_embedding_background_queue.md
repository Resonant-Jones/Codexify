# TASK-2026-02-05-012_chat_embedding_background_queue: move chat embeddings to background worker

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-012_chat_embedding_background_queue
Task title: move chat embeddings to background worker
Task artifact path: docs/work/tasks/2026/02/TASK_2026_02_05_012_chat_embedding_background_queue.md
Risk: MED
Allowed files list:
- guardian/routes/chat.py
- guardian/queue/redis_queue.py
- guardian/workers/chat_embedding_worker.py
- docker-compose.yml
- README.md
- tests/routes/test_chat_routes.py
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "_embed_message|embedding" guardian/routes/chat.py
- rg -n "enqueue|queue" guardian/queue/redis_queue.py
- docker compose config
- python -m pytest tests/routes/test_chat_routes.py
- git status --porcelain -uall
Expected outputs:
- Chat message embeddings are queued instead of computed synchronously.
- A background worker processes chat embedding jobs.
- docker-compose.yml includes the new worker or README.md documents how to run it.
- Tests pass or failures are documented in the task summary.
Rollback/cleanup commands:
- git checkout -- guardian/routes/chat.py guardian/queue/redis_queue.py guardian/workers/chat_embedding_worker.py docker-compose.yml README.md tests/routes/test_chat_routes.py
Dependencies/Prereqs (commands):
- python -m pip install -r requirements.txt
- docker compose version

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-012_chat_embedding_background_queue: queue chat embeddings"
Commit B message EXACT:
"TASK-2026-02-05-012_chat_embedding_background_queue: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-012_chat_embedding_background_queue -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add guardian/routes/chat.py guardian/queue/redis_queue.py guardian/workers/chat_embedding_worker.py docker-compose.yml README.md tests/routes/test_chat_routes.py
- git commit --no-verify -m "TASK-2026-02-05-012_chat_embedding_background_queue: queue chat embeddings"
- git log -1 --oneline
- git add docs/work/tasks/2026/02/TASK_2026_02_05_012_chat_embedding_background_queue.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-012_chat_embedding_background_queue: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.

## Summary
- Status: DONE.
- Changes:
  - Queued chat embeddings instead of running synchronously in `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/routes/chat.py`.
  - Added chat embedding queue helpers/constants in `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/queue/redis_queue.py`.
  - Added `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/workers/chat_embedding_worker.py`.
  - Added `worker-chat-embed` service in `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/docker-compose.yml`.
  - Documented worker in `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/README.md`.
- Tests:
  - `docker compose config` (pass)
  - `python -m pytest tests/routes/test_chat_routes.py` (fail: `No module named pytest`)
- Commit mode: two-phase.
- Implementation commit: `dc9592f7`.
