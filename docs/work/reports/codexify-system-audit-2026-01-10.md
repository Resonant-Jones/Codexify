# Codexify System Audit

---

## Metadata

| Field | Value |
|-------|-------|
| Repo name | Codexify |
| Date of audit | 2026-01-10 |
| Agent/Model | Claude Opus 4.5 (claude-opus-4-5-20251101) |
| Runner/Environment | VSCode IDE Agent (Claude Code) |
| Git branch | `chore/post-skip-hook-fixes` |
| Git commit | `2a4e2596` (latest) |

---

## Executive Summary

- **Overall health:** The project is actively developed with a comprehensive architecture supporting local-first AI workflows, persona management, RAG retrieval, and multi-model routing. The codebase demonstrates good structure with clear separation of concerns.

- **Key strengths:**
  - Well-designed modular architecture with clear separation between frontend (React/Vite), backend (FastAPI), and data layers
  - Functional RAG pipeline with both FAISS (in-memory) and ChromaDB (persistent) vector stores
  - Comprehensive SQLAlchemy models with proper indexing and migrations via Alembic
  - Multi-provider model routing (OpenAI, Groq, Gemini) with fallback mechanisms
  - Active federation layer for cross-node collaboration with JWT-based authentication

- **Top 5 concerns:**
  1. **[RISK]** Neo4j integration is **Partial** - connection code exists but graph sync is guarded behind a config flag that defaults to disabled ([guardian/routes/chat.py:511-546](guardian/routes/chat.py#L511-L546))
  2. **[RISK]** External API calls to OpenAI/Groq/Gemini send prompt content and embeddings to third-party services without explicit user consent gates in the code path ([guardian/providers/openai_adapter.py:32-41](guardian/providers/openai_adapter.py#L32-L41), [guardian/providers/groq_adapter.py:29-37](guardian/providers/groq_adapter.py#L29-L37))
  3. **[WARN]** Federation session token validation uses `verify_signature=False` for peer manifest verification in accept flow ([guardian/routes/federation.py:287](guardian/routes/federation.py#L287))
  4. **[WARN]** Plugin system loads manifests but execution engine appears **Stubbed** - no runtime invocation of plugin code found ([guardian/plugins/plugin_loader.py](guardian/plugins/plugin_loader.py))
  5. **[WARN]** Test coverage for security-critical paths (rate limiting, API key validation) exists but some tests are marked as skipped in current branch

---

## System Overview

### Project Purpose

Codexify is a local-first, sovereignty-focused AI runtime designed for software engineering workflows. It provides:
- Persona-based, memory-aware chat interfaces
- RAG (Retrieval-Augmented Generation) with vector and graph retrieval
- Multi-model routing across providers (OpenAI, Groq, Gemini)
- Plugin/extension system for custom capabilities
- Federation layer for cross-node collaboration

### Major Subsystems

```
                    +------------------+
                    |    Frontend      |
                    |  (React/Vite)    |
                    +--------+---------+
                             |
                             v
          +------------------+------------------+
          |           Guardian API              |
          |         (FastAPI/Uvicorn)           |
          +------------------+------------------+
                             |
      +----------------------+----------------------+
      |                      |                      |
      v                      v                      v
+------------+      +----------------+      +---------------+
|   Data     |      |  Model/RAG     |      |   Federation  |
|   Layer    |      |    Layer       |      |     Layer     |
+------------+      +----------------+      +---------------+
| PostgreSQL |      | Providers:     |      | JWT Auth      |
| Redis Queue|      |  - OpenAI      |      | WebSocket     |
| ChromaDB   |      |  - Groq        |      | Relay         |
| FAISS      |      |  - Gemini      |      | Diff Sync     |
| Neo4j (opt)|      | Embedder:      |      | Graph Sync    |
+------------+      |  - SentenceTfm |      +---------------+
                    | VectorStore:   |
                    |  - FAISS/Chroma|
                    +----------------+
```

### Subsystem Status Summary

| Subsystem | Status | Evidence |
|-----------|--------|----------|
| Frontend (React/Vite) | **Implemented** | [frontend/src/main.tsx](frontend/src/main.tsx), 100+ TSX components |
| Backend API (FastAPI) | **Implemented** | [guardian/guardian_api.py](guardian/guardian_api.py), 25+ route modules |
| PostgreSQL Database | **Implemented** | [guardian/db/models.py](guardian/db/models.py), Alembic migrations |
| Redis Task Queue | **Implemented** | [guardian/queue/redis_queue.py](guardian/queue/redis_queue.py) |
| Vector Store (FAISS) | **Implemented** | [backend/rag/embedder.py:147-167](backend/rag/embedder.py#L147-L167) |
| Vector Store (ChromaDB) | **Implemented** | [backend/rag/embedder.py:169-183](backend/rag/embedder.py#L169-L183) |
| Neo4j Graph | **Partial** | Models exist ([guardian/graph/models.py](guardian/graph/models.py)), sync disabled by default |
| Model Routing | **Implemented** | [guardian/providers/registry.py](guardian/providers/registry.py) |
| Persona/Imprint System | **Implemented** | [guardian/cognition/prompts.py](guardian/cognition/prompts.py), DB models |
| Plugin System | **Partial** | Manifest loading works; runtime execution **Stubbed** |
| Federation Layer | **Implemented** | [guardian/routes/federation.py](guardian/routes/federation.py), 800 lines |
| Mobile/Scout | **Documented-only** | Referenced in docs, no implementation found |

---

## Architecture & Module Map

### 1. Frontend (React/TypeScript/Vite)

**Purpose:** Single-page application providing chat interface, settings, persona management, and workspace views.

**Key Modules/Files:**
- Entry point: [frontend/src/main.tsx](frontend/src/main.tsx)
- App shell: [frontend/src/App.tsx](frontend/src/App.tsx)
- Chat components: [frontend/src/components/chat/](frontend/src/components/chat/)
- Persona system: [frontend/src/components/persona/](frontend/src/components/persona/)
- Settings: [frontend/src/features/settings/](frontend/src/features/settings/)
- API client: [frontend/src/lib/guardianApi.ts](frontend/src/lib/guardianApi.ts)

**Public Interfaces:**
- `GuardianAPI` class exposed globally for API calls
- React context providers for theme, persona, threads

**Critical Invariants:**
- API base URL configured via `VITE_GUARDIAN_API_BASE` env var
- API key passed in `X-API-Key` header for authenticated requests

**Implementation Status:** **Implemented** - Full-featured SPA with 100+ components

---

### 2. Backend API (FastAPI/Guardian)

**Purpose:** REST API server handling chat, threads, memory, RAG, connectors, and federation.

**Key Modules/Files:**
- Main app: [guardian/guardian_api.py](guardian/guardian_api.py)
- Route modules: [guardian/routes/*.py](guardian/routes/) (25+ modules)
- Core dependencies: [guardian/core/dependencies.py](guardian/core/dependencies.py)
- Database layer: [guardian/core/db.py](guardian/core/db.py)

**Public Interfaces:**
- `/api/chat/*` - Thread/message CRUD, completions
- `/api/projects/*` - Project management
- `/api/memory/*` - Memory silo operations
- `/api/federation/*` - Cross-node collaboration
- `/api/connectors/*` - External service sync

**Critical Invariants:**
- DB session must be available before route handlers execute
- Provider registry initialized on startup based on env vars
- API key validation via `require_api_key` dependency

**Implementation Status:** **Implemented** - Comprehensive REST API

---

### 3. Database Layer (PostgreSQL/SQLAlchemy)

**Purpose:** Primary persistence for threads, messages, memory, connectors, personas, and audit logs.

**Key Modules/Files:**
- ORM models: [guardian/db/models.py](guardian/db/models.py) (1000+ lines)
- Additional models: [guardian/db/models_additions.py](guardian/db/models_additions.py)
- DB connection: [guardian/core/db.py](guardian/core/db.py)
- Migrations: [backend/alembic/versions/](backend/alembic/versions/)

**Tables (from models.py):**
- `projects`, `chat_threads`, `chat_messages`
- `memory_entries` (silos: ephemeral/midterm/longterm)
- `connector_configs`, `connector_runs`, `raw_documents`, `sync_jobs`
- `events_outbox`, `audit_log`
- `generated_images`, `uploaded_images`, `generated_documents`, `uploaded_documents`
- `imprints`, `personas`, `system_docs`, `system_doc_links`
- `shared_links`, `collaboration_permissions`, `collaboration_audit_log`

**Implementation Status:** **Implemented** - Full schema with indexes and constraints

---

### 4. Vector Store Layer

**Purpose:** Semantic search and RAG retrieval using local embeddings.

**Key Modules/Files:**
- Embedder: [backend/rag/embedder.py](backend/rag/embedder.py)
- VectorStore wrapper: [guardian/vector/store.py](guardian/vector/store.py)
- Model path resolver: [guardian/utils/embed_paths.py](guardian/utils/embed_paths.py)

**Public Interfaces:**
- `VectorStore.add_texts(items)` - Index documents
- `VectorStore.search(query, k)` - Semantic search

**Critical Invariants:**
- `LOCAL_EMBED_MODEL` env var required for SentenceTransformers
- Model must be pre-downloaded to local cache
- Store type selected via `CODEXIFY_VECTOR_STORE` (faiss/chroma)

**Implementation Status:** **Implemented** - Both FAISS and ChromaDB functional

---

### 5. Model Provider Layer

**Purpose:** Abstract interface to multiple LLM providers with unified chat/completion API.

**Key Modules/Files:**
- Registry: [guardian/providers/registry.py](guardian/providers/registry.py)
- Base interfaces: [guardian/providers/base.py](guardian/providers/base.py)
- OpenAI adapter: [guardian/providers/openai_adapter.py](guardian/providers/openai_adapter.py)
- Groq adapter: [guardian/providers/groq_adapter.py](guardian/providers/groq_adapter.py)
- Gemini adapter: [guardian/providers/gemini_adapter.py](guardian/providers/gemini_adapter.py)

**Critical Invariants:**
- Provider selected via `GUARDIAN_PROVIDER` env var
- Each provider requires its own API key env var
- Fallback to "openai" if provider not specified

**Implementation Status:** **Implemented** - Three providers (OpenAI, Groq, Gemini)

---

### 6. Persona/Cognition System

**Purpose:** System prompt assembly with immutable safety core, persona layers, and style customization.

**Key Modules/Files:**
- Prompt builder: [guardian/cognition/prompts.py](guardian/cognition/prompts.py)
- System prompt assembly: [guardian/cognition/system_prompt_builder.py](guardian/cognition/system_prompt_builder.py)
- Imprint store: [guardian/cognition/imprints/store.py](guardian/cognition/imprints/store.py)
- Persona store: [guardian/cognition/personas/store.py](guardian/cognition/personas/store.py)

**Prompt Composition Order:**
1. Immutable core (non-negotiable safety rules)
2. Depth mode guidance (shallow/normal/deep/diagnostic)
3. Imprint_Zero style block (user preferences)
4. User persona instructions
5. System docs
6. RAG context hints

**Implementation Status:** **Implemented** - Full prompt assembly pipeline

---

### 7. Plugin System

**Purpose:** Extensible plugin architecture for custom capabilities.

**Key Modules/Files:**
- Plugin loader: [guardian/plugins/plugin_loader.py](guardian/plugins/plugin_loader.py)
- Plugin manifest: [guardian/plugins/plugin_manifest.py](guardian/plugins/plugin_manifest.py)
- Plugin directory: [plugins/](plugins/)

**Implementation Status:** **Partial** - Manifest loading implemented, runtime execution **Stubbed**

**Evidence:** `load_all_manifests()` scans and parses plugin manifests, but no code path invokes plugin functionality at runtime.

---

### 8. Federation Layer

**Purpose:** Cross-node collaboration with session exchange, relay channels, and diff synchronization.

**Key Modules/Files:**
- Federation routes: [guardian/routes/federation.py](guardian/routes/federation.py)
- Federation manager: [guardian/federation/manager.py](guardian/federation/manager.py)
- Diff engine: [guardian/federation/diff_engine.py](guardian/federation/diff_engine.py)
- Graph store: [guardian/federation/graph_store.py](guardian/federation/graph_store.py)

**Implementation Status:** **Implemented** - Full session/relay/diff/graph sync

---

## Data, Memory, and Retrieval Pipeline

### 6.1 Storage Inventory (Reality-First)

| Storage Layer | Status | What is Stored | Location |
|--------------|--------|----------------|----------|
| **PostgreSQL** | **Implemented** | Threads, messages, memory, connectors, personas, audit | [guardian/db/models.py](guardian/db/models.py) |
| **Redis** | **Implemented** | Task queue, rate limiting | [guardian/queue/redis_queue.py](guardian/queue/redis_queue.py) |
| **FAISS (in-memory)** | **Implemented** | Vector embeddings (ephemeral) | [backend/rag/embedder.py:147-167](backend/rag/embedder.py#L147-L167) |
| **ChromaDB** | **Implemented** | Vector embeddings (persistent) | [backend/rag/embedder.py:100-106](backend/rag/embedder.py#L100-L106), `./.chroma` dir |
| **Neo4j** | **Partial** | Graph relations (users, threads, messages) | [guardian/graph/](guardian/graph/), disabled by default |
| **Local filesystem** | **Implemented** | Uploaded files, generated media | `uploads/`, `media/` dirs |

#### Data Flow Details

**Ingestion paths:**
1. Chat messages -> PostgreSQL + Vector store (auto-embed on creation)
2. Document uploads -> PostgreSQL metadata + Vector store (parsed text)
3. Connector sync (GitHub) -> `raw_documents` table -> Vector store

**Query paths:**
1. Semantic search: Query -> Embedder -> Vector store search -> Results
2. Memory search: Silo filter -> PostgreSQL -> Optional vector search
3. Graph queries: Neo4j Cypher (when enabled)

**Retention:**
- Messages: Persistent in PostgreSQL, no TTL
- Memory silos: User-controlled (ephemeral/midterm/longterm)
- Vector index: FAISS volatile (lost on restart), ChromaDB persistent
- Events outbox: Status-based cleanup available

---

### 6.2 RAG / Retrieval Pipeline

| Stage | Implementation Status | Evidence |
|-------|----------------------|----------|
| **Ingestion/Chunking** | **Implemented** | [backend/rag/embedder.py:135-183](backend/rag/embedder.py#L135-L183) |
| **Embedding** | **Implemented** | SentenceTransformers via `LOCAL_EMBED_MODEL` |
| **Vector Storage** | **Implemented** | FAISS (in-memory) or ChromaDB (persistent) |
| **Retrieval** | **Implemented** | [backend/rag/embedder.py:185-241](backend/rag/embedder.py#L185-L241) |
| **Prompt Injection** | **Implemented** | [guardian/cognition/prompts.py:98-116](guardian/cognition/prompts.py#L98-L116) |
| **Persona-aware Filtering** | **Partial** | User_id scoping exists, project scoping partial |

**Embedding Details:**
- Model: Configured via `LOCAL_EMBED_MODEL` (SentenceTransformers)
- Vectors: Stored in FAISS (`IndexFlatIP`) or ChromaDB collection
- Normalization: L2 normalization applied for cosine similarity

**Retrieval Details:**
- Query: Embed query -> Vector search (top-k, default 5)
- Scoring: Inner product (FAISS) or 1-distance (ChromaDB)
- Results: `{text, meta, metadata, score}` format

**Local-First Compliance:**
- **Yes** - Embeddings generated locally via SentenceTransformers
- **Yes** - Vector stores (FAISS/ChromaDB) run locally
- **Exception** - OpenAI embeddings adapter exists but not default path

**Persona-Aware Retrieval:**
- Thread/user metadata attached to vectors
- Filtering by `thread_id`, `user_id` in search possible but not enforced

---

## Persona, Agent, and Model Routing Layer

### Persona Representation

**Data Model:** [guardian/db/models.py:721-746](guardian/db/models.py#L721-L746)
```python
class Persona(Base):
    id: Mapped[int]
    user_id: Mapped[str]
    project_id: Mapped[int | None]
    body: Mapped[str]  # User instructions
    source: Mapped[str]  # 'user' or 'system'
    is_active: Mapped[bool]
```

**Imprint (Imprint_Zero):** [guardian/db/models.py:680-718](guardian/db/models.py#L680-L718)
```python
class Imprint(Base):
    guardian_name: str  # Custom AI name
    preferred_name: str  # User's preferred name
    style: str  # 'playful-dry', 'clinical'
    grammar_prefs: dict  # Oxford comma, etc.
    heat_score: float
    status: str  # 'draft', 'active', 'superseded'
```

### Persona Effect on System

| Aspect | How Persona Affects It | Location |
|--------|----------------------|----------|
| **Model Selection** | Not affected - provider selected at call time | [guardian/providers/registry.py:45-55](guardian/providers/registry.py#L45-L55) |
| **Prompt Templates** | Persona body injected into system prompt | [guardian/cognition/prompts.py:66-77](guardian/cognition/prompts.py#L66-L77) |
| **Memory Scope** | User_id filtering on memory queries | [guardian/routes/memory.py](guardian/routes/memory.py) |
| **Retrieval Scope** | Metadata filtering possible but not enforced | [backend/rag/embedder.py](backend/rag/embedder.py) |

### Agent Orchestration

**Task Queue:** [guardian/queue/redis_queue.py](guardian/queue/redis_queue.py)
- Redis-backed task queue for async completions
- Task types: `ChatCompletionTask`

**Agent Planning:** Not found - no explicit planner/executor pattern

**Tool Use:** Limited - connector sync, no general tool-use framework

### Safety Layer Boundaries

**System (Immutable) Core:** [guardian/cognition/prompts.py:12-25](guardian/cognition/prompts.py#L12-L25)
```python
def _base_codexify_system_prompt() -> str:
    return (
        "You are Guardian... Non-negotiable rules:\n"
        "- Follow Codexify safety policies...\n"
        "- Never fabricate access to tools or data...\n"
        "- When uncertain, say so explicitly...\n"
    )
```

This core is **always prepended** and cannot be overridden by user personas.

---

## Security, Privacy, and Sovereignty

### 8.1 Secrets Management

| Secret Type | Location | Risk |
|-------------|----------|------|
| `OPENAI_API_KEY` | `.env`, docker-compose | **OK** - env-based |
| `GROQ_API_KEY` | `.env`, docker-compose | **OK** - env-based |
| `GEMINI_API_KEY` | `.env`, docker-compose | **OK** - env-based |
| `GUARDIAN_API_KEY` | `.env`, docker-compose | **OK** - env-based |
| `DATABASE_URL` | `.env` | **OK** - env-based |
| `NEO4J_PASSWORD` | `.env` | **OK** - default in code is "guardian" |
| Federation private key | Env or generated | **OK** - ephemeral if not set |

**No hardcoded secrets found** in scanned code paths.

---

### 8.2 Data Egress Map (Code-Evidenced)

| Outbound Call Site | Destination | Data Sent | Controls | Risk |
|--------------------|-------------|-----------|----------|------|
| [guardian/providers/openai_adapter.py:34-41](guardian/providers/openai_adapter.py#L34-L41) | api.openai.com | Prompt text, messages | API key required | **[RISK]** No user consent gate |
| [guardian/providers/openai_adapter.py:81-83](guardian/providers/openai_adapter.py#L81-L83) | api.openai.com | Embedding text | API key required | **[RISK]** No user consent gate |
| [guardian/providers/groq_adapter.py:31-37](guardian/providers/groq_adapter.py#L31-L37) | api.groq.com | Prompt text, messages | API key required | **[RISK]** No user consent gate |
| [guardian/connectors/github.py:26](guardian/connectors/github.py#L26) | api.github.com | Repo/issue requests | Token auth | **[WARN]** User-initiated sync |
| [guardian/connectors/notion.py:11](guardian/connectors/notion.py#L11) | api.notion.com | Database writes | Token auth | **[WARN]** User-initiated |
| [guardian/routes/federation.py:185](guardian/routes/federation.py#L185) | Peer nodes | Manifest fetch | Rate limited | **[WARN]** Federation trust |

**Local-First Violations:**
- Default model providers require sending prompts to external APIs
- No explicit "local-only mode" toggle to prevent egress

---

### 8.3 Access Control / Multi-User Considerations

**API Key Validation:** [guardian/core/dependencies.py](guardian/core/dependencies.py)
- `require_api_key` dependency checks `X-API-Key` header
- Single key per deployment (not per-user)

**User Isolation:**
- `user_id` field on threads, messages, memory
- No enforcement of cross-user access restrictions
- Single-tenant design assumed

**Weak Points:**
1. No per-user API key or JWT-based authentication
2. User_id is client-provided, not server-enforced
3. Federation peer trust based on manifest signature only

---

## Docs <-> Code Consistency

### Doc Claims Not Found in Code

| Claim | Source | Finding |
|-------|--------|---------|
| "Mobile/Scout integration" | docs/work/reports/codexify-mvp-roadmap.md | **Documented-only** - No mobile code found |
| "pgvector support" | README mentions | **Documented-only** - No pgvector code found |
| "GraphRAG integration" | Project goals | **Partial** - Neo4j exists but graph RAG pipeline incomplete |

### Code Not Described in Docs

| Feature | Location | Finding |
|---------|----------|---------|
| Federation diff sync | [guardian/federation/diff_engine.py](guardian/federation/diff_engine.py) | **Code drift** - Advanced feature undocumented |
| Collaboration permissions | [guardian/db/models.py:951-984](guardian/db/models.py#L951-L984) | **Code drift** - Full RBAC model undocumented |
| TTS outputs table | [guardian/db/models.py:594-635](guardian/db/models.py#L594-L635) | **Code drift** - TTS feature undocumented |

---

## Code Quality, Testing, and DX

### Type Hygiene

- **Python:** mypy configured in Makefile (`mypy $(SRC_DIR) $(TEST_DIR)`)
- **TypeScript:** Strict mode in frontend
- **Ruff:** Line length 88, E203 ignored for Black compatibility

### Lint/Format Setup

From [Makefile](Makefile):
```makefile
lint:
    ruff check $(RUFF_ARGS) $(SRC_DIR) $(TEST_DIR)
    mypy $(SRC_DIR) $(TEST_DIR)

format:
    black -l $(LINE_LENGTH) $(SRC_DIR) $(TEST_DIR)
    isort $(SRC_DIR) $(TEST_DIR)
```

### Test Suites

**Location:** [tests/](tests/)

**Test Categories:**
- `tests/routes/` - API route tests (chat, memory, connectors, etc.)
- `tests/federation/` - Federation protocol tests
- `tests/realtime/` - WebSocket/collaboration tests
- `tests/core/` - Core functionality tests
- `tests/integration/` - Integration tests

**Run Command:** `make test` or `pytest`

**Coverage Gaps:**
- Plugin runtime execution not tested (feature stubbed)
- Neo4j integration tests may be skipped when service unavailable

### Dev Experience

**Setup Scripts:**
- `make install` - Production deps
- `make dev-install` - Dev deps + pre-commit hooks
- `make venv` - Create virtualenv

**Run Instructions:**
- `make run` - Start system
- `make dev` - Start with debug
- `docker-compose up` - Full stack with services

**Env Templates:**
- [.env.example](.env.example) - Sample environment file

---

## Performance and Scalability

### Hot Paths Identified

| Path | Location | Concern |
|------|----------|---------|
| LLM API calls | Provider adapters | Blocking, timeout-bound (60s default) |
| Embedding generation | [backend/rag/embedder.py](backend/rag/embedder.py) | Synchronous, CPU-bound |
| Vector search | [backend/rag/embedder.py:185-241](backend/rag/embedder.py#L185-L241) | FAISS is fast, ChromaDB may be slower |
| Database queries | All route handlers | Async-capable via SQLAlchemy |

### Blocking Operations

- `SentenceTransformer.encode()` - Synchronous, should be backgrounded for large batches
- `requests.get()` in connectors - Blocking HTTP calls

### Potential Optimizations

| Optimization | Status | Impact |
|--------------|--------|--------|
| Background embedding | **Not implemented** | Med - Would unblock request handlers |
| Response streaming | **Implemented** | High - Available via provider adapters |
| Connection pooling | **Implemented** | High - SQLAlchemy manages pools |
| Caching | **Partial** | Med - Federation manifests cached |
| Pagination | **Implemented** | Med - Available on list endpoints |

---

## Risk Register & Recommendations

| ID | Area | Description | Impact | Likelihood | Effort | Next Action | Evidence | Status |
|----|------|-------------|--------|------------|--------|-------------|----------|--------|
| R01 | Privacy | LLM calls send prompts to external APIs without consent gates | High | High | Med | Add "local-only mode" config flag | [guardian/providers/](guardian/providers/) | Implemented (egress exists) |
| R02 | Security | Federation token validation skips signature verify | Med | Med | Low | Enable `verify_signature=True` with proper key lookup | [federation.py:287](guardian/routes/federation.py#L287) | Implemented (insecure) |
| R03 | Feature | Plugin runtime execution not wired | Med | Low | Med | Implement plugin execution engine | [plugin_loader.py](guardian/plugins/plugin_loader.py) | Stubbed |
| R04 | Feature | Neo4j sync disabled by default | Low | Low | Low | Document how to enable; test with Neo4j | [chat.py:511](guardian/routes/chat.py#L511) | Partial |
| R05 | Auth | Single API key for all users | Med | Med | High | Implement per-user JWT authentication | [dependencies.py](guardian/core/dependencies.py) | Implemented (limited) |
| R06 | Data | FAISS index lost on restart | Med | Med | Low | Default to ChromaDB or add FAISS persistence | [embedder.py](backend/rag/embedder.py) | Implemented |
| R07 | DX | Some tests skipped in CI | Low | Low | Low | Review and fix skipped tests | [tests/](tests/) | Partial |
| R08 | Docs | Federation features undocumented | Low | Low | Med | Add federation architecture doc | [federation.py](guardian/routes/federation.py) | Code drift |
| R09 | Privacy | user_id client-provided, not validated | Med | Med | High | Add authentication layer | Multiple routes | Implemented (weak) |
| R10 | Feature | GraphRAG not fully integrated | Med | Low | High | Complete graph-based retrieval pipeline | [guardian/graph/](guardian/graph/) | Partial |

---

## Prioritized Roadmap

### Phase 1: Critical Fixes (Security & Privacy)

1. **Add local-only mode** - Config flag to prevent LLM egress when using local models
2. **Fix federation token verification** - Enable signature verification in session accept flow
3. **Strengthen user_id handling** - At minimum, validate format; ideally add auth layer

### Phase 2: Important Improvements

4. **Complete plugin execution** - Wire plugin manifests to runtime invocation
5. **Enable Neo4j by default** - With proper connection retry and fallback
6. **Add FAISS persistence** - Or switch default to ChromaDB
7. **Document federation** - Architecture doc for cross-node collaboration

### Phase 3: Nice-to-Have Refinements

8. **Per-user authentication** - JWT-based auth with user isolation
9. **Complete GraphRAG** - Graph-based retrieval in RAG pipeline
10. **Background embedding** - Async/background embedding for large documents
11. **Comprehensive test coverage** - Fix skipped tests, add security path coverage

---

## Model Notes

### Agent Information
- **Model:** Claude Opus 4.5 (claude-opus-4-5-20251101)
- **Environment:** VSCode IDE Agent (Claude Code)

### Tooling Limitations

1. Could not execute runtime tests to verify actual behavior
2. Did not have access to run the application to verify runtime wiring
3. Some files may not have been read due to size limits

### Areas That Look Planned vs Real

| Feature | Assessment | Rationale |
|---------|------------|-----------|
| Mobile/Scout | **Planned** | Mentioned in docs, no code |
| Plugin execution | **Stubbed** | Loader works, no runtime invoke |
| pgvector | **Planned** | Not found in code |
| Neo4j | **Partial** | Code exists, disabled by default |
| Federation | **Implemented** | Full feature with tests |
| RAG | **Implemented** | Working pipeline verified in code |
| Multi-model routing | **Implemented** | Three providers confirmed |

---

*End of Codexify System Audit - 2026-01-10*
