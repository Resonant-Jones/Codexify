# @module:extract.spec + @module:extract.graph
# @pattern:threshold-interface
# @tone:hybrid

## CODEXIFY SYSTEM SPECIFICATION
**Extracted:** 2025-11-16
**Version:** 0.1.0 (Beta)
**Architecture Pattern:** Multi-tier event-driven with pluggable AI routing

---

## 1. PURPOSE & HIGH-LEVEL DESCRIPTION

**Codexify** is a **local-first AI conversation orchestration and knowledge management platform**. It combines:
- Multi-provider LLM routing (Groq, OpenAI, Anthropic, Gemini, Ollama)
- Retrieval-augmented generation (RAG) with semantic search
- Three-tier memory architecture (ephemeral/midterm/longterm)
- Real-time collaborative editing
- Event-sourced audit trails
- Extensible plugin/connector framework

**Primary Use Cases:**
- Private AI chat with data sovereignty
- Knowledge base management with semantic search
- Document ingestion from GitHub, Notion, Google Workspace
- Multi-user collaborative note-taking
- Conversational memory with context persistence

---

## 2. CORE MODULES & RESPONSIBILITIES

### 2.1 Configuration Layer (`guardian/config/`)
**Purpose:** Centralized environment-based settings with Pydantic validation

**Key Components:**
- `core.py`: `Config` dataclass with `get_settings()` factory
- `system_config.py`: `SystemConfig` for system-level parameters
- Dual validation mode: strict (prod), lenient (dev/test)

**Environment Variables:**
- `DATABASE_URL`: PostgreSQL DSN
- `LLM_PROVIDER`: Active provider (groq/openai/anthropic/gemini)
- `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GENAI_API_KEY`
- `EMBEDDING_BACKEND`: sentence-transformers or stub
- `GUARDIAN_API_KEY`: Authentication secret

### 2.2 Database Layer (`guardian/core/`, `guardian/db/`)
**Purpose:** Abstract database interface with dual backend support

**Key Components:**
- `guardian/core/chat_db.py`: `ChatDB` abstract base class
- `guardian/core/db.py`: SQLite implementation (legacy)
- `guardian/core/pgdb.py`: **PostgreSQL implementation (primary)**
- `guardian/core/__init__.py`: Auto-detects backend from `DATABASE_URL`

**Data Models** (`guardian/db/models.py`):
- `ChatThread`: Conversation threads with hierarchy (parent_id)
- `ChatMessage`: Individual messages (role, content, timestamps)
- `GeneratedDocument`: AI-generated docs (markdown/json/docx/pdf)
- `UploadedDocument`: User uploads with parsed text
- `MemoryEntry`: Three-tier memory storage (ephemeral/midterm/longterm)
- `ConnectorConfig`: External service configurations
- `ConnectorRun`: Sync job execution logs
- `RawDocument`: Unprocessed connector ingestion
- `EventOutbox`: Durable event log with outbox pattern
- `AuditLog`: Compliance and change tracking
- `SharedLink`: Secure token-based sharing

**Migrations:**
- Alembic-based (revision ac973209add4 is foundational)
- Tables: `chat_threads`, `chat_messages`, `memory_entries`, `events_outbox`, `sync_jobs`, `connector_*`, `projects`, `agent_profiles`

### 2.3 AI Provider System (`guardian/providers/`)
**Purpose:** Protocol-based LLM abstraction with soft dependency loading

**Interface** (`base.py`):
```python
class ChatProvider(Protocol):
    name: str
    def generate(prompt, model=None, **kw) -> str
    def stream(prompt, model=None, **kw) -> Iterator[str]

class EmbeddingsProvider(Protocol):
    name: str
    def embed(texts, model=None, **kw) -> List[List[float]]
```

**Adapters:**
- `groq_adapter.py`: Groq (fast inference, default)
- `openai_adapter.py`: OpenAI GPT models
- `gemini_adapter.py`: Google Gemini
- `anthropic_adapter.py`: Claude models (inferred)
- `ollama_adapter.py`: Local models (inferred)

