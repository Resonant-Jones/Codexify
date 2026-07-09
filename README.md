<img width="1983" height="793" alt="Codexify-GH-Banner" src="https://github.com/user-attachments/assets/deff1db0-28f7-4a01-8b1a-fce3249cb350" />

# Codexify

**Codexify is a local-first AI operating system for building persistent AI workspaces.** It combines thread-based chat, long-term memory, document management, semantic retrieval, provider routing, and optional workers into a single self-hosted platform.

Codexify is built around a FastAPI backend called **Guardian** and a React UI. Docker Compose is the primary supported way to run the full stack.

## Why Codexify?

Most AI applications treat conversations as disposable tabs in a browser storm.

Codexify treats AI work as an evolving workspace. Threads, documents, memories, tools, providers, and runtime events live together so long-running projects can build context over time instead of restarting from prompt zero.

The goal is not to hide complexity. The goal is to make the complexity legible, inspectable, and useful.

The future of AI work is not just better models. It is better boundaries.

## Highlights

- **Local-first runtime** with Docker Compose as the reference path.
- **Guardian FastAPI backend** for routing, memory, provider access, documents, tasks, and runtime contracts.
- **React workspace UI** for chat, documents, memory surfaces, and operator workflows.
- **Thread-based chat** with durable messages and SSE event streams.
- **Memory silos** for ephemeral, midterm, and longterm storage.
- **Document autosave and secure sharing** through thread/document share tokens.
- **Media uploads** with Postgres metadata and local disk storage.
- **Semantic retrieval** through FAISS or Chroma when embeddings are configured.
- **Provider routing** for local OpenAI-compatible endpoints and explicitly enabled cloud providers.
- **Worker-backed task loops** using Redis streams for observable background execution.

## Terms in One Breath

- **Guardian** is Codexify's orchestration backend. It owns API routing, auth boundaries, database access, memory operations, provider configuration, workers, task events, documents, media, and app lifecycle.
- **Whoosh'd / Whooshd** refers to the local runtime/provider lane used for narrow operator bring-up and local model execution work. The README links the supported Zac Mac Studio path below without implying federation or Pattern/Instance sync support.
- **Memory silos** are Codexify's scoped memory layers: ephemeral, midterm, and longterm.
- **Execution loop** is the emerging task path for queueing, running, observing, validating, and auditing work before declaring completion.

## Architecture at a Glance

```mermaid
flowchart LR
    Operator[Operator] --> UI[React UI]
    UI --> Guardian[Guardian FastAPI]

    Guardian --> Postgres[(Postgres)]
    Guardian --> Redis[(Redis Streams)]
    Guardian --> Vector[FAISS / Chroma]
    Guardian --> Graph[Neo4j - optional]

    Guardian --> Providers[Provider Router]
    Providers --> Local[Local OpenAI-compatible LLM]
    Providers --> Cloud[Cloud providers - explicit opt-in]
    Providers --> Whooshd[Whooshd runtime lane]

    Redis --> Workers[Workers]
    Workers --> Guardian
```

## Current Status

This README reflects what is actually wired today. No vaporware fog machine, no roadmap-as-contract ritual.

| Area | Status | Notes |
| --- | --- | --- |
| Guardian backend | Implemented | FastAPI app on port `8888`. |
| React UI | Implemented | Vite dev server on port `5173`. |
| Postgres persistence | Implemented | Compose `db` service. |
| Redis task/event streams | Implemented | Used by workers and task events. |
| Vector retrieval | Implemented when configured | FAISS or Chroma with local embeddings. |
| Neo4j graph | Optional | Compose includes it, but graph context/logging require flags. |
| Connector worker | Wired but off | Requires `ENABLE_CONNECTOR_WORKER=true`. |
| ChatGPT import | Profiled/off | CLI/Compose profile path, export file, Neo4j, and embeddings required. |
| Backfill workers | Profiled/off | Compose `backfill` profile. |
| RAG upload endpoint | Incomplete | `/upload-chat` depends on missing `codexify.rag.enhanced_rag` and returns `503`. |
| Embeddings API | Guarded | Dummy vectors only when explicitly requested or fallback is enabled. |
| Image generation | Deferred | Local/Stability paths may return `503`. |
| TTS | Partially wired | API mock provider exists; HuggingFace TTS service is separate and not integrated into main API. |
| Desktop shell | Manual parity flow | Tauri app exists with manual build/release commands. |

