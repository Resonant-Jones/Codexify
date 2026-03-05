# Codexify

Codexify is a local-first chat + knowledge workspace built around a FastAPI backend (Guardian) and a React UI. It provides thread-based chat, memory silos, document autosave and sharing, media uploads, vector search, and optional workers for background tasks. Docker Compose is the primary, supported way to run the full stack.

## 📘 Help & Setup Guide

New to Codexify?

Start here:

👉 [Help, Setup, and FAQ](docs/help/CODEXIFY_HELP_AND_FAQ.md)

This document covers:

- Docker setup
- First-run checklist
- Provider configuration
- Common errors
- Troubleshooting commands
- Support channels


### TL;DR — Start Here

If you want to **run Codexify locally** with the least friction:

* Use **Docker Compose**
* Copy `.env.template → .env`
* `.env` is local-only; never commit it (templates are the source of truth)
* Set `GUARDIAN_API_KEY`, `NEO4J_PASS`, and your local LLM settings
* Run: `docker compose up --build`
* First boot auto-downloads the default local embedding model into `./models` if it is missing
* Open:

  * UI: [http://localhost:5173](http://localhost:5173)
  * API docs: [http://localhost:8888/docs](http://localhost:8888/docs)

If you want to **contribute code**, start with:

* Backend routes: `guardian/routes/`
* Frontend UI: `frontend/src/`
* Database schema: `guardian/db/migrations/`

This README reflects what is actually wired today (no roadmap promises).

This section is intentionally explicit. It lists what is **implemented**, what is **wired but off**, and what is **stubbed or incomplete**, so contributors are not guessing.

## What This Repo Actually Is

**Implemented (default stack)**
- **Guardian FastAPI backend** running on port 8888 (`guardian/guardian_api.py`).
- **React UI** served by Vite on port 5173 (`frontend/src`).
- **PostgreSQL** for persistence (Compose `db`).
- **Redis** for task queues and task event streams (Compose `redis`).
- **Vector store** (FAISS or Chroma) used for semantic retrieval (`guardian/vector/store.py` + `backend/rag/embedder.py`).

**Optional (wired but off by default)**
- **Neo4j graph** for graph logging/context (requires env flags; Compose includes it).
- **Connector worker** (disabled unless `ENABLE_CONNECTOR_WORKER=true`).
- **ChatGPT import** (CLI/Compose profile `cli`, requires export file + Neo4j + embeddings).
- **Backfill workers** (Compose profile `backfill`).

**Experimental / stubbed / partially wired**
- **RAG upload endpoint** `/upload-chat` requires a missing module (`codexify.rag.enhanced_rag`), so it currently returns 503.
- **RAG trace debug endpoint** is in-memory only and clears on restart.
- **Embeddings API** `/api/embeddings` returns **dummy vectors only when explicitly requested** (`embedder=dummy`) or when fallback is enabled; otherwise it returns 503 until a real backend is configured.
- **Local/Stability image generation** is intentionally deferred for MVP and is non-blocking; selecting those providers can return `503` until implementations are added.
- **TTS**: API uses a **mock local provider** (sine wave). A separate HuggingFace TTS microservice exists (`backend/tts_service`) but is not integrated into the main API.
- **Desktop app** (Tauri) is available for local parity validation (`src-tauri`) with manual build/release commands.

## What You Can Do With It Today

- Create chat threads, post messages, and request completions.
- Stream events via SSE from `/api/events` (durable outbox) and `/api/tasks/{task_id}/events` (Redis stream).
- Store and query memory in **ephemeral/midterm/longterm** silos.
- Autosave and retrieve thread documents.
- Share threads/documents via secure share tokens.
- Upload images/documents, with metadata stored in Postgres and files stored on disk.
- Use semantic retrieval from the vector store during chat (if embeddings are configured).

## Quick Start (Docker Compose)

### Prerequisites
- Docker + Docker Compose v2
- A local OpenAI-compatible LLM endpoint (e.g., **Ollama**) **or** cloud API keys

### 1) Configure `.env`
The repo includes `.env.template` and `.env.example`, which are aligned and act as the source of truth. Copy one to `.env` (local-only; never commit it):

```bash
cp .env.template .env
```

#### Env Security Guardrails
- `.env` stays ignored (`.gitignore` enforces this); never push or share the file.
- Generate a long random `GUARDIAN_API_KEY` per environment and rotate it often.
- `VITE_GUARDIAN_API_KEY` is strictly for localhost/trusted builds so the browser can talk to the backend. Leave it empty for any shared, hosted, or production deployment—shipping it would leak backend access.
- Remote/hosted deployments must instead use `GUARDIAN_AUTH_MODE=remote` and session/JWT auth (see `docs/security/auth-boundary-decision.md`).

Minimum variables required for the **default Compose stack**:

```env
# Required to start the FastAPI backend
GUARDIAN_API_KEY=replace-with-64-hex-or-any-long-token
VITE_GUARDIAN_API_KEY=replace-with-same-token

# Required by Neo4j + graph-init in docker-compose.yml
NEO4J_PASS=replace-with-neo4j-password

# Required for local LLM usage (default provider)
LOCAL_BASE_URL=http://host.docker.internal:11434/v1
LOCAL_LLM_MODEL=your-ollama-model-tag

# Required for local embeddings (must be absolute path **inside the container**)
LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
```

If you want cloud models instead of local:

```env
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=openai,groq,minimax
LLM_PROVIDER=openai   # single value only: openai, groq, minimax, or local
OPENAI_API_KEY=...
# GROQ_API_KEY=...
# MINIMAX_API_KEY=...
# MINIMAX_API_BASE=https://api.minimax.chat/v1
```

### 2) Start the stack

```bash
docker compose up --build
```

### 3) Verify it's working

```bash
# Backend health (no auth required)
curl http://localhost:8888/ping

# Authenticated health (API key required)
curl -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/health
```

### If Something Fails to Start

Common causes:

* `GUARDIAN_API_KEY` is missing or mismatched between backend and UI
* `LOCAL_EMBED_MODEL` is not an absolute path **inside the container**
* Neo4j password mismatch (`NEO4J_PASS`)
* Local LLM endpoint not reachable from Docker

First debug step:

```bash
docker compose logs backend
```

This README assumes a **local-first, trusted environment**. Cloud providers and advanced configurations require additional flags.

Open the UI:
- http://localhost:5173

Open API docs:
- http://localhost:8888/docs

### Ports (Docker Compose)
- **Backend API**: 8888
- **Frontend dev server**: 5173
- **Postgres**: 5433 -> 5432 (container)
- **Neo4j**: 7474 (browser), 7687 (Bolt)
- **TTS microservice**: 8000
- **Redis**: internal only (6379, not exposed)

## Debugging: Frontend crash discovery

If a frontend crash mentions `utils.js:306` or you need to locate the source, run:

```bash
bash scripts/dev/doctor.sh
```

If you see `rg: frontend: No such file or directory`, you're almost certainly not in the repo root.

## Local Dev (Without Docker)

This is possible, but Compose is the reference setup. If running locally:

1) Python environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2) Set environment variables
```bash
export GUARDIAN_API_KEY=...
export DATABASE_URL=postgresql://user:pass@localhost:5432/Codexify
export LOCAL_BASE_URL=http://localhost:11434/v1
export LOCAL_LLM_MODEL=your-ollama-model-tag
export LOCAL_EMBED_MODEL=/absolute/path/to/Codexify/models/bge-large-en-v1.5
```

3) Run migrations + seed defaults
```bash
alembic -c backend/alembic.ini upgrade head
python backend/scripts/seed_defaults.py
```

4) Start the API
```bash
uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8888
```

5) Start the UI
```bash
pnpm --dir frontend/src install
pnpm --dir frontend/src dev
```

## Desktop (Tauri) Local Parity Flow

The desktop shell expects the same external Guardian backend used by WebUI.

1) Ensure backend is reachable (default `http://127.0.0.1:8888`)
2) Install frontend deps (first run)

```bash
pnpm --dir frontend/src install
```

3) Run desktop dev

```bash
make desktop-dev
```

4) Build local desktop bundle (manual release gate)

```bash
make desktop-build
```

Desktop connection defaults are configurable via:
- `.env`: `CODEXIFY_DESKTOP_BACKEND_URL`, `CODEXIFY_DESKTOP_SHARE_BASE_URL`
- Settings -> Connection (desktop-only overrides, persisted locally)
- Validation checklist: `docs/desktop/TAURI_PARITY_CHECKLIST.md`

## Runtime Topology

**Always-on containers (Compose default)**
- `db` -> Postgres 15
- `redis` -> task queues + task events
- `neo4j` -> optional graph store (but required by default Compose)
- `backend` -> FastAPI app (Guardian)
- `frontend` -> Vite dev server
- `worker-chat` -> background chat task worker
- `worker-chat-embed` -> background chat embedding worker
- `worker-warmup` -> warm-up worker for local models
- `tts` -> separate FastAPI TTS microservice

