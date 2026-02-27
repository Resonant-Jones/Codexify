# Codexify Solo Operator System Map

Purpose: One-page operational map for a solo operator. Use this to answer "where does X live?" in under 30 seconds and to pick the first debug move without guessing.
Last updated: 2026-02-27
Source anchors:
- `README.md`
- `docs/help/CODEXIFY_HELP_AND_FAQ.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/flows.md`
- `docs/guardian/command-bus-auth-cli-automations.md`
- `guardian/routes/cron.py`
- `guardian/cron/scheduler.py`
- `guardian/workers/cron_worker.py`
- `docker-compose.yml`

## 6-Lane Map

| Lane | What lives here | Primary anchors | Ownership (solo mode) | Blast radius | First-debug command |
|---|---|---|---|---|---|
| UI | React app shell, API client wiring, route/view rendering | `frontend/src/App.tsx`, `frontend/src/lib/api.ts`, `docs/ui/UI-DESIGN-MAP.md` | You | medium | `docker compose logs --tail=120 frontend` |
| API | FastAPI app wiring, route contracts, auth boundary, request handling | `guardian/guardian_api.py`, `guardian/routes/`, `guardian/core/dependencies.py` | You | high | `curl -sS http://localhost:8888/ping` |
| Workers | Queue consumers and async execution for chat, embeddings, cron | `guardian/workers/chat_worker.py`, `guardian/workers/document_embed_worker.py`, `guardian/workers/cron_worker.py` | You | high | `docker compose ps worker-chat worker-chat-embed worker-document-embed worker-warmup` |
| Data | Postgres entities, Redis queue/event transport, migrations | `guardian/db/models.py`, `backend/alembic.ini`, `guardian/queue/redis_queue.py` | You | high | `docker compose ps db redis` |
| Automation | Command bus (`/api/guardian/commands/*`), tools compatibility surface (`/api/tools/*`), durable cron (`/api/cron/*`) | `guardian/routes/command_bus.py`, `guardian/command_bus/`, `guardian/routes/tools.py`, `guardian/routes/cron.py`, `guardian/cron/` | You | high | `curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/cron/jobs` |
| Ops | Compose topology, env wiring, service-level diagnostics | `docker-compose.yml`, `.env.template`, `README.md`, `docs/architecture/config-and-ops.md` | You | high | `docker compose ps` |

## First Logs and Endpoints Per Lane

| Lane | First endpoint/signal | First logs to inspect |
|---|---|---|
| UI | `http://localhost:5173` renders and API calls return | `docker compose logs --tail=120 frontend` |
| API | `/ping` and `/health` return 200 with valid API key | `docker compose logs --tail=120 backend` |
| Workers | Queue-backed flows transition from queued to terminal state | `docker compose logs --tail=120 worker-chat` and worker-specific container logs |
| Data | DB and Redis containers are healthy in Compose | `docker compose logs --tail=120 db redis` |
| Automation | `/api/guardian/commands/manifest` and `/api/cron/jobs` return expected payloads | `docker compose logs --tail=120 backend` plus cron scheduler/worker logs if running manually |
| Ops | Service set matches expected default stack | `docker compose ps` and `docker compose logs --tail=120 backend` |

## Where To Debug First (By Broken Flow)

| Broken flow | Check first | Then check | Lane |
|---|---|---|---|
| UI loads but actions fail | `curl -sS http://localhost:8888/ping` | backend logs for route/auth errors | UI -> API |
| Chat completion stuck | worker status (`docker compose ps ...`) | `worker-chat` logs and Redis availability | Workers -> Data |
| Command invocation blocked | `GET /api/guardian/commands/manifest` then invoke response `status/error` | `GET /api/guardian/commands/runs/{run_id}/events` | Automation |
| Cron run stuck `queued` | confirm scheduler + cron worker processes are running | `GET /api/cron/jobs/{job_id}/runs` for transitions | Automation -> Workers |
| 401/403 surprises | verify `X-API-Key` and `GUARDIAN_AUTH_MODE` assumptions | `guardian/core/dependencies.py` rules | API |
| Webhook cron rejected | inspect 403/422 detail payload | `guardian/routes/cron.py` policy checks and egress settings | Automation |

## 30-Second Locate Index

- Command bus contracts: `guardian/command_bus/contracts.py`
- Command bus invoke flow: `guardian/command_bus/invoke.py`
- Command run event stream route: `guardian/routes/command_bus.py`
- Tools compatibility shim (`/api/tools/*`): `guardian/routes/tools.py`
- Cron CRUD + validation + trigger: `guardian/routes/cron.py`
- Cron scheduler tick/enqueue: `guardian/cron/scheduler.py`
- Cron queue consumer/executor: `guardian/workers/cron_worker.py`
- Cron execution primitives (`noop`, `webhook`): `guardian/cron/executor.py`
- Durable cron schema: `guardian/db/models.py` (`CronJob`, `CronRun`)
- Core runtime topology: `docker-compose.yml`
