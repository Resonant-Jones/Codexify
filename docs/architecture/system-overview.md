# System Overview

Purpose: Capture the current runtime architecture of Codexify in one place so PM/dev planning starts from what is actually implemented, not assumed.
Last updated: 2026-02-17
Source anchors:
- docker-compose.yml
- guardian/guardian_api.py
- guardian/core/dependencies.py
- guardian/routes/chat.py
- guardian/workers/chat_worker.py
- guardian/context/broker.py
- guardian/routes/media.py
- guardian/workers/document_embed_worker.py
- guardian/routes/tools.py
- guardian/routes/cron.py
- guardian/routes/federation.py
- guardian/sync/api.py
- frontend/src/main.tsx
- frontend/src/App.tsx

## Components and Responsibilities

| Component | Responsibility | Key anchors |
|---|---|---|
| Frontend (React + Vite) | UI shell, thread/document views, auth token + dev key request headers, route-to-view mapping | `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/lib/api.ts` |
| API gateway (FastAPI app) | Router composition, startup/shutdown orchestration, middleware, SSE endpoints, static media mount | `guardian/guardian_api.py` |
| Auth boundary layer | Local API-key mode vs remote session/JWT mode, exposure mode allowlisting | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py` |
| Chat API surface | Thread/message CRUD, completion enqueue, debug traces | `guardian/routes/chat.py`, `guardian/routes/threads.py` |
| Completion worker | Dequeue chat tasks, assemble prompt/context, call provider, persist assistant message, emit task events | `guardian/workers/chat_worker.py` |
| Context/RAG broker | Retrieve recent messages + semantic + memory + graph/federated context by depth mode | `guardian/context/broker.py` |
| Provider/model routing | Route to local/groq/openai backends, enforce egress constraints, build provider catalog | `guardian/core/ai_router.py`, `guardian/core/llm_catalog.py`, `guardian/core/egress.py` |
| Media ingestion | Upload image/document, dedupe via canonical asset identity, parse document text, enqueue embedding | `guardian/routes/media.py`, `guardian/services/document_parsers/` |
| Embedding workers | Process document/chat embedding tasks and index into configured vector store | `guardian/workers/document_embed_worker.py`, `guardian/workers/chat_embedding_worker.py` |
| Storage/persistence | Postgres system of record (threads/messages/media/events/etc), Redis queues/streams, optional Neo4j graph, local/remote file storage | `guardian/db/models.py`, `guardian/queue/redis_queue.py`, `guardian/routes/health.py`, `docker-compose.yml` |
| Tool/job execution | Direct tools endpoint (in-memory jobs) plus durable cron scheduler/worker queue path | `guardian/routes/tools.py`, `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py` |
| Federation/sync | Peer manifest/session exchange, relay ws, diff push/pull, lightweight sync event bus API | `guardian/routes/federation.py`, `guardian/routes/federation_context.py`, `guardian/sync/api.py` |

## Deployment and Runtime Topology (As Implemented)

Default Docker Compose runtime (`docker-compose.yml`):
- `frontend` serves Vite UI on `:5173`, proxies to backend.
- `backend` serves FastAPI on `:8888` (`uvicorn guardian.guardian_api:app`).
- `db` provides Postgres (`:5433` host mapping).
- `redis` backs queue + task event stream transport.
- `neo4j` is present by default; graph context/logging still gated by config flags.
- Workers run as separate services:
  - `worker-chat`
  - `worker-chat-embed`
  - `worker-document-embed`
  - `worker-warmup`
- One-shot startup services:
  - `migrator` (alembic + seed)
  - `graph-init` (constraints + seed graph nodes)
- Additional profiles: `chatgpt-migrate`, `embedding-backfill`, `graph-backfill`.

Unverified:
- Production deployment layout outside Compose is not described in-repo. Verify via deployment manifests or infra repo (not present under this workspace).

## Critical Paths

### 1) Chat Completion Path

- Entry: `POST /chat/{thread_id}/complete` and `/api/chat/{thread_id}/complete`.
- Queue + lock: route acquires per-thread turn lock and enqueues `ChatCompletionTask` in Redis.
- Worker: `worker-chat` dequeues, resolves profile/provider/model, builds system prompt + context bundle.
- Provider call: local streaming or cloud sync completion.
- Persist + emit: assistant message written to Postgres, embeddings enqueued/written, task events streamed, turn lock released.
- Anchors: `guardian/routes/chat.py`, `guardian/queue/redis_queue.py`, `guardian/workers/chat_worker.py`, `guardian/queue/task_events.py`.

### 2) RAG/Context Assembly Path

- Trigger: chat worker processing a completion task.
- Broker: message history + semantic search (+ memory for deep/diagnostic) + optional graph/federated context.
- Prompt merge: `build_guardian_system_prompt` + `build_context_system_message` become a single system section prepended to conversation messages.
- Anchors: `guardian/context/broker.py`, `guardian/cognition/system_prompt_builder.py`, `guardian/cognition/prompts.py`, `guardian/workers/chat_worker.py`.

### 3) Ingestion Path (Documents + Images)

- Trigger: `/api/media/upload/document` or `/api/media/upload/image`.
- Identity/dedupe: hash + canonical media asset identity created/reused.
- Parse: document text extraction (`txt/md/pdf/docx`) done inline in API process.
- Async embedding: if parsed text exists, enqueue `document_embed` task and worker updates `embedding_status` lifecycle.
- Anchors: `guardian/routes/media.py`, `guardian/services/document_parsers/`, `guardian/queue/document_embed_queue.py`, `guardian/workers/document_embed_worker.py`.

### 4) Tool Execution Path

- Direct tools path: `/tools/execute` writes immediate result to in-memory `JOBS`; supports profile switch + noop.
- Durable scheduled jobs path: `/api/cron/jobs` definitions -> scheduler tick creates `cron_runs` + queue message -> cron worker executes and writes run result/errors.
- Anchors: `guardian/routes/tools.py`, `guardian/routes/cron.py`, `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py`.

### 5) Sync/Federation Path

- Federation: trust policy gates manifest/session exchange and peer relay operations; includes diff push/pull endpoints.
- Sync bus: separate `/api/sync/event` and `/api/sync/subscribe` SSE event bus with idempotent side-effect upserts.
- Anchors: `guardian/routes/federation.py`, `guardian/routes/federation_context.py`, `guardian/sync/api.py`, `guardian/sync/models.py`.