## Roadmap Shape

These are direction markers, not date promises.

- [x] Local-first Compose runtime
- [x] Guardian API backend
- [x] React workspace UI
- [x] Threaded chat
- [x] Memory silos
- [x] Document autosave
- [x] Media upload metadata
- [x] Redis-backed task/event streams
- [x] Vector retrieval path
- [ ] Full execution loop hardening
- [ ] Runtime verification and validator receipts
- [ ] Federated collaboration boundaries
- [ ] Mobile companion surfaces
- [ ] Plugin SDK and operator-safe extension lanes

## Help & Setup Guide

New to Codexify? Start here:

👉 [Help, Setup, and FAQ](docs/help/CODEXIFY_HELP_AND_FAQ.md)

That document covers:

- Docker setup
- First-run checklist
- Provider configuration
- Common errors
- Troubleshooting commands
- Support channels

For Zac's Mac Studio / Whoosh'd beta bring-up, use the narrow operator path in [`docs/Ops/ZAC_MAC_STUDIO_LOCAL_BRINGUP.md`](docs/Ops/ZAC_MAC_STUDIO_LOCAL_BRINGUP.md). It stays on the supported Docker Compose path and does not imply Pattern/Instance sync or federation support.

Trusted collaborators should start at [`docs/Collaborators/README.md`](docs/Collaborators/README.md) for the collaboration protocol, dev-kit inventory, worktree guide, and task-spec workflow.

## TL;DR - Start Here

If you want to **run Codexify locally** with the least friction:

- Use **Docker Compose**.
- Copy `.env.template` to `.env`.
- Keep `.env` local-only. Never commit it. Templates are the source of truth.
- Set `GUARDIAN_API_KEY`, `NEO4J_PASS`, and local LLM settings.
- Run `docker compose up --build`.
- First boot auto-downloads the default local embedding model into `./models` if it is missing.
- Open the UI at [http://localhost:5173](http://localhost:5173).
- Open API docs at [http://localhost:8888/docs](http://localhost:8888/docs).

If you want to **contribute code**, start with:

- Backend routes: `guardian/routes/`
- Frontend UI: `frontend/src/`
- Database schema: `guardian/db/migrations/`

## What This Repo Actually Is

### Implemented by Default

- **Guardian FastAPI backend** running on port `8888` (`guardian/guardian_api.py`).
- **React UI** served by Vite on port `5173` (`frontend/src`).
- **PostgreSQL** for persistence through Compose `db`.
- **Redis** for task queues and task event streams through Compose `redis`.
- **Vector store** using FAISS or Chroma for semantic retrieval (`guardian/vector/store.py` and `backend/rag/embedder.py`).

### Optional, Wired, but Off by Default

- **Neo4j graph** for graph logging/context. Requires env flags. Compose includes it.
- **Connector worker** disabled unless `ENABLE_CONNECTOR_WORKER=true`.
- **ChatGPT import** through CLI/Compose profile `cli`. Requires export file, Neo4j, and embeddings.
- **Backfill workers** through Compose profile `backfill`.

### Experimental, Stubbed, or Partially Wired

- **RAG upload endpoint** `/upload-chat` requires a missing module (`codexify.rag.enhanced_rag`), so it currently returns `503`.
- **RAG trace debug endpoint** is in-memory only and clears on restart.
- **Embeddings API** `/api/embeddings` returns dummy vectors only when explicitly requested (`embedder=dummy`) or when fallback is enabled. Otherwise it returns `503` until a real backend is configured.
- **Local/Stability image generation** is intentionally deferred for MVP and is non-blocking. Selecting those providers can return `503` until implementations are added.
- **TTS** uses a mock local provider in the API. A separate HuggingFace TTS microservice exists (`backend/tts_service`) but is not integrated into the main API.
- **Desktop app** through Tauri is available for local parity validation (`src-tauri`) with manual build/release commands.

## What You Can Do With It Today

- Create chat threads, post messages, and request completions.
- Stream events through SSE from `/api/events` and `/api/tasks/{task_id}/events`.
- Store and query memory in **ephemeral**, **midterm**, and **longterm** silos.
- Autosave and retrieve thread documents.
- Share threads/documents through secure share tokens.
- Upload images/documents, with metadata stored in Postgres and files stored on disk.
- Use semantic retrieval from the vector store during chat when embeddings are configured.

## Quick Start: Docker Compose

### Prerequisites

- Docker + Docker Compose v2
- A local OpenAI-compatible LLM endpoint, such as **Ollama**, or explicitly enabled cloud API keys

### 1. Configure `.env`

The repo includes `.env.template` and `.env.example`, which are aligned and act as the source of truth. Copy one to `.env`:

```bash
cp .env.template .env
```

### Env Security Guardrails

- `.env` stays ignored through `.gitignore`. Never push or share it.
- Generate a long random `GUARDIAN_API_KEY` per environment and rotate it often.
- `VITE_GUARDIAN_API_KEY` is strictly for localhost/trusted builds so the browser can talk to the backend. Leave it empty for shared, hosted, or production deployment.
- Remote/hosted deployments must instead use `GUARDIAN_AUTH_MODE=remote` and session/JWT auth. See `docs/security/auth-boundary-decision.md`.

Minimum variables required for the **default Compose stack**:

```env
GUARDIAN_API_KEY=replace-with-64-hex-or-any-long-token
VITE_GUARDIAN_API_KEY=replace-with-same-token

NEO4J_PASS=replace-with-neo4j-password

LOCAL_BASE_URL=http://host.docker.internal:11434/v1
LOCAL_LLM_MODEL=your-ollama-model-tag

LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
```

If you want cloud models instead of local:

```env
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=openai,groq,minimax
LLM_PROVIDER=minimax
OPENAI_API_KEY=...
# GROQ_API_KEY=...
MINIMAX_API_KEY=...
MINIMAX_API_BASE=https://api.minimax.io/anthropic
MINIMAX_API_FLAVOR=anthropic
MINIMAX_MODEL=MiniMax-M2.1
# Optional live inventory override:
# MINIMAX_MODEL_DISCOVERY_URL=...
```

MiniMax is the recommended direct cloud provider here when you want:

- Anthropic-compatible chat/tool use by default
- Prompt caching for stable system/tool prefixes
- Thinking blocks preserved through the Anthropic-compatible response shape

OpenAI-compatible MiniMax remains available only as an explicit fallback by setting `MINIMAX_API_FLAVOR=openai`.

### 2. Start the Stack

```bash
docker compose up --build
```

### 3. Verify It Works

```bash
# Backend health, no auth required
curl http://localhost:8888/ping

# Authenticated health, API key required
curl -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/health
```

### If Something Fails to Start

Common causes:

- `GUARDIAN_API_KEY` is missing or mismatched between backend and UI.
- `LOCAL_EMBED_MODEL` is not an absolute path inside the container.
- `NEO4J_PASS` does not match the graph service configuration.
- Local LLM endpoint is not reachable from Docker.

First debug step:

```bash
docker compose logs backend
```

This README assumes a **local-first, trusted environment**. Cloud providers and advanced configurations require additional flags.

### Ports

- **Backend API**: `8888`
- **Frontend dev server**: `5173`
- **Postgres**: `5433 -> 5432` in the container
- **Neo4j**: `7474` browser, `7687` Bolt
- **TTS microservice**: `8000`
- **Redis**: internal only, `6379` not exposed

## Debugging: Frontend Crash Discovery

If a frontend crash mentions `utils.js:306` or you need to locate the source, run:

```bash
bash scripts/dev/doctor.sh
```

If you see `rg: frontend: No such file or directory`, you are almost certainly not in the repo root.

## Local Dev Without Docker

Compose is the reference setup. If running locally:

### 1. Python Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export GUARDIAN_API_KEY=...
export DATABASE_URL=postgresql://user:pass@localhost:5432/Codexify
export LOCAL_BASE_URL=http://localhost:11434/v1
export LOCAL_LLM_MODEL=your-ollama-model-tag
export LOCAL_EMBED_MODEL=/absolute/path/to/Codexify/models/bge-large-en-v1.5
```

### 3. Run Migrations and Seed Defaults

```bash
alembic -c backend/alembic.ini upgrade head
python backend/scripts/seed_defaults.py
```

### 4. Start the API

```bash
uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8888
```

### 5. Start the UI

```bash
pnpm --dir frontend/src install
pnpm --dir frontend/src dev
```

## Desktop: Tauri Local Parity Flow

The desktop shell expects the same external Guardian backend used by WebUI.

1. Ensure backend is reachable. Default: `http://127.0.0.1:8888`.
2. Install frontend deps:

```bash
pnpm --dir frontend/src install
```

3. Run desktop dev:

```bash
make desktop-dev
```

4. Build local desktop bundle through the manual release gate:

```bash
make desktop-build
```

Desktop connection defaults are configurable through:

- `.env`: `CODEXIFY_DESKTOP_BACKEND_URL`, `CODEXIFY_DESKTOP_SHARE_BASE_URL`
- Settings -> Connection, desktop-only overrides persisted locally
- Validation checklist: `docs/desktop/TAURI_PARITY_CHECKLIST.md`

## Runtime Topology

### Always-on Containers, Compose Default

- `db` -> Postgres 15
- `redis` -> task queues and task events
- `neo4j` -> optional graph store, but required by default Compose
- `backend` -> FastAPI app, Guardian
- `frontend` -> Vite dev server
- `worker-chat` -> background chat task worker
- `worker-chat-embed` -> background chat embedding worker
- `worker-warmup` -> warm-up worker for local models
- `tts` -> separate FastAPI TTS microservice

### One-shot Containers

- `migrator` -> runs Alembic + seed defaults, then exits
- `graph-init` -> applies Neo4j constraints + seed nodes, then exits
- `model-prep` -> ensures the local embedding model exists under `./models`, then exits

### Profiled Containers

These do not start unless enabled:

- `chatgpt-migrate`, through the `cli` profile
- `embedding-backfill`, through the `backfill` profile
- `graph-backfill`, through the `backfill` profile

### Communication Summary

- Backend <-> Postgres for chat threads, messages, memory, outbox, documents, media, etc.
- Backend <-> Redis for task queues and task event streams.
- Backend <-> Neo4j only if graph flags are enabled.
- Backend <-> Vector store for FAISS/Chroma retrieval using local embeddings.
- Frontend <-> Backend through the Vite proxy, which injects `X-API-Key` automatically in dev.

### Startup Sequence

1. Postgres + Neo4j start.
2. `graph-init` applies constraints and requires `NEO4J_PASS`.
3. `migrator` runs Alembic + `seed_defaults.py`.
4. `model-prep` ensures the local embedding model is present and downloads it on first boot if needed.
5. Backend starts, verifies required tables, seeds defaults again, then serves API.
6. Workers start once Redis is available.

## Repo Structure

- `guardian/` - Main backend package: FastAPI app, routes, DB logic, workers, plugins, providers.
- `backend/` - Dockerfile, Alembic config, RAG embedder, and separate TTS microservice.
- `frontend/` - React + Vite app. Source lives in `frontend/src`.
- `src-tauri/` - Tauri desktop shell, macOS-first local parity flow, manual packaging gate.
- `guardian/db/migrations/` - Alembic migrations and authoritative schema path.
- `scripts/` - CLI tools, ChatGPT import, maintenance scripts.
- `models/` - Local embedding model files mounted into containers.
- `plugins/` and `guardian/plugins/` - Plugin scaffolding and example plugins.

## Configuration Reality

### Required to Boot, Docker Compose Default

- `GUARDIAN_API_KEY` - backend refuses to start without it.
- `VITE_GUARDIAN_API_KEY` - UI uses this to call the API.
- `NEO4J_PASS` - required by `graph-init`.
- `LOCAL_BASE_URL` - OpenAI-compatible LLM endpoint, such as Ollama.
- `LOCAL_LLM_MODEL` - model name passed to the local endpoint.
- `LOCAL_EMBED_MODEL` - absolute path inside container, such as `/models/bge-large-en-v1.5`.

### Required if Running Without Docker

- `DATABASE_URL` or `GUARDIAN_DATABASE_URL`. No DB means no chat/memory persistence.

### Common Optional Settings

- Cloud LLM usage requires all of:
  - `ALLOW_CLOUD_PROVIDERS=true`
  - `CODEXIFY_LOCAL_ONLY_MODE=false`
  - `CODEXIFY_EGRESS_ALLOWLIST=<provider ids>`, including your target provider
  - `LLM_PROVIDER=<single provider id>`, not a comma-separated list
  - Provider keys, such as `OPENAI_API_KEY`, `GROQ_API_KEY`, or `MINIMAX_API_KEY` + `MINIMAX_API_BASE`
- `CODEXIFY_VECTOR_STORE=chroma|faiss`
- `CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=1`
- `EMBEDDING_BACKEND=local|dummy|gpt_oss|nomic`, where `stub` is accepted as an alias for `dummy`
- `GUARDIAN_ENABLE_GRAPH_CONTEXT=true` / `GUARDIAN_ENABLE_GRAPH_LOGGING=true`
- `ENABLE_CONNECTOR_WORKER=true`, plus provider tokens such as `GITHUB_TOKEN`
- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL`
- `ELEVENLABS_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` for real TTS
- `GUARDIAN_ALLOWED_ORIGINS`, such as `http://localhost:5173,tauri://localhost,https://tauri.localhost`

## Development Workflow

### Environment Contract, macOS + zsh

Required tools:

- Python 3 through `python` on PATH
- pip
- pytest
- Node.js
- pnpm
- npm
- Docker + Docker Compose for compose-based tasks

Verify:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

python --version
python -m pip --version
python -m pytest --version || true

node --version
pnpm --version || true
npm --version

docker --version
docker compose version
```

Remediation with Homebrew:

```bash
brew install python
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest

brew install node
corepack enable
corepack prepare pnpm@9.12.1 --activate

brew install --cask docker
```

Optional isolated Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

### Preflight

Run this before campaign/task work:

```bash
./scripts/preflight.sh
```

It validates toolchain availability, pytest importability, and a clean working tree.

### Validation: Chat Embedding Queue Loop

This validates enqueue -> worker consume -> observable result.

```bash
# 1. Start dependencies
docker compose up -d redis db backend worker-chat-embed

# 2. Enqueue a message, which creates an embed job
BASE_URL="${BASE_URL:-http://localhost:8888}"
API_KEY="${GUARDIAN_API_KEY:-}"

THREAD_JSON="$(curl -sS -H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{}' "${BASE_URL}/api/chat/threads")"

THREAD_ID="$(python - <<'PY'
import json, sys
payload = sys.stdin.read()
data = json.loads(payload)
print(data.get("id") or data.get("thread", {}).get("id") or "")
PY
<<<"${THREAD_JSON}")"

curl -sS -H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"role":"user","content":"preflight-embed"}' \
  "${BASE_URL}/api/chat/${THREAD_ID}/messages"

