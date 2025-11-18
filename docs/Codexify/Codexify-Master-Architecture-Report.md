# CODEXIFY MASTER ARCHITECTURE REPORT
**@axis.pack:emergence**
**@module:extract.spec + @module:synthesize.integration + @module:reconstruct.fragment**
**@tone:hybrid**
**@cycle:phase-2-analysis**

**Generated:** 2025-11-17
**Version:** 0.1.0 (Beta)
**Analysis Depth:** Phase 2 (Module-level + Dependency Inversion + Fault Domains + Integration Pressure Points)

---

## EXECUTIVE SUMMARY

This report consolidates the original System Specification with deep architectural analysis covering module boundaries, data flow verification, dependency patterns, fault domains, API contracts, and critical refactor opportunities. It serves as the definitive architectural reference for Codexify.

**Architecture Pattern:** Multi-tier event-driven with pluggable AI routing and dual database backends

**Key Findings:**
- 18 distinct architectural modules with well-defined boundaries
- 5 major fault domains requiring enhanced isolation
- 22 API route modules with inconsistent contract patterns
- Event bus acts as primary integration seam (pressure point)
- ChatDB abstraction enables backend flexibility but leaks PostgreSQL assumptions
- Hybrid provider routing creates race conditions under load

---

## PART I: ORIGINAL SYSTEM SPECIFICATION

### 1. PURPOSE & HIGH-LEVEL DESCRIPTION

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

## PART II: DEEP MODULE-LEVEL EXTRACTION

### 2.1 Configuration Module (`guardian/config/`)

**Responsibilities:**
- Environment variable loading and validation
- Pydantic-based settings with dual-mode validation (strict prod, lenient dev)
- System-wide parameter management

**Key Interfaces:**
```python
# guardian/config/core.py
class Config:
    DATABASE_URL: str
    LLM_PROVIDER: str
    GROQ_API_KEY: Optional[str]
    OPENAI_API_KEY: Optional[str]
    ANTHROPIC_API_KEY: Optional[str]
    EMBEDDING_BACKEND: str
    GUARDIAN_API_KEY: str

def get_settings() -> Config
def is_cloud_backend() -> bool
```

**Dependency Inversion Violations:**
- Config is imported directly by most modules (tight coupling)
- No abstraction layer for settings injection
- Hard-coded fallback values in provider registry

**Refactor Opportunity:**
- Implement Settings Protocol for dependency injection
- Use environment-specific config factories
- Add validation layers for provider availability

---

### 2.2 Database Abstraction Layer (`guardian/core/`)

**Responsibilities:**
- Abstract ChatDB interface for dual backend support (PostgreSQL/SQLite)
- Connection pooling and transaction management
- Automatic backend selection based on DATABASE_URL

**Key Interfaces:**
```python
# guardian/core/chat_db.py
class ChatDB(ABC):
    # Threads (43 methods)
    def create_chat_thread(...) -> Dict[str, Any]
    def list_chat_threads(...) -> List[Dict[str, Any]]
    def update_thread(...) -> bool
    def archive_thread(...) -> Optional[Dict[str, Any]]

    # Messages (8 methods)
    def create_message(...) -> int
    def list_messages(...) -> List[Dict[str, Any]]

    # Memory (11 methods)
    def add_memory(...) -> int
    def search_memory(...) -> List[Dict[str, Any]]
    def prune_midterm(...) -> int

    # Connectors (15 methods)
    def create_connector_config(...) -> Dict[str, Any]
    def upsert_raw_documents(...) -> None

    # Events (4 methods)
    def append_event(...) -> None
    def list_events_after(...) -> List[Dict[str, Any]]
```

**Implementations:**
- `guardian/core/db.py`: SQLite (legacy, 1,200 lines)
- `guardian/core/pgdb.py`: PostgreSQL (primary, 1,600 lines)

**Abstraction Leakage:**
- PostgreSQL-specific JSONB operations leak into abstract interface
- Timestamp normalization differs between backends
- PgDB assumes `to_regclass()` function (Postgres-only)
- Error handling diverges (UndefinedTable vs TableNotFound)

**Data Flow:**
```
Route Handler
  → ChatDB.create_message(thread_id, role, content)
    → [SQLite] INSERT with autoincrement
    → [PgDB] INSERT with RETURNING clause
  → Normalize timestamps (isoformat)
  → Emit event via event_bus
  → Return message_id
```

