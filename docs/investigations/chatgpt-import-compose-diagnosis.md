# ChatGPT Import Compose Failure Diagnosis

Date: 2026-03-10
Scope: investigation-only (no runtime code changes)

## Summary
The ChatGPT import path is **synchronous in the backend API process** and does **not** enqueue import work to Redis workers. The observed failures are most consistent with a **partial Docker Compose runtime state** (frontend/redis/workers stopped while backend lifecycle changed), not with a bug in ChatGPT import logic itself.

Most likely root cause (working theory): import attempts occurred while the frontend could not resolve `backend` on the Compose network (`getaddrinfo ENOTFOUND backend`), and later backend restarted without redis running, causing startup warmup enqueue to log `Error -2 connecting to redis:6379`.

## Reproduction path
1. Open Settings -> Data tab in UI (`Import ChatGPT history` button).
2. `frontend/src/features/settings/SettingsView.tsx` opens `ChatGPTImportModal`.
3. Modal submit (`handleMigrate`) posts `POST /api/upload-chatgpt-export`.
4. Vite proxy in container routes `/api/*` to `VITE_PROXY_TARGET=http://backend:8888`.
5. Failure symptoms observed:
   - frontend proxy errors: `socket hang up` on `/api/upload-chatgpt-export`, then repeated `getaddrinfo ENOTFOUND backend`
   - backend startup warning when redis unavailable: `Error -2 connecting to redis:6379. Name or service not known`

## Evidence collected
### Commands run
- `docker compose config --services`
- `docker compose ps`
- `docker compose ps -a`
- `docker compose logs backend --tail=300`
- `docker compose logs backend --since=40m`
- `docker compose logs redis --tail=300`
- `docker compose logs worker-chat --tail=300`
- `docker compose logs worker-document-embed --tail=300`
- `docker compose logs frontend --tail=300`
- targeted filters:
  - `docker compose logs -t frontend | rg "upload-chatgpt-export|socket hang up|ENOTFOUND backend"`
  - `docker compose logs -t backend | rg "redis:6379|warmup enqueue failed"`

### Runtime snapshots
- `docker compose ps` showed only `backend`, `db`, `neo4j`, `tts` up.
- `docker compose ps -a` showed `frontend`, `redis`, `worker-chat`, `worker-document-embed`, and other workers exited.
- `redis` log shows graceful SIGTERM/shutdown at `2026-03-10 17:14:23`.
- `backend` restarted around `2026-03-10 17:15`, booted HTTP successfully, but logged redis name-resolution failure during startup warmup enqueue.
- `frontend` logs include:
  - `http proxy error: /api/upload-chatgpt-export` + `socket hang up` (`03:48:06`)
  - repeated `getaddrinfo ENOTFOUND backend` (including `03:53` and `17:14` ranges)

### Code inspection evidence
- Import UI trigger:
  - `frontend/src/features/settings/SettingsView.tsx` (`Import ChatGPT history` button)
  - `frontend/src/components/modals/ChatGPTImportModal.tsx` -> `handleMigrate()` posts `/api/upload-chatgpt-export`
- Backend route:
  - `guardian/routes/migration.py`:
    - `@router.post("/api/upload-chatgpt-export")`
    - `@router.post("/upload-chatgpt-export")`
    - calls `ingest_chatgpt_export(content, user_id=user_id)`
- Import implementation:
  - `backend/rag/chatgpt_migration.py::ingest_chatgpt_export`
  - performs JSON parse/validation + DB writes + optional inline vector write
  - no Redis queue enqueue in this function
- Router registration:
  - `guardian/guardian_api.py` includes `migration.router` (label `migration`)
- Redis usage on backend startup:
  - `guardian/guardian_api.py` enqueues warmup task via `enqueue(task, "codexify:queue:system")`
  - this uses `guardian/queue/redis_queue.py` (`REDIS_URL` default `redis://redis:6379/0`)

## Import execution path
1. **Frontend action**: `SettingsView` -> `ChatGPTImportModal`
2. **HTTP call**: `api.post("/api/upload-chatgpt-export", formData, ...)`
3. **Route**: `guardian/routes/migration.py::upload_chatgpt_export`
4. **Service/function**: `backend/rag/chatgpt_migration.py::ingest_chatgpt_export`
5. **Work performed**:
   - bounded file read / size guard
   - JSON decode + format validation
   - thread/message creation in chat DB
   - optional inline vector store `.add_texts(...)` when vector store exists
6. **Response shape**: synchronous stats object (`threads_imported`, `messages_imported`, ...), no `task_id` required

## Queue / Redis dependency analysis
### Confirmed
- ChatGPT import route and `ingest_chatgpt_export` do **not** enqueue import jobs to Redis.
- Import response is synchronous (stats payload), not background-queued by default.
- Redis is used by:
  - startup warmup enqueue path in `guardian/guardian_api.py`
  - task-event streaming infrastructure (`/api/tasks/{task_id}/events`)
  - worker queues (`worker-chat`, `worker-document-embed`, etc.)

### Implication
- A redis outage should not inherently prevent synchronous ChatGPT import logic from executing.
- Redis failure messages observed are startup-adjacent and queue-adjacent, but not direct proof that import itself requires Redis.

## Compose networking / dependency analysis
### backend
- Service name: `backend`
- Exposes `8888`
- `depends_on`: `db`, `migrator`, `model-prep`, `graph-init`, `tts`
- **Does not depend on `redis`** in compose.
- Env sets `REDIS_URL=redis://redis:6379/0`.

### frontend
- Service name: `frontend`
- Env sets `VITE_PROXY_TARGET=http://backend:8888`.
- Vite proxy (`frontend/src/vite.config.ts`) routes `/api` to `PROXY_TARGET`.
- No `depends_on` entry for backend in compose.

### redis
- Service name: `redis`
- healthcheck present
- restart policy `unless-stopped`

### import-adjacent workers
- `worker-chat`, `worker-document-embed`, and others depend on `redis` + `backend` health.
- Workers were exited in current snapshot.

### Network assumption
- Default compose network DNS service-name resolution (`backend`, `redis`).
- `ENOTFOUND backend` / `Name or service not known` indicates DNS target absent/unresolvable at time of request.

## Most likely root cause
**Working theory (high confidence):**
A partial/inconsistent compose runtime caused name-resolution failures during import attempts:
- Frontend proxy attempted to reach `backend` by service DNS (`backend`) and intermittently failed with `ENOTFOUND backend`.
- Backend later restarted while `redis` was not running/resolvable, triggering startup warmup enqueue redis resolution failures.

This matches all observed symptoms:
- backend can boot and serve HTTP (confirmed)
- db resolves (confirmed via startup logs)
- redis sometimes unresolved (confirmed)
- frontend sometimes unresolved backend (confirmed)
- failure appears when import is attempted (import path is a high-signal API call through that proxy)

## Rejected alternative explanations
1. **"ChatGPT import requires Redis worker queue"**
   - Rejected by code path: route calls `ingest_chatgpt_export` directly, synchronously.
2. **"Import endpoint path mismatch"**
   - Rejected: UI posts `/api/upload-chatgpt-export`; route exists and is canonical.
3. **"Database connectivity caused import failure"**
   - Rejected: backend startup shows DB ready and `/ping` healthy.
4. **"Frontend proxy target is wrong by design"**
   - Rejected in-container: `backend` is the intended Compose hostname. Failure is intermittent/unavailable-state, not static misconfiguration.
5. **"Legacy rag_upload route conflict is the main cause"**
   - Rejected: active router registration uses `guardian/routes/migration.py`; no evidence that `rag_upload` router is mounted in the active API surface.

## Suggested fix
1. **Operational baseline (immediate):** ensure import is run only when full dependency set is up (`backend`, `frontend`, `redis`, and expected workers if needed).
2. **Compose hardening:**
   - Add `depends_on: redis: service_healthy` to `backend` **or** explicitly gate startup warmup enqueue when redis is unavailable.
   - Add `depends_on: backend: service_healthy` to `frontend` to reduce startup race / missing upstream windows.
   - Consider explicit restart policy for `backend`/`frontend` consistent with intended dev lifecycle.
3. **Import UX resilience (follow-up task):** preflight check before import submit (`/ping` + dependency readiness signal) and clear user-facing error if upstream unavailable.

## Risk / blast radius of the suggested fix
- Adding hard backend->redis dependency can block backend startup in scenarios where API-only mode without Redis is otherwise acceptable.
- Adding frontend->backend dependency changes startup timing and may mask backend readiness issues rather than fixing root lifecycle control.
- Changing restart policies can alter local dev ergonomics and may hide crash loops unless logs are monitored.
- Preflight checks are low-risk but add one extra request and a UX branch.

## Follow-up implementation task recommendation
Create a separate implementation PR with:
1. Compose dependency policy decision (strict vs optional redis for backend startup).
2. Compose updates for dependency ordering and restart semantics.
3. Optional backend readiness endpoint exposing queue dependency status separately from `/ping`.
4. Frontend import preflight and clearer error messaging for upstream DNS/unreachable conditions.
5. Regression checks:
   - import succeeds when all required services are healthy
   - import failure message is explicit when backend/redis unavailable
   - no regression to existing synchronous import behavior

## Files inspected
- `docker-compose.yml`
- `frontend/src/vite.config.ts`
- `frontend/src/components/modals/ChatGPTImportModal.tsx`
- `frontend/src/features/settings/SettingsView.tsx`
- `frontend/src/lib/api.ts`
- `guardian/routes/migration.py`
- `backend/rag/chatgpt_migration.py`
- `guardian/guardian_api.py`
- `guardian/queue/redis_queue.py`
- `guardian/queue/task_events.py`
- `guardian/queue/document_embed_queue.py`
- `guardian/workers/document_embed_worker.py`
- `guardian/routes/rag_upload.py`
- `backend/scripts/docker/run_backend.py`
- `guardian/core/dependencies.py`
- `tests/routes/test_migration_routes.py`