# 3. Observe worker consumption
docker compose logs --tail=200 worker-chat-embed
```

Expected signals:

- Success log: `[chat-embed] embedded message_id=...`
- Acceptable loop validation: `[chat-embed] embedding failed ...`, which means the queue loop is working but embeddings are misconfigured

If it fails:

- Ensure `GUARDIAN_API_KEY` is set from `.env`.
- Ensure embeddings are configured and `LOCAL_EMBED_MODEL` is mounted and valid.

### Running Tests

- Two test trees exist: `guardian/tests` and `tests`.
- `make test` runs `python -m pytest -q guardian/tests tests` and will prompt if pytest is missing.
- You can also run pytest directly:

```bash
pytest guardian/tests
pytest tests
```

### Migrations

- Alembic config: `backend/alembic.ini`
- Migrations live in `guardian/db/migrations/`

```bash
alembic -c backend/alembic.ini revision -m "your change"
alembic -c backend/alembic.ini upgrade head
```

### Known Foot-guns

- Backend exits if `GUARDIAN_API_KEY` is missing.
- `LOCAL_EMBED_MODEL` must be absolute or embeddings will fail.
- Default templates use `http://localhost:11434/v1` for `LOCAL_BASE_URL`; update it for Docker, such as `http://host.docker.internal:11434/v1`, or your local setup.
- `make dev` runs `guardian.system_init`, not the FastAPI API server.

## Explicit Non-Goals / Deferred Systems

- Full graph context is off by default and requires explicit env flags.
- The `/upload-chat` RAG endpoint is effectively disabled due to the missing module noted above.
- Embeddings API returns mock vectors only when explicitly requested. Otherwise it fails closed until configured.
- Local/Stability image generation is deferred for MVP and may return `503` until implemented.
- TTS microservice exists but is not integrated into the main API.
- Desktop/Tauri app uses a manual packaging flow. There is no CI signing/notarization pipeline yet.

## Documentation Map

Codexify has extensive documentation. You do **not** need to read everything. Start with the document that matches your goal.

### 1. High-level System Understanding

- **Codexify-System-Specification.md** - what Codexify is, what problems it solves, and what it intentionally does not do.

### 2. Architectural Truth

- **Codexify-Master-Architecture-Report.md** - end-to-end runtime topology, services, data flow, and container roles.

### 3. Backend Internals

- **system_architecture.md** - Guardian internals, lifecycle, DB wiring, workers, and event flow.

### 4. Data, Memory, and Cognition

- **Event_Graph.md**
- **Thread-Artifact-Lineage.md**
- **context-report.md**

These cover how memory, threads, artifacts, and context interact over time.

### 5. UI + Perceptual Layer

- **Codexify-UI-Rendering-Protocol.md**
- **CODEXIFY-PERCEPTUAL-STACK-SPEC.md**