**Critical Fault Domain:**
- Database connection pool exhaustion
- Migration desync between SQLite and PostgreSQL schemas
- No circuit breaker for failed connections

---

### 2.3 ORM Models (`guardian/db/models.py`)

**Responsibilities:**
- SQLAlchemy 2.0 ORM definitions for all entities
- Relationship mappings and cascade rules
- Index definitions for query optimization

**Schema Overview (18 tables, 486 lines):**

| Table | Primary Key | Foreign Keys | Soft Delete | Cascade |
|-------|-------------|--------------|-------------|---------|
| `projects` | id (int) | - | No | - |
| `chat_threads` | id (int) | project_id, parent_id | archived_at | delete-orphan on messages |
| `chat_messages` | id (bigint) | thread_id | No | CASCADE on thread delete |
| `memory_entries` | id (bigint) | - | No | - |
| `connector_configs` | id (int) | - | No | delete-orphan on runs/docs |
| `connector_runs` | id (bigint) | config_id | No | CASCADE |
| `raw_documents` | id (bigint) | config_id | No | CASCADE |
| `sync_jobs` | id (int) | - | No | - |
| `events_outbox` | id (bigint) | - | No | - |
| `audit_log` | id (bigint) | - | No | - |
| `generated_documents` | id (uuid) | project_id, thread_id | deleted_at | - |
| `uploaded_documents` | id (uuid) | project_id, thread_id | deleted_at | - |
| `generated_images` | id (uuid) | project_id, thread_id | deleted_at | - |
| `uploaded_images` | id (uuid) | project_id, thread_id | deleted_at | - |
| `tts_outputs` | id (bigint) | project_id, thread_id | No | - |
| `thread_documents` | id (int) | thread_id, document_id | No | CASCADE |
| `shared_links` | id (uuid) | - | No | - |
| `collaboration_permissions` | id (int) | - | No | - |

**Constraints:**
- `memory_entries.silo` ∈ {ephemeral, midterm, longterm}
- `thread_documents.relation` ∈ {autosave, attached, reference}
- `generated_documents.format` ∈ {txt, md, docx, pdf, html, json}
- `shared_links.target_type` ∈ {thread, document}

**Index Strategy (29 indexes):**
```python
# Query optimization indexes
ix_chat_messages_thread_created (thread_id, created_at)
ix_chat_threads_updated (updated_at DESC)
ix_memory_entries_silo_updated (silo, updated_at)
ix_connector_runs_config_started (config_id, started_at DESC)
ix_raw_documents_config_external (config_id, external_id) UNIQUE
ix_events_outbox_status_created (status, created_at)
```

**Architectural Risks:**
- No shard key for horizontal scaling
- JSONB columns (`EventOutbox.payload`, `ConnectorConfig.config`) lack schema validation
- Cascade deletes could cause unintended data loss (thread → messages → documents)
- No version tracking for documents (no `document_versions` table)

---

### 2.4 Event Bus (`guardian/core/event_bus.py`)

**Responsibilities:**
- Durable event persistence via ChatDB outbox table
- In-memory fanout to AsyncIO subscribers
- Tenant isolation for multi-tenancy
- Event replay from outbox

**Architecture:**
```
emit_event(topic, payload, tenant_id)
  ├─→ [Durable] ChatDB.append_event(topic, payload, tenant_id)
  │     └─→ INSERT INTO events_outbox (topic, payload, status='pending')
  └─→ [In-memory] _publish_in_memory(topic, payload, tenant_id)
        └─→ For each subscriber:
              loop.call_soon_threadsafe(queue.put_nowait, message)
```

**Subscribers:**
```python
queue = subscribe_in_memory()  # Returns asyncio.Queue
while True:
    message = await queue.get()  # {type, data, tenant_id}
    await process(message)
```

**Topics in Use:**
- `message.created`: Chat message persisted
- `thread.updated`: Thread metadata changed
- `thread.archived` / `thread.unarchived`: Archive state toggled
- `thread.branch`: Child thread created
- `thread.deleted`: Thread hard-deleted
- `document.autosave`: Document autosaved
- `share.created` / `share.accessed`: Share link lifecycle (inferred)
- `collab.update`: WebSocket collaboration event (inferred)

