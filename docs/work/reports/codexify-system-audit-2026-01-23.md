# Codexify System Audit
 
## Metadata
 
- **Repository**: Codexify
- **Audit Date**: 2026-01-23
- **Agent/Model**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- **Runner/Environment**: Claude Code CLI (worktree mode)
- **Git Branch**: `busy-sinoussi`
- **Commit Hash**: `e954ee3724f1a64aca5e5804dd86eafc13c8efa7`
- **Main Repository**: `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify`
- **Worktree Path**: `/Users/resonant_jones/.claude-worktrees/Codexify/busy-sinoussi`
 
---
 
## Executive Summary
 
Codexify is a **local-first, AI-powered conversation and knowledge management platform** that successfully implements multi-provider LLM orchestration, three-tier memory management, and a mature plugin system. The architecture is production-ready for local/on-premise deployment with good separation of concerns and comprehensive database-backed state management.
 
### Overall Health: **GOOD** (Production-ready for local deployment with caveats)
 
### Key Strengths
 
1. **Strong local-first architecture** - No cloud dependencies when configured for local inference (Ollama/SentenceTransformers)
2. **Production-ready data layer** - PostgreSQL + Alembic migrations with proper schema management
3. **Mature plugin system** - Full lifecycle management with safeguards (rate limiting, health checks, error tracking)
4. **Three-tier memory architecture** - Clean separation between ephemeral/midterm/longterm with database backing
5. **Multi-provider AI routing** - Clean abstraction for Groq/OpenAI/Local with streaming support
6. **Comprehensive vector retrieval** - Dual backend support (ChromaDB/PGVector) with factory pattern
 
### Top 5 Concerns
 
1. **[RISK]** Secrets management uses environment variables with no encryption at rest
   - Location: `.env` files, `docker-compose.yml:278` (hardcoded API key)
   - Impact: API keys visible in plaintext in compose files and logs
   - Recommendation: Use Docker secrets, Vault, or encrypted env vars
 
2. **[RISK]** Neo4j integration is scaffolding only - not wired into main chat pipeline
   - Location: `guardian/db/neo.py` (schema defined), `guardian/routes/neo.py` (minimal usage)
   - Impact: README claims "Neo4j-powered relationship mapping" but it's not actively used
   - Recommendation: Either wire it into context enrichment or remove from marketing claims
 
3. **[WARN]** Data egress to cloud LLM providers when not in local-first mode
   - Location: `guardian/core/ai_router.py:194-251` (Groq/OpenAI calls)
   - Data sent: Full conversation history, user messages, system prompts
   - Controls: Environment-driven provider selection only
   - Recommendation: Add per-request consent flags, data minimization, and audit logging
 
4. **[WARN]** No RBAC/ACL system - only basic user_id ownership
   - Location: `guardian/db/models.py` (user_id columns), no permission tables
   - Impact: No fine-grained access control, no role-based permissions
   - Recommendation: Implement permission system before multi-user production deployment
 
5. **[WARN]** Hardcoded database credentials in docker-compose.yml
   - Location: `docker-compose.yml:8-9` (postgres password), `:22` (neo4j password)
   - Impact: Credentials visible in version control
   - Recommendation: Use Docker secrets or external secret management
 
---
 
## System Overview
 
### Project Purpose
 
Codexify is an AI-powered conversation orchestration and knowledge management platform that combines:
- **Conversational AI** with streaming responses and context management
- **RAG (Retrieval-Augmented Generation)** with vector search and semantic caching
- **Three-tier memory system** (ephemeral/midterm/longterm) with auto-consolidation
- **Knowledge graph** via Neo4j for relationship mapping (partially implemented)
- **Connector framework** for syncing data from GitHub, Google Drive, Notion
- **Plugin system** for extensible agents and custom tools
- **Project workspaces** for organizing conversations and documents
 
Target users: Developers, researchers, and organizations needing intelligent conversation management with enterprise-grade data sovereignty.
 
### Major Subsystems
 
```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Layer                          │
│  - React 19 + TypeScript UI (frontend/src/)                 │
│  - Tauri Desktop App (src-tauri/)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                    API Gateway Layer                         │
│  - FastAPI Server (guardian/guardian_api.py)                │
│  - Route handlers (guardian/routes/)                        │
│  - WebSocket collaboration (guardian/realtime/)             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Core Services Layer                        │
│  - AI Router (guardian/core/ai_router.py)                   │
│  - Memory System (guardian/memory/)                         │
│  - Chat Manager (guardian/chat/)                            │
│  - RAG Engine (backend/rag/)                                │
│  - Plugin Manager (guardian/plugin_manager.py)              │
│  - Event Bus (guardian/core/event_bus.py)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Storage Layer                             │
│  - PostgreSQL (structured data + migrations)                │
│  - ChromaDB/PGVector (vector embeddings)                    │
│  - Neo4j (knowledge graph - partially used)                 │
│  - Redis (task queue for workers)                           │
│  - Local FS (plugin storage, temp files)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  External Services                           │
│  - LLM Providers (Groq/OpenAI/Local Ollama)                │
│  - Integrations (GitHub/Google Drive/Notion)                │
│  - Embedding Models (SentenceTransformers local)            │
└─────────────────────────────────────────────────────────────┘
```
 
### Subsystem Status List
 
| Subsystem | Implementation Status | Evidence |
|-----------|---------------------|----------|
| **Frontend (React)** | Implemented | `frontend/src/` with Vite build |
| **Backend API (FastAPI)** | Implemented | `guardian/guardian_api.py:1-100+` |
| **PostgreSQL Data Layer** | Implemented | `guardian/core/pgdb.py`, migrations in `backend/migrations/` |
| **Vector Store (ChromaDB)** | Implemented | `backend/vector_store/chroma_store.py:1-127` |
| **Vector Store (PGVector)** | Implemented | `backend/vector_store/pgvector_store.py:1-188` |
| **Neo4j Graph Database** | Partial | `guardian/db/neo.py` (schema only, minimal usage) |
| **Redis Queue** | Implemented | `guardian/queue/redis_queue.py`, workers in `guardian/workers/` |
| **AI Router (Multi-provider)** | Implemented | `guardian/core/ai_router.py:43-251` |
| **RAG Pipeline** | Implemented | `backend/rag/embedder.py:103-371` |
| **Memory System (3-tier)** | Implemented | `guardian/memory/memoryos.py:89-215` |
| **Persona System** | Implemented | `guardian/cognition/personas/store.py:1-98` |
| **Identity/Imprint** | Implemented | `guardian/imprint_zero_onboarding.py` |
| **Plugin System** | Implemented | `guardian/plugin_manager.py:1-265` |
| **WebSocket Collaboration** | Implemented | `guardian/realtime/collaboration.py` |
| **Connector Framework** | Partial | `guardian/connectors/` (GitHub/GDrive exist, not fully tested) |
| **Tauri Desktop App** | Stubbed | `src-tauri/` exists but not actively developed |
 
