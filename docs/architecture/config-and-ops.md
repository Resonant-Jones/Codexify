Purpose: Give senior engineers the operational truth needed to run, debug, and change Codexify safely, with special attention to config precedence, worker dependencies, and failure signatures.
Last updated: 2026-03-17
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

## Provider Governance and Beta Operator Workflow

### Governance model

- `guardian/core/provider_registry.py` is the canonical source of truth for provider authorization, availability, and capability decisions. Catalog, health, router, and worker paths are expected to agree with it.
- `config/supported_profiles/v1-local-core-web-mcp.yaml` is the beta release contract for the current supported local-first provider posture. `/health` exposes the active supported-profile state during runtime.
- `/api/llm/catalog` is the discovered inventory surface. It shows provider/model entries and policy-shaped availability state; `?include=all` is the operator view when hidden or unauthorized providers need inspection.
- `/health/llm` is the active-provider runtime surface. It reports the currently selected provider, provider-runtime status, and queue-backed completion-service health for that live runtime.
- `/health/chat` is the queue/worker surface. It is the quickest confirmation that Redis, enqueue, and worker heartbeat are healthy for chat completion.

### Why operators should read registry, health, and catalog together

- Catalog answers “what inventory does the runtime currently describe?”
- Health answers “is the currently selected execution path reachable and are chat workers alive?”
- The supported profile and provider registry answer “what should be allowed and treated as supported for this beta?”
- None of those surfaces is sufficient alone. A green health check does not prove the mounted route surface matches the supported profile, and catalog presence does not prove that a provider path is part of the supported beta contract.

### Current operator limits without a full Command Center / Observability Deck

- Operators can currently infer whether the selected provider is configured, credentialed, egress-allowed, and reachable enough for the active runtime path.
- Operators can currently infer whether discovered provider inventory is available, disabled, or filtered with a reason.
- Operators can currently infer whether the chat completion service is degraded because Redis is unreachable, enqueue is failing, or worker heartbeat is missing.
- Operators cannot yet rely on a single integrated surface to explain every routing decision, provider downgrade, discovery mismatch, or queue-to-UI causal chain.
- Operators cannot treat partial operator UI components as the supported beta source of truth. The repo contains internal/operator-facing UI work, but the Command Center / Observability Deck is not the released beta operator surface and should not be assumed to live in the main shell navigation.

### Current dev-only and internal operational surfaces

- `/debug/rag-trace/{thread_id}/latest` is explicitly dev-only. It reads the latest completion trace from task events when available, falls back to in-memory cache, and is cleared by restart.
- In the current supported profile, `command_bus` is marked internal-only. That route posture is an operator/runtime concern, not an end-user release surface.
- Partial action-center style UI exists in the frontend codebase, but its backing data sources depend on routes and operational surfaces that are not the primary supported beta workflow.

### Expected source of truth during beta operation

| Question | Current source of truth | Notes |
|---|---|---|
| Which provider posture is supported for this beta? | `config/supported_profiles/v1-local-core-web-mcp.yaml` plus `GET /health` | Use this before trusting broader route or provider availability claims. |
| Which providers/models are currently discoverable and policy-shaped? | `GET /api/llm/catalog` | Use `?include=all` for operator debugging when filtered providers matter. |
| Is the active provider path actually available right now? | `GET /health/llm` | Read `provider_runtime` together with completion-service status. |
| Is chat execution degraded because of queue or worker issues? | `GET /health/chat` | This is the fastest signal for Redis reachability, enqueue health, and worker heartbeat. |
| How should routing validation be done? | Supported profile + provider registry behavior + live completion evidence | Do not infer routing correctness from shell UI presence alone. |
| What is the best current evidence for RAG trace behavior? | `GET /debug/rag-trace/{thread_id}/latest` plus task events/logs | Dev-only and non-durable; useful for live debugging, not durable release proof by itself. |

### Beta readiness operator verification workflow

1. Confirm the intended beta contract before trusting runtime signals.
   - Read `config/supported_profiles/v1-local-core-web-mcp.yaml` for the supported provider posture, internal-only extensions, and quarantined routes.
   - Treat `guardian/core/provider_registry.py` as the canonical provider-governance source and `GET /health` as the runtime read of the active supported profile.
   - Call the release `hold` if runtime profile state or mounted route posture contradicts that contract.
2. Compare discovered inventory with the live provider path.
   - Use `GET /api/llm/catalog` and `GET /api/llm/catalog?include=all` to inspect what the runtime is exposing and filtering.
   - Use `GET /health/llm` to confirm the active provider path and `GET /health/chat` to confirm Redis, enqueue, and worker heartbeat for completion.
   - Treat catalog, health, and supported-profile state as one release gate; a green health response alone is not beta proof.
3. Use current shipped operator surfaces, not partial UI, for signoff.
   - The Command Center / Observability Deck and partial action-center UI are still internal or dev-only; they are supplemental, not the released beta source of truth.
   - `/debug/rag-trace/{thread_id}/latest` is useful for live debugging, but it is still dev-only and non-durable.
   - For current beta decisions, the supported evidence pack is backend endpoints, logs, `/metrics`, and direct probes.
4. Separate backend correctness from observability completeness.
   - Strong deterministic tests plus green queue/provider health can justify a "runtime stabilizing" read.
   - They do not justify `go` if the supported-profile contract is drifting, quarantined routes are exposed, or the operator still needs ad hoc Compose/container inspection to explain the real state.
5. Manually verify the minimum beta-ready evidence before calling `go`.
   - Verify the supported-profile flags are active, internal-only/quarantined routes are not exposed on the supported beta surface, provider registry posture agrees with catalog and health, and the current audit window includes fresh live proof for assistant completion plus upload -> embed -> retrieve.
   - If any of those checks fail, or if the mismatch can only be explained through unsupported/internal surfaces, record the release as `hold`.

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