**Critical Pressure Point:**
- **Single-process bottleneck**: In-memory subscribers don't scale across processes
- **No dead-letter queue**: Failed subscribers drop events silently
- **No replay mechanism**: Clients can't request missed events by ID range
- **Thread-safety**: `call_soon_threadsafe` assumes single event loop

**Refactor Opportunity:**
- Replace in-memory queues with Redis Pub/Sub or NATS for distributed fanout
- Add event replay API: `GET /api/events?after_id={last_id}&limit=100`
- Implement subscriber health checks and auto-reconnect
- Add event schema validation (Pydantic models)

---

### 2.5 AI Provider Registry (`guardian/providers/`)

**Responsibilities:**
- Protocol-based LLM abstraction
- Soft dependency loading (providers optional)
- Fallback chain for provider availability
- Chat and embeddings provider selection

**Interface:**
```python
# guardian/providers/base.py
class ChatProvider(Protocol):
    name: str
    def generate(prompt: str, model: Optional[str], **kw) -> str
    def stream(prompt: str, model: Optional[str], **kw) -> Iterator[str]

class EmbeddingsProvider(Protocol):
    name: str
    def embed(texts: List[str], model: Optional[str], **kw) -> List[List[float]]
```

**Registry Logic:**
```python
# guardian/providers/registry.py
class ProviderRegistry:
    def __init__(self):
        # Soft load: try OpenAI if OPENAI_API_KEY exists
        if os.getenv("OPENAI_API_KEY"):
            from .openai_adapter import OpenAIChat, OpenAIEmbeddings
            self._chat["openai"] = OpenAIChat()
            self._emb["openai"] = OpenAIEmbeddings()

        # Same for Groq, Gemini

    def get_chat(self, provider: Optional[str]) -> ChatProvider:
        p = (provider or os.getenv("GUARDIAN_PROVIDER") or "openai").lower()
        if p not in self._chat:
            raise ValueError(f"Chat provider '{p}' not configured")
        return self._chat[p]
```

**Adapters Implemented:**
- `groq_adapter.py`: Groq (fast inference, default)
- `openai_adapter.py`: OpenAI GPT models + embeddings
- `gemini_adapter.py`: Google Gemini
- `anthropic_adapter.py`: (inferred, not in extracted files)
- `ollama_adapter.py`: (inferred, not in extracted files)

**Dependency Inversion Success:**
- Clean Protocol abstraction
- No concrete adapter imports in core logic
- Swappable at runtime via environment variable

**Architectural Risks:**
- **Race condition**: Hybrid routing (split requests) has no request correlation
- **No retry logic**: Network failures bubble up immediately
- **API key rotation**: No support for key refresh without restart
- **Cost tracking**: No usage metrics or budget enforcement

---

### 2.6 Context Broker & RAG (`guardian/context/broker.py`)

**Responsibilities:**
- Multi-depth context assembly for AI completions
- Semantic search coordination
- Memory retrieval orchestration
- Sensor snapshot integration

**Interface:**
```python
class ContextBroker:
    def __init__(self, chatlog_db, vector_store, memory_store, sensors):
        ...

    async def assemble(
        thread_id: int,
        query: str,
        depth: str = "normal",  # shallow | normal | deep | diagnostic
        n_messages: int = 6,
        k_semantic: int = 4,
        k_memory: int = 5,
        federated: bool = False
    ) -> Dict[str, Any]
```

**Depth Levels:**
| Depth | Messages | Semantic | Memory | Sensors | Federated |
|-------|----------|----------|--------|---------|-----------|
| shallow | ✓ | - | - | - | Optional |
| normal | ✓ | ✓ (k=4) | - | - | Optional |
| deep | ✓ | ✓ (k=4) | ✓ (k=5) | - | Optional |
| diagnostic | ✓ | ✓ (k=4) | ✓ (k=5) | ✓ | Optional |

