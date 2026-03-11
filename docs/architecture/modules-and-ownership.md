Purpose: Provide a subsystem-level map of Codexify so planning can follow real dependency edges, ownership conversations can start from actual seams, and blast radius is visible before code changes land.
Last updated: 2026-03-11
Source anchors:
- guardian/guardian_api.py
- guardian/routes/
- guardian/core/
- guardian/context/broker.py
- guardian/cognition/
- guardian/workers/
- guardian/queue/
- guardian/command_bus/
- guardian/db/models.py
- guardian/cron/
- guardian/realtime/
- guardian/routes/federation.py
- guardian/sync/
- frontend/src/
- docker-compose.yml

# Modules and Ownership

## Subsystem Matrix

| Subsystem | Class | Responsibilities | Key anchors | Depends on | Depended on by | Blast radius |
|---|---|---|---|---|---|---|
| API bootstrap and middleware | supporting | app creation, startup order, middleware, router inclusion, SSE endpoints, metrics | `guardian/guardian_api.py` | config, dependencies, all routers | every HTTP and SSE client | high |
| Auth and exposure boundary | supporting | API key/session auth, current-user derivation, public exposure controls, CORS | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py` | env, settings, crypto/session helpers | almost every protected route | high |
| Chat routes and thread lifecycle | core loop | thread creation, message persistence, completion enqueue, depth gating, debug traces | `guardian/routes/chat.py`, `guardian/routes/threads.py` | DB, Redis, depth rules | frontend chat UX, chat worker | high |
| Completion assembly and execution | core loop | prompt assembly, provider selection, output persistence, embeddings handoff | `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py` | context broker, provider router, DB, Redis | core assistant behavior | high |
| Context and retrieval broker | core loop | message history, semantic retrieval, doc scope, memory, graph, federated context | `guardian/context/broker.py`, `guardian/memoryos/retriever.py` | vector store, memory store, optional graph/federation | completion service | high |
| Prompt and profile system | core loop | system prompt layering, persona/profile resolution, system doc attachment | `guardian/cognition/system_prompt_builder.py`, `guardian/cognition/system_profiles/` | DB-backed docs/personas, thread/profile metadata | completion service, profile-switch flows | medium |
| Provider routing and catalog | core loop | provider health, request formatting, timeouts, model catalog, runtime provider sync | `guardian/core/ai_router.py`, `guardian/core/llm_catalog.py`, `guardian/core/provider_state.py` | settings, network, provider credentials | completion service, docs generation, frontend provider selection | high |
| Media and document ingestion | core loop | upload validation, asset dedupe, parsing, storage, document/thread/project links | `guardian/routes/media.py`, `guardian/routes/documents.py`, `guardian/services/document_parsers/` | storage, DB, queues | RAG corpus, document UI | high |
| Embedding and vector indexing | core loop | document/chat embedding, chunking, vector writes, semantic search | `guardian/workers/document_embed_worker.py`, `guardian/workers/chat_embedding_worker.py`, `guardian/vector/store.py` | embed models, vector backend, queues | context broker, ingestion UX | high |
| Queue and task transport | supporting | Redis queue access, cancellation, turn locks, task event streams, worker heartbeats | `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py` | Redis | chat, ingestion, cron, health endpoints | high |
| Durable events and audit | supporting | domain outbox, audit rows, event streaming, event graph lineage | `guardian/core/event_bus.py`, `guardian/core/outbox.py`, `guardian/db/models.py` | Postgres | live UI updates, debugging, downstream consumers | medium |
| Command bus | supporting | manifest derivation, invoke validation, idempotency, policy, loopback execution, run/event persistence | `guardian/routes/command_bus.py`, `guardian/command_bus/` | auth, OpenAPI, DB, HTTP loopback | tools shim, future agent/tool callers | high |
| Legacy tools shim | experimental | compatibility wrapper over command bus plus a few local helper behaviors | `guardian/routes/tools.py` | command bus, profile resolver | existing `/tools` clients | medium |
| Cron and scheduled automation | supporting | job CRUD, due-job scanning, queued execution, run history | `guardian/routes/cron.py`, `guardian/cron/`, `guardian/workers/cron_worker.py` | DB, Redis, egress policy | automation features and ops tasks | medium |
| Collaboration and WebSocket RPC | supporting | doc collaboration permissions, websocket sessions, RPC rate limiting, audit logging | `guardian/realtime/collaboration.py`, `guardian/ws/`, `guardian/routes/websocket.py` | auth, DB | realtime clients, shared-doc flows | medium |
| Federation and peer context | experimental | node trust, relay sessions, diff sync, peer context search, graph updates | `guardian/routes/federation.py`, `guardian/routes/federation_context.py` | trust policy, egress, optional graph | cross-node features | high |
| Sync API | experimental | idempotent event ingest plus process-local SSE subscription bus | `guardian/sync/api.py`, `guardian/sync/bus.py` | in-memory bus, sync models | light sync consumers | medium |
| Persistence layer | supporting | SQLAlchemy models, DB adapter methods, migrations, provider/runtime tables | `guardian/db/models.py`, `guardian/core/db.py`, `guardian/db/migrations/` | Postgres | almost every backend subsystem | high |
| Frontend shell and session spine | supporting | view routing, chat/doc/gallery/settings shell, persisted session state, local orchestration events | `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/state/session/SessionSpine.ts` | browser storage, backend APIs | end-user workflows | high |
| Frontend transport and auth client | supporting | backend URL resolution, auth header injection, live event transport, outage gating | `frontend/src/lib/runtimeConfig.ts`, `frontend/src/lib/api.ts`, `frontend/src/hooks/useLiveEvents.ts` | browser storage, backend endpoints | every frontend request path | high |

## Dependency Edges That Matter Most

- `guardian/guardian_api.py` is the top-level composition root.
  - Changing startup order or router inclusion can break unrelated subsystems at once.
- `guardian/core/chat_completion_service.py` sits at the center of the core assistant loop.
  - It depends on retrieval, prompting, provider routing, DB access, and task/event plumbing.
- `guardian/routes/media.py` is both a user-facing API and an ingestion orchestrator.
  - It couples storage, parsing, dedupe, DB writes, and queueing.
- `guardian/routes/tools.py` depends on the command bus manifest but still carries its own compatibility behavior.
  - That makes tool changes a two-surface problem.
- Frontend shell code in `AppShell.tsx` depends on several backend contracts directly and also coordinates local browser state.

## High-Coupling Hotspots

- `guardian/guardian_api.py`
- `guardian/routes/chat.py`
- `guardian/core/chat_completion_service.py`
- `guardian/routes/media.py`
- `guardian/routes/tools.py`
- `frontend/src/components/persona/layout/AppShell.tsx`

These files are the fastest way to change system behavior and the fastest way to create multi-subsystem regressions.

## Ownership Guidance

This repo does not declare formal team ownership in code, so the grouping below is a recommendation derived from coupling:

- Core loop cluster:
  - chat routes
  - completion service and chat worker
  - context broker
  - prompt/profile system
  - provider routing
- Retrieval and ingestion cluster:
  - media/doc routes
  - embedding workers
  - vector/memory layers
- Platform and control-plane cluster:
  - API bootstrap
  - auth boundary
  - queues/events
  - persistence
  - command bus
  - cron
  - websocket/realtime
- Experimental boundary cluster:
  - federation
  - sync API
  - legacy tools shim

## Change Planning Heuristics

- If a change touches the chat API contract, inspect:
  - `guardian/routes/chat.py`
  - `guardian/core/chat_completion_service.py`
  - `frontend/src/features/chat/`
  - `tests/routes/test_chat_routes.py`
- If a change touches document ingestion, inspect:
  - `guardian/routes/media.py`
  - `guardian/workers/document_embed_worker.py`
  - `guardian/context/broker.py`
  - `tests/routes/test_media_routes.py`
- If a change touches tools or automation, inspect:
  - `guardian/routes/command_bus.py`
  - `guardian/command_bus/invoke.py`
  - `guardian/routes/tools.py`
  - `guardian/routes/cron.py`
  - `tests/routes/test_command_bus_*`
