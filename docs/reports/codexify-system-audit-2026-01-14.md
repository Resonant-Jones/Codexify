# Codexify System Audit

## Metadata
- Repo name: Codexify
- Date of audit: 2026-01-14
- Agent/Model: Codex (GPT-5, runtime)
- Runner/Environment: Codex CLI (zsh, workspace-write sandbox)
- Git branch: chore/post-skip-hook-fixes
- Git commit: 6bcf51015783709a79f1ad994fe61f25156a29b1

## Executive Summary
- Overall health: a functioning FastAPI backend, React frontend, and Postgres/Redis/Neo4j stack exist, but wiring and auth coverage are inconsistent. Evidence: `guardian/guardian_api.py:315-389`, `docker-compose.yml:4-75, 33-50, 19-31`.
- Strength: local-first embeddings and vector search are implemented with FAISS/Chroma and dedicated backfill workers. Evidence: `guardian/vector/store.py:8-26`, `backend/rag/embedder.py:59-183`, `docker-compose.yml:508-558`.
- Strength: persona/imprint/system-doc data are persisted and used to build system prompts. Evidence: `guardian/db/models.py:824-935`, `guardian/cognition/system_prompt_builder.py:48-139`.
- [RISK] Auth gaps and explicit bypasses exist on chat, memory, media, and devtools routes (some endpoints accept no API key or force `api-bypass`). Evidence: `guardian/routes/chat.py:432-655, 746-783, 1053-1056`, `guardian/routes/memory.py:87-180`, `guardian/routes/media.py:135-200`, `guardian/routes/devtools.py:34-108`.
- [RISK] RAG context is assembled but not injected into main chat worker completions; only a hint is added to the system prompt and full context injection is in a different path. Evidence: `guardian/workers/chat_worker.py:151-220`, `guardian/cognition/prompts.py:98-116`, `guardian/core/dependencies.py:343-405`, `guardian/routes/chat.py:909-939`.
- [RISK] Documents/share/collaboration routers are included without DB configuration; runtime errors or stub DB usage are likely. Evidence: `guardian/routes/documents.py:46-60`, `guardian/routes/share.py:50-64`, `guardian/realtime/collaboration.py:33-59`, `guardian/guardian_api.py:378-381`, `guardian/server/app.py:109-115`.
- [WARN] Cloud provider gating is advisory; `ALLOW_CLOUD_PROVIDERS` errors are logged but do not block provider calls. Evidence: `guardian/core/config.py:16-27, 172-197`, `guardian/workers/chat_worker.py:94-102`, `guardian/core/ai_router.py:47-74`.
- [WARN] Configuration is split across `guardian/core/config.py` and `guardian/config/core.py` with different provider lists and vector-store settings. Evidence: `guardian/core/config.py:16-197`, `guardian/config/core.py:8-226`.
- [WARN] A hardcoded API key is present in docker-compose and injected into frontend builds. Evidence: `docker-compose.yml:287,621`, `frontend/src/main.tsx:35-40`.

## System Overview
Project purpose (per README): local-first AI conversation and knowledge management platform with RAG, semantic memory, and multi-provider LLM orchestration, prioritizing data sovereignty. Evidence: `README.md:20-34`.

Major subsystems observed:
- Frontend web UI (React/Vite): `frontend/src/main.tsx:1-81`, `frontend/src/vite.config.ts:6-205`.
- Backend API (FastAPI): `guardian/guardian_api.py:315-389`.
- Chat + threads + memory: `guardian/routes/chat.py:323-783`, `guardian/routes/memory.py:55-242`.
- Workers and queues: `guardian/workers/chat_worker.py:1-260`, `guardian/queue/redis_queue.py:17-112`, `docker-compose.yml:480-605`.
- Data layer: Postgres, Redis, Neo4j, vector store, SQLite memory store, filesystem storage. Evidence: `guardian/core/dependencies.py:212-268`, `guardian/queue/redis_queue.py:17-34`, `guardian/graph/connection.py:11-38`, `guardian/vector/store.py:8-26`, `guardian/memory/query_memory.py:20-179`, `guardian/core/storage.py:166-215`.
- Persona/imprint/system docs: `guardian/routes/imprint.py:80-240`, `guardian/db/models.py:824-935`.
- Plugins/agent system: `guardian/plugins/plugin_loader.py:18-63`, `guardian/agent_task_queue.py:30-205`, `scripts/agent_task_worker.py:139-195`.
- Media and image generation: `guardian/routes/media.py:135-200`, `guardian/image_gen/providers/openai.py:46-61`.
- Federation: `guardian/routes/federation.py:50-259`, `guardian/routes/federation_context.py:121-206`.