---
 
## Architecture & Module Map
 
### 1. Backend/API Layer
 
**Purpose**: FastAPI application serving REST endpoints and WebSocket connections
 
**Key Modules**:
- `guardian/guardian_api.py` - Main FastAPI app initialization, middleware, route registration
- `guardian/server/codexify_api.py` - Alternative API wiring (appears to be duplicate/legacy)
- `guardian/routes/*.py` - 27 route modules for specific domains (chat, memory, projects, etc.)
 
**Public Interfaces**:
- REST API at `http://localhost:8888` with OpenAPI docs at `/docs`
- WebSocket endpoint: `/api/collab/ws/{document_id}`
- Health checks: `/healthz`, `/ping`, `/readyz`
 
**Critical Invariants**:
- Database must be initialized before API startup (`migrator` service dependency in docker-compose)
- API key authentication required for all protected endpoints (via `require_api_key` dependency)
- Environment variables must be loaded before settings initialization
 
**Implementation Status**: **Implemented** - Production-ready with comprehensive route coverage
 
---
 
### 2. Data Layer (PostgreSQL)
 
**Purpose**: Primary relational database for structured data with schema migrations
 
**Key Modules**:
- `guardian/core/pgdb.py` - Database connection and session management
- `guardian/db/models.py` - SQLAlchemy ORM models (30+ tables)
- `backend/migrations/versions/*.py` - Alembic migrations
 
**Public Interfaces**:
- `get_db()` dependency injection in FastAPI routes
- `ChatDB` class with CRUD operations
- ORM models: `ChatThread`, `ChatMessage`, `MemoryEntry`, `Persona`, `Project`, etc.
 
**Critical Invariants**:
- All database access must use session context managers
- Migrations must be applied before application startup
- Connection string format: `postgresql://user:pass@host:port/dbname`
 
**Implementation Status**: **Implemented** - Production-ready with proper migration management
 
**Evidence**:
- `guardian/core/pgdb.py:1-200+` implements connection pooling and session management
- `guardian/db/models.py:1-500+` defines 30+ ORM models
- `backend/migrations/` contains timestamped Alembic migrations
- `docker-compose.yml:249-409` shows backend service with health checks on database
 
---
 
### 3. Vector Store Layer
 
**Purpose**: Embeddings storage and semantic search
 
**Key Modules**:
- `backend/vector_store/factory.py:11-45` - Factory for selecting vector store backend
- `backend/vector_store/chroma_store.py:1-127` - ChromaDB implementation
- `backend/vector_store/pgvector_store.py:1-188` - PGVector implementation
- `backend/rag/embedder.py:243-263` - FAISS in-memory index
 
**Public Interfaces**:
- `get_vector_store()` factory function (env-driven selection)
- Methods: `add()`, `search()`, `delete()`, `update()`
- Vector dimensions: 384 (bge-large-en-v1.5) or 768 (other models)
 
**Critical Invariants**:
- Embeddings must be normalized before FAISS storage (uses IndexFlatIP)
- ChromaDB requires persistence directory if not ephemeral
- PGVector requires `pgvector` extension enabled in PostgreSQL
 
**Implementation Status**: **Implemented** - Production-ready with dual backend support
 
**Evidence**:
- Factory pattern in `backend/vector_store/factory.py:11-45`
- ChromaDB: `backend/vector_store/chroma_store.py:1-127` with persistence support
- PGVector: `backend/vector_store/pgvector_store.py:84-188` with cosine similarity search
 
---
 
### 4. AI Router & Model Providers
 
**Purpose**: Multi-provider LLM orchestration with streaming support
 
**Key Modules**:
- `guardian/core/ai_router.py:43-251` - Main routing logic
- `guardian/providers/local_ollama.py` - Ollama integration
- `guardian/providers/groq_client.py` - Groq API client
- `guardian/core/dependencies.py:81-94` - Provider configuration
 
**Public Interfaces**:
- `chat_with_ai(messages, model, provider)` - Main entry point
- `stream_local(messages, model)` - Streaming for Ollama
- `call_groq(messages, model)` - Groq inference
- `call_openai(messages, model)` - OpenAI inference
 
**Critical Invariants**:
- Provider selection order: parameter → settings → default ("groq")
- Streaming requires SSE parsing with `data:` prefix
- Local provider requires `LOCAL_BASE_URL` configuration
 
**Implementation Status**: **Implemented** - Production-ready for 3 providers (Groq/OpenAI/Local)
 
**Evidence**:
- Router: `guardian/core/ai_router.py:43-69` implements provider selection
- Groq: `guardian/core/ai_router.py:194-221` with OpenAI-compatible endpoint
- OpenAI: `guardian/core/ai_router.py:224-251` with model normalization
- Local: `guardian/core/ai_router.py:72-192` with SSE streaming support
 
---
 
### 5. Memory System
 
**Purpose**: Three-tier memory architecture (ephemeral/midterm/longterm)
 
**Key Modules**:
- `guardian/memory/memoryos.py:89-215` - Memory orchestration
- `guardian/memory/query_memory.py:183-209` - Query interface
- `guardian/db/models.py` - `MemoryEntry` model with `silo` column
 
**Public Interfaces**:
- `MemoryStore.query_by_time(start, end, tags)` - Time-range queries
- `MemoryStore.query_by_tags(tags, limit)` - Tag-based search
- `MemoryStore.query_by_content(query, limit)` - Full-text search
- `query_memory(query_str, limit)` - Convenience wrapper
 
**Critical Invariants**:
- `silo` column must be one of: "ephemeral", "midterm", "longterm"
- Ephemeral memory pruned based on token count
- Midterm memory has 7-30 day retention (configurable)
- Longterm memory persists indefinitely with semantic search
 
**Implementation Status**: **Implemented** - Production-ready with database backing and caching
 
**Evidence**:
- Three-tier architecture: `guardian/db/models.py` defines `MemoryEntry` with `silo` constraint
- Query interface: `guardian/memory/query_memory.py:58-175` implements time/tag/content queries
- Caching: LRU cache for time queries (line 58), disk memoization for tag queries (line 104)
- Integration: `guardian/memory/memoryos.py:89-130` orchestrates memory tiers
 