**Registry** (`registry.py`):
- Dynamic provider loading
- Fallback chain: configured → Groq → OpenAI → Anthropic
- Hybrid routing: split requests across cloud/local models

### 2.4 Memory System (`guardian/memory/`, `guardian/memoryos/`)
**Purpose:** Three-tier memory with heat-based eviction

**Architecture** (inferred from README):
- **Ephemeral (Short-term)**: Deque-based, conversation-scoped
- **Midterm**: Heat-scored entries, semantic indexing
- **Longterm**: Knowledge-extracted, vectorized, persistent

**Key Files:**
- `guardian/memory/conversation.py`: Conversational memory
- `guardian/memory/query_memory.py`: Memory search
- `guardian/memoryos/*`: Orchestrator layer (file not readable, inferred from structure)

**Operations:**
- `add_memory(user_id, silo, content, tags, pinned)`
- `list_memories(silo, limit, offset)`
- `search_memory(query, limit)`
- `prune_midterm(older_than_iso)`

### 2.5 Event Bus (`guardian/core/event_bus.py`)
**Purpose:** Durable event sourcing with PostgreSQL outbox pattern

**Features:**
- Persistent event storage in `events_outbox` table
- In-memory fanout via AsyncIO queues
- Topics: `collab.update`, `document.autosave`, `share.created`, `share.accessed`
- Tenant isolation (tenant_id)

**API:**
```python
configure_event_store(store: ChatDB)
emit_event(topic, payload, tenant_id="default")
queue = subscribe_in_memory()  # Returns asyncio.Queue
```

### 2.6 API Routes (`guardian/routes/`, `guardian/api/`)
**Purpose:** FastAPI endpoint modules

**22+ Route Files:**
- `documents.py`: Autosave, document linkage
- `workspace.py`: Workspace state aggregation
- `share.py`: Secure link generation/access (inferred)
- `threads.py`: Thread CRUD (inferred)
- `messages.py`: Message operations (inferred)
- `memory.py`: Memory API (inferred)
- `connectors.py`: Connector management (inferred)
- `federation_context.py`: Federated search (referenced in broker.py)

**Server** (`guardian/server/app.py`):
- **Rate limiting**: slowapi with configurable limits (`GUARDIAN_RATE_LIMITS`)
- **CORS**: Configurable origins (`GUARDIAN_CORS_ORIGINS`)
- **Security headers**: CSP, HSTS via `fastapi-security-headers`
- **Log scrubbing**: Masks `client_secret*.json`, `token.*`, `.pem` files
- **Health endpoint**: `/healthz`

### 2.7 Context Assembly & RAG (`guardian/context/broker.py`)
**Purpose:** Multi-depth context assembly for AI completions

**Depth Levels:**
- **shallow**: Recent messages only
- **normal**: Messages + semantic search
- **deep**: Messages + semantic + memory search
- **diagnostic**: Messages + semantic + memory + sensor snapshots

**API:**
```python
broker = ContextBroker(chatlog_db, vector_store, memory_store, sensors)
context = await broker.assemble(
    thread_id, query, depth="normal",
    n_messages=6, k_semantic=4, k_memory=5,
    federated=False
)
```

**Returns:**
```python
{
    "messages": [...],      # Always
    "semantic": [...],      # normal+
    "memory": [...],        # deep+
    "sensors": {...},       # diagnostic only
    "federated": [...]      # if federated=True
}
```

### 2.8 Authentication (`guardian/core/auth.py`)
**Purpose:** Multi-method authentication with timing-attack protection

**Methods:**
1. **API Key**: `X-API-Key: {GUARDIAN_API_KEY}`
2. **Bearer Token**: `Authorization: Bearer {session_token}`
3. **Session Cookie**: `gc_session: {session_token}`

