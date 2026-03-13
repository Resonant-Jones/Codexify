Purpose: Give senior engineers the operational truth needed to run, debug, and change Codexify safely, with special attention to config precedence, worker dependencies, and failure signatures.
Last updated: 2026-03-11
Source anchors:
- Makefile
- package.json
- frontend/src/package.json
- docker-compose.yml
- guardian/guardian_api.py
- guardian/core/
- guardian/config/
- guardian/routes/
- guardian/command_bus/
- src-tauri/
- frontend/src/
- tests/

# Config and Ops

## Primary Environment Variables

### Server and auth

| Variable | Current behavior | Anchors |
|---|---|---|
| `GUARDIAN_API_KEY` | Required at backend startup; app fails fast if absent | `guardian/guardian_api.py` |
| `GUARDIAN_API_KEYS` | Optional additional accepted API keys | `guardian/core/dependencies.py`, `guardian/core/config.py` |
| `GUARDIAN_EXPOSURE_MODE` | Defaults to `local_safe`; can force public-facing restrictions | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py` |
| `GUARDIAN_AUTH_MODE` | Defaults to local auth unless exposure mode or remote settings require otherwise | `guardian/core/dependencies.py` |
| `GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET` | Needed for remote/session/JWT flows | `guardian/core/dependencies.py` |
| `GUARDIAN_ALLOWED_ORIGINS` | CORS allowlist consumed at app startup | `guardian/core/dependencies.py`, `guardian/guardian_api.py` |
| `CODEXIFY_SINGLE_USER_ID` | Default subject in single-user mode | `guardian/core/dependencies.py` |

### Database, queues, and event transport

| Variable | Current behavior | Anchors |
|---|---|---|
| `GUARDIAN_DATABASE_URL`, `DATABASE_URL` | Postgres DSN for the primary DB adapter and migrations | `guardian/core/dependencies.py`, `guardian/core/db.py`, `guardian/db/migrations/env.py` |
| `REDIS_URL` | Defaults to `redis://redis:6379/0` | `guardian/queue/redis_queue.py` |
| `CHAT_TURN_LOCK_TTL_SECONDS` | Defaults to `300` seconds | `guardian/queue/redis_queue.py` |
| `CHAT_EMBED_QUEUE_NAME` | Defaults to `codexify:queue:chat-embed` | `guardian/queue/redis_queue.py` |
| document embed queue env | Defaults to `codexify:queue:document-embed` through queue module constants | `guardian/queue/document_embed_queue.py` |
| cron queue env | Defaults to `codexify:queue:cron` through scheduler/worker constants | `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py` |
| outbox envs | Poll interval, batch size, and tenant semantics are parsed defensively for `/api/events` | `guardian/core/outbox.py`, `guardian/guardian_api.py` |

### Providers and model routing