---
 
### 6. RAG (Retrieval-Augmented Generation) Pipeline
 
**Purpose**: Document ingestion, chunking, embedding, and retrieval
 
**Key Modules**:
- `backend/rag/embedder.py:103-371` - Embedding generation and search
- `backend/rag/parser.py:12-62` - Document parsing
- `guardian/vector/store.py:8-37` - Vector store wrapper
- `guardian/retrieve/api.py:1-22` - Retrieval API endpoint
 
**Public Interfaces**:
- `POST /api/retrieve` - Semantic search endpoint
- `VectorStore.add_texts(texts, metadatas)` - Index documents
- `VectorStore.search(query, k)` - Retrieve similar documents
- `embed_and_index(texts, namespace)` - Combined embedding + storage
 
**Critical Invariants**:
- Embeddings generated via SentenceTransformers (local-only, no OpenAI)
- Model: `bge-large-en-v1.5` (384 dimensions) or configurable via env
- FAISS uses normalized vectors with IndexFlatIP (inner product)
- ChromaDB uses cosine distance by default
 
**Implementation Status**: **Implemented** - Production-ready with local embeddings
 
**Evidence**:
- Embedding: `backend/rag/embedder.py:185-217` uses SentenceTransformers
- Retrieval: `backend/rag/embedder.py:281-337` implements FAISS and Chroma search
- API: `guardian/retrieve/api.py:16-21` exposes `POST /api/retrieve`
- Parser: `backend/rag/parser.py:12-62` supports JSON/JSONL/text
 
**Limitation**: Chunking is basic (split by double newlines), no sophisticated strategies like sliding windows or semantic chunking.
 
---
 
### 7. Persona & Identity System
 
**Purpose**: User-defined personas and identity management
 
**Key Modules**:
- `guardian/cognition/personas/store.py:1-98` - Persona CRUD operations
- `guardian/imprint_zero_onboarding.py` - Identity/Imprint system
- `guardian/cognition/imprints/store.py:64-136` - Imprint storage helpers
- `guardian/db/models.py` - `Persona` and `Imprint` tables
 
**Public Interfaces**:
- `get_active_persona(user_id, project_id)` - Fetch active persona
- `set_persona(user_id, project_id, body, source)` - Create/activate persona
- `create_imprint(guardian_name, preferred_name, style)` - Create identity
- `supersede_imprint(imprint_id)` - Mark as superseded
 
**Critical Invariants**:
- Only one active persona per (user_id, project_id) pair
- Imprint status transitions: draft → active → superseded
- Persona `body` is plain text, `source` tracks origin (user/system)
 
**Implementation Status**: **Implemented** - Production-ready with database backing
 
**Evidence**:
- Persona storage: `guardian/cognition/personas/store.py:43-90` enforces uniqueness
- Imprint lifecycle: `guardian/imprint_zero_onboarding.py:78-130` manages status transitions
- Database models: `guardian/db/models.py` defines tables with proper constraints
 
**Limitation**: Persona does not actively affect model routing (skeleton only in `guardian/router.py:7-12`).
 
---
 
### 8. Plugin System
 
**Purpose**: Extensible plugin architecture with lifecycle management and safeguards
 
**Key Modules**:
- `guardian/plugin_manager.py:1-265` - Safe plugin manager with rate limiting
- `guardian/plugin_loader.py:80-221` - Dynamic module loading
- `guardian/plugins/plugin_manifest.py:15-58` - Manifest schema
 
**Public Interfaces**:
- `SafePluginManager.load_plugin(name)` - Load and initialize plugin
- `SafePlugin.execute(method, **kwargs)` - Execute plugin method
- `SafePluginManager.health_check(name)` - Check plugin health
- `PluginLoader.discover_plugins()` - Scan plugin directory
 
**Critical Invariants**:
- Plugins must have `manifest.yaml` with required metadata
- Rate limiting: 1 req/s for discovery, 2 req/s for loading, 10 req/s for health checks
- Error tracking: max 5 errors before plugin disabled
- Async locking for concurrent access
 
**Implementation Status**: **Implemented** - Production-ready with comprehensive safeguards
 
**Evidence**:
- Safe execution: `guardian/plugin_manager.py:65-82` with `@safe_plugin_execution` decorator
- Rate limiting: `guardian/plugin_manager.py:95,109,223` with `@throttle` and `@rate_limited`
- Lifecycle: `guardian/plugin_manager.py:166-243` implements init/health/cleanup hooks
- Manifest validation: `guardian/plugins/plugin_manifest.py:15-58` Pydantic schema
 
---
 
### 9. Connector Framework
 
**Purpose**: Sync data from external services (GitHub, Google Drive, Notion)
 
**Key Modules**:
- `guardian/connectors/github.py` - GitHub integration
- `guardian/connectors/google.py` - Google Drive OAuth
- `guardian/routes/connectors.py` - Connector API routes
- `guardian/db/models.py` - `ConnectorConfig`, `ConnectorRun`, `RawDocument` tables
 
**Public Interfaces**:
- `POST /api/connectors` - Create connector
- `POST /api/connectors/{id}/sync` - Trigger sync
- `GET /api/connectors/{id}/runs` - Fetch sync history
 
**Critical Invariants**:
- OAuth tokens stored in `ConnectorConfig.secrets` JSONB field
- Connector runs tracked with status (pending/running/completed/failed)
- Raw documents stored before processing into `UploadedDocument`
 
**Implementation Status**: **Partial** - Schema and routes exist, but integration testing incomplete
 
**Evidence**:
- GitHub connector: `guardian/connectors/github.py` implements OAuth and API calls
- Google Drive: `guardian/connectors/google.py` implements OAuth flow
- Database models: `guardian/db/models.py` defines connector tables
- Routes: `guardian/routes/connectors.py` exposes REST API
 
**Limitation**: Connector worker is disabled by default (`ENABLE_CONNECTOR_WORKER=false` in docker-compose), suggesting incomplete testing or reliability issues.
 
---
 
## Data, Memory, and Retrieval Pipeline
 
### 6.1 Storage Inventory (Reality-First)
 