**Session Tokens:**
- HMAC-SHA256 signed
- Format: `base64(payload.nonce.signature)`
- Payload: `subject.exp.nonce`
- TTL: 86400s default (24 hours)
- Secret resolution: `GUARDIAN_SESSION_SECRET` → `GUARDIAN_API_KEY` → `dev-secret`

**API:**
```python
token, expires = issue_session_token(subject="web", ttl_seconds=86400)
valid, subject = verify_session_token(token)
user_id = extract_auth_identity(x_api_key, authorization, gc_session)
```

### 2.9 Plugins (`guardian/plugins/`)
**Purpose:** Extensible agent and analyzer framework

**Structure** (inferred):
- `PluginBase` abstract contract
- Manifest-based registration (`manifest.yaml`)
- Dependency injection of core services
- Per-plugin test directories

**Examples:**
- Pattern analyzers
- Memory analyzers
- Custom tools

### 2.10 Connectors (`guardian/connectors/`)
**Purpose:** External service integration for document ingestion

**Supported Services:**
- GitHub (issues, PRs, code)
- Notion (pages, databases)
- Google Workspace (Drive, Docs)
- Slack (inferred)

**Database Schema:**
- `connector_configs`: Connection settings
- `connector_runs`: Execution history
- `raw_documents`: Ingested data before processing

**Operations:**
```python
create_connector_config(name, type, config, schedule)
create_connector_run(config_id, status, started_at, error)
upsert_raw_documents(config_id, docs)
```

### 2.11 Real-time Collaboration (`guardian/realtime/collaboration.py`)
**Purpose:** WebSocket-based multi-user document editing

**Features:**
- Presence tracking (join/leave)
- Broadcast updates to all connected clients
- Connection pooling per document
- Event emission for telemetry

**Endpoint:**
```
WS /api/collab/ws/{document_id}
```

**Message Types:**
- `presence.join`: User joined
- `presence.leave`: User left
- `update`: Content change

---

## 3. DATA FLOW & STATE FLOW

### 3.1 Chat Completion Flow
```
User → FastAPI /api/chat
  → ContextBroker.assemble(thread_id, query, depth)
    → Fetch messages (ChatDB)
    → Semantic search (VectorStore)
    → Memory search (MemoryStore)
    → Sensor snapshot (Sensors)
  → AI Router (hybrid or single provider)
    → Provider.stream(prompt, model)
  → Store message (ChatDB.create_message)
  → Emit event (event_bus.emit_event)
  → Stream response to client
```

### 3.2 Memory Promotion Flow
```
Short-term (deque)
  → Eviction trigger (size/time)
    → Mid-term storage (heat scoring)
      → Heat decay over time
        → Promotion to Long-term
          → Knowledge extraction
            → Vector indexing (ChromaDB/pgvector)
```

### 3.3 Event Outbox Flow
```
emit_event(topic, payload, tenant_id)
  → Insert into events_outbox (PostgreSQL)
  → Fanout to in-memory subscribers (AsyncIO queues)
  → Subscribers process events
  → Cleanup old events (delete_events_through)
```

### 3.4 Connector Sync Flow
```
Connector.sync()
  → create_sync_job(connector_id, status="queued")
  → update_sync_job(job_id, status="running", started_at=now)
  → Fetch from external API (GitHub/Notion/etc.)
  → upsert_raw_documents(config_id, docs)
  → Process documents → memory entries
  → update_sync_job(job_id, status="completed", finished_at=now)
```

---

## 4. INVARIANTS & CONSTRAINTS

### 4.1 Database Invariants
- `ChatThread.id` is unique primary key
- `ChatMessage.thread_id` must reference existing thread
- `MemoryEntry.silo` ∈ {ephemeral, midterm, longterm}
- `EventOutbox.status` ∈ {pending, processed}
- Soft deletes use `deleted_at` timestamp (GeneratedDocument, UploadedDocument)

### 4.2 Memory Invariants
- Ephemeral memory has bounded size (deque)
- Midterm entries have heat scores that decay
- Longterm entries are immutable once promoted
- Vector embeddings use consistent dimensionality (384 by default)