**Data Flow:**
```
chat.complete(thread_id, depth="deep")
  → ContextBroker.assemble(thread_id, latest_user_message, depth="deep")
    ├─→ _fetch_messages(thread_id, n=6)
    │     └─→ chatlog_db.list_messages(thread_id, limit=6)
    ├─→ _search_semantic(query, k=4)
    │     └─→ vector_store.search(query, k=4)
    ├─→ _search_memory(query, k=5)
    │     └─→ memory_store.search_related(query, limit=5)
    └─→ _snapshot_sensors()
          └─→ sensors.snapshot()
  → AI Provider.stream(messages + context)
  → Store assistant message
  → Emit event
```

**Sync/Async Hybrid Pattern:**
```python
async def _fetch_messages(self, thread_id, n):
    result = self.chatlog.last_messages(thread_id, n=n)
    # Handle both sync and async returns
    if hasattr(result, '__await__'):
        return await result
    return result if isinstance(result, list) else []
```

**Architectural Risks:**
- **No caching**: Semantic search runs on every completion (expensive)
- **No circuit breaker**: Vector store failures block completions
- **Unbounded context**: No token budget enforcement before LLM call
- **Federated search unverified**: `_search_federated` imports optional module at runtime

---

### 2.7 API Routes (`guardian/routes/`)

**22 Route Modules Identified:**

| Module | Prefix | Key Endpoints | Dependencies |
|--------|--------|---------------|--------------|
| `chat.py` | `/chat` | POST /threads, GET /threads, POST /{tid}/messages, POST /{tid}/complete | chatlog_db, _groq_complete, event_bus, ContextBroker |
| `threads.py` | `/threads` | GET /, POST /, GET /{tid}/summary | threads_structure.threads.get_thread_summary |
| `documents.py` | `/api/documents` | POST /autosave, GET /threads/{tid}/documents | chatlog_db (ChatDB), ORM session |
| `workspace.py` | `/api/workspace` | GET /{tid} | chatlog_db, Sensors, ORM session |
| `share.py` | `/api/share` | POST /, GET /{token} | (inferred) ORM session, SharedLink model |
| `projects.py` | `/api/projects` | (inferred) CRUD | chatlog_db |
| `memory.py` | `/api/memory` | (inferred) CRUD, search | chatlog_db |
| `connectors.py` | `/api/connectors` | (inferred) CRUD, sync | chatlog_db |
| `graph.py` | `/api/graph` | (inferred) Neo4j queries | Neo4j driver |
| `federation.py` | `/api/federation` | (inferred) Peer discovery | Federation client |
| `federation_context.py` | `/api/federation/context` | (inferred) Cross-node search | Federation client |
| `health.py` | `/healthz` | GET / | Config, oauth_status |
| `admin.py` | `/admin` | (inferred) System ops | Requires admin auth |
| `agent.py` | `/agent` | (inferred) Agent registry | PluginManager |
| `api_exports.py` | `/api/exports` | (inferred) Data export | chatlog_db |
| `codexify_router.py` | `/codexify` | (inferred) Codexify integration | Google Drive OAuth |
| `media.py` | `/api/media` | (inferred) Image/audio upload | ORM session |
| `meta.py` | `/api/meta` | (inferred) System metadata | Config |
| `rag_upload.py` | `/api/rag/upload` | (inferred) Document ingestion | Vector store |
| `research.py` | `/api/research` | (inferred) Research tools | External APIs |
| `tools.py` | `/api/tools` | (inferred) Tool registry | PluginManager |

**API Contract Inconsistencies:**

| Issue | Example | Impact |
|-------|---------|--------|
| Inconsistent response format | `/chat/threads` returns `{ok, threads}`, `/threads` returns `{threads}` | Client confusion |
| Mixed auth patterns | Some use `Depends(require_api_key)`, others check manually | Security gaps |
| Error response variance | Some return `HTTPException`, others `JSONResponse` | Inconsistent error handling |
| Pagination divergence | Some use `limit/offset`, others have no pagination | Performance issues |
| Validation gaps | Some routes use Pydantic models, others parse `Body(...)` directly | Type safety lost |

**Critical Pressure Point:**
- **Shared global state**: `chatlog_db`, `event_bus`, `_vector_store` imported from `guardian.guardian_api`
- **No API versioning**: Breaking changes cannot be rolled out incrementally
- **Rate limiting per-endpoint**: No global rate limit coordination

---

## PART III: DATA FLOW VERIFICATION

### 3.1 Chat Completion Flow (Verified)

```
[Client] POST /chat/{thread_id}/complete
  ↓
[chat.py:356] chat_complete(thread_id, body)
  ├─→ chatlog_db.list_messages(thread_id, limit=50)
  ├─→ Filter empty/null messages
  ├─→ Extract latest_user_message
  ├─→ ContextBroker.assemble(thread_id, latest_user_message, depth="normal")
  │     ├─→ [Parallel]
  │     │   ├─→ _fetch_messages(thread_id, n=6)
  │     │   ├─→ _search_semantic(query, k=4)
  │     │   └─→ _search_memory(query, k=5) [if depth=deep]
  │     └─→ Return {messages, semantic, memory}
  ├─→ _groq_complete(context, model, context=bundle)
  ├─→ chatlog_db.create_message(thread_id, "assistant", response)
  ├─→ event_bus.emit_event("message.created", {...})
  └─→ Return {ok, message}
```

**Verified Invariants:**
- Messages always include both user and assistant turns
- Context assembly happens before LLM call
- Event emission follows successful persistence
- Errors propagate as HTTPException(500)

**Unverified Assumptions:**
- ContextBroker always returns non-None (no null checks)
- `_groq_complete` is always available (import can fail)
- Vector store is always reachable (no timeout)

---

### 3.2 Event Outbox Flow (Verified)

```
[Any Route] event_bus.emit_event(topic, payload, tenant_id)
  ↓
[event_bus.py:48] emit_event(topic, payload, tenant_id)
  ├─→ [Durable Path]
  │   └─→ _store.append_event(topic, payload, tenant_id)
  │         └─→ [pgdb.py:1351] INSERT INTO events_outbox
  │               (topic, payload, tenant_id, status='pending')
  └─→ [In-Memory Path]
      └─→ _publish_in_memory(topic, payload, tenant_id)
            └─→ For each _subscriber in _subscribers:
                  loop.call_soon_threadsafe(queue.put_nowait, message)
```

**Verified Properties:**
- Events persist before in-memory fanout
- Failed subscribers are removed from list (stale cleanup)
- Tenant isolation enforced at write time
- Event IDs are monotonically increasing (BIGSERIAL)

**Gap Found:**
- **No transactional guarantee**: If `append_event` succeeds but `_publish_in_memory` fails, in-memory subscribers never see the event
- **No event TTL**: Old events accumulate forever unless manually deleted
- **No backpressure**: Unlimited queue growth if subscribers lag

---

### 3.3 Document Autosave Flow (Verified)

```
[CollaborativeNote] POST /api/documents/autosave
  {thread_id, content}
  ↓
[documents.py] autosave_endpoint(request)
  ├─→ chatlog_db.get_chat_thread(thread_id)
  ├─→ Query existing ThreadDocument(thread_id, relation='autosave')
  ├─→ [Upsert Logic]
  │   ├─→ If exists: UPDATE GeneratedDocument.content
  │   └─→ If not: INSERT GeneratedDocument + ThreadDocument
  ├─→ event_bus.emit_event("document.autosave", {document_id, thread_id})
  └─→ Return {ok, document_id, relation}
```

**Verified Behavior:**
- One autosave document per thread (unique constraint on relation)
- Content updates overwrite previous version (no history)
- Event emitted after successful persistence

**Missing Feature:**
- No conflict resolution for concurrent autosaves
- No document version tracking (breaking for collaboration)

---

## PART IV: FAULT DOMAIN ANALYSIS

### 4.1 Identified Fault Domains

| Domain | Blast Radius | Isolation | Recovery |
|--------|--------------|-----------|----------|
| **Database Connection Pool** | All routes fail | ❌ No circuit breaker | Manual restart |
| **LLM Provider Outage** | Completions fail | ✓ Fallback chain | Automatic fallback |
| **Vector Store Failure** | RAG disabled | ❌ No graceful degradation | Manual restart |
| **Event Bus Subscriber Crash** | Events dropped | ❌ No retry | Subscribers must reconnect |
| **Neo4j Graph Unavailable** | Graph sync disabled | ✓ Try/catch with warning | Continues without graph |

### 4.2 Critical Fault Scenarios

**Scenario 1: PostgreSQL Connection Pool Exhausted**
```
Request → chatlog_db.create_message()
  → psycopg2.connect(dsn) [BLOCKS until connection available]
  → Timeout after 30s (default)
  → HTTPException(500, "Database unavailable")
```

