# Codexify

Codexify is a local-first chat + knowledge workspace built around a FastAPI backend (Guardian) and a React UI. It provides thread-based chat, memory silos, document autosave and sharing, media uploads, vector search, and optional workers for background tasks. Docker Compose is the primary, supported way to run the full stack.

### TL;DR — Start Here

If you want to **run Codexify locally** with the least friction:

* Use **Docker Compose**
* Copy `.env.template → .env`
* `.env` is local-only; never commit it (templates are the source of truth)
* Set `GUARDIAN_API_KEY`, `NEO4J_PASS`, and your local LLM settings
* Run: `docker compose up --build`
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
- **Embeddings API** `/api/embeddings` returns **dummy vectors** (deterministic mock) and is not backed by real models.
- **Local image generation** returns a 1x1 placeholder image unless an external provider is configured.
- **TTS**: API uses a **mock local provider** (sine wave). A separate HuggingFace TTS microservice exists (`backend/tts_service`) but is not integrated into the main API.
- **Desktop app** (Tauri) is a skeleton config (`src-tauri`) without a published build pipeline.

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
LLM_PROVIDER=openai   # or groq
OPENAI_API_KEY=...
# GROQ_API_KEY=...
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

## Runtime Topology

**Always-on containers (Compose default)**
- `db` -> Postgres 15
- `redis` -> task queues + task events
- `neo4j` -> optional graph store (but required by default Compose)
- `backend` -> FastAPI app (Guardian)
- `frontend` -> Vite dev server
- `worker-chat` -> background chat task worker
- `worker-warmup` -> warm-up worker for local models
- `tts` -> separate FastAPI TTS microservice

**One-shot containers**
- `migrator` -> runs Alembic + seed defaults, then exits
- `graph-init` -> applies Neo4j constraints + seed nodes, then exits

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
4. Backend starts, verifies required tables, seeds defaults again, then serves API
5. Workers start (Redis required)

## Repo Structure (Truthful)

- `guardian/` - **Main backend package** (FastAPI app, routes, DB logic, workers, plugins, providers).
- `backend/` - Dockerfile, Alembic config, RAG embedder, and **separate** TTS microservice.
- `frontend/` - React + Vite app (source in `frontend/src`).
- `src-tauri/` - Tauri desktop shell (not a published app yet).
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
- `ALLOW_CLOUD_PROVIDERS=true` + `OPENAI_API_KEY` or `GROQ_API_KEY`
- `CODEXIFY_VECTOR_STORE=chroma|faiss`
- `CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=1` (allow mock embeddings if local model fails)
- `GUARDIAN_ENABLE_GRAPH_CONTEXT=true` / `GUARDIAN_ENABLE_GRAPH_LOGGING=true`
- `ENABLE_CONNECTOR_WORKER=true` (and provider tokens like `GITHUB_TOKEN`)
- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation)
- `ELEVENLABS_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` (real TTS)

## Development Workflow (As It Exists)

### Running tests
- Two test trees exist: `guardian/tests` (large) and `tests` (smaller).
- The **Makefile test target is broken**: it references `tests/run_tests.py` which does not exist.
- Use pytest directly instead:

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
- Embeddings API returns mock vectors; not production-ready.
- Local image generation is a placeholder; real providers require env setup.
- TTS microservice exists but is not integrated into the main API.
- Desktop/Tauri app is not production-ready.

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
- **SECURITY.md**
- **SECURITY_HARDENING_PLAN.md**
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

* **SECURITY.md**
* **SECURITY_HARDENING_PLAN.md**
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
* Embeddings API returns mock vectors; not production-ready.
* Local image generation is a placeholder; real providers require env setup.
* TTS microservice exists but is not integrated into the main API.
* Desktop/Tauri app is not production-ready.
