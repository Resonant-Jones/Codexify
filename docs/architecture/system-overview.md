Purpose: Capture Codexify's current runtime architecture in one place so onboarding, estimation, and design review start from implemented behavior rather than assumptions.
Last updated: 2026-03-17
Source anchors:
- docker-compose.yml
- src-tauri/
- guardian/server/run.py
- guardian/guardian_api.py
- guardian/core/
- guardian/routes/
- guardian/context/
- guardian/workers/
- guardian/command_bus/
- guardian/vector/
- guardian/sync/api.py
- frontend/src/

# System Overview

## Runtime Components

| Component | Responsibility | Key anchors |
|---|---|---|
| React frontend | Manual route-to-view mapping, chat/doc/gallery/settings UX, local session state, live event consumption | `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx` |
| Frontend API/runtime layer | Resolves backend base URL, injects auth/API-key headers, manages SSE connections | `frontend/src/lib/runtimeConfig.ts`, `frontend/src/lib/api.ts`, `frontend/src/hooks/useLiveEvents.ts`, `frontend/src/lib/guardianEventSource.ts` |
| FastAPI app | Startup orchestration, middleware, router inclusion, `/api/events`, `/api/tasks/*/events`, metrics, media mount | `guardian/guardian_api.py`, `guardian/server/run.py` |
| Auth and exposure boundary | Chooses local vs remote auth mode, derives current user, enforces API key/session rules, shapes CORS/public exposure | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py` |
| Chat API surface | Thread CRUD, message persistence, completion enqueue, RAG trace/debug endpoints | `guardian/routes/chat.py`, `guardian/routes/threads.py` |
| Completion service and chat worker | Builds provider-ready message bundles, runs model calls, persists assistant output, emits task events | `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py` |
| Context broker | Composes recent messages, semantic retrieval, document context, memory retrieval, optional graph/federated context | `guardian/context/broker.py`, `guardian/memoryos/retriever.py` |
| Media and document ingestion | Uploads documents/images, deduplicates assets, extracts text, links docs to threads/projects, enqueues embedding jobs | `guardian/routes/media.py`, `guardian/routes/documents.py`, `guardian/services/document_parsers/` |
| Embedding and retrieval stack | Creates chat/document embeddings, indexes and searches vector data, exposes health state | `guardian/workers/document_embed_worker.py`, `guardian/workers/chat_embedding_worker.py`, `guardian/vector/store.py`, `guardian/runtime/embed/embedder.py` |
| Command bus layer | Derives callable commands from OpenAPI, enforces policy/idempotency, exposes the canonical invoke surface | `guardian/routes/command_bus.py`, `guardian/command_bus/` |
| Cron and job execution | Persists schedules, queues due runs, executes jobs, records run history | `guardian/routes/cron.py`, `guardian/cron/`, `guardian/workers/cron_worker.py` |
| Federation and sync | Manages peer trust/session flows, relay/diff/context endpoints, and a separate lightweight sync bus | `guardian/routes/federation.py`, `guardian/routes/federation_context.py`, `guardian/sync/api.py` |
| Persistence and infra | Postgres system of record, Redis queues/locks/events, optional Neo4j, local/object media storage | `guardian/db/models.py`, `guardian/queue/redis_queue.py`, `guardian/core/storage.py`, `docker-compose.yml` |
| Desktop shell | Tauri runtime that can inject backend base URL and API key into the frontend | `src-tauri/src/commands.rs`, `frontend/src/lib/runtimeConfig.ts` |

## Deployment and Runtime Topology

### Default local topology

- `frontend` serves the Vite UI and proxies browser traffic to `backend`.
- `backend` runs `uvicorn guardian.guardian_api:app` on port `8888`.
- `db` provides Postgres and is the primary system of record.
- `redis` backs chat/document/cron queues, cancellation, heartbeats, and task event transport.
- `neo4j` is started by default in Compose, but graph usage is still feature-flagged.
- Worker processes run separately in Compose:
  - `worker-chat`
  - `worker-chat-embed`
  - `worker-document-embed`
  - `worker-warmup`
- One-shot services handle schema/bootstrap tasks:
  - `migrator`
  - `graph-init`
  - optional profiles such as `chatgpt-migrate` and `embedding-backfill`

### Runtime boundaries

- Node boundary:
  - browser / Tauri desktop shell
  - FastAPI backend
  - Postgres
  - Redis
  - optional Neo4j
  - optional external provider endpoints
- Trust boundaries:
  - browser or desktop client to backend auth boundary
  - backend to local/cloud model providers
  - backend to peer nodes in federation mode
  - backend to storage backends for media assets
- Threat model implied by code:
  - honest-but-buggy local runtime is the default assumption
  - public exposure and peer federation paths add explicit signature/auth/policy checks
  - enforcement is in route/auth/policy code, not in prompts

### Unverified runtime

- Production deployment outside Docker Compose is `Unverified`; no Kubernetes, Nomad, or other infra manifests were found in this repo.

## Provider Governance Contract

The configured provider is not the same thing as discovered provider inventory. Configuration selects the execution surface. Discovered inventory is only the live model list fetched by the registry for providers whose governance policy expects discovery.

`guardian/core/provider_registry.py` is the canonical source of provider-governance truth. Router behavior, catalog behavior, health reporting, and runtime model-selection checks should derive from that registry contract rather than from provider-specific hardcoded lists.

| Governance category | Providers | Operational meaning | Live discovery expected | Routing validates against discovered inventory | Configured defaults allowed during degraded discovery | Local-only / unavailable |
|---|---|---|---|---|---|---|
| `discovery_backed` | `alibaba`, `minimax` | Provider is routed through the canonical registry and expected to expose a live model index. | Yes | Yes | Yes | No |
| `static_authorized` | `openai`, `groq` | Provider is supported for routed execution through static model descriptors plus credential and egress authorization. | No | No | No | No |
| `local_only` | `local` | Provider is intentionally local-first and does not depend on cloud discovery or remote authorization. | No | No | No | Yes, intentionally local-only |
| `disabled` | `anthropic`, `gemini` | Provider remains explicitly classified in the registry but is unavailable for routed execution under the current contract. | No | No | No | Yes, unavailable |

## Critical Paths

### Chat completion path

- Trigger: `POST /api/chat/{thread_id}/complete`
- Core sequence:
  - validate thread and depth context
  - acquire Redis turn lock
  - enqueue `ChatCompletionTask`
  - worker assembles context and calls provider
  - persist assistant message and emit task/domain events
- Anchors: `guardian/routes/chat.py`, `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`, `guardian/queue/redis_queue.py`

### RAG/context assembly path

- Trigger: chat worker or completion service building model input
- Core sequence:
  - load recent thread messages
  - pull vector matches
  - add project/thread documents
  - optionally add memory, graph, sensors, or federated context by depth/flags
  - render system/context messages
- Anchors: `guardian/context/broker.py`, `guardian/memoryos/retriever.py`, `guardian/cognition/system_prompt_builder.py`

### Ingestion path

- Trigger: document/image upload or document generation
- Core sequence:
  - validate content type
  - compute canonical media identity
  - store bytes and metadata
  - extract document text inline
  - enqueue embed work
  - mark `embedding_status` as worker progresses
- Anchors: `guardian/routes/media.py`, `guardian/routes/documents.py`, `guardian/workers/document_embed_worker.py`

### Tool execution path

- Trigger: command bus invoke
- Core sequence:
  - derive manifest from OpenAPI
  - validate actor claim and idempotency
  - apply tool policy and execution-lane rules
  - execute loopback HTTP request for allowed commands
  - stream run events or return shim response
- Anchors: `guardian/routes/command_bus.py`, `guardian/command_bus/invoke.py`, `guardian/command_bus/loopback_http_adapter.py`

### Sync/federation path

- Trigger: federation session/diff/context endpoints or `/api/sync/event`
- Core sequence:
  - validate feature flags and trust policy
  - establish peer session or accept local event
  - apply diff/context/sync side effects
  - publish relay or SSE updates
- Anchors: `guardian/routes/federation.py`, `guardian/routes/federation_context.py`, `guardian/sync/api.py`

## Testing Reality

- Backend coverage is concentrated in Python tests for routes, core services, workers, realtime, federation, and migrations.
- Frontend test harnesses exist for Vitest, Playwright, and Cypress, but they are configured under `frontend/src` rather than integrated into the Python `make test` path.
- Docs-specific validation is nominally `make docs`, but the repo's actual docs build health should be checked each time because the target exists independently of the content in `docs/architecture/`.
- Anchors: `tests/`, `frontend/src/vitest.config.ts`, `frontend/src/playwright.config.ts`, `frontend/src/cypress.config.ts`, `Makefile`