Subsystem interaction diagram (observed):
```
Frontend (Vite/React)
  -> Guardian API (FastAPI)
       -> Postgres (chat, memory, persona, docs)
       -> Redis (task queues, task events)
       -> VectorStore (FAISS/Chroma embeddings)
       -> Neo4j (optional graph logging/context)
       -> Media storage (local filesystem by default)
       -> Workers (chat completions, embedding backfill, graph backfill)
```

Subsystem status list:
- Frontend UI: Implemented (app entrypoint + API wiring). Evidence: `frontend/src/main.tsx:28-81`.
- Backend API: Implemented (FastAPI app with routers). Evidence: `guardian/guardian_api.py:315-389`.
- Chat/Threads: Implemented (routes + Postgres backing). Evidence: `guardian/routes/chat.py:323-783`, `guardian/core/dependencies.py:212-236`.
- Workers/Queues: Implemented (chat worker + Redis). Evidence: `guardian/workers/chat_worker.py:1-260`, `guardian/queue/redis_queue.py:17-112`.
- RAG/Memory retrieval: Partial (context assembled but not injected into worker path). Evidence: `guardian/context/broker.py:56-207`, `guardian/workers/chat_worker.py:151-220`.
- Knowledge graph: Partial (optional Neo4j logging/backfill, gated by config). Evidence: `guardian/routes/chat.py:510-546`, `guardian/workers/graph_backfill_worker.py:115-188`.
- Persona/imprint/system docs: Implemented (DB-backed, prompt assembly). Evidence: `guardian/db/models.py:824-935`, `guardian/cognition/system_prompt_builder.py:48-139`.
- Plugins/agents: Partial (manifest loader + queue exist, but no orchestrated runtime). Evidence: `guardian/plugins/plugin_loader.py:18-63`, `scripts/agent_task_worker.py:139-195`.
- Documents/share/collab: Partial (routers exist but DB config not wired in main app). Evidence: `guardian/routes/documents.py:46-60`, `guardian/guardian_api.py:378-381`.
- Media/image/TTS: Partial (OpenAI image gen works; local/stability providers are placeholders). Evidence: `guardian/image_gen/providers/openai.py:46-61`, `guardian/image_gen/providers/local.py:14-27`, `guardian/image_gen/providers/stability.py:14-27`.
- Federation: Stubbed/Partial (configure_federation not called in main app). Evidence: `guardian/routes/federation.py:50-93`, `guardian/guardian_api.py:378-381`.

## Architecture & Module Map

### Frontend UI (React/Vite)
- Purpose: browser UI and API client wiring for the Guardian backend.
- Key modules/files: `frontend/src/main.tsx:1-81`, `frontend/src/vite.config.ts:6-205`.
- Public interfaces: Vite dev server and `/api` proxy; runtime API base/key in `GuardianAPI`.
- Critical invariants/assumptions: API base and `X-API-Key` header must be provided by env or proxy for protected endpoints. Evidence: `frontend/src/main.tsx:28-41`, `frontend/src/vite.config.ts:25-170`.
- Implementation status: Implemented (entrypoint renders app and configures API client). Evidence: `frontend/src/main.tsx:28-81`.

### Backend API (Guardian FastAPI)
- Purpose: central API surface for chat, memory, tools, connectors, and media.
- Key modules/files: `guardian/guardian_api.py:315-389`, `guardian/core/dependencies.py:51-268`, `guardian/routes/*`.
- Public interfaces: HTTP routes in `guardian/routes`, SSE events at `/api/events`. Evidence: `guardian/guardian_api.py:352-455`.
- Critical invariants/assumptions: environment chain must load before DB init; chatlog DB must be initialized before routes import. Evidence: `guardian/guardian_api.py:90-175`.
- Implementation status: Implemented (app created and routers included). Evidence: `guardian/guardian_api.py:315-389`.