### 4.3 Authentication Invariants
- Session tokens expire after TTL
- HMAC verification uses constant-time comparison
- API keys never appear in logs (scrubbed)

### 4.4 Event Bus Invariants
- Events persist in PostgreSQL before fanout
- Event IDs are monotonically increasing (BIGSERIAL)
- Tenant isolation enforced on read/write

---

## 5. PERFORMANCE CONSIDERATIONS

### 5.1 Database Optimization
- **Indexes:**
  - `(thread_id, created_at)` on `chat_messages`
  - `(user_id)` on `chat_threads`
  - `(connector_id, created_at)` on `sync_jobs`
  - `(config_id, external_id)` unique on `raw_documents`
- **Connection pooling:** psycopg2 context managers
- **Pagination:** LIMIT/OFFSET on all list operations
- **Server-side cursors:** `fetch_threads_for_user()` for large exports

### 5.2 Vector Search
- **Backends:** ChromaDB (default), pgvector (PostgreSQL extension)
- **Embedding dimension:** 384 (sentence-transformers)
- **Batch embedding:** Process texts in batches to reduce API calls
- **Semantic caching:** Cache frequent queries

### 5.3 AI Provider Optimization
- **Streaming:** Use `stream()` for real-time responses
- **Hybrid routing:** Split expensive/cheap queries across providers
- **Rate limiting:** slowapi with per-IP limits
- **Fallback chain:** Automatic provider fallback on failure

### 5.4 Event Bus Optimization
- **In-memory fanout:** AsyncIO queues for low-latency delivery
- **Durable persistence:** PostgreSQL for reliability
- **Cleanup:** Periodic deletion of processed events

---

## 6. ERROR MODEL & FAULT DOMAINS

### 6.1 Database Errors
- **UndefinedTable:** Missing migrations → fail fast with migration prompt
- **UniqueViolation:** Idempotent operations use `ON CONFLICT DO NOTHING`
- **Connection errors:** Retry with exponential backoff (not implemented in core, only in export)

### 6.2 Provider Errors
- **API key missing:** Fall back to next provider in chain
- **Rate limit:** Retry with backoff (provider-specific)
- **Model not found:** Fall back to default model

### 6.3 Vector Store Errors
- **Embedding failure:** Return empty results, log warning
- **Index corruption:** Rebuild index from database

### 6.4 Event Bus Errors
- **Outbox write failure:** Transaction rollback, surface error
- **Subscriber failure:** Isolated per subscriber, logged

---

## 7. INTEGRATION POINTS

### 7.1 External Services
- **LLM APIs:** OpenAI, Groq, Google Gemini, Anthropic
- **Vector Stores:** ChromaDB, pgvector
- **Graph Database:** Neo4j (referenced in README, not in extracted code)
- **External APIs:** GitHub, Notion, Google Workspace, Slack

### 7.2 Frontend Integration
- **React 19** (`frontend/src/`)
- **TypeScript** with Vite
- **Tailwind CSS 4.1.14**
- **WebSocket** for real-time collaboration
- **REST API** for CRUD operations

### 7.3 Desktop Integration
- **Tauri** (`src-tauri/`)
- Rust backend for native OS integration

---

## 8. TEST PHILOSOPHY

**Framework:** pytest with pytest-asyncio

**Test Organization:**
- Unit tests: `guardian/tests/test_*.py`
- Integration tests: Database-backed (requires PostgreSQL or SQLite)
- Network tests: Gated by `ALLOW_NET_TESTS=1`
- Fixtures: `conftest.py` provides DB fixtures

**Coverage:**
- Core logic: High (contracts, event bus, auth)
- Routes: Medium (autosave, share links, workspace)
- Providers: Low (soft dependencies, network-dependent)

**CI/CD:**
- GitHub Actions (`guardian-ci.yml`)
- Python 3.10, 3.11, 3.12
- Database schema validation
- Security scanning (Bandit)

---

