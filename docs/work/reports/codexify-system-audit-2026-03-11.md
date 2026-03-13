# Codexify System Audit

## Metadata
- Repo name: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Date of audit: 2026-03-11
- Agent/Model: Claude Opus 4.6 (qwen3-coder-plus)
- Runner/Environment: Claude Code CLI
- Git branch: codex/apply-campaign-task-execution-rules
- Git commit hash: a0b2b21029b3dc43e72635e35bd1516142ff357d

## Executive Summary
- [RISK] Missing local embedding model configuration leads to runtime failures unless CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK is enabled
- [RISK] Plugin system has inconsistent manifests and potential security concerns with remote plugin execution
- [WARN] RAG upload endpoint is disabled due to missing module dependency
- [WARN] Neo4j graph store integration is available but requires explicit enabling via env vars
- [WARN] Local/Stability image generation is deferred and returns 503 until implemented

## System Overview
Project purpose: Codexify is a local-first chat + knowledge workspace built around a FastAPI backend (Guardian) and a React UI. It provides thread-based chat, memory silos, document autosave and sharing, media uploads, vector search, and optional workers for background tasks.

Major subsystems:
- **Frontend**: React UI served by Vite on port 5173 (`frontend/src`)
- **Backend/API**: Guardian FastAPI backend running on port 8888 (`guardian/guardian_api.py`)
- **Data layer**: PostgreSQL for persistence (Compose `db`), with optional Neo4j for graph logging
- **Memory/RAG**: Vector store (FAISS or Chroma) used for semantic retrieval
- **Model routing**: Multi-provider LLM support with local (Ollama), OpenAI, Groq, Alibaba, and MiniMax
- **Plugin system**: Modular plugin architecture with manifest-based loading
- **Mobile/Scout integration**: Not present in this codebase

A simple text-based diagram of subsystem interactions:
```
[Frontend] <---> [Guardian API] <---> [PostgreSQL]
                      |
                [Redis Queues]
                      |
         [Vector Store (FAISS/Chroma)]
                      |
              [Optional: Neo4j]
                      |
              [LLM Providers]
```

**Subsystem status list**:
- Frontend: Implemented
- Backend/API: Implemented
- Data layer: Implemented
- Memory/RAG: Partial (Chroma/FAISS available, but RAG upload endpoint disabled)
- Model routing: Implemented
- Plugin system: Implemented
- Mobile/Scout integration: Not present

## Architecture & Module Map

**Frontend**:
- Purpose: React-based user interface
- Key modules/files: `frontend/src/`
- Public interfaces: Web UI served on port 5173
- Critical invariants: Requires API key to communicate with backend
- **Implementation status**: Implemented

**Guardian API**:
- Purpose: Main FastAPI backend application
- Key modules/files: `guardian/guardian_api.py`
- Public interfaces: REST API on port 8888 with various route modules
- Critical invariants: Requires GUARDIAN_API_KEY to start
- **Implementation status**: Implemented

**Data layer**:
- Purpose: Persistent storage using PostgreSQL
- Key modules/files: `guardian/db/models.py`, `guardian/db/migrations/`
- Public interfaces: SQLAlchemy ORM models and Alembic migrations
- Critical invariants: Schema managed via Alembic migrations, no raw DDL creation
- **Implementation status**: Implemented

**Memory/RAG**:
- Purpose: Vector-based retrieval augmented generation
- Key modules/files: `guardian/vector/store.py`, `backend/rag/embedder.py`
- Public interfaces: Search and indexing functions
- Critical invariants: Uses either FAISS or Chroma as vector store
- **Implementation status**: Partial (available but RAG upload endpoint disabled)

**Model routing**:
- Purpose: Multi-provider LLM support
- Key modules/files: `guardian/core/config.py`, `guardian/core/ai_router.py`
- Public interfaces: Centralized provider routing and configuration
- Critical invariants: Supports local (Ollama), OpenAI, Groq, Alibaba, MiniMax
- **Implementation status**: Implemented

**Plugin system**:
- Purpose: Extensible plugin architecture
- Key modules/files: `guardian/plugins/`, `plugins/`
- Public interfaces: Manifest-based plugin loading and activation
- Critical invariants: Plugins must implement PluginBase contract
- **Implementation status**: Implemented

## Data, Memory, and Retrieval Pipeline

#### Storage inventory (reality-first)
Identify **every** storage layer actually used, including:

**PostgreSQL**:
- Used for persistent data (chat threads, messages, memory, documents, etc.)
- Located in `guardian/db/models.py` with Alembic migrations
- Data stored includes user conversations, thread metadata, documents, and media references
- Data flows in through API endpoints and out via query endpoints
- Retention: Based on database retention policies

**Redis**:
- Used for task queues and task event streams
- Located in `guardian/queue/redis_queue.py`
- Data stored includes background job queues and task event streams
- Data flows in through task enqueue operations and out through worker consumption
- Retention: Short-term for task coordination

**Vector stores (FAISS/Chroma)**:
- Used for semantic retrieval and RAG
- Located in `guardian/vector/store.py` and `backend/rag/embedder.py`
- Data stored includes embeddings for semantic search
- Data flows in through embedding/indexing operations and out through search queries
- Retention: Based on vector store persistence mechanisms

**Local filesystem**:
- Used for media file storage
- Located in `guardian/core/storage.py`
- Data stored includes uploaded documents and images
- Data flows in through upload endpoints and out through download endpoints
- Retention: Based on filesystem policies

