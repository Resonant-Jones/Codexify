# Config and Ops

Purpose: Give senior developers the operational truth needed to run, debug, and harden Codexify without guessing hidden defaults.
Last updated: 2026-02-17
Source anchors:
- guardian/core/dependencies.py
- guardian/core/config.py
- guardian/config/core.py
- guardian/guardian_api.py
- guardian/routes/health.py
- guardian/core/egress.py
- docker-compose.yml
- Makefile
- README.md
- frontend/src/lib/api.ts

## Primary Environment Variables (Grouped)

### Server/Auth boundary

| Variable | Default/behavior | Anchor |
|---|---|---|
| `GUARDIAN_API_KEY` | Required at API startup; process exits if missing | `guardian/guardian_api.py` |
| `GUARDIAN_API_KEYS` | Optional additional static API keys | `guardian/core/dependencies.py`, `guardian/core/config.py` |
| `GUARDIAN_EXPOSURE_MODE` | `local_safe` by default; `public_allowlist` forces remote auth mode | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py` |
| `GUARDIAN_AUTH_MODE` | `local` default; `remote` requires session/JWT tokens | `guardian/core/dependencies.py` |
| `GUARDIAN_SESSION_SECRET` / `GUARDIAN_JWT_SECRET` | Required for remote session/JWT verification | `guardian/core/dependencies.py` |
| `GUARDIAN_ALLOWED_ORIGINS` | Comma-separated CORS origins | `guardian/core/dependencies.py`, `guardian/guardian_api.py` |
| `CODEXIFY_DESKTOP_BACKEND_URL` | Default backend URL for Tauri shell runtime config | `src-tauri/src/commands.rs`, `.env.template` |
| `CODEXIFY_DESKTOP_SHARE_BASE_URL` | Default web share origin used by desktop copy-link flows | `src-tauri/src/commands.rs`, `.env.template` |
| `CODEXIFY_SINGLE_USER_ID` | Canonical user id in single-user mode | `guardian/core/dependencies.py` |

### Data/DB/queues

| Variable | Default/behavior | Anchor |
|---|---|---|
| `GUARDIAN_DATABASE_URL` / `DATABASE_URL` | Postgres DSN used by DB init | `guardian/core/dependencies.py` |
| `REDIS_URL` | `redis://redis:6379/0` fallback | `guardian/queue/redis_queue.py` |
| `CHAT_QUEUE_NAME` | `codexify:queue:chat` | `guardian/workers/chat_worker.py` |
| `DOCUMENT_EMBED_QUEUE_NAME` | `codexify:queue:document-embed` | `guardian/queue/document_embed_queue.py` |
| `CRON_QUEUE_NAME` | `codexify:queue:cron` | `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py` |
| `CHAT_TURN_LOCK_TTL_SECONDS` | 300 seconds default lock ttl | `guardian/queue/redis_queue.py` |

### Providers/models/egress

| Variable | Default/behavior | Anchor |
|---|---|---|
| `LLM_PROVIDER` | `local` default in core settings | `guardian/core/config.py` |
| `ALLOW_CLOUD_PROVIDERS` | `false` default; blocks openai/groq unless enabled | `guardian/core/config.py`, `guardian/core/egress.py` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `true` default; blocks outbound egress | `guardian/core/config.py`, `guardian/core/egress.py` |
| `CODEXIFY_EGRESS_ALLOWLIST` | Empty default; explicit allowlist required when non-local | `guardian/core/config.py`, `guardian/core/egress.py` |
| `LOCAL_BASE_URL`, `LOCAL_API_KEY`, `LOCAL_LLM_MODEL` | Local provider connection/model | `guardian/core/config.py`, `guardian/core/ai_router.py` |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL` | OpenAI provider credentials/endpoint | `guardian/core/config.py`, `guardian/core/ai_router.py` |
| `GROQ_API_KEY`, `GROQ_BASE_URL` | Groq provider credentials/endpoint | `guardian/core/config.py`, `guardian/core/ai_router.py` |
| `LLM_REQUEST_TIMEOUT_SECONDS` | Provider request timeout | `guardian/core/config.py`, `guardian/core/ai_router.py` |

### Vector/storage/ingestion

| Variable | Default/behavior | Anchor |
|---|---|---|
| `CODEXIFY_VECTOR_STORE` | `faiss` in `VectorStore`, often overridden to `chroma` in compose workers | `guardian/vector/store.py`, `docker-compose.yml` |
| `CODEXIFY_CHROMA_PATH` | `./.chroma` default | `guardian/runtime/embed/embedder.py` |
| `CODEXIFY_COLLECTION` | `codexify_vault` default | `guardian/runtime/embed/embedder.py` |
| `LOCAL_EMBED_MODEL` | Expected local embedding model path | `backend/rag/embedder.py`, `docker-compose.yml` |
| `ENABLE_BLIP_MODEL` | Feature flag for optional image model path | `guardian/core/dependencies.py` |

### Federation/graph/websocket/cron

| Variable | Default/behavior | Anchor |
|---|---|---|
| `GUARDIAN_FEDERATION_ENABLED` | Master federation feature gate | `guardian/core/config.py`, `guardian/routes/federation.py` |
| `GUARDIAN_FEDERATION_REQUIRE_SIGNED_POLICY` | Signed trust policy required by default | `guardian/core/config.py`, `guardian/routes/federation.py` |
| `GUARDIAN_FEDERATION_TRUST_POLICY_JSON` + signature fields | Peer allowlist policy source | `guardian/core/config.py`, `guardian/routes/federation.py` |
| `GUARDIAN_ENABLE_GRAPH_CONTEXT` | Enables graph snippets in context broker | `guardian/core/config.py`, `guardian/context/broker.py` |
| `WS_RPC_RATE_LIMIT_*`, `WS_RPC_IDLE_TIMEOUT_SECONDS`, `WS_RPC_MAX_CONNECTIONS` | websocket RPC guards | `guardian/core/config.py`, `guardian/routes/websocket.py` |
| `CRON_SCHEDULER_POLL_SECONDS` | cron tick cadence (default 30s) | `guardian/cron/scheduler.py` |
| `CRON_WEBHOOK_ALLOWLIST` | optional host allowlist for webhook jobs | `guardian/routes/cron.py` |

## Config Resolution Order and Defaults

1. `guardian/guardian_api.py` imports and calls `dependencies._load_env_chain()` before app init.
2. `_load_env_chain()` attempts to load files in this order:
   - `.env`
   - `.env.backend.{GUARDIAN_ENV|development}`
   - `.env.local`
3. Implementation detail: each `load_dotenv(..., override=False)` call preserves existing `os.environ` values.
   - Practical consequence: process env wins, and earlier-loaded dotenv values can prevent later dotenv layers from overriding the same key.
4. Pydantic settings (`guardian/core/config.py`) then read env + `.env` defaults.
5. Coherence checks compare `guardian/core/config.py` with legacy `guardian/config/core.py` depending on `CODEXIFY_CONFIG_SOURCE` (`strict` default).

Unverified:
- Exact precedence interaction between dotenv-loaded values and pydantic `env_file` for every variable in all deployment modes. Verify with controlled env matrix tests in `tests/core/test_config_coherence.py` and runtime print diagnostics.

## Local Dev Run Commands (As Implemented)

- Full stack (recommended):
  - `docker compose up --build`
- Backend only (non-Docker path):
  - `alembic -c backend/alembic.ini upgrade head`
  - `python backend/scripts/seed_defaults.py`
  - `uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8888`
- Frontend only:
  - `pnpm --dir frontend/src install`
  - `pnpm --dir frontend/src dev`
- Desktop shell:
  - `make desktop-dev`
  - `make desktop-build`
- Test/lint entrypoints:
  - `make test`
  - `make lint`
  - `pnpm lint` (root routes to `frontend/src` lint)
- Docs check/build:
  - `make docs`

## Healthchecks and Diagnostics

- Base health: `GET /health`
- Provider health: `GET /health/llm`, `GET /api/health/llm`
- Chat/memory/vector health: `GET /health/chat`, `GET /health/memory`, `GET /health/vector`
- Metrics: `GET /metrics`
- Dependency snapshot: `GET /health/deps`
- Task event stream: `GET /api/tasks/{task_id}/events`
- Domain event stream: `GET /api/events`
- LLM catalog payload: `GET /api/llm/catalog`
- Docker first-response debugging: `docker compose logs backend`

Anchors:
- `guardian/routes/health.py`
- `guardian/guardian_api.py`
- `README.md`

## Logging Conventions and Signal Sources

- API layer uses stdlib logging with request-id middleware and global exception handler returning `request_id` in error body.
  - Anchor: `guardian/guardian_api.py`.
- Workers log with subsystem prefixes (`[chat-worker]`, `[document-embed]`, `[cron-worker]`) and task lifecycle labels.
  - Anchors: `guardian/workers/chat_worker.py`, `guardian/workers/document_embed_worker.py`, `guardian/workers/cron_worker.py`.
- Task progress is dual-channel:
  - Logs + Redis stream events (`task_events.publish`).
  - Anchor: `guardian/queue/task_events.py`.
- Structured JSON logging pipeline is Unverified (no repo-level JSON logger formatter found in scanned startup path).

## Common Failure Signatures

| Symptom | Likely cause | Where to look |
|---|---|---|
| Backend exits on startup with auth error | `GUARDIAN_API_KEY` missing | `guardian/guardian_api.py` |
| `POST /chat/{id}/complete` returns `503 queue_unavailable` | Redis down or unreachable | `guardian/routes/chat.py`, `guardian/queue/redis_queue.py` |
| Completion hangs or fails after enqueue | worker not running or provider/network failure | `guardian/workers/chat_worker.py`, Compose worker services |
| Deep mode silently behaves like normal | project `identity_depth` not allowed for deep | `guardian/routes/chat.py`, `guardian/cognition/identity_policy.py` |
| Document upload returns success but never searchable | parse failed or embed task failed (`embedding_status=failed`) | `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py` |
| Local provider errors mentioning DNS / `.local` names | container cannot resolve hostname | `guardian/core/ai_router.py` (error formatting), `docker-compose.yml` |
| Federation request rejected with 403/503 | federation disabled or trust policy/signature invalid | `guardian/routes/federation.py`, `guardian/core/config.py` |
| Webhook cron run fails immediately | egress denied or target host forbidden | `guardian/routes/cron.py`, `guardian/cron/executor.py`, `guardian/core/egress.py` |
| `/api/events` appears idle while UI expects updates | outbox disabled/misconfigured tenant/polling mismatch | `guardian/guardian_api.py`, `guardian/core/event_bus.py` |
| Websocket RPC closes unexpectedly | auth failure, rate limit, payload too large, or idle timeout | `guardian/routes/websocket.py` |