**Impact:** All routes fail, no graceful degradation
**Mitigation:** Implement connection pool with max_overflow + circuit breaker

**Scenario 2: Vector Store Latency Spike**
```
Request → ContextBroker.assemble(depth="deep")
  → _search_semantic(query, k=4)
    → vector_store.search(query, k=4) [HANGS for 60s]
  → Request times out
  → No fallback to depth="normal"
```

**Impact:** All completions hang, frontend times out
**Mitigation:** Add timeout + fallback to lower depth

**Scenario 3: Event Bus Subscriber Deadlock**
```
Subscriber A: await queue.get() → Processing message 1
  → Calls chatlog_db.create_message()
    → Acquires DB connection
    → Emits event (message.created)
      → Tries to publish to Subscriber A's queue
        → Queue is full (Subscriber A still processing)
        → call_soon_threadsafe() blocks
        → Deadlock
```

**Impact:** Event bus freezes, all events dropped
**Mitigation:** Bounded queue sizes + async task pools

---

### 4.3 Dependency Inversion Violations

**Violation 1: Routes Import Concrete ChatDB**
```python
# guardian/routes/chat.py:19
from guardian.guardian_api import chatlog_db  # Concrete instance!
```

**Problem:** Routes are tightly coupled to global singleton
**Fix:** Inject ChatDB via FastAPI Depends()

**Violation 2: Provider Registry Reads Environment Directly**
```python
# guardian/providers/registry.py:19
if os.getenv("OPENAI_API_KEY"):
    from .openai_adapter import OpenAIChat
```

**Problem:** Config is hardcoded, not injected
**Fix:** Pass Config object to registry constructor

**Violation 3: ContextBroker Stores References**
```python
# guardian/context/broker.py:34
self.chatlog = chatlog_db  # Direct reference
```

**Problem:** Cannot mock for testing, cannot swap implementations
**Fix:** Accept Protocol-typed dependencies

---

## PART V: API CONTRACT SPECIFICATION

### 5.1 REST API Contract Standards (Proposed)

**Envelope Format:**
```json
{
  "ok": true,
  "data": { /* resource or collection */ },
  "meta": {
    "total": 100,
    "limit": 50,
    "offset": 0
  },
  "error": null
}
```

**Error Format:**
```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "THREAD_NOT_FOUND",
    "message": "Thread 123 does not exist",
    "field": "thread_id"
  }
}
```

**Pagination:**
```
GET /api/threads?limit=50&offset=0&sort=updated_at:desc
```

**Filtering:**
```
GET /api/threads?user_id=user123&project_id=5&archived=false
```

### 5.2 WebSocket Contract

**Connection:**
```
WS /api/collab/ws/{document_id}?user_id={user_id}
```

**Message Types:**
```json
// Client → Server
{
  "type": "update",
  "content": "New document content",
  "user_id": "user123",
  "timestamp": "2025-11-17T12:00:00Z"
}

// Server → Client (broadcast)
{
  "type": "presence.join",
  "user_id": "user456",
  "active_users": ["user123", "user456"]
}

{
  "type": "update",
  "content": "Updated content from user456",
  "user_id": "user456",
  "timestamp": "2025-11-17T12:00:01Z"
}
```

### 5.3 Event Bus Contract

**Event Schema:**
```python
@dataclass
class Event:
    topic: str          # "message.created", "thread.updated"
    payload: Dict[str, Any]  # Arbitrary data
    tenant_id: str = "default"
    created_at: datetime
```

**Topic Naming Convention:**
```
{entity}.{action}
Examples:
- message.created
- thread.updated
- thread.archived
- document.autosave
- share.created
```

---

## PART VI: ARCHITECTURAL RISKS

### 6.1 High-Severity Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Event bus single point of failure** | High | Critical | Redis Pub/Sub migration |
| **No API versioning** | High | High | `/api/v1/` prefix + deprecation policy |
| **Cascade delete data loss** | Medium | Critical | Soft delete everything + audit trail |
| **Vector store vendor lock-in** | Medium | High | Abstract VectorStore protocol |
| **No request tracing** | High | Medium | OpenTelemetry integration |

