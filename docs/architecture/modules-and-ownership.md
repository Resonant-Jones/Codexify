# Modules and Ownership

Purpose: Provide a PM/Senior-dev subsystem map with dependency edges and blast-radius guidance so change planning can target the right seams first.
Last updated: 2026-02-17
Source anchors:
- guardian/guardian_api.py
- guardian/routes/
- guardian/core/
- guardian/context/broker.py
- guardian/workers/
- guardian/queue/
- guardian/db/models.py
- guardian/cron/
- guardian/routes/federation.py
- guardian/sync/
- frontend/src/App.tsx
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/lib/api.ts
- docker-compose.yml

## Subsystem Matrix

| Subsystem | Type | Responsibilities | Key anchors | Depends on | Depended on by | Blast radius |
|---|---|---|---|---|---|---|
| API bootstrap and middleware | supporting | App creation, router inclusion, request-id, CORS, SSE endpoints, startup orchestration | `guardian/guardian_api.py` | `guardian/core/*`, all routers | All HTTP clients, workers via startup contracts | high |
| Auth boundary and exposure policy | supporting | Local API key vs remote session/JWT auth, public allowlist mode | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py` | env + settings | Nearly all protected routes | high |
| Chat routes and turn gating | core loop | Thread/message APIs, completion enqueue, turn lock semantics | `guardian/routes/chat.py`, `guardian/queue/redis_queue.py` | chat DB, Redis queue | Frontend chat UX, chat worker | high |
| Chat completion worker | core loop | Dequeue chat tasks, provider call, persistence, task event lifecycle | `guardian/workers/chat_worker.py` | context broker, ai_router, DB, Redis | Completion UX and assistant output quality | high |
| Context broker | core loop | Depth-based message/semantic/memory/graph/federated retrieval | `guardian/context/broker.py` | vector store, memory retriever, optional graph/federation | chat worker prompt assembly | high |
| Prompt/profile layer | core loop | System prompt composition and per-thread profile overrides | `guardian/cognition/system_prompt_builder.py`, `guardian/cognition/system_profiles/resolver.py` | DB-backed persona/system-doc stores | chat worker and profile switch tools | medium |
| Provider routing and catalog | core loop | Resolve provider/model, call backend APIs, expose provider catalog | `guardian/core/ai_router.py`, `guardian/core/llm_catalog.py`, `guardian/core/egress.py` | settings + network | chat worker, docs generation, health/catalog routes | high |
| Vector + embedding stack | core loop | Embed/index/search text chunks and message embeddings | `guardian/vector/store.py`, `backend/rag/embedder.py`, `guardian/runtime/embed/embedder.py` | local model files or cloud keys | context broker, ingestion workers, health/vector | high |
| Media ingestion pipeline | core loop | Upload/dedupe assets, parse documents, enqueue embed tasks | `guardian/routes/media.py`, `guardian/services/document_parsers/` | storage backend, DB, queues | docs/images UX, RAG source material | high |
| Document generation + linkage | supporting | Autosave docs and LLM-driven document generation to thread links | `guardian/routes/documents.py` | chat provider calls, DB | frontend document modal/workspace | medium |
| Task/event transport | supporting | Redis queue operations, task streams, cancellation, lock TTL | `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py` | Redis | chat/document/cron workers, SSE task stream | high |
| Durable event outbox | supporting | Domain event persistence + replay over `/api/events` | `guardian/core/event_bus.py`, `guardian/core/outbox.py`, `guardian/guardian_api.py` | Postgres | frontend live updates/consumers | medium |
| Cron scheduler/executor | supporting | Scheduled job definitions, due-job queueing, run execution and status | `guardian/routes/cron.py`, `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py` | DB, Redis, egress policy | automation paths and future background orchestration | medium |
| Tools execution endpoint | experimental | Direct tool dispatch with in-memory job registry | `guardian/routes/tools.py` | profile resolver | frontend/admin tool calls | medium |
| Federation + peer sync | experimental | Manifest/session trust flow, relay channel, peer diff/context endpoints | `guardian/routes/federation.py`, `guardian/routes/federation_context.py` | signed policy + network | cross-node collaboration features | high |
| Sync bus API | experimental | Idempotent event ingest + in-process SSE publish | `guardian/sync/api.py`, `guardian/sync/bus.py` | in-memory bus, sync models | consumers of `/api/sync/subscribe` | medium |
| WebSocket RPC and audit | supporting | Authenticated RPC endpoint, rate limits, idle timeout, audit rows | `guardian/routes/websocket.py`, `guardian/ws/*` | auth, DB, rate limiter | real-time clients, admin tooling | medium |
| Connectors worker | supporting | Connector config CRUD, github sync, ingest into memory/events | `guardian/routes/connectors.py` | DB, optional external APIs | connector status UI and ingestion | medium |
| Frontend app shell and state spine | supporting | View routing, thread/doc state, event listeners, workflow orchestration | `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx` | backend APIs, browser storage | end-user experience | high |
| Frontend API/auth client | supporting | Auth header injection, 401 handling, token persistence | `frontend/src/lib/api.ts`, `frontend/src/lib/authState.ts` | browser storage + runtime env | all frontend API requests | high |

## Coupling and Blast-Radius Notes

- Highest coupling hotspots (change carefully):
  - `guardian/workers/chat_worker.py` (touches profile resolution, prompt, context, provider, persistence, events).
  - `guardian/routes/media.py` (identity, storage, parsing, embedding queue, API response contract).
  - `guardian/guardian_api.py` (startup order and router wiring).
- Experimental surfaces with unclear production guarantees:
  - `guardian/routes/tools.py` (in-memory job registry).
  - `guardian/sync/*` in-process event bus.
  - Portions of federation runtime where external peer policy and deployment assumptions are environment-driven.

## Ownership Model (Suggested)

Recommendations (not current declared team ownership):
- Treat `chat routes + worker + context broker + provider routing` as one ownership cluster for core-loop stability.
- Treat `media ingestion + embedding workers + vector layer` as a second ownership cluster for retrieval quality and ingestion reliability.
- Treat `auth boundary + API bootstrap + websocket + cron` as platform/ops cluster.
- Keep federation/sync behind explicit feature-owner review due high blast radius and policy/security coupling.