### Chat + Threads + Memory
- Purpose: thread creation, message storage, completion task enqueue, memory silos.
- Key modules/files: `guardian/routes/chat.py:323-783`, `guardian/routes/memory.py:55-242`, `guardian/core/pgdb.py:65-260`, `guardian/db/models.py:72-201`.
- Public interfaces: `/chat/*`, `/threads/*`, `/api/memory/*`. Evidence: `guardian/routes/chat.py:323-783`, `guardian/routes/memory.py:76-242`.
- Critical invariants/assumptions: Postgres DSN is configured; vector store is available for embeddings. Evidence: `guardian/core/dependencies.py:212-268`, `guardian/routes/chat.py:141-160`.
- Implementation status: Implemented (routes wired and Postgres-backed). Evidence: `guardian/core/dependencies.py:212-236`, `guardian/routes/chat.py:323-655`.

### Worker Pipeline (Chat + Backfill)
- Purpose: async completions and embedding/graph backfills.
- Key modules/files: `guardian/workers/chat_worker.py:1-260`, `guardian/workers/embedding_backfill_worker.py:1-239`, `guardian/workers/graph_backfill_worker.py:115-188`, `guardian/queue/redis_queue.py:17-112`.
- Public interfaces: Redis queues `codexify:queue:chat` and task event streams. Evidence: `guardian/queue/redis_queue.py:17-112`, `guardian/queue/task_events.py:14-75`.
- Critical invariants/assumptions: Redis reachable, vector store configured, DB DSN set. Evidence: `guardian/workers/chat_worker.py:33-80`, `guardian/workers/embedding_backfill_worker.py:81-93`.
- Implementation status: Implemented (workers present and docker-compose services defined). Evidence: `docker-compose.yml:480-605`.

### Model Routing and Providers
- Purpose: route LLM calls between local, Groq, and OpenAI endpoints.
- Key modules/files: `guardian/core/ai_router.py:47-245`, `guardian/core/config.py:16-197`, `guardian/core/dependencies.py:311-429`.
- Public interfaces: `chat_with_ai`, `call_local`, `call_groq`, `call_openai`, `_groq_complete`. Evidence: `guardian/core/ai_router.py:47-74`, `guardian/core/dependencies.py:311-405`.
- Critical invariants/assumptions: provider API keys set, local base URL configured. Evidence: `guardian/core/config.py:67-96`.
- Implementation status: Implemented for local/groq/openai; Partial for other providers referenced elsewhere (gemini/anthropic in `guardian/config/core.py`). Evidence: `guardian/core/ai_router.py:47-74`, `guardian/config/core.py:112-115`.

### Persona/Imprint/System Docs
- Purpose: store persona and imprint data and build system prompts.
- Key modules/files: `guardian/db/models.py:824-935`, `guardian/cognition/imprints/store.py:22-122`, `guardian/cognition/personas/store.py:22-116`, `guardian/cognition/system_prompt_builder.py:48-139`, `guardian/cognition/prompts.py:12-160`.
- Public interfaces: `/api/imprint/*`, `/api/system_docs/*`. Evidence: `guardian/routes/imprint.py:80-240`.
- Critical invariants/assumptions: DSN configured for SQLAlchemy stores; user/project must be resolved from thread or request. Evidence: `guardian/cognition/imprints/store.py:22-36`, `guardian/routes/imprint.py:35-53`.
- Implementation status: Implemented (DB-backed and used in prompt assembly). Evidence: `guardian/cognition/system_prompt_builder.py:48-83`.

### RAG and Context Assembly
- Purpose: assemble semantic/memory/graph context for completions.
- Key modules/files: `guardian/context/broker.py:12-207`, `guardian/vector/store.py:8-26`, `backend/rag/embedder.py:59-183`, `guardian/memoryos/retriever.py:12-107`.
- Public interfaces: `ContextBroker.assemble` used by chat worker. Evidence: `guardian/workers/chat_worker.py:151-167`.
- Critical invariants/assumptions: `LOCAL_EMBED_MODEL` is an absolute path; vector store is initialized at startup. Evidence: `guardian/utils/embed_paths.py:7-19`, `guardian/core/dependencies.py:260-268`.
- Implementation status: Partial (context assembled, but main worker does not inject actual context into LLM messages). Evidence: `guardian/workers/chat_worker.py:151-220`, `guardian/cognition/prompts.py:98-116`.

### Knowledge Graph (Neo4j)
- Purpose: optional graph logging and context retrieval.
- Key modules/files: `guardian/graph/connection.py:11-38`, `guardian/routes/chat.py:510-546`, `guardian/context/broker.py:325-378`, `guardian/workers/graph_backfill_worker.py:115-188`.
- Public interfaces: backfill worker, optional graph context in `ContextBroker`.
- Critical invariants/assumptions: `GUARDIAN_ENABLE_GRAPH_LOGGING` and `GUARDIAN_ENABLE_GRAPH_CONTEXT` must be enabled; Neo4j driver available. Evidence: `guardian/guardian_api.py:165-219`, `guardian/context/broker.py:122-135`.
- Implementation status: Partial (gated by config and optional dependencies). Evidence: `guardian/routes/chat.py:510-546`.

### Plugins and Agent Orchestration
- Purpose: plugin manifest discovery and agent task execution via Redis and HTTP plugin endpoints.
- Key modules/files: `guardian/plugins/plugin_loader.py:18-63`, `guardian/plugin_manager.py:85-197`, `guardian/agent_task_queue.py:30-205`, `scripts/agent_task_worker.py:139-195`, `guardian/guardian_loop.py:118-197`.
- Public interfaces: `/dev/plugins`, `/dev/delegate`, agent worker CLI. Evidence: `guardian/routes/devtools.py:58-108`, `scripts/agent_task_worker.py:139-195`.
- Critical invariants/assumptions: Redis available, plugin manifests present, worker running.
- Implementation status: Partial/Stubbed (manifest listing exists; SafePluginManager is not wired; agent worker not part of docker-compose). Evidence: `guardian/routes/devtools.py:58-71`, `docker-compose.yml` (no agent worker), `guardian/plugin_manager.py:85-197`.

### Documents/Share/Collaboration
- Purpose: autosave docs, share links, real-time collaboration.
- Key modules/files: `guardian/routes/documents.py:46-180`, `guardian/routes/share.py:50-180`, `guardian/realtime/collaboration.py:33-194`, `guardian/core/db.py:1-100`.
- Public interfaces: `/api/documents/autosave`, `/api/share/*`, `/api/collab/*`.
- Critical invariants/assumptions: `configure_db` must be called to set `GuardianDB` for these routers. Evidence: `guardian/routes/documents.py:46-60`, `guardian/routes/share.py:50-64`, `guardian/realtime/collaboration.py:33-59`.
- Implementation status: Partial (routers included but not configured in main app). Evidence: `guardian/guardian_api.py:378-381`, `guardian/server/app.py:109-115`.

### Media/Image/TTS
- Purpose: upload media, track AI-generated images/docs, TTS.
- Key modules/files: `guardian/routes/media.py:135-200`, `guardian/core/storage.py:166-215`, `guardian/image_gen/router.py:59-87`, `guardian/image_gen/providers/openai.py:46-61`, `guardian/audio/tts_trigger.py:22-35`.
- Public interfaces: `/api/media/*`.
- Critical invariants/assumptions: storage backend configured; DB URL set. Evidence: `guardian/routes/media.py:120-127`, `guardian/core/storage.py:166-215`.
- Implementation status: Partial (OpenAI provider works; local/stability image gen are placeholders). Evidence: `guardian/image_gen/providers/local.py:14-27`, `guardian/image_gen/providers/stability.py:14-27`, `guardian/image_gen/providers/openai.py:46-61`.

### Federation
- Purpose: cross-node collaboration and federated context retrieval.
- Key modules/files: `guardian/routes/federation.py:50-259`, `guardian/routes/federation_context.py:121-206`.
- Public interfaces: `/api/federation/*`, `/api/federation/context/*`.
- Critical invariants/assumptions: `configure_federation()` must be called with node keys and relay endpoint. Evidence: `guardian/routes/federation.py:50-93`.
- Implementation status: Stubbed/Partial (configuration not wired in main app). Evidence: `guardian/routes/federation.py:50-93`, `guardian/guardian_api.py:378-381`.

## Data, Memory, and Retrieval Pipeline