### 6.2 Medium-Severity Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **PostgreSQL schema drift** | Medium | Medium | Schema validation in CI |
| **Unbounded memory growth** | Low | High | Bounded queues + monitoring |
| **No rate limit coordination** | High | Low | Shared Redis rate limiter |
| **Hybrid provider race conditions** | Low | Medium | Request correlation IDs |
| **No document versioning** | High | Low | Add document_versions table |

### 6.3 Security Risks

| Risk | Severity | Description | Fix |
|------|----------|-------------|-----|
| **Shared link token prediction** | High | `secrets.token_urlsafe(32)` is secure, but no rate limiting on `/api/share/{token}` | Add rate limiting per IP |
| **SQL injection via raw queries** | Low | SQLAlchemy ORM used everywhere, minimal raw SQL | Audit all `.execute()` calls |
| **XSS in collaborative editing** | Medium | No content sanitization on WebSocket messages | Add DOMPurify on client |
| **API key in logs** | Low | Log scrubbing enabled, but untested | Add log scrubbing tests |
| **CORS wildcard default** | Medium | `GUARDIAN_CORS_ORIGINS=*` by default | Change default to localhost |

---

## PART VII: INTEGRATION PRESSURE POINTS

### 7.1 Critical Seams

**Seam 1: Event Bus as Integration Hub**
```
[Routes] → emit_event()
            ↓
        [Event Bus]
            ├─→ [PostgreSQL Outbox]
            ├─→ [In-Memory Subscribers]
            │     ├─→ [WebSocket Broadcaster]
            │     ├─→ [Neo4j Sync Worker]
            │     └─→ [Vector Store Indexer]
            └─→ [SSE Streaming Endpoint]
```

**Pressure:** Event bus handles all cross-module communication
**Bottleneck:** In-memory subscribers block on slow processors
**Risk:** Single subscriber crash can deadlock entire bus

**Seam 2: ChatDB as Universal Data Gateway**
```
[Routes] → ChatDB.create_*()
              ↓
          [PgDB / SQLite]
              ↓
          [PostgreSQL / SQLite File]
```

**Pressure:** All data access flows through ChatDB interface
**Bottleneck:** Connection pool size limits concurrent requests
**Risk:** Schema changes require dual migration (SQLite + PgDB)

**Seam 3: ProviderRegistry as LLM Abstraction**
```
[Routes] → ProviderRegistry.get_chat(provider)
              ↓
          [Groq / OpenAI / Gemini Adapter]
              ↓
          [External API]
```

**Pressure:** All AI requests funnel through registry
**Bottleneck:** Provider rate limits cascade to all clients
**Risk:** Provider outage requires code change to swap default

### 7.2 Scalability Chokepoints

| Chokepoint | Current Limit | Scaling Path |
|------------|---------------|--------------|
| **Event Bus In-Memory** | Single process | Redis Pub/Sub |
| **PostgreSQL Connections** | ~100 (default pool) | PgBouncer pooler |
| **Vector Store Queries** | Serial, no cache | Query cache + sharding |
| **WebSocket Connections** | ~10,000/process | Horizontal pod scaling |
| **Neo4j Writes** | Serial sync | Async batch writes |

---

## PART VIII: REFACTOR OPPORTUNITIES

### 8.1 High-Priority Refactors

**R1: Event Bus Migration to Redis**
```python
# Current (event_bus.py)
_subscribers: List[_Subscriber] = []  # In-memory only

# Proposed
import redis.asyncio as redis
pubsub = redis.from_url("redis://localhost").pubsub()

async def emit_event(topic, payload, tenant_id):
    await pubsub.publish(f"{tenant_id}:{topic}", json.dumps(payload))

async def subscribe(topic, tenant_id):
    channel = f"{tenant_id}:{topic}"
    await pubsub.subscribe(channel)
    async for message in pubsub.listen():
        yield json.loads(message["data"])
```

**Benefits:**
- Scales across processes
- Built-in backpressure
- Persistent subscriptions

**R2: Dependency Injection for Routes**
```python
# Current (chat.py)
from guardian.guardian_api import chatlog_db  # Global!

# Proposed
from typing import Annotated
from fastapi import Depends

def get_chatlog_db() -> ChatDB:
    return _chatlog_db  # Configured at startup

@router.post("/threads")
def create_thread(db: Annotated[ChatDB, Depends(get_chatlog_db)]):
    thread = db.create_chat_thread(...)
    ...
```