| Variable | Current behavior | Anchors |
|---|---|---|
| `LLM_PROVIDER` | Canonical provider default in core settings; defaults to `local` | `guardian/core/config.py` |
| `ALLOW_CLOUD_PROVIDERS` | Default `false`; used with egress policy to gate cloud providers | `guardian/core/config.py`, `guardian/core/egress.py` |
| `CODEXIFY_LOCAL_ONLY_MODE` | Default `true`; keeps the system local-first unless explicitly relaxed | `guardian/core/config.py`, `guardian/core/egress.py` |
| `CODEXIFY_EGRESS_ALLOWLIST` | Explicit outbound allowlist when non-local access is permitted | `guardian/core/config.py`, `guardian/core/egress.py` |
| `LOCAL_BASE_URL`, `LOCAL_API_KEY`, `LOCAL_CHAT_MODEL`, `LOCAL_EMBED_MODEL` | Local provider connectivity and model selection | `guardian/core/config.py`, `guardian/core/ai_router.py`, `docker-compose.yml` |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL` | OpenAI execution path | `guardian/core/config.py`, `guardian/core/ai_router.py` |
| `GROQ_API_KEY`, `GROQ_BASE_URL` | Groq execution path | `guardian/core/config.py`, `guardian/core/ai_router.py` |
| `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` | Minimax execution path | `guardian/core/config.py`, `guardian/core/ai_router.py` |
| `LLM_REQUEST_TIMEOUT_SECONDS` | Global timeout shaping for provider calls | `guardian/core/config.py`, `guardian/core/ai_router.py` |

### Storage, media, and embeddings

| Variable | Current behavior | Anchors |
|---|---|---|
| `CODEXIFY_VECTOR_STORE` | Selects vector backend in the general vector abstraction | `guardian/vector/store.py` |
| `CODEXIFY_CHROMA_PATH` | Local Chroma persistence path | `guardian/runtime/embed/embedder.py`, `docker-compose.yml` |
| `CODEXIFY_COLLECTION` | Chroma collection name | `guardian/runtime/embed/embedder.py` |
| storage backend envs | Storage factory can target local filesystem, S3, or GCS | `guardian/core/storage.py` |
| `GUARDIAN_MEDIA_URL_SECRET` | Signs `/media/*` URLs | `guardian/core/media_signing.py` |

### Federation, graph, and command bus

| Variable | Current behavior | Anchors |
|---|---|---|
| `GUARDIAN_ENABLE_GRAPH_CONTEXT` | Enables graph snippets during context assembly | `guardian/context/broker.py`, `guardian/core/config.py` |
| `GUARDIAN_FEDERATION_ENABLED` | Master feature gate for federation routes | `guardian/routes/federation.py`, `guardian/core/config.py` |
| trust policy envs | Signed policy, node allowlist, and federation auth requirements are env-driven | `guardian/routes/federation.py`, `guardian/core/config.py` |
| `GUARDIAN_COMMAND_BUS_LOOPBACK_BASE` | Base URL for command bus loopback execution | `guardian/command_bus/loopback_http_adapter.py`, `docker-compose.yml` |
| WebSocket rate-limit envs | Guard `/api/ws/rpc` connection and payload behavior | `guardian/routes/websocket.py`, `guardian/core/config.py` |

### Frontend and desktop runtime

| Variable | Current behavior | Anchors |
|---|---|---|
| `VITE_PROXY_TARGET` | Frontend dev proxy target in Compose | `docker-compose.yml` |
| desktop backend/share envs | Tauri can inject backend/share base URLs at runtime | `src-tauri/src/commands.rs`, `frontend/src/lib/runtimeConfig.ts` |
| browser-stored overrides | Desktop/web runtime can be overridden by local storage keys | `frontend/src/lib/runtimeConfig.ts` |

## Config Resolution Order and Defaults

1. `guardian/guardian_api.py` imports `guardian.core.dependencies` and explicitly loads dotenv files through `_load_env_chain()`.
2. `_load_env_chain()` attempts to read, in order:
   - `.env`
   - `.env.backend.{GUARDIAN_ENV|development}`
   - `.env.local`
3. Each dotenv file loads with `override=False`.
   - Practical result: existing `os.environ` wins, and earlier dotenv layers can block later dotenv layers from overriding the same key.
4. `guardian/core/config.py` then materializes canonical settings through Pydantic.
5. `assert_config_coherence()` compares canonical settings against legacy settings in `guardian/config/core.py`.
6. `CODEXIFY_CONFIG_SOURCE` controls how strict that reconciliation is, with `strict` as the default in `guardian/core/config.py`.

Operational consequence:
- Config is not yet single-source. A safe config change should be checked against both `guardian/core/config.py` and `guardian/config/core.py`.

Unverified:
- The full precedence matrix across every deployment mode is not exhaustively documented in-repo; `tests/core/test_config_coherence.py` is the best current verification anchor.

## Local Dev Run Commands

### Main entry points

- Full stack with containers:
  - `docker compose up --build`
- Backend app:
  - `uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8888`
- Packaged backend entrypoint:
  - `guardian-api`
- Frontend:
  - `pnpm --dir frontend/src install`
  - `pnpm --dir frontend/src dev`
- Desktop shell:
  - `make desktop-dev`
  - `make desktop-build`

### Checks and tests

- Python test suite:
  - `make test`
- Python lint/type checks:
  - `make lint`
- Frontend lint:
  - `pnpm lint`
- Frontend tests:
  - `pnpm test`
- Docs build:
  - `make docs`

## Healthchecks and Diagnostics

- `GET /ping`
- `GET /health`
- `GET /health/llm`
- `GET /health/chat`
- `GET /health/memory`
- `GET /api/llm/catalog`
- `GET /metrics`
- `GET /api/tasks/{task_id}/events`
- `GET /api/events`
- command bus run stream:
  - `GET /api/guardian/commands/runs/{run_id}/events`

Primary anchors:
- `guardian/routes/health.py`
- `guardian/guardian_api.py`
- `guardian/routes/command_bus.py`

## Logging and Observability

- API requests get request IDs through middleware, and both HTTP and unhandled exception responses include `request_id`.
- Worker processes log with subsystem-specific prefixes and emit task lifecycle signals through Redis task events.
- `/metrics` exists and Prometheus setup is initialized during app startup.
- Command bus and websocket paths have explicit event/audit storage rather than relying only on console logs.
- Structured JSON logger setup is `Unverified`; the scanned startup path used stdlib logging plus subsystem-specific log messages.

## Common Failure Signatures

| Symptom | Likely cause | Where to look |
|---|---|---|
| Backend exits immediately on boot | `GUARDIAN_API_KEY` missing or config coherence failure | `guardian/guardian_api.py`, `guardian/core/config.py` |
| `POST /api/chat/{id}/complete` returns `503` | Redis unavailable or queue enqueue failure | `guardian/routes/chat.py`, `guardian/queue/redis_queue.py` |
| Completion task starts but no answer arrives | chat worker down, provider timeout, or provider connectivity issue | `guardian/workers/chat_worker.py`, `guardian/core/ai_router.py`, Compose worker logs |
| Provider appears selectable but fails at runtime | catalog/runtime mismatch for provider support | `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py` |
| Document upload succeeds but never becomes searchable | parse failure, embed enqueue failure, or embed worker failure | `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py` |
| Command bus run stays `blocked` | policy decision, write-lane restriction, or loopback recursion guard | `guardian/command_bus/invoke.py`, `guardian/routes/tools.py` |
| Cron run is queued but never finishes | scheduler/worker split or Redis issue | `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py` |
| Federation endpoints reject requests with `403` or `503` | feature flag disabled, trust policy invalid, or egress disallowed | `guardian/routes/federation.py`, `guardian/core/egress.py` |
| Live UI events stop after restart | relying on process-local sync/event fanout path | `guardian/sync/bus.py`, `guardian/core/event_bus.py` |

## Testing Reality

- Python tests cover:
  - startup and config coherence
  - chat routes and worker behavior
  - command bus and tools
  - federation and realtime layers
  - migrations and storage behavior
- Frontend harnesses exist separately for:
  - Vitest
  - Playwright
  - Cypress
- Golden-path regression for architecture work usually means:
  - boot backend successfully
  - create/send/complete a chat turn
  - upload a document and observe embedding lifecycle
  - invoke a command bus command and inspect run events