### 6.1 Storage inventory (reality-first)
- PostgreSQL (chatlog DB via PgDB): stores chat threads/messages, memory entries, projects, and event outbox. Ingest via chat routes and memory routes; queries via ChatDB methods. Retention: memory pruning uses `MEMORY_RETENTION_DAYS` for midterm. Status: Implemented. Evidence: `guardian/core/dependencies.py:212-236`, `guardian/db/models.py:72-201`, `guardian/routes/memory.py:55-69`.
- PostgreSQL (GuardianDB layer): stores documents, media, share links, collaboration records, etc. Ingest via documents/share/media routes; queries via ORM sessions. Retention: no explicit retention rules in code. Status: Partial (not wired in main app). Evidence: `guardian/core/db.py:1-100`, `guardian/routes/documents.py:63-180`, `guardian/routes/share.py:67-179`, `guardian/routes/media.py:120-188`.
- Redis: task queues and task event streams for chat and agent tasks. Ingest via `enqueue`; query via `dequeue` and stream readers. Retention: task status uses TTL; queues are not bounded. Status: Implemented. Evidence: `guardian/queue/redis_queue.py:17-132`, `guardian/queue/task_events.py:14-75`, `guardian/agent_task_queue.py:109-137`.
- Neo4j: optional knowledge graph storage of user/thread/message nodes. Ingest via chat_post_message and graph backfill worker; query via ContextBroker graph context. Retention: no explicit retention. Status: Partial (gated). Evidence: `guardian/routes/chat.py:510-546`, `guardian/workers/graph_backfill_worker.py:115-188`, `guardian/context/broker.py:325-378`.
- Vector store (FAISS/Chroma): semantic embeddings for chat messages. Ingest via `chat_post_message` auto-embed and embedding backfill worker; query via `ContextBroker._search_semantic`. Persistence: FAISS in-memory only; Chroma persisted under `./.chroma` when enabled. Status: Implemented. Evidence: `guardian/routes/chat.py:141-160, 475-476`, `guardian/vector/store.py:8-26`, `backend/rag/embedder.py:97-183`.
- SQLite memory store: `guardian/memory/store.db` for generic memory queries. Ingest not wired from API routes; queried via helper functions. Retention: none explicit. Status: Partial. Evidence: `guardian/memory/query_memory.py:20-179`.
- Local filesystem: media files stored under `/app/media` by default; backfill status snapshots in `guardian/logs/*.json`; Chroma persistence under `./.chroma`. Status: Implemented. Evidence: `guardian/core/storage.py:166-215`, `guardian/workers/backfill_status.py:36-101`, `backend/rag/embedder.py:66-107`.

### 6.2 RAG / retrieval pipeline (if present)
- Ingestion/chunking: chat messages are embedded as whole strings (no chunking), stored via `VectorStore.add_texts`. Status: Implemented. Evidence: `guardian/routes/chat.py:141-160`, `guardian/vector/store.py:16-22`.
- Embedding: SentenceTransformers local-only embedder; requires `LOCAL_EMBED_MODEL` absolute path; supports FAISS or Chroma. Status: Implemented. Evidence: `backend/rag/embedder.py:59-108`, `guardian/utils/embed_paths.py:7-19`.
- Retrieval: `ContextBroker._search_semantic` uses vector store search with top-k; no per-user or project filtering is applied. Status: Partial. Evidence: `guardian/context/broker.py:236-246`.
- Prompt construction: main chat worker uses `build_guardian_system_prompt` which only adds RAG hints, not the retrieved content. Full context injection exists in `_groq_complete` but is only used by the simple chat endpoint. Status: Partial/Stubbed. Evidence: `guardian/workers/chat_worker.py:151-220`, `guardian/cognition/prompts.py:98-116`, `guardian/core/dependencies.py:343-405`, `guardian/routes/chat.py:909-939`.
- Persona-aware retrieval: not implemented beyond hints; retrieval does not filter by persona or user_id. Status: Partial. Evidence: `guardian/context/broker.py:122-135, 236-246`, `guardian/cognition/prompts.py:98-116`.

Local-first evaluation:
- Embeddings are local by default (SentenceTransformers, FAISS/Chroma). Status: Implemented. Evidence: `backend/rag/embedder.py:59-108`.
- LLM completions can be local or cloud; cloud gating is advisory and can be bypassed if provider is set. Status: Partial. Evidence: `guardian/core/config.py:16-27`, `guardian/workers/chat_worker.py:94-102`, `guardian/core/ai_router.py:47-74`.

## Persona, Agent, and Model Routing Layer
- Personas/imprints/system docs: stored in Postgres tables and used to build the system prompt. Status: Implemented. Evidence: `guardian/db/models.py:824-935`, `guardian/cognition/system_prompt_builder.py:48-83`.
- Persona state effects:
  - Prompt templates: injected via `build_guardian_system_prompt` and `get_guardian_system_prompt`. Status: Implemented. Evidence: `guardian/cognition/system_prompt_builder.py:48-83`, `guardian/cognition/prompts.py:119-160`.
  - Memory/retrieval scope: no explicit filtering in vector search; only hints in prompt. Status: Partial. Evidence: `guardian/context/broker.py:236-246`, `guardian/cognition/prompts.py:98-116`.
  - Model routing: provider selected from task/provider settings. Status: Implemented. Evidence: `guardian/workers/chat_worker.py:87-104`, `guardian/core/ai_router.py:47-74`.
- Agent orchestration:
  - Guardian loop proposes tasks and enqueues them. Status: Partial. Evidence: `guardian/guardian_loop.py:118-197`.
  - Agent task queue and worker exist, but worker is not wired in docker-compose. Status: Partial. Evidence: `guardian/agent_task_queue.py:30-205`, `scripts/agent_task_worker.py:139-195`, `docker-compose.yml` (no agent worker).
- Safety/Guardian policy layers:
  - System prompt includes non-negotiable safety rules and instruction to avoid fabrication. Status: Implemented. Evidence: `guardian/cognition/prompts.py:12-25`.
- Implementation status: Persona/prompt assembly is Implemented; agent routing is Partial; model routing is Implemented for local/groq/openai and Partial for other providers. Evidence: `guardian/workers/chat_worker.py:151-220`, `guardian/core/ai_router.py:47-74`, `guardian/config/core.py:112-115`.

## Security, Privacy, and Sovereignty

### 8.1 Secrets management
- Environment loading order: `.env`, `.env.backend.{mode}`, `.env.local`. Status: Implemented. Evidence: `guardian/core/dependencies.py:51-70`.
- Env templates exist for secrets and DB URLs. Status: Implemented. Evidence: `.env.example:1-94`, `.env.template:1-30`.
- Hardcoded API key in docker-compose and frontend env injection. Status: Implemented. Evidence: `docker-compose.yml:287,621`, `frontend/src/main.tsx:35-40`.
- API key fallback allows `changeme` when no key is configured. Status: Implemented. Evidence: `guardian/core/dependencies.py:78-81, 164-174`.

### 8.2 Data egress map (code-evidenced)
| Outbound call site | Destination | Data classes sent | Controls/gates | Risk |
| --- | --- | --- | --- | --- |
| `guardian/core/ai_router.py:115-245` | `LOCAL_BASE_URL`, `GROQ_BASE_URL`, `OPENAI_BASE_URL` | Chat messages (prompts), model selection | Provider chosen by `LLM_PROVIDER`; `ALLOW_CLOUD_PROVIDERS` errors are logged but not enforced. Evidence: `guardian/workers/chat_worker.py:94-102` | [RISK] |
| `guardian/core/dependencies.py:417-429` | `https://api.groq.com/openai/v1` (or `GROQ_BASE_URL`) | Chat messages + optional context bundle | Requires `GROQ_API_KEY`; used by `/chat` simple endpoint. Evidence: `guardian/routes/chat.py:909-939` | [WARN] |
| `guardian/connectors/github.py:11-70` | `https://api.github.com` | Repo issues/PRs, optional token | Connector config; uses token if provided | [WARN] |
| `guardian/image_gen/providers/openai.py:46-61` | OpenAI images API | Image prompt + model + size | Requires `IMAGE_GEN_PROVIDER=openai` and OpenAI API key | [WARN] |
| `guardian/audio/tts_trigger.py:22-35` | Plugin endpoint from manifest | TTS text + metadata | Only if a plugin with `tts` capability is discovered | [WARN] |
| `guardian/routes/federation.py:183-189` | Peer node `/api/federation/manifest` | Manifest fetch (peer URL only) | Federation must be configured; not wired in main app | [WARN] |

### 8.3 Access control / multi-user considerations
- API key auth is inconsistent; many core routes do not require `require_api_key`. Status: Implemented. Evidence: `guardian/routes/chat.py:432-655, 746-783`, `guardian/routes/memory.py:87-180`, `guardian/routes/media.py:135-200`, `guardian/routes/devtools.py:34-108`.
- User identity defaults to "default" and can be supplied via `X-User-Id` without authentication, so tenancy boundaries are weak. Status: Implemented. Evidence: `guardian/routes/memory.py:43-53`, `guardian/core/dependencies.py:194-199`.
- Explicit `/api/chat` alias bypasses auth by passing `api_key="api-bypass"`. Status: Implemented. Evidence: `guardian/routes/chat.py:1053-1056`.

## Docs vs Code Consistency
Doc claims that do not match code:
- Docs drift: README claims multi-provider support including Anthropic and Gemini; main routing only supports local/groq/openai. Evidence: `README.md:31,55`, `guardian/core/ai_router.py:47-74`.
- Docs drift: README claims hybrid DB strategy with Chroma as vector store; default vector store is FAISS (in-memory) with optional Chroma; pgvector code exists but is not wired. Evidence: `README.md:30`, `guardian/vector/store.py:8-15`, `backend/vector_store/factory.py:28-43`.
- Docs drift: README claims connector framework for GitHub, Google Drive, Notion; runtime registry only lists GitHub and other connectors appear incomplete. Evidence: `README.md:48`, `guardian/routes/connectors.py:81-97`, `guardian/connectors/google.py:9-12`.
- Docs drift: README claims multi-silo memory with auto-consolidation; code provides manual memory CRUD with pruning only. Evidence: `README.md:46`, `guardian/routes/memory.py:55-180`.

Code paths not described in docs:
- Code drift: SSE outbox event stream at `/api/events`. Evidence: `guardian/guardian_api.py:418-455`.
- Code drift: Media upload/image generation routes under `/api/media`. Evidence: `guardian/routes/media.py:135-200`.
- Code drift: Devtools routes for state inspection, plugins, and agent delegation. Evidence: `guardian/routes/devtools.py:34-108`.

## Code Quality, Testing, and DX
- Python tooling: Black, Ruff, isort, mypy configured in `pyproject.toml`. Mypy is non-strict with many error codes disabled. Evidence: `pyproject.toml:68-160`.
- Tests: pytest configured to run `tests/` and ignore `guardian/tests`. Evidence: `pytest.ini:1-12`.
- Frontend tooling: Vite config provides proxy and PWA; uses pnpm in docker-compose. Evidence: `frontend/src/vite.config.ts:6-205`, `docker-compose.yml:606-642`.
- DX scripts: backend entrypoint runs Alembic and uvicorn. Evidence: `backend/entrypoint-dev.sh:33-36`.

## Performance and Scalability
- LLM calls are synchronous HTTP requests; chat worker uses blocking calls to providers. Status: Implemented. Evidence: `guardian/core/ai_router.py:140-245`, `guardian/workers/chat_worker.py:249-260`.
- Embedding runs synchronously in the request path for chat message creation; note in-code comment about sync behavior. Status: Implemented. Evidence: `guardian/routes/chat.py:141-160, 147-151`.
- FAISS backend is in-memory only; Chroma persistence requires explicit config; scaling to large datasets likely needs a persistent vector store. Status: Partial. Evidence: `backend/rag/embedder.py:97-183`, `guardian/vector/store.py:8-15`.
- Suggested optimizations (not implemented): background embedding tasks, batching vector search, and caching frequently used embeddings. Status: Planned.