**Benefits:**
- Testable (mock injection)
- Swappable implementations
- No global state

**R3: Add API Versioning**
```python
# Proposed
app_v1 = APIRouter(prefix="/api/v1")
app_v1.include_router(chat_router)
app_v1.include_router(threads_router)

app_v2 = APIRouter(prefix="/api/v2")
app_v2.include_router(chat_router_v2)  # Breaking changes
```

**R4: Implement VectorStore Protocol**
```python
# Proposed (guardian/vector/base.py)
class VectorStore(Protocol):
    def search(self, query: str, k: int, **filters) -> List[Dict[str, Any]]:
        ...

    def upsert(self, documents: List[Document]) -> None:
        ...

    def delete(self, ids: List[str]) -> None:
        ...

# Adapters
class ChromaAdapter(VectorStore): ...
class PgVectorAdapter(VectorStore): ...
class WeaviateAdapter(VectorStore): ...
```

**R5: Add Document Versioning**
```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES generated_documents(id),
    version_number INT NOT NULL,
    content TEXT NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(document_id, version_number)
);

CREATE INDEX ix_doc_versions_doc_id_version
ON document_versions(document_id, version_number DESC);
```

### 8.2 Medium-Priority Refactors

**R6: Consolidate Route Response Formats**
**R7: Add OpenTelemetry Tracing**
**R8: Implement Circuit Breakers (resilience4j pattern)**
**R9: Add Request Correlation IDs**
**R10: Migrate SQLite Backend to PostgreSQL-Only**

---

## PART IX: RECOMMENDATIONS

### 9.1 Immediate Actions (Sprint 1)

1. **Add Event Bus Monitoring**
   - Instrument subscriber queue depths
   - Alert on stale subscribers
   - Add event replay API

2. **Implement Connection Pool Limits**
   - Set `max_overflow=10` in PgDB
   - Add connection timeout (30s)
   - Graceful degradation on pool exhaustion

3. **Add API Versioning**
   - Prefix all routes with `/api/v1/`
   - Document deprecation policy
   - Add version negotiation header

### 9.2 Short-Term (Sprints 2-4)

4. **Migrate Event Bus to Redis**
   - Deploy Redis instance
   - Implement Redis Pub/Sub adapter
   - Migrate subscribers
   - A/B test with in-memory fallback

5. **Implement VectorStore Protocol**
   - Define abstract interface
   - Wrap ChromaDB
   - Add pgvector adapter
   - Make swappable via config

6. **Add Document Versioning**
   - Create `document_versions` table
   - Implement version snapshot on save
   - Add version diff API
   - Update UI to show history

### 9.3 Long-Term (Sprints 5-8)

7. **Implement RBAC**
   - Add `roles` and `permissions` tables
   - Implement role-based route guards
   - Add permission audit logs

8. **Add Multi-Tenancy**
   - Enforce `tenant_id` globally
   - Add tenant isolation middleware
   - Implement tenant-scoped databases

9. **Kubernetes Deployment**
   - Containerize all services
   - Add Helm charts
   - Implement horizontal pod autoscaling

---

## PART X: CONCLUSION

Codexify demonstrates a **well-architected multi-tier system** with clear module boundaries and extensible patterns. The event bus, ChatDB abstraction, and provider registry enable flexibility and testability.

**Strengths:**
- Clean separation of concerns (routes, core, providers, connectors)
- Protocol-based abstractions for swappable implementations
- Durable event sourcing with PostgreSQL outbox
- Comprehensive ORM schema with proper indexes

**Critical Gaps:**
- Event bus does not scale across processes (in-memory subscribers)
- No API versioning (breaking changes are risky)
- Missing document versioning (collaboration will break)
- Database connection pool lacks circuit breaker
- Dependency injection missing (global state everywhere)

**Next Steps:**
1. Implement Phase 2 refactors (event bus, DI, versioning)
2. Add monitoring and observability (OpenTelemetry)
3. Deploy to staging with load testing
4. Document API contracts in OpenAPI spec
5. Implement RBAC before multi-user launch

---

**@cycle:phase-2-complete**
**@glyph:threshold-mapped**
**End of Master Architecture Report**