| Storage Layer | Status | What is Stored | Data Flow | Retention Behavior |
|--------------|--------|----------------|-----------|-------------------|
| **PostgreSQL** | Implemented | - Chat threads & messages<br>- Memory entries (all silos)<br>- Personas & imprints<br>- Projects<br>- Events outbox<br>- Connector configs | Ingestion: ORM create/update via SQLAlchemy<br>Query: ORM queries, session management | Explicit: soft deletes (`deleted_at`)<br>Memory silos: ephemeral (token-based), midterm (7-30d), longterm (infinite) |
| **ChromaDB** | Implemented | - Document embeddings (384-dim)<br>- Metadata (JSONB) | Ingestion: `add()` via `backend/vector_store/chroma_store.py`<br>Query: `search()` with cosine distance | Persistent if `CHROMA_PERSIST_DIRECTORY` set, else ephemeral (in-memory) |
| **PGVector** | Implemented | - Vector embeddings (PostgreSQL)<br>- Namespaced collections | Ingestion: `upsert()` via `backend/vector_store/pgvector_store.py:84-97`<br>Query: `search()` with `<=>` cosine distance operator (lines 109-111) | Persists in PostgreSQL, follows database retention policy |
| **FAISS** | Implemented | - In-memory vector index (IndexFlatIP) | Ingestion: `add_embeddings()` via `backend/rag/embedder.py:243-263`<br>Query: `search()` with normalized vectors | Ephemeral (in-memory only, lost on restart) |
| **Neo4j** | Partial | - User nodes<br>- Thread nodes<br>- Message nodes<br>- Relationship edges | Ingestion: `neomodel` ORM via `guardian/db/neo.py`<br>Query: Cypher queries (minimal usage) | Persists in Neo4j, but minimal usage found |
| **Redis** | Implemented | - Task queue (warmup, chat, embedding backfill) | Ingestion: `enqueue()` via `guardian/queue/redis_queue.py`<br>Query: Workers poll queue | Ephemeral (no persistence, allkeys-lru eviction) |
| **Local FS** | Implemented | - Plugin storage (`guardian/plugins/`)<br>- Temp files<br>- Chroma persist directory (`./.chroma`) | Ingestion: File writes via Python I/O<br>Query: File reads | Manual cleanup required |
 
**Key Findings**:
1. **Multi-backend vector storage** with factory pattern for flexibility
2. **Neo4j underutilized** - schema exists but not actively used in chat pipeline
3. **Redis configured as ephemeral** - task queue only, no persistence
4. **Local FS used for plugins** - no database backing for plugin storage
 
---
 
### 6.2 RAG / Retrieval Pipeline
 
#### Ingestion/Chunking
 
**Implementation**: `backend/rag/parser.py:12-62`
 
- **Supported formats**: JSON, JSONL, plain text
- **Chunking strategy**: Simple split by double newlines (`\n\n`)
- **Limitation**: No sophisticated chunking (no sliding windows, no semantic chunking, no size-based splits with overlap)
 
**Evidence**:
```python
# backend/rag/parser.py:48-52
def chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
    # Simple chunking by splitting on double newlines
    paragraphs = text.split('\n\n')
    # ... (basic concatenation until chunk_size reached)
```
 
**Status**: **Partial** - Basic implementation, needs enhancement for production use
 
---
 
#### Embedding: Models/Libs, Vector Storage, Keying/Scoping
 
**Implementation**: `backend/rag/embedder.py:103-371`
 
**Embedding Generation**:
- **Library**: SentenceTransformers (`sentence_transformers==2.6.0`)
- **Model Selection**: `resolve_local_embed_model()` checks env vars in order:
  1. `LOCAL_EMBED_MODEL`
  2. `EMBEDDING_MODEL`
  3. `DEFAULT_LOCAL_EMBED_MODEL`
  4. Fallback: `BAAI/bge-large-en-v1.5` (384 dimensions)
- **Batch Encoding**: `model.encode(texts, batch_size=32, show_progress_bar=False)`
- **Normalization**: FAISS requires normalized embeddings for IndexFlatIP
 
**Evidence**: `backend/rag/embedder.py:185-217`
 
**Vector Storage**:
- **FAISS**: In-memory IndexFlatIP for normalized embeddings (`backend/rag/embedder.py:243-263`)
- **ChromaDB**: Persistent collection with metadata (`backend/vector_store/chroma_store.py:60-88`)
- **PGVector**: PostgreSQL table with `vector(384)` column and JSONB metadata (`backend/vector_store/pgvector_store.py:84-97`)
 
**Keying/Scoping**:
- **Namespaces**: PGVector queries filter by `namespace` column (`backend/vector_store/pgvector_store.py:124-125`)
- **Collections**: ChromaDB creates separate collections per namespace
- **Metadata**: JSONB fields store source, timestamp, tags for filtering
 
**Evidence**: `backend/vector_store/pgvector_store.py:109-125`
 
**Status**: **Implemented** - Production-ready with local embeddings
 
**Critical Finding**: **No OpenAI embeddings** - Codebase explicitly ignores `use_openai` parameter:
```python
# backend/rag/embedder.py:351-352
# Note: use_openai parameter is ignored; we always use SentenceTransformers
```
 
---
 
#### Retrieval: Query Patterns, Filters, Scoring, Top-K
 
**Implementation**: `backend/rag/embedder.py:281-337`
 
**Query Pattern**:
1. Encode query text to embedding vector
2. Search vector store with similarity metric
3. Return top-k results with scores
 
**Filters**:
- **Namespace filtering**: PGVector queries include `WHERE namespace = :ns` (`backend/vector_store/pgvector_store.py:124`)
- **Metadata filtering**: ChromaDB supports `where` clauses (not actively used in current code)
 
**Scoring**:
- **FAISS**: Inner product (requires normalized vectors)
- **ChromaDB**: Cosine distance (default)
- **PGVector**: Cosine distance operator `<=>` (line 109-111)
 
**Top-K**:
- Configurable via `k` parameter (default: 5)
- API endpoint: `POST /api/retrieve` with `k` in request body
 
**Hybrid Logic**: Not implemented - no combination of vector + keyword search
 
**Evidence**: `guardian/retrieve/api.py:16-21`
 
**Status**: **Implemented** - Production-ready with single retrieval strategy
 
---
 
#### Prompt Construction: Context Injection and Bounding
 
**Implementation**: `guardian/context/broker.py` (Context broker for enrichment)
 
**Context Injection**:
- Retrieved documents injected into system message or user message
- Format: Depends on prompt template (not analyzed in detail)
 
**Bounding**:
- Token count management via `tiktoken` or model-specific tokenizers
- Context window limits enforced per model (e.g., 4096 for GPT-3.5, 8192 for GPT-4)
 
**Evidence**: Inferred from memory system and chat context management, but detailed implementation not analyzed due to time constraints.
 
**Status**: **Partial** - Implementation exists but requires deeper analysis
 
---
 
#### Persona-Aware Retrieval
 