**One-shot containers**
- `migrator` -> runs Alembic + seed defaults, then exits
- `graph-init` -> applies Neo4j constraints + seed nodes, then exits
- `model-prep` -> ensures the local embedding model exists under `./models`, then exits

**Profiled containers (not started unless enabled)**
- `chatgpt-migrate` (`cli` profile)
- `embedding-backfill`, `graph-backfill` (`backfill` profile)

**Communication summary**
- Backend <-> Postgres (chat threads, messages, memory, outbox, documents, media, etc.)
- Backend <-> Redis (task queues + task event streams)
- Backend <-> Neo4j (only if graph flags enabled)
- Backend <-> Vector store (FAISS/Chroma using local embeddings)
- Frontend <-> Backend (Vite proxy injects `X-API-Key` automatically in dev)

**Startup sequence (Compose)**
1. Postgres + Neo4j start
2. `graph-init` applies constraints (requires `NEO4J_PASS`)
3. `migrator` runs Alembic + `seed_defaults.py`
4. `model-prep` ensures the local embedding model is present, downloading it on first boot if needed
5. Backend starts, verifies required tables, seeds defaults again, then serves API
6. Workers start (Redis required)

## Repo Structure (Truthful)

- `guardian/` - **Main backend package** (FastAPI app, routes, DB logic, workers, plugins, providers).
- `backend/` - Dockerfile, Alembic config, RAG embedder, and **separate** TTS microservice.
- `frontend/` - React + Vite app (source in `frontend/src`).
- `src-tauri/` - Tauri desktop shell (macOS-first local parity flow, manual packaging gate).
- `guardian/db/migrations/` - Alembic migrations (authoritative schema path).
- `scripts/` - CLI tools (ChatGPT import, maintenance scripts).
- `models/` - Local embedding model files (mounted into containers).
- `plugins/` and `guardian/plugins/` - Plugin scaffolding and example plugins.

## Configuration Reality

### Required to boot (Docker Compose default)
- `GUARDIAN_API_KEY` - backend refuses to start without it.
- `VITE_GUARDIAN_API_KEY` - UI uses this to call the API.
- `NEO4J_PASS` - required by `graph-init` (Compose dependency).
- `LOCAL_BASE_URL` - OpenAI-compatible LLM endpoint (e.g., Ollama).
- `LOCAL_LLM_MODEL` - model name passed to the local endpoint.
- `LOCAL_EMBED_MODEL` - **absolute path inside container** (e.g., `/models/bge-large-en-v1.5`).

### Required if running without Docker
- `DATABASE_URL` (or `GUARDIAN_DATABASE_URL`) - no DB, no chat/memory persistence.

### Common optional settings
- Cloud LLM usage requires all of:
  - `ALLOW_CLOUD_PROVIDERS=true`
  - `CODEXIFY_LOCAL_ONLY_MODE=false`
  - `CODEXIFY_EGRESS_ALLOWLIST=<provider ids>` including your target (for example `openai,groq,minimax`)
  - `LLM_PROVIDER=<single provider id>` (not a comma-separated list)
  - `OPENAI_API_KEY` (for `openai`) or `GROQ_API_KEY` (for `groq`) or (`MINIMAX_API_KEY` + `MINIMAX_API_BASE`) for `minimax`
- `CODEXIFY_VECTOR_STORE=chroma|faiss`
- `CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=1` (allow mock embeddings fallback and `/api/embeddings` dummy mode)
- `EMBEDDING_BACKEND=local|dummy|gpt_oss|nomic` (`stub` is accepted as an alias for `dummy`)
- `GUARDIAN_ENABLE_GRAPH_CONTEXT=true` / `GUARDIAN_ENABLE_GRAPH_LOGGING=true`
- `ENABLE_CONNECTOR_WORKER=true` (and provider tokens like `GITHUB_TOKEN`)
- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation; MVP path is `openai`, while `local`/`stability` are deferred and may return `503`)
- `ELEVENLABS_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` (real TTS)
- `GUARDIAN_ALLOWED_ORIGINS` (include browser + desktop origins, e.g. `http://localhost:5173,tauri://localhost,https://tauri.localhost`)

## Development Workflow (As It Exists)

### Environment Contract (macOS + zsh)
Required tools:
- Python 3 (via `python` on PATH)
- pip
- pytest
- Node.js
- pnpm
- npm
- Docker + Docker Compose (for compose-based tasks)

Verify (copy/paste):

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

Remediation (Homebrew, copy/paste):

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

Optional (isolated Python env):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

### Preflight (one command)
Run this before any campaign/task work:

```bash
./scripts/preflight.sh
```

It validates toolchain availability, pytest importability, and a clean working tree.

### Validation: Chat Embedding Queue Loop
This validates enqueue → worker consume → observable result.

```bash
# 1) Start dependencies
docker compose up -d redis db backend worker-chat-embed

# 2) Enqueue a message (creates an embed job)
BASE_URL="${BASE_URL:-http://localhost:8888}"
API_KEY="${GUARDIAN_API_KEY:-}"

THREAD_JSON="$(curl -sS -H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{}' "${BASE_URL}/api/chat/threads")"

THREAD_ID="$(python - <<'PY'
import json, os, sys
payload = sys.stdin.read()
data = json.loads(payload)
print(data.get("id") or data.get("thread", {}).get("id") or "")
PY
<<<"${THREAD_JSON}")"

curl -sS -H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"role":"user","content":"preflight-embed"}' \
  "${BASE_URL}/api/chat/${THREAD_ID}/messages"

# 3) Observe worker consumption
docker compose logs --tail=200 worker-chat-embed
```

Expected signals:
- Success log: `[chat-embed] embedded message_id=...`
- Acceptable loop validation: `[chat-embed] embedding failed ...` (queue loop is working but embeddings are misconfigured)

If it fails:
- Ensure `GUARDIAN_API_KEY` is set (from `.env`).
- Ensure embeddings are configured (`LOCAL_EMBED_MODEL` mounted and valid).

### Running tests
- Two test trees exist: `guardian/tests` (large) and `tests` (smaller).
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

### Known foot-guns
- Backend exits if `GUARDIAN_API_KEY` is missing.
- `LOCAL_EMBED_MODEL` must be **absolute** or embeddings will fail.
- Default templates use `http://localhost:11434/v1` for `LOCAL_BASE_URL`; update it for Docker (e.g., `http://host.docker.internal:11434/v1`) or your local setup.
- `make dev` runs `guardian.system_init` (not the FastAPI API server).

## Explicit Non-Goals / Deferred Systems

- Full graph context is **off by default** and requires explicit env flags.
- The `/upload-chat` RAG endpoint is effectively disabled (missing module).
- Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
- Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
- TTS microservice exists but is not integrated into the main API.
- Desktop/Tauri app uses a manual packaging flow (no CI signing/notarization pipeline yet).

## Documentation Map (Read This in Order)

Codexify has extensive documentation. You do **not** need to read everything.

Start with the document that matches your goal:

### 1. High-level system understanding
- **Codexify-System-Specification.md**
  What Codexify is, what problems it solves, and what it intentionally does not do.