## Risk Register & Recommendations
| ID | Area | Description | Impact | Likelihood | Effort | Suggested Next Action | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Auth | Core chat routes lack API key enforcement and `/api/chat` alias bypasses auth. | High | High | Medium | Add `Depends(require_api_key)` to all chat routes and remove `api-bypass` path. | `guardian/routes/chat.py:432-655, 746-783, 1053-1056` | Implemented |
| R2 | Auth | Memory, media, and devtools routes lack auth or rely on `X-User-Id` only. | High | High | Medium | Require API key or user auth; gate devtools to debug builds only. | `guardian/routes/memory.py:87-180`, `guardian/routes/media.py:135-200`, `guardian/routes/devtools.py:34-108` | Implemented |
| R3 | Persistence | Documents/share/collab routers require `configure_db` but main app never calls it. | Medium | High | Medium | Wire `GuardianDB` in `guardian_api` or remove these routers until configured. | `guardian/routes/documents.py:46-60`, `guardian/routes/share.py:50-64`, `guardian/realtime/collaboration.py:33-59`, `guardian/guardian_api.py:378-381` | Partial |
| R4 | RAG | ContextBroker results are not injected into main worker completions. | Medium | High | Medium | Inject semantic/memory/graph context in worker path (similar to `_groq_complete`). | `guardian/workers/chat_worker.py:151-220`, `guardian/cognition/prompts.py:98-116`, `guardian/core/dependencies.py:343-405` | Partial |
| R5 | Sovereignty | `ALLOW_CLOUD_PROVIDERS` is advisory; worker logs errors but continues with cloud providers. | Medium | Medium | Low | Fail fast when cloud providers are disallowed; enforce in `chat_worker`. | `guardian/core/config.py:16-27, 172-197`, `guardian/workers/chat_worker.py:94-102` | Implemented |
| R6 | Config | Duplicate settings modules cause provider/vector-store drift. | Medium | Medium | Medium | Consolidate settings into one module and update imports. | `guardian/core/config.py:16-197`, `guardian/config/core.py:8-226` | Partial |
| R7 | Vector store | Multiple vector-store implementations (pgvector factory, in-memory stub, active VectorStore) are inconsistent. | Medium | Medium | Medium | Choose a single vector store API and remove/merge the others. | `guardian/vector/store.py:8-26`, `backend/vector_store/factory.py:28-43`, `guardian/vector_store.py:26-60` | Partial |
| R8 | Federation | Federation routes are included but not configured; requests will fail. | Low | Medium | Medium | Add configuration in startup or remove routes until ready. | `guardian/routes/federation.py:50-93`, `guardian/guardian_api.py:378-381` | Stubbed |
| R9 | Plugins/Agents | Agent worker is not wired and SafePluginManager is unused; plugin execution is not integrated. | Medium | Medium | Medium | Add agent worker service and integrate plugin execution in runtime; document plugin entrypoints. | `scripts/agent_task_worker.py:139-195`, `guardian/plugin_manager.py:85-197`, `docker-compose.yml` | Partial |
| R10 | Secrets | Hardcoded API key in docker-compose and injected into frontend. | Medium | High | Low | Move keys to `.env` and document rotation; avoid committing real values. | `docker-compose.yml:287,621`, `frontend/src/main.tsx:35-40` | Implemented |
| R11 | Dependencies | `memoryos` is imported but not declared in dependencies; CLI/orchestrator may fail. | Medium | Medium | Medium | Add explicit dependency or vendor the module; guard imports in runtime paths. | `guardian/core/client_factory.py:5-9`, `pyproject.toml:8-64` | Partial |
| R12 | Performance | Message embedding is synchronous in request path. | Low | Medium | Medium | Move embedding to background worker or async task queue. | `guardian/routes/chat.py:141-160` | Implemented |

Prioritized roadmap:
- Phase 1: Critical fixes
  - Enforce API key/auth across all routes; remove `/api/chat` bypass and devtools exposure.
  - Wire `GuardianDB` configuration for documents/share/collab or remove routes until ready.
  - Enforce `ALLOW_CLOUD_PROVIDERS` in the chat worker to prevent unintended egress.
  - Inject actual RAG context into worker completions or disable RAG hints until it is real.

- Phase 2: Important improvements
  - Consolidate configuration modules and align provider settings.
  - Unify vector store implementations and decide on FAISS vs Chroma vs pgvector.
  - Add persona-aware retrieval filters (user_id/project_id) in `ContextBroker`.

- Phase 3: Nice-to-have refinements
  - Finish federation wiring and trust registry flows.
  - Integrate agent worker into docker-compose and document plugin lifecycle.
  - Expand connector support beyond GitHub with tested OAuth storage.

## Model Notes
- Agent/Model: Codex (GPT-5 per runtime instruction).
- Tooling limitations: network access restricted; tests and runtime services not executed.
- Planned/stubbed areas observed: `guardian/vector_store.py` (in-memory stub), `guardian/core/orchestrator/context_runtime.py` (undefined variables), `guardian/connectors/google.py` (imports missing modules), local/stability image providers return placeholder images. Evidence: `guardian/vector_store.py:26-60`, `guardian/core/orchestrator/context_runtime.py:1-11`, `guardian/connectors/google.py:9-12`, `guardian/image_gen/providers/local.py:14-27`, `guardian/image_gen/providers/stability.py:14-27`.