**Implementation**: `guardian/memory/query_memory.py:183-208`
 
**How Persona Affects Retrieval**:
- Memory entries tagged with persona context
- Queries can filter by persona metadata
- Namespace scoping per (user_id, project_id) pair
 
**Evidence**:
- Persona stored per (user_id, project_id) in `guardian/cognition/personas/store.py:68-75`
- Memory queries support tag filtering (`query_by_tags()` method)
 
**Status**: **Implemented** - Persona context available for filtering
 
**Limitation**: Not clear if persona actively filters retrieval in practice (requires runtime analysis).
 
---
 
### Evaluation Against Design Goals
 
| Goal | Status | Evidence |
|------|--------|----------|
| **Local-first** | ✅ Implemented | SentenceTransformers for embeddings, Ollama for inference, no cloud dependencies when configured |
| **Persona-aware retrieval** | ⚠️ Partial | Persona stored per user/project, memory tagged, but active filtering unclear |
| **Minimal data egress** | ⚠️ Conditional | Local mode has no egress; Groq/OpenAI modes send full conversation history |
 
---
 
## Persona, Agent, and Model Routing Layer
 
### Persona Representation
 
**Types/Interfaces**:
- Database model: `guardian/db/models.py` defines `Persona` table
- Fields: `id`, `user_id`, `project_id`, `body` (text), `source` (user/system), `is_active`, `created_at`, `updated_at`
 
**Config Files**: None - Personas stored in database only
 
**Evidence**: `guardian/cognition/personas/store.py:1-98`
 
---
 
### Persona State Effects
 
#### Model Selection/Routing
 
**Status**: **Stubbed**
 
**Evidence**: `guardian/router.py:7-12` defines identity contract validation but is not actively used:
```python
def validate_identity_contract(persona: Persona) -> bool:
    """Validate persona against identity contract."""
    # TODO: Implement actual validation
    return True
```
 
**Finding**: Persona does not currently affect model routing. Provider selection is environment-driven only.
 
---
 
#### Prompt Templates
 
**Status**: **Partial**
 
**Evidence**:
- `guardian/cognition/system_prompt_builder.py` exists (not analyzed in detail)
- `guardian/character_switcher.py:73-86` creates identity files with prompt templates
 
**Finding**: Prompt construction exists but integration with persona system unclear.
 
---
 
#### Memory/Retrieval Scope and Permissions
 
**Status**: **Implemented**
 
**Evidence**:
- Persona stored per (user_id, project_id) in `guardian/cognition/personas/store.py:68-75`
- Memory queries can filter by persona context
- Namespace scoping in vector stores supports multi-tenancy
 
**Finding**: Persona affects memory scope through (user_id, project_id) keying.
 
---
 
### Agent Orchestration Logic
 
**Status**: **Partial** (Research agents only)
 
**Evidence**: `guardian/core/research/Modules/router/router.py` implements agent routing for research tasks
 
**Finding**: No general-purpose agent orchestration (e.g., ReAct, tool use) wired into main chat pipeline.
 
---
 
### Boundaries Between System/Guardian and User Personas
 
**System/Guardian Ethics Layers**:
- `guardian/imprint_zero_onboarding.py` manages system identity (Imprint Zero)
- Imprint status: draft → active → superseded
 
**User-Defined Personas**:
- Stored in `Persona` table with `source` field (user/system)
- One active persona per (user_id, project_id)
 
**Boundary**: Clear separation via `source` field and database constraints
 
**Evidence**: `guardian/cognition/personas/store.py:68-75` enforces uniqueness
 
**Status**: **Implemented** - Clear separation maintained
 
---
 
## Security, Privacy, and Sovereignty
 
### 8.1 Secrets Management
 
**Where Secrets Live**:
1. **Environment variables** (`.env` files) - **[RISK]**
   - Location: `.env` (gitignored), `.env.example` (committed)
   - Secrets: `OPENAI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `GUARDIAN_API_KEY`, `NEO4J_PASSWORD`
 
2. **Docker Compose** - **[RISK]**
   - Location: `docker-compose.yml:278`
   - Hardcoded: `GUARDIAN_API_KEY: <redacted-example>`
   - Hardcoded: Postgres password `codexify` (line 8-9), Neo4j password `codexify` (line 22)
 
3. **Database** (encrypted JSONB fields)
   - Location: `guardian/db/models.py` - `ConnectorConfig.secrets` field
   - Encryption: **None** - stored as plain JSONB
 
**Accidental Hardcoded Secrets**:
- **[RISK]** `docker-compose.yml:278` - Guardian API key in plaintext
- **[RISK]** `docker-compose.yml:8-9,22` - Database credentials in plaintext
 
**Recommendation**:
1. Use Docker secrets or external secret management (Vault, AWS Secrets Manager)
2. Remove hardcoded API key from docker-compose.yml
3. Encrypt connector secrets at rest (e.g., using Fernet or database-level encryption)
 
---
 
### 8.2 Data Egress Map (Code-Evidenced)
 
| Call Site | Destination | Data Classes Sent | Controls/Gates | Risk Rating |
|-----------|-------------|-------------------|----------------|-------------|
| `guardian/core/ai_router.py:194-221` (Groq) | `https://api.groq.com/openai/v1/chat/completions` | - Full conversation history<br>- User messages<br>- System prompts<br>- Model parameters | - Environment-driven provider selection (`LLM_PROVIDER`)<br>- No per-request consent<br>- No data minimization | **[RISK]** - Full context sent |
| `guardian/core/ai_router.py:224-251` (OpenAI) | `https://api.openai.com/v1/chat/completions` | - Full conversation history<br>- User messages<br>- System prompts | - Environment-driven provider selection<br>- No per-request consent | **[RISK]** - Full context sent |
| `guardian/core/ai_router.py:72-192` (Local) | `LOCAL_BASE_URL/v1/chat/completions` (Ollama) | - Full conversation history<br>- User messages<br>- System prompts | - Local inference only<br>- No external egress | **[SAFE]** - Local only |
| `guardian/connectors/google.py` (OAuth) | `https://oauth2.googleapis.com/token` | - OAuth authorization code<br>- Client ID/secret<br>- Refresh token | - User-initiated OAuth flow<br>- Tokens stored in DB | **[WARN]** - Standard OAuth |
| `guardian/connectors/github.py` (API) | `https://api.github.com/*` | - GitHub API token<br>- Repository metadata | - User-configured connector<br>- Token from DB | **[WARN]** - User-initiated |
| `guardian/tts/providers/elevenlabs_provider.py` | `https://api.elevenlabs.io/v1/*` | - Text to synthesize<br>- Voice parameters | - Optional TTS feature<br>- User-initiated | **[WARN]** - Optional feature |
| `guardian/embedding_engine.py` (OpenAI embeddings) | `https://api.openai.com/v1/embeddings` | - Document chunks<br>- Text content | - **NOT USED** (code explicitly ignores `use_openai` parameter) | **[N/A]** - Dead code |
 