**Neo4j (optional)**:
- Used for graph-based logging and context when enabled
- Located in `guardian/graph/`
- Data stored includes knowledge graph relationships
- Data flows in through graph logging and out through graph queries
- Retention: Based on Neo4j retention policies

#### RAG / retrieval pipeline (if present)
Describes the implemented pipeline:

- **Ingestion/chunking**: Implemented via `backend/rag/embedder.py` with text processing
- **Embedding**: Models/libs include SentenceTransformers with local cache or mock backend, vectors stored in FAISS/Chroma, keyed by namespace metadata
- **Retrieval**: Query patterns include semantic search with filtering by namespace, scoring uses cosine similarity, top-k results returned
- **Prompt construction**: Retrieved context is injected during LLM completion calls
- **Persona-aware retrieval**: Not implemented - namespaces used instead for scoping
- **Implementation status**: Partial - embedding and retrieval implemented but RAG upload endpoint disabled

Explicitly evaluated behavior:
- Local-first: ✅ Implemented
- Persona-aware retrieval: ❌ Not implemented
- Minimal unnecessary data egress: ✅ Implemented with egress controls

## Persona, Agent, and Model Routing Layer

- How personas are represented: Through project-based organization and thread context, with potential for future persona-specific routing
- How persona state affects: Model selection via project context, prompt templates scoped to context, memory/retrieval limited to relevant namespaces
- Agent orchestration logic: Implemented with task-based worker system for background processing
- Boundaries between: System/Guardian ethics layers enforce authentication and authorization, user-defined personas operate within project scopes
- **Implementation status** of persona + routing features: Partial - basic routing implemented but advanced persona features are planned

## Security, Privacy, and Sovereignty

#### Secrets management
- Where secrets live: In `.env` files, protected by `.gitignore`
- No hardcoded secrets found in codebase

#### Data egress map (code-evidenced)
| Outbound call site (file:line) | Destination (host/domain or local service) | Data classes sent (prompt, embeddings, persona state, files, telemetry) | Controls/gates (consent flags, redaction, minimization, allowlists) | Risk rating ([RISK]/[WARN]) |
|---|---|---|---|---|
| LLM provider calls (`guardian/core/ai_router.py`) | OpenAI, Groq, Alibaba, MiniMax endpoints | Prompts and context data | `CODEXIFY_LOCAL_ONLY_MODE`, `CODEXIFY_EGRESS_ALLOWLIST`, `ALLOW_CLOUD_PROVIDERS` | [WARN] |
| Image gen calls (`guardian/image_gen/providers/openai.py`) | OpenAI/Stability endpoints | Image prompts and parameters | `CODEXIFY_EGRESS_ALLOWLIST` gates access | [WARN] |

#### Access control / multi-user considerations
- Authentication via API keys with multiple key support
- Tenant isolation through project-based data separation
- Potential weak points: Direct database access could bypass API-level controls

## Docs ↔ Code Consistency

**Doc claims that do not match code**:
- Some documentation describes RAG upload endpoint as working, but code shows it as disabled due to missing module dependency
- Some docs suggest advanced persona features exist but code shows basic persona implementation

**Code paths not described in docs**:
- Advanced plugin system with manifest validation
- Vector store switching between FAISS and Chroma
- Multiple egress control layers

## Code Quality, Testing, and DX

- TypeScript strictness: N/A (Python backend)
- Lint/format setup: Black, Flake8, and Prettier configured
- Test suites: Comprehensive pytest suite with unit and integration tests
- Dev experience: Good with Makefile commands and Docker Compose setup

## Performance and Scalability

- Hot paths include LLM API calls and vector search operations
- Potential optimizations through embedding caching and query optimization
- Current implementation uses synchronous operations for most flows
- Redis-based task queues provide asynchronous processing for heavy operations

## Risk Register & Recommendations

| ID | Area | Description | Impact | Likelihood | Effort | Suggested Next Action | Evidence (file paths + line ranges where possible) | Status |
|---|---|---|---|---|---|---|---|---|
| RISK-001 | Embedding | Missing local embedding model causes runtime failures | High | Medium | Low | Configure embedding model or enable fallback | `backend/rag/embedder.py:260-267` | Partial |
| RISK-002 | Plugins | Inconsistent plugin manifests may cause security issues | Medium | Low | Medium | Standardize plugin manifest schema | `guardian/plugins/plugin_manifest.py` | Implemented |
| WARN-001 | RAG | Upload endpoint disabled due to missing module | Medium | High | Medium | Implement missing module or remove endpoint | `guardian/routes/migration.py` | Stubbed |
| WARN-002 | Image Gen | Local image generation not implemented | Low | Medium | High | Implement local image generation or document cloud setup | `guardian/image_gen/providers/local.py:17-22` | Partial |
| WARN-003 | Graph | Neo4j integration requires explicit enabling | Medium | High | Low | Document graph integration requirements | `guardian/guardian_api.py:380-390` | Partial |

**Phase 1: Critical fixes**
1. Ensure local embedding model is properly configured or fallback is enabled
2. Address RAG upload endpoint issues

**Phase 2: Important improvements**
1. Enhance plugin security with standardized manifest validation
2. Implement local image generation or better document cloud setup

**Phase 3: Nice-to-have refinements**
1. Expand persona-aware retrieval capabilities
2. Add advanced graph-based context features

## Model Notes

- Which model/agent: Claude Opus 4.6 (qwen3-coder-plus)
- Tooling limitations: Could not run tests during audit process
- Areas that look planned/stubbed: Advanced persona features, enhanced RAG functionality, local image generation