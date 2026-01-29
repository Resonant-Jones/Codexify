# Codexify

<div align="center">

**AI-Powered Conversation Orchestration & Knowledge Management Platform**

[![Python Tests](https://github.com/Resonant-Jones/Codexify/workflows/Guardian%20CI/badge.svg)](https://github.com/Resonant-Jones/Codexify/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Where memory meets intelligence, and context becomes wisdom.*

[Quick Start](#-quick-start) • [Documentation](#-documentation) • [Architecture](#-architecture) • [Contributing](#-contributing)

</div>

---

## 🌟 Overview

Codexify is a **local-first, AI-powered conversation and knowledge management platform** that combines retrieval-augmented generation (RAG), semantic memory, and multi-provider LLM orchestration into a unified system. Built for developers, researchers, and organizations who need intelligent conversation management with enterprise-grade data sovereignty.

Unlike cloud-based AI platforms, Codexify runs **entirely on your infrastructure**—from local Docker containers to on-premise deployments—ensuring your data never leaves your control.

### What Makes Codexify Different

- **🧠 Multi-Silo Memory System**: Ephemeral, midterm, and long-term memory silos with semantic search
- **🔌 Extensible Plugin Architecture**: Build custom agents, analyzers, and integrations
- **📊 Hybrid Database Strategy**: PostgreSQL for structured data, ChromaDB for vectors; Neo4j is optional/experimental and deferred for MVP graph context
- **🎯 Provider-Agnostic AI**: Switch between Groq, OpenAI, Anthropic, Gemini, or self-hosted models
- **⚡ Event-Sourced Design**: Reliable event bus with outbox pattern for distributed workflows
- **🔐 Local-First Security**: No cloud dependencies, full data sovereignty, encrypted at rest
- **🎨 Modern Stack**: FastAPI, React 19, TypeScript, Tailwind, Tauri desktop app

---

## ✨ Key Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Conversational AI** | Multi-turn chat with streaming responses, context management, and thread hierarchies |
| **RAG Orchestration** | Vector search, semantic caching, and hybrid retrieval across multiple knowledge bases |
| **Memory Management** | Three-tiered memory system (ephemeral/midterm/longterm) with auto-consolidation |
| **Knowledge Graph** | Optional Neo4j graph (experimental; disabled by default for context reasoning) |
| **Connector Framework** | Sync data from GitHub, Google Drive, Notion, and custom sources |
| **Plugin System** | Extend functionality with pattern analyzers, memory analyzers, and custom tools |
| **Project Workspaces** | Organize conversations, documents, and memory by project context |
| **Audit Trail** | Complete event sourcing and audit logs for compliance and debugging |

### AI Capabilities

- **Multi-Provider Support**: Groq, OpenAI, Anthropic Claude, Google Gemini, DeepSeek, Ollama
- **Streaming Generation**: Real-time token streaming with Server-Sent Events
- **Semantic Search**: ChromaDB and FAISS-backed vector search with sentence-transformers
- **Smart Summarization**: Auto-generate thread summaries and memory consolidations
- **Context Management**: Intelligent token budget management and context window optimization

### Developer Experience

- **RESTful API**: FastAPI with auto-generated OpenAPI docs at `/docs`
- **CLI Tools**: Rich terminal UI for memory management, diagnostics, and development
- **Desktop App**: Tauri-based native application for macOS, Linux, and Windows
- **Live Reload**: Vite HMR for frontend, Uvicorn auto-reload for backend
- **Type Safety**: Full TypeScript frontend, Python type hints with MyPy validation
- **Pre-commit Hooks**: Automated linting, formatting, and security checks

---

## 🏗 Architecture

Codexify follows a **multi-tier architecture** with clear separation of concerns and event-driven communication.

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React + TypeScript UI]
        Desktop[Tauri Desktop App]
    end

    subgraph "API Gateway"
        FastAPI[FastAPI Server<br/>Port 8888]
    end

    subgraph "Core Services"
        Router[AI Router<br/>Provider Selection]
        Memory[Memory System<br/>3-Tier Silos]
        Chat[Chat Manager<br/>Thread Orchestration]
        RAG[RAG Engine<br/>Semantic Search]
        Connectors[Connector Framework<br/>External Sync]
        Plugins[Plugin Registry<br/>Extensible Agents]
    end

    subgraph "Storage Layer"
        PG[(PostgreSQL<br/>Structured Data)]
        Neo[(Neo4j<br/>Optional Graph)]
        Vector[(ChromaDB<br/>Vector Store)]
    end

    subgraph "External Services"
        LLM[LLM Providers<br/>Groq/OpenAI/Claude]
        Integrations[Integrations<br/>GitHub/GDrive/Notion]
    end

    UI --> FastAPI
    Desktop --> FastAPI
    FastAPI --> Router
    FastAPI --> Memory
    FastAPI --> Chat
    FastAPI --> RAG
    FastAPI --> Connectors
    FastAPI --> Plugins

    Router --> LLM
    Connectors --> Integrations

    Memory --> PG
    Memory --> Vector
    Chat --> PG
    Chat --> Neo
    RAG --> Vector
    RAG --> Neo
    Connectors --> PG
    Plugins --> PG

    style FastAPI fill:#4CAF50
    style PG fill:#336791
    style Neo fill:#00857C
    style Vector fill:#FF6B6B
    style LLM fill:#FFD93D
```

### Data Flow

1. **User Request** → React UI or CLI sends request to FastAPI
2. **Routing** → API layer routes to appropriate service (Chat, Memory, RAG, etc.)
3. **AI Processing** → Router selects optimal LLM provider and streams response
4. **Memory Update** → Conversation context stored in PostgreSQL + vectorized
5. **Event Emission** → Events written to outbox table for async processing
6. **Graph Update (optional)** → Relationships indexed in Neo4j when graph logging/context is enabled

---

### Decision: Neo4j Deferred Post-MVP

Neo4j-backed graph context is optional and disabled by default. The MVP does not depend on Neo4j for chat context, and graph logging/backfill remain experimental. We will revisit full graph enrichment post-MVP.

---

## ✅ Coherence Contract

Codexify treats **meaning** as the only valid trigger for downstream updates.

- **Identity vs Meaning**: Object identity, timestamps, or empty payloads are not meaningful changes.
- **Eventual Consistency Boundaries**: SSE/outbox events are authoritative for live UI; API fetches reconcile drift.
- **Semantic Guards > Debounce**: Prefer explicit equality checks at producers/consumers over throttle hacks.

---

## 🚀 Quick Start

### Prerequisites

- **Docker** (20.10+) and **Docker Compose** (v2.0+)
- **Node.js** (20+) with **pnpm** (9+)
- **Python** (3.10, 3.11, or 3.12)
- **Make** (optional, for convenience commands)

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/Resonant-Jones/Codexify.git
cd Codexify

# Copy environment template
cp .env.example .env

# Edit .env with your API keys (at minimum, set GROQ_API_KEY or OPENAI_API_KEY)
nano .env
```

### 2. Start the Stack

```bash
# Option A: Using Docker Compose (recommended for first run)
docker-compose up -d

# Option B: Using Make targets
make dev

# This starts:
# - PostgreSQL (port 5432)
# - Neo4j (optional; 7474 web, 7687 bolt)
# - Backend API (port 8888)
# - Frontend dev server (port 5173)
```

### Backfill Workers (Embeddings + Graph)

Backfill workers run as one-shot services at startup and exit when complete.
They never block API startup and are safe to re-run.

- Automatic startup: `embedding-backfill` runs on `docker compose up`; `graph-backfill` runs only when Neo4j is enabled (deferred for CORE LOOP).
- Manual run: `docker compose run --rm embedding-backfill` or `docker compose run --rm graph-backfill` (graph is optional).
- Status: `GET /backfill/status` (API) or `python -m guardian.cli backfill:status`
- No-work behavior: logs a clear `no_work` exit reason and exits 0

### 3. Verify Installation

```bash
# Check backend health
curl http://localhost:8888/healthz

# Check frontend
open http://localhost:5173

# View API documentation
open http://localhost:8888/docs
```

### 4. Database Migrations (Canonical Workflow)

Migrations run automatically via the `migrator` service in Docker Compose. When running Alembic manually, **always run it via Docker**; the backend container is the canonical execution environment.

Correct commands (run from the repo root):

```bash
docker compose exec backend alembic -c backend/alembic.ini current
docker compose exec backend alembic -c backend/alembic.ini history
docker compose exec backend alembic -c backend/alembic.ini upgrade head
```

Incorrect command (will fail):

```bash
alembic current
```

Why it fails: running bare `alembic` on the host does not load `backend/alembic.ini`, so Alembic cannot find `script_location` and exits with `No 'script_location' key found in configuration`.

### 5. Create Your First Chat

```bash
# Using the CLI
guardian chat create --title "My First Chat"

# Or via API
curl -X POST http://localhost:8888/api/threads \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "title": "My First Chat"}'
```

---

## 📥 ChatGPT Migration

Bring your ChatGPT conversation history into Codexify with a simple upload.

### Quick Migration (UI - Recommended)

1. Export your data from [ChatGPT Settings → Data Controls](https://chat.openai.com/settings)
2. Extract `conversations.json` from the downloaded archive
3. Open Codexify UI at <http://localhost:5173>
4. Go to **Settings → Import** and upload your file

Your conversations appear immediately and become searchable as embeddings are created.

### CLI Migration (Advanced)

For automation or headless environments:

```bash
# Place your export in the data/ directory
mkdir -p data && cp conversations.json data/

# Run the migration
docker compose run --rm --profile cli chatgpt-migrate --file /data/conversations.json
```

### API Migration

```bash
curl -X POST http://localhost:8888/upload-chatgpt-export \
  -H "X-User-Id: me" \
  -H "X-Api-Key: ${GUARDIAN_API_KEY}" \
  -F "file=@./conversations.json"
```

For detailed instructions, troubleshooting, and advanced options, see the [ChatGPT Migration Guide](docs/CHATGPT_MIGRATION_GUIDE.md).

---

## 💻 Development Workflow

### Initial Setup

```bash
# 1. Install Python dependencies
python -m pip install -e .
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt  # Dev dependencies

# 2. Install frontend dependencies
cd frontend/src
pnpm install

# 3. Install pre-commit hooks
cd ../..
pip install pre-commit
pre-commit install

# 4. Verify setup
make check  # Runs format + lint + tests
```

### Daily Development

```bash
# Start backend with live reload
make run
# Or: uvicorn guardian.server.run:app --reload --port 8888

# Start frontend with HMR
cd frontend/src
pnpm dev

# Run tests on change
pytest --watch guardian/tests/

# Format and lint before committing
make format  # Black + isort
make lint    # Ruff + MyPy

# Or let pre-commit handle it
git commit -m "feat: add new feature"  # Hooks run automatically
```

### Working with Databases

```bash
# Create a new migration
alembic revision --autogenerate -m "add new table"

# Review and edit migration in guardian/db/migrations/versions/

# Apply migration
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Seed database with test data
python backend/scripts/seed_db.py
```

### Plugin Development

```bash
# Scaffold a new plugin
make init-plugin name=my_analyzer

# This creates:
# guardian/plugins/my_analyzer/
#   ├── __init__.py
#   ├── manifest.yaml
#   ├── my_analyzer.py
#   └── tests/

# List installed plugins
make plugins

# Run a specific plugin
make plugin name=my_analyzer args="--help"
```

---

## 🧪 Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=guardian --cov-report=html
open htmlcov/index.html

# Run specific test file
pytest guardian/tests/test_contracts.py

# Run tests matching pattern
pytest -k "test_chat"

# Run with network tests enabled (requires API keys)
ALLOW_NET_TESTS=1 pytest

# Skip slow tests
pytest -m "not slow"
```

### Frontend Tests

```bash
cd frontend/src

# Run unit tests
pnpm test

# Run with coverage
pnpm test:coverage

# Run E2E tests (Cypress)
pnpm test:e2e

# Run linter
pnpm lint

# Type check
pnpm type-check
```

### CI/CD

Tests run automatically on GitHub Actions for:
- Python 3.10, 3.11, 3.12
- Frontend linting, build, and tests
- Database schema validation
- Security scanning with Bandit

See `.github/workflows/guardian-ci.yml` for full pipeline.

---

## 🛠 Tech Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | Core language |
| **FastAPI** | 0.119.1 | REST API framework |
| **SQLAlchemy** | 2.0.44 | ORM for PostgreSQL |
| **Alembic** | 1.17.0 | Database migrations |
| **PostgreSQL** | 15 | Primary database |
| **Neo4j** | 5 (optional) | Knowledge graph (experimental; disabled by default) |
| **ChromaDB** | 1.2.1 | Vector storage |
| **LangChain** | 1.0.2 | LLM orchestration |
| **Pydantic** | 2.x | Data validation |
| **Uvicorn** | 0.38.0 | ASGI server |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.1.1 | UI framework |
| **TypeScript** | 5.x | Type-safe JavaScript |
| **Vite** | 5.x | Build tool & dev server |
| **Tailwind CSS** | 4.1.14 | Utility-first CSS |
| **Monaco Editor** | 0.53.0 | Code editing |
| **React Force Graph** | 1.48.1 | Graph visualization |
| **DOMPurify** | 3.3.0 | XSS protection |

### AI/ML Stack

| Provider/Tool | Purpose |
|---------------|---------|
| **Groq** | Fast inference (default) |
| **OpenAI** | GPT-4, GPT-3.5 models |
| **Anthropic** | Claude models |
| **Google Gemini** | Multimodal capabilities |
| **Sentence Transformers** | Local embeddings |
| **FAISS** | Fast vector search |
| **Torch** | ML framework |

### Development Tools

- **Ruff** + **Black** + **isort**: Code formatting
- **MyPy**: Static type checking
- **Bandit**: Security linting
- **pytest**: Testing framework
- **pre-commit**: Git hooks
- **Docker Compose**: Local orchestration

---

## 📁 Folder Structure

```
Codexify/
├── guardian/                 # Core Python backend
│   ├── api/                 # FastAPI route handlers
│   ├── core/                # Business logic (db, ai_router, event_bus)
│   ├── db/                  # SQLAlchemy models + migrations
│   ├── server/              # FastAPI app configuration
│   ├── plugins/             # Extensible plugin system
│   ├── connectors/          # External service integrations
│   ├── memory/              # Memory system implementation
│   ├── cli/                 # Command-line interfaces
│   ├── tui/                 # Terminal UI with Textual
│   ├── tests/               # Backend test suite
│   └── config/              # Configuration management
│
├── frontend/src/            # React + TypeScript UI
│   ├── components/          # Reusable React components
│   ├── pages/               # Page-level components
│   ├── main.tsx             # React entry point
│   ├── vite.config.ts       # Vite configuration
│   ├── tailwind.config.ts   # Tailwind CSS config
│   └── package.json         # Frontend dependencies
│
├── src-tauri/               # Tauri desktop application
│   ├── src/                 # Rust backend for desktop
│   └── Cargo.toml           # Rust dependencies
│
├── backend/                 # Backend configuration
│   ├── Dockerfile           # Backend container image
│   ├── requirements.txt     # Python dependencies
│   ├── alembic.ini          # Migration configuration
│   ├── migrations/          # Alembic migration files
│   └── scripts/             # Seed scripts, utilities
│
├── docs/                    # Documentation
│   ├── DB_POSTGRES_ONLY.md # Database architecture
│   ├── CLI/                 # CLI documentation
│   ├── Plugins/             # Plugin development guide
│   ├── prompt-docs/         # Prompt engineering
│   └── infra/               # Infrastructure guides
│
├── .github/workflows/       # CI/CD pipelines
├── docker-compose.yml       # Full stack orchestration
├── Makefile                 # Development convenience commands
├── pyproject.toml           # Python project metadata
├── .pre-commit-config.yaml  # Git hook configuration
└── .env.example             # Environment variable template
```

---

## 🔑 Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://guardian:guardian@localhost:5432/guardian
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# API Authentication
GUARDIAN_API_KEY=your_secure_api_key_here

# LLM Provider (choose one or more)
LLM_PROVIDER=groq  # Options: groq, openai, anthropic, gemini
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GENAI_API_KEY=...  # Google Gemini

# Optional: External Integrations
NOTION_API_KEY=secret_...
GITHUB_TOKEN=ghp_...

# Optional: Embeddings
EMBEDDING_BACKEND=sentence-transformers  # or "stub" for testing
EMBEDDING_DIM=384
```

See `.env.example` for complete list with descriptions.

---

## 📚 Documentation

### Quick Links

- **[Database Architecture](docs/DB_POSTGRES_ONLY.md)** - Schema design, migrations, and best practices
- **[Completion Pipeline](docs/architecture/completion_pipeline.md)** - End-to-end completion flow and context/prompt assembly
- **[API Documentation](http://localhost:8888/docs)** - Interactive OpenAPI docs (run locally)
- **[Plugin Development](docs/Plugins/)** - Build custom agents and tools
- **[CLI Guide](docs/CLI/)** - Command-line interface reference
- **[Infrastructure](docs/infra/)** - Deployment and scaling guides

### Additional Resources

- **[PostgreSQL Setup Guide](guardian/db/SETUP_GUIDE.md)** - Database installation and configuration
- **[Prompt Engineering](docs/prompt-docs/)** - Optimize your LLM interactions
- **[Refactor Summary](POSTGRES_REFACTOR_SUMMARY.md)** - Recent architecture changes

---

## 🤝 Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, or improving documentation, your help makes Codexify better.

### Getting Started

1. **Fork the repository** and clone your fork
2. **Create a feature branch**: `git checkout -b feat/my-new-feature`
3. **Make your changes** and add tests
4. **Run the test suite**: `make check`
5. **Commit with conventional commits**: `git commit -m "feat: add new feature"`
6. **Push to your fork**: `git push origin feat/my-new-feature`
7. **Open a Pull Request** with a clear description

### Development Standards

- ✅ All tests must pass (`pytest` and `pnpm test`)
- ✅ Code must pass linting (`make lint`)
- ✅ Format with Black and isort (`make format`)
- ✅ Add tests for new features
- ✅ Update documentation as needed
- ✅ Follow conventional commit format
- ✅ Pre-commit hooks must pass

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new memory consolidation algorithm
fix: resolve token count overflow in chat context
docs: update API documentation for /embeddings endpoint
test: add integration tests for optional graph connector
refactor: simplify plugin loading mechanism
chore: update dependencies to latest versions
```

### Code of Conduct

Be respectful, inclusive, and collaborative. We're building something meaningful together.

For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md) *(coming soon)*.

---

## 🔒 Security

### Reporting Vulnerabilities

If you discover a security vulnerability, please email **security@catalystlabs.ai** instead of opening a public issue. We take security seriously and will respond promptly.

### Security Features

- 🔐 API key authentication with environment-based secrets
- 🛡️ Input validation with Pydantic models
- 🔍 SQL injection protection via SQLAlchemy ORM
- 🎭 Log scrubbing for sensitive filenames and credentials
- 🔒 Private key detection in pre-commit hooks
- ✅ Security linting with Bandit
- 🌐 CORS middleware with configurable origins

---

## 📊 Project Status

**Current Version**: 0.1.0 (Beta)
**Status**: Active Development
**Last Updated**: November 2025

### Recent Milestones

- ✅ Postgres-only architecture (October 2025)
- ✅ Alembic migration system
- ✅ Multi-provider AI routing
- ✅ Plugin architecture v1
- 🟡 Neo4j graph scaffolding (optional; deferred for MVP context)
- ✅ React 19 frontend upgrade

### Roadmap

- 🚧 WebSocket collaboration (document editing only; broader real-time updates planned)
- 🚧 Advanced RAG with hybrid search
- 🚧 Fine-tuning support for local models (roadmap)
- 🚧 Multi-user authentication & RBAC (roadmap)
- 🚧 Kubernetes deployment guides
- 🚧 Plugin marketplace (roadmap)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with ❤️ by **[Resonant Constructs LLC](https://catalystlabs.ai)** and the Codexify community.

### Core Technologies

Special thanks to the teams behind:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - Frontend excellence
- [PostgreSQL](https://www.postgresql.org/) - Reliable data storage
- [Neo4j](https://neo4j.com/) - Graph database innovation
- [LangChain](https://www.langchain.com/) - LLM orchestration

---

## 📬 Contact & Community

- **Website**: [catalystlabs.ai](https://catalystlabs.ai)
- **Documentation**: [docs.codexify.io](https://docs.codexify.io) *(coming soon)*
- **Issues**: [GitHub Issues](https://github.com/Resonant-Jones/Codexify/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Resonant-Jones/Codexify/discussions)
- **Email**: dev@catalystlabs.ai

---

<div align="center">

**Star ⭐ this repo if Codexify helps your work!**

*"In the convergence of memory and intelligence, we find not just answers, but understanding."*

</div>