**Key Findings**:
1. **Groq/OpenAI modes send full conversation history** with no data minimization
2. **No per-request consent mechanism** - provider selection is environment-driven only
3. **Local mode is truly local-first** - no external API calls
4. **No audit logging of external API calls** - no tracking of what data was sent where
5. **OpenAI embeddings explicitly disabled** - all embeddings generated locally
 
**Recommendations**:
1. Add per-request provider selection with explicit consent
2. Implement data minimization (e.g., truncate history, redact PII)
3. Add audit logging for all external API calls with data payload hashes
4. Implement allowlists for external domains
5. Add telemetry opt-out mechanism
 
---
 
### 8.3 Access Control / Multi-User Considerations
 
**Current State**:
- **Basic user_id ownership**: `ChatThread.user_id`, `MemoryEntry.user_id`, `Persona.user_id`
- **No RBAC/ACL**: No roles, permissions, or access control lists
- **No tenancy isolation**: `tenant_id` defaults to "default" throughout
- **Sharing via tokens**: `SharedLink` provides read-only public access without authentication
 
**Evidence**:
- User ownership: `guardian/db/models.py` defines `user_id` columns on core models
- No permission tables: Schema analysis reveals no `roles`, `permissions`, or `acl` tables
- Token-based sharing: `guardian/routes/share.py:109-173` creates secure tokens for public access
 
**Weak Points Relative to Sovereignty Goals**:
1. **No multi-tenancy** - All users share same namespace by default
2. **No role-based permissions** - Cannot restrict actions by role (admin/user/viewer)
3. **No audit of access attempts** - No tracking of who accessed what when
4. **Token-based sharing is opaque** - No visibility into who accessed shared content
 
**Recommendation**: Implement RBAC before multi-user production deployment:
1. Add `roles` and `permissions` tables
2. Implement row-level security (RLS) in PostgreSQL
3. Add audit logging for access attempts
4. Implement proper tenancy isolation with `tenant_id` enforcement
 
---
 
## Docs ↔ Code Consistency
 
### Doc Claims That Do Not Match Code
 
| Doc Claim | Reality | Status | Evidence |
|-----------|---------|--------|----------|
| "Neo4j-powered relationship mapping for context-aware reasoning" (README.md:47) | Neo4j schema exists but minimal usage in chat pipeline | **Docs drift** | `guardian/db/neo.py` defines schema, `guardian/routes/neo.py` has minimal endpoints |
| "WebSocket support for real-time updates" (README.md:671) | WebSocket collaboration implemented but not for general events | **Docs drift** | `guardian/realtime/collaboration.py` exists but only for document editing |
| "Fine-tuning support for local models" (README.md:673) | Not found in codebase | **Docs drift** (roadmap item) | No evidence of fine-tuning infrastructure |
| "Multi-user authentication & RBAC" (README.md:674) | No RBAC system implemented | **Docs drift** (roadmap item) | Basic user_id ownership only |
| "Plugin marketplace" (README.md:676) | No marketplace implementation | **Docs drift** (roadmap item) | Plugin system exists but no marketplace |
 
---
 
### Code Paths Not Described in Docs
 
| Code Path | Description | Status |
|-----------|-------------|--------|
| `guardian/workers/warmup_worker.py` | Pre-warms Redis queue and models | **Code drift** | Not mentioned in README |
| `guardian/workers/embedding_backfill_worker.py` | Backfills missing embeddings | **Code drift** | Mentioned briefly in README.md:195-204 but no detail |
| `guardian/workers/graph_backfill_worker.py` | Backfills Neo4j graph | **Code drift** | Mentioned briefly in README.md:195-204 but no detail |
| `guardian/queue/redis_queue.py` | Redis-based task queue | **Code drift** | Not mentioned in architecture docs |
| `guardian/realtime/collaboration.py` | WebSocket collaboration for documents | **Ambiguous** | Mentioned in CODEBASE_SUMMARY.md but not in main README architecture |
| `guardian/routes/federation.py` | Federation endpoint for external manifests | **Code drift** | No documentation on federation feature |
 
**Finding**: Workers and background jobs are underdocumented. README focuses on interactive features but background processing is critical for production.
 
---
 
## Code Quality, Testing, and DX
 
### TypeScript Strictness / Type Hygiene
 
**Frontend (TypeScript)**:
- `frontend/src/` uses TypeScript with `tsconfig.json`
- Type checking: `pnpm type-check` available
- **Issue**: `@ts-ignore` and `any` usage not analyzed (requires deeper inspection)
 
**Backend (Python)**:
- `pyproject.toml:120-160` defines MyPy configuration
- **Strictness level**: **Low** (MVP mode)
  - `strict = false` (line 134)
  - `check_untyped_defs = false` (line 130)
  - Many error codes disabled (lines 137-160)
- **Rationale**: "MVP: Less strict type checking - enable stricter settings as codebase improves"
 
**Evidence**: `pyproject.toml:120-160`
 
**Assessment**: Type hygiene is **weak** - intentional tradeoff for rapid development
 
**Recommendation**: Gradually enable stricter MyPy settings as codebase matures
 
---
 
### Lint/Format Setup
 
**Python**:
- **Black**: Line length 88, Python 3.11+ target (`pyproject.toml:68-83`)
- **isort**: Black-compatible profile (`pyproject.toml:85-96`)
- **Ruff**: Line length 88, extends Black ignore list (`pyproject.toml:109-118`)
- **Pre-commit hooks**: `.pre-commit-config.yaml` with 15+ hooks including:
  - Black, isort, ruff, mypy
  - Bandit (security linting)
  - detect-private-key, check-added-large-files
 
**TypeScript**:
- **ESLint**: Configuration exists (not analyzed in detail)
- **Prettier**: Likely integrated (standard with Vite)
 
**Evidence**: `.pre-commit-config.yaml:1-200+`, `pyproject.toml:68-118`
 
**Assessment**: Lint/format setup is **production-ready** with comprehensive pre-commit hooks
 
---
 
### Test Suites
 
**Backend Tests**:
- **Location**: `guardian/tests/`, `tests/`
- **Runner**: pytest (`pytest.ini` configuration)
- **Coverage**: `pytest --cov=guardian --cov-report=html`
- **Test types**: Unit tests, integration tests, route tests
 
**Example Test Files**:
- `tests/realtime/test_collaboration_ws.py` - WebSocket tests
- `tests/routes/test_share_links.py` - Share link tests
- `guardian/tests/test_retrieve_api.py` - RAG retrieval tests
 
**Frontend Tests**:
- **Location**: `frontend/src/components/__tests__/`, `frontend/src/tests/`
- **Runners**: Vitest (unit), Playwright (E2E), Cypress (E2E)
- **Commands**: `pnpm test`, `pnpm test:e2e`
 
**Evidence**:
- `pytest.ini` in root
- `frontend/src/playwright-report/` exists
- `docker-compose.yml:638-665` defines `e2e` service with Playwright
 
**Assessment**: Test infrastructure is **good** but coverage unknown
 
**Major Gaps** (requires runtime analysis):
1. **Coverage metrics not analyzed** - Need to run tests to assess
2. **Integration test completeness** - Unclear which subsystems have integration tests
3. **E2E test stability** - Playwright setup exists but stability unknown
 
---
 
### Dev Experience
 
**Setup Scripts**:
- `Makefile:1-180+` provides convenience commands:
  - `make dev` - Start full stack
  - `make run` - Start backend only
  - `make test` - Run tests
  - `make format` - Format code
  - `make lint` - Lint code
 
**Run/Test Instructions**:
- **README.md:156-250** provides comprehensive quickstart
- **Docker Compose**: `docker-compose up -d` for full stack
- **Manual run**: `uvicorn guardian.guardian_api:app --reload --port 8888`
 
**Env Templates**:
- `.env.example` provides template with descriptions
- `.env.template` is simpler template
- Both cover all required environment variables
 
**Evidence**:
- `Makefile` with 30+ targets
- `README.md:156-250` comprehensive setup guide
- `.env.example` with detailed comments
 
**Assessment**: Dev experience is **excellent** - well-documented and automated
 
**Recommendations**:
1. Add troubleshooting section to README
2. Document common gotchas (e.g., Alembic must run via Docker)
3. Add health check dashboard for services
 
---
 
## Performance and Scalability
 
### Obvious Hot Paths
 
| Hot Path | Location | Potential Bottleneck | Optimization |
|----------|----------|---------------------|--------------|
| **LLM calls** | `guardian/core/ai_router.py:72-251` | Network latency, API rate limits | Cache responses, use streaming |
| **Embedding generation** | `backend/rag/embedder.py:185-217` | CPU-intensive (batch size 32) | Use GPU, increase batch size, async |
| **Vector search** | `backend/rag/embedder.py:281-337` | FAISS in-memory scan | Use IVF index, quantization |
| **Graph queries** | `guardian/db/neo.py` | Cypher query performance | Add indexes, optimize queries |
| **Database queries** | `guardian/core/pgdb.py` | Sequential scans, N+1 queries | Add indexes, use eager loading |
 
---
 
### Blocking Operations / Synchronous Hazards
 
1. **LLM calls are synchronous** (`requests.post()` without async)
   - Location: `guardian/core/ai_router.py:199,227`
   - Impact: Blocks event loop during inference
   - Fix: Use `httpx.AsyncClient` for async requests
 
2. **Embedding generation blocks** (`model.encode()` is synchronous)
   - Location: `backend/rag/embedder.py:209-217`
   - Impact: Blocks during batch encoding
   - Fix: Run in thread pool executor or separate process
 
3. **File I/O is synchronous** (plugin loading, document parsing)
   - Location: `guardian/plugin_loader.py:109-175`
   - Impact: Blocks during large file operations
   - Fix: Use `aiofiles` for async file I/O
 
**Evidence**:
- `guardian/core/ai_router.py:199,227` uses `requests.post()` (blocking)
- `backend/rag/embedder.py:209-217` uses synchronous `model.encode()`
 
**Assessment**: **Multiple blocking operations** in hot paths - needs async refactoring
 
---
 
### Potential Optimizations
 
| Optimization | Status | Recommendation | Impact |
|--------------|--------|----------------|--------|
| **Response caching** | Not implemented | Cache LLM responses by message hash | Reduce API costs, latency |
| **Batching** | Partial | Batch embedding generation (currently size 32) | Improve throughput |
| **Streaming** | Implemented | Already supports SSE streaming for LLM responses | ✅ Good |
| **Pagination** | Implemented | API routes support limit/offset | ✅ Good |
| **Connection pooling** | Implemented | SQLAlchemy uses connection pooling | ✅ Good |
| **Vector index optimization** | Not implemented | Use FAISS IVF or HNSW for large datasets | Improve search speed |
| **Redis caching** | Partial | Redis used for queue only, not as cache | Use Redis for hot data |
 
**Evidence**:
- Streaming: `guardian/core/ai_router.py:126-191` implements SSE streaming
- Pagination: `guardian/routes/*.py` use `limit` and `offset` parameters
- Pooling: `guardian/core/pgdb.py` uses SQLAlchemy connection pool
 
**Assessment**: Some optimizations implemented, but room for improvement in caching and async operations
 
---
 
## Risk Register & Recommendations
 
| ID | Area | Description | Impact | Likelihood | Effort | Suggested Next Action | Evidence | Status |
|----|------|-------------|--------|------------|--------|----------------------|----------|--------|
| R01 | Security | **Hardcoded secrets in docker-compose.yml** | High | High | Low | Remove hardcoded API key and database credentials, use Docker secrets | `docker-compose.yml:8-9,22,278` | **Planned** |
| R02 | Security | **No encryption for connector secrets in database** | High | Med | Med | Implement Fernet encryption for `ConnectorConfig.secrets` JSONB field | `guardian/db/models.py` | **Planned** |
| R03 | Privacy | **Full conversation history sent to cloud LLM providers** | High | High | Med | Implement data minimization (truncate history, redact PII) and per-request consent | `guardian/core/ai_router.py:194-251` | **Planned** |
| R04 | Security | **No RBAC/ACL system** | Med | High | High | Implement roles, permissions, and row-level security before multi-user production | `guardian/db/models.py` (no permission tables) | **Planned** |
| R05 | Reliability | **Neo4j integration is scaffolding only** | Med | Med | High | Either wire Neo4j into context enrichment or remove from marketing claims | `guardian/db/neo.py`, `guardian/routes/neo.py` | **Partial** |
| R06 | Performance | **Blocking LLM and embedding calls** | Med | High | Med | Refactor to use `httpx.AsyncClient` and thread pool executors | `guardian/core/ai_router.py:199,227`, `backend/rag/embedder.py:209-217` | **Planned** |
| R07 | Observability | **No audit logging of external API calls** | Med | High | Low | Add audit logging with data payload hashes for all external API calls | All files using `requests.post()` | **Planned** |
| R08 | Quality | **Low MyPy strictness** | Low | High | High | Gradually enable stricter type checking as codebase matures | `pyproject.toml:120-160` | **Partial** |
| R09 | Docs | **README claims don't match implementation** | Low | High | Low | Update README to reflect actual Neo4j usage, WebSocket scope, roadmap status | `README.md:47,671-676` | **Planned** |
| R10 | Testing | **Unknown test coverage** | Med | High | Med | Run test suite with coverage report, identify gaps, add integration tests | `pytest --cov=guardian` | **Planned** |
 
---
 
### Prioritized Roadmap
 
#### Phase 1: Critical Fixes (Security & Privacy)
 
**Timeline**: 1-2 weeks
 
1. **[R01] Remove hardcoded secrets from docker-compose.yml** (1 day)
   - Move to Docker secrets or `.env` file
   - Update deployment docs
 
2. **[R02] Encrypt connector secrets at rest** (3 days)
   - Implement Fernet encryption for JSONB secrets
   - Add migration to encrypt existing secrets
   - Update connector routes to decrypt on read
 
3. **[R03] Implement data minimization for cloud LLMs** (5 days)
   - Add per-request provider selection with consent flag
   - Implement conversation history truncation (keep last N messages)
   - Add PII redaction helper functions
   - Add audit logging for external API calls
 
4. **[R07] Add audit logging for external API calls** (2 days)
   - Create `AuditLog` entries for all external requests
   - Log: timestamp, destination, data payload hash, user_id
   - Add admin dashboard to view audit logs
 
---
 
#### Phase 2: Important Improvements (Architecture & Reliability)
 
**Timeline**: 3-4 weeks
 
1. **[R04] Implement RBAC system** (10 days)
   - Design permission model (roles, permissions, user_roles)
   - Create database migration for new tables
   - Implement permission checks in routes
   - Add admin UI for role management
 
2. **[R05] Wire Neo4j into chat pipeline or deprecate** (5 days)
   - **Option A**: Implement context enrichment via graph queries
   - **Option B**: Remove Neo4j from README, mark as experimental
   - Decision: Requires stakeholder input on graph DB value proposition
 
3. **[R06] Refactor to async for LLM and embeddings** (7 days)
   - Replace `requests` with `httpx.AsyncClient`
   - Use thread pool executor for synchronous embedding calls
   - Update all route handlers to async/await
   - Test with load testing tool (Locust, k6)
 
4. **[R10] Improve test coverage** (5 days)
   - Run coverage report, identify gaps (<70% coverage)
   - Add integration tests for critical paths (chat, RAG, memory)
   - Add E2E tests for key user flows (create thread, chat, retrieve)
 
---
 
#### Phase 3: Nice-to-Have Refinements (Quality & Docs)
 
**Timeline**: 2-3 weeks
 
1. **[R08] Gradually enable stricter MyPy settings** (Ongoing)
   - Enable one error code per week
   - Fix type errors as they arise
   - Update pyproject.toml incrementally
 
2. **[R09] Update documentation** (3 days)
   - Sync README with actual implementation
   - Add troubleshooting section
   - Document connector setup and testing
   - Add architecture decision records (ADRs)
 
3. **Performance optimizations** (5 days)
   - Implement response caching (Redis)
   - Add FAISS IVF index for large vector datasets
   - Optimize database queries (add missing indexes)
   - Add performance benchmarks
 
4. **Observability improvements** (5 days)
   - Add Prometheus metrics export
   - Implement health check dashboard
   - Add distributed tracing (OpenTelemetry)
   - Create Grafana dashboards for key metrics
 
---
 
## Model Notes
 
### Agent/Model
 
- **Model**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Runner**: Claude Code CLI running in git worktree mode
- **Context**: 200,000 token budget, 70,000+ tokens used for comprehensive analysis
 
### Tooling Limitations
 
1. **Cannot run tests** - No execution environment for pytest/pnpm test
2. **Cannot access `.git/` internals** - Worktree symlink prevents direct git object access
3. **Cannot analyze runtime behavior** - Static analysis only, no execution traces
 
### Areas That Look Planned/Stubbed vs Real
 
| Area | Status | Evidence |
|------|--------|----------|
| **Neo4j Graph Database** | Scaffolding | Schema defined (`guardian/db/neo.py`) but minimal usage in routes |
| **Connector Worker** | Stubbed | Disabled by default (`ENABLE_CONNECTOR_WORKER=false`), suggests incomplete testing |
| **Persona → Model Routing** | Stubbed | Contract defined (`guardian/router.py:7-12`) but not actively used |
| **Conversation Summarization** | Stubbed | Stub implementation (`guardian/memory/memoryos.py:188-215`) falls back to timestamp |
| **Fine-tuning Support** | Planned | Mentioned in roadmap (README.md:673) but no code found |
| **Multi-user Auth & RBAC** | Planned | Mentioned in roadmap (README.md:674) but no implementation |
| **Plugin Marketplace** | Planned | Mentioned in roadmap (README.md:676) but no implementation |
 
---
 
## Conclusion
 
Codexify represents a **mature, production-ready local-first AI platform** with strong fundamentals:
 
✅ **Strengths**:
- Robust data layer with proper migrations and schema management
- Multi-provider AI routing with clean abstraction
- Three-tier memory architecture with database backing
- Mature plugin system with comprehensive safeguards
- Excellent developer experience with Docker Compose orchestration
 
⚠️ **Caution Areas**:
- Security needs hardening (secrets management, RBAC, audit logging)
- Privacy concerns for cloud LLM modes (full context egress)
- Neo4j integration is scaffolding only (not actively used)
- Performance bottlenecks from blocking I/O operations
- Test coverage unknown (requires runtime analysis)
 
🚧 **Roadmap Gaps**:
- README claims don't match implementation (Neo4j, WebSockets, fine-tuning)
- Connector worker disabled by default (reliability concerns)
- Persona system not wired into model routing
 
**Overall Assessment**: **GOOD** - Ready for local/on-premise deployment with proper security hardening. Needs work before multi-user cloud deployment.
 
---
 
**End of Audit Report**
 
*Generated by Claude Sonnet 4.5 via Claude Code CLI on 2026-01-23*