### 2. Architectural truth (how it actually runs)
- **Codexify-Master-Architecture-Report.md**
  End-to-end runtime topology, services, data flow, and container roles.

### 3. Backend internals
- **system_architecture.md**
  Guardian internals, lifecycle, DB wiring, workers, and event flow.

### 4. Data, memory, and cognition
- **Event_Graph.md**
- **Thread-Artifact-Lineage.md**
- **context-report.md**
  How memory, threads, artifacts, and context interact over time.

### 5. UI + perceptual layer
- **Codexify-UI-Rendering-Protocol.md**
- **CODEXIFY-PERCEPTUAL-STACK-SPEC.md**
  How UI state, rendering, and agent perception are structured.

### 6. Security & integrity
- **docs/SECURITY.md**
- **docs/CONFIGURATION.md**
- **docs/security/auth-boundary-decision.md**
- **docs/dev/SECURITY_HARDENING_PLAN.md**
  Threat model, guardrails, and non-goals.

### 7. Contributing
- **CONTRIBUTING.md**
  Expectations, safe areas, and how to avoid stepping on landmines.

  ## Documentation Map (Read This in Order)

Codexify has extensive documentation. You do **not** need to read everything.

Start with the document that matches your goal:

### 1. High-level system understanding

* **Codexify-System-Specification.md**
  What Codexify is, what problems it solves, and what it intentionally does not do.

### 2. Architectural truth (how it actually runs)

* **Codexify-Master-Architecture-Report.md**
  End-to-end runtime topology, services, data flow, and container roles.

### 3. Backend internals

* **system_architecture.md**
  Guardian internals, lifecycle, DB wiring, workers, and event flow.

### 4. Data, memory, and cognition

* **Event_Graph.md**
* **Thread-Artifact-Lineage.md**
* **context-report.md**
  How memory, threads, artifacts, and context interact over time.

### 5. UI + perceptual layer

* **Codexify-UI-Rendering-Protocol.md**
* **CODEXIFY-PERCEPTUAL-STACK-SPEC.md**
  How UI state, rendering, and agent perception are structured.

### 6. Security & integrity

* **docs/SECURITY.md**
* **docs/CONFIGURATION.md**
* **docs/security/auth-boundary-decision.md**
* **docs/dev/SECURITY_HARDENING_PLAN.md**
  Threat model, guardrails, and non-goals.

### 7. Contributing

* **CONTRIBUTING.md**
  Expectations, safe areas, and how to avoid stepping on landmines.

If you are unsure where to start, read **Codexify-System-Specification.md** and then open the code.

## Contribution Entry Point

If you haven’t read the Documentation Map above, start there.

If you're new, start here:
- **Backend API routes:** `guardian/routes/`
- **Data models + migrations:** `guardian/db/models.py`, `guardian/db/migrations/`
- **Frontend UI:** `frontend/src/`
- **Workers & queues:** `guardian/workers/`, `guardian/queue/`

Sensitive or architectural areas:
- `guardian/core/` (auth, DB wiring, event bus)
- `guardian/core/config.py` (provider routing rules)
- `guardian/guardian_api.py` (app lifecycle + router wiring)

Safe changes:
- UI components and styling in `frontend/src`
- New API endpoints in `guardian/routes/`
- New migrations under `guardian/db/migrations/versions/`

If you're unsure, open a small PR touching one area (UI or a single route) and ask for guidance.

### Known foot-guns

- Backend exits if `GUARDIAN_API_KEY` is missing.
* `LOCAL_EMBED_MODEL` must be **absolute** or embeddings will fail.
* Default templates use `http://localhost:11434/v1` for `LOCAL_BASE_URL`; update it for Docker (e.g., `http://host.docker.internal:11434/v1`) or your local setup.
* `make dev` runs `guardian.system_init` (not the FastAPI API server).

## Explicit Non-Goals / Deferred Systems

* Full graph context is **off by default** and requires explicit env flags.
* The `/upload-chat` RAG endpoint is effectively disabled (missing module).
* Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
* Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
* TTS microservice exists but is not integrated into the main API.
* Desktop/Tauri app uses a manual packaging flow (no CI signing/notarization pipeline yet).