These cover UI state, rendering, and agent perception.

### 6. Security and Integrity

- **docs/SECURITY.md**
- **docs/CONFIGURATION.md**
- **docs/security/auth-boundary-decision.md**
- **docs/dev/SECURITY_HARDENING_PLAN.md**

These cover threat model, guardrails, and non-goals.

### 7. Contributing

- **CONTRIBUTING.md** - expectations, safe areas, and how to avoid stepping on landmines.

If you are unsure where to start, read **Codexify-System-Specification.md** and then open the code.

## Contribution Entry Point

If you have not read the Documentation Map above, start there.

If you are new, start here:

- **Backend API routes:** `guardian/routes/`
- **Data models + migrations:** `guardian/db/models.py`, `guardian/db/migrations/`
- **Frontend UI:** `frontend/src/`
- **Workers & queues:** `guardian/workers/`, `guardian/queue/`

Sensitive or architectural areas:

- `guardian/core/` for auth, DB wiring, and event bus
- `guardian/core/config.py` for provider routing rules
- `guardian/guardian_api.py` for app lifecycle and router wiring

Safe changes:

- UI components and styling in `frontend/src`
- New API endpoints in `guardian/routes/`
- New migrations under `guardian/db/migrations/versions/`

If you are unsure, open a small PR touching one area, such as UI or a single route, and ask for guidance.