## 9. DEPLOYMENT PATTERNS

### 9.1 Docker Compose (Recommended)
```yaml
services:
  postgres:
  neo4j:
  backend:
  frontend:
  migrator:
```

### 9.2 Environment Requirements
- PostgreSQL 15+
- Python 3.10+
- Node.js 20+
- pnpm 9+
- Neo4j 5+ (optional for knowledge graph)

### 9.3 Configuration
- `.env` file with API keys
- Database migrations via Alembic
- Pre-commit hooks for code quality

---

## 10. DEPENDENCY GRAPH

### 10.1 Core Dependencies
```
FastAPI 0.119.1
  └─ Uvicorn 0.38.0 (ASGI server)

SQLAlchemy 2.0.44
  ├─ psycopg2 (PostgreSQL)
  └─ aiosqlite (SQLite fallback)

Pydantic 2.x
  └─ pydantic-settings (env validation)

LangChain 1.0.2 (LLM orchestration)

ChromaDB 1.2.1 (vector store)
  └─ sentence-transformers 2.6+ (embeddings)

slowapi 0.1.8+ (rate limiting)
prometheus-client 0.20.0+ (metrics)
```

### 10.2 Optional Dependencies
```
dev:
  - black, ruff, isort (formatting)
  - mypy (type checking)
  - pytest, pytest-asyncio (testing)
  - mcp, notion-client, markitdown

tui:
  - textual 0.50+
  - rich 13+

rag:
  - chromadb 0.5+
  - faiss-cpu 1.7+
  - sentence-transformers 2.6+
  - openai 1.0+
```

### 10.3 Module Dependency Map
```
guardian/server/app.py
  ├─ guardian/routes/* (API endpoints)
  ├─ guardian/core/db (database adapter)
  ├─ guardian/core/event_bus (events)
  └─ guardian/config/core (settings)

guardian/routes/*
  ├─ guardian/core/db (data access)
  ├─ guardian/db/models (ORM)
  └─ guardian/core/event_bus (emit events)

guardian/context/broker.py
  ├─ guardian/core/db (messages)
  ├─ guardian/vector/* (semantic search)
  ├─ guardian/memory/* (memory search)
  └─ guardian/sensors/* (diagnostics)

guardian/providers/*
  └─ External APIs (OpenAI, Groq, etc.)

guardian/connectors/*
  ├─ guardian/core/db (connector configs)
  └─ External APIs (GitHub, Notion, etc.)
```

---

## 11. KNOWN LIMITATIONS

### 11.1 Architectural Gaps
- **No RBAC:** Basic user_id ownership, no fine-grained permissions
- **No OT/CRDT:** Real-time collaboration uses last-write-wins semantics
- **Single-tenant:** Multi-tenancy support exists in outbox but not enforced globally
- **No document versioning:** No diff/merge capabilities
- **No cursor tracking:** WebSocket presence shows join/leave only

### 11.2 Scaling Limits
- **In-memory event fanout:** Doesn't scale across processes (needs Redis/NATS)
- **Rate limiting storage:** In-memory (upgrade to Redis for multi-instance)
- **Vector store:** ChromaDB is single-node (pgvector scales better)

---

## 12. FUTURE EVOLUTION PATHS

### 12.1 Planned Features (from README roadmap)
- WebSocket support for real-time updates ✅ (exists in `/realtime`)
- Advanced RAG with hybrid search
- Fine-tuning support for local models
- Multi-user authentication & RBAC
- Kubernetes deployment guides
- Plugin marketplace

### 12.2 Suggested Enhancements
- **CRDT-based collaboration:** Replace last-write-wins
- **Distributed event bus:** Redis Streams or NATS
- **Multi-tenant isolation:** Enforce tenant_id across all tables
- **Document versioning:** Git-like diffs for GeneratedDocument
- **Advanced search:** Full-text search with PostgreSQL tsvector

---

@cycle:coherence-complete
@glyph:extraction-sigil
**End of System Spec Extraction**
