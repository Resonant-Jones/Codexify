# Guardian Codebase Structure - Collaboration & Realtime Features

## Executive Summary

The Guardian codebase implements a comprehensive collaborative editing system with WebSocket support, autosave functionality, and secure sharing capabilities. The architecture uses FastAPI with SQLAlchemy ORM models, a durable event bus backed by PostgreSQL, and React components for real-time UI updates.

---

## 1. COLLABORATION/REALTIME INFRASTRUCTURE

### WebSocket Server & Collaboration Manager

**Location:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/realtime/collaboration.py`

**Key Components:**
- **CollaborationManager**: Core class managing WebSocket connections for document editing
  - Maintains active connections per document (`Dict[str, Set[WebSocket]]`)
  - Tracks user presence (`Dict[str, Set[str]]`)
  - Broadcasts updates to all connected clients
  - Emits telemetry events via event bus

**Key Methods:**
- `connect(doc_id, ws, user_id)`: Register new WebSocket, broadcast presence.join
- `disconnect(doc_id, ws, user_id)`: Remove connection, broadcast presence.leave
- `broadcast(doc_id, message)`: Send message to all connected clients
- `get_active_sessions()`: Return count of active collaboration sessions
- `get_session_user_count(doc_id)`: Get number of active users in a session

**WebSocket Endpoint:**
```
POST /api/collab/ws/{document_id}
```
- Accepts WebSocket connections
- Receives JSON updates from clients
- Broadcasts to all connected clients
- Emits `collab.update` events for metrics

**Message Types:**
- `presence.join`: When user joins document session
- `presence.leave`: When user leaves document session
- `update`: Content/document updates from clients

**Event Topics:**
- `collab.update`: Emitted on each client update (includes document_id, user_id, active_sessions count)

---

## 2. DATABASE MODELS STRUCTURE

### Location
`/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/db/models.py`

### Core ORM Models

#### Chat & Threading Models
- **ChatThread**: Main conversation threads
  - Columns: id, user_id, title, summary, project_id, parent_id, archived_at, created_at, updated_at
  - Relationships: messages (one-to-many), parent/children (self-referential)
  - Indexes: user_id, project_id, parent_id, updated_at

- **ChatMessage**: Individual messages in threads
  - Columns: id (BigInteger), thread_id, role, content, created_at
  - Relationship: thread (back-reference to ChatThread)
  - Indexes: thread_id, (thread_id, created_at)

#### Document Models
- **GeneratedDocument**: AI-generated documents
  - Columns: id (UUID), project_id, thread_id, user_id, title, content, format (txt/md/docx/pdf/html/json), model, created_at, updated_at, deleted_at
  - Relationships: project, thread
  - Use: Autosave documents, generated outputs

- **UploadedDocument**: User-uploaded documents with full-text search
  - Columns: id (UUID), project_id, thread_id, user_id, filename, filesize, mime_type, src_url, parsed_text, created_at, updated_at, deleted_at
  - Relationships: project, thread

- **UploadedImage**: User-uploaded images
  - Columns: id (UUID), project_id, thread_id, user_id, src_url, filename, filesize, mime_type, created_at, updated_at, deleted_at

- **GeneratedImage**: AI-generated images
  - Columns: id (UUID), project_id, thread_id, user_id, src_url, prompt, model, created_at, updated_at, deleted_at

#### Linkage Models
- **ThreadDocument**: Links documents to chat threads
  - Columns: id (Integer), thread_id (FK), document_id (UUID), relation (autosave/attached/reference), created_at
  - Purpose: Associates multiple documents with a thread
  - Indexes: thread_id, (thread_id, relation), document_id

#### Sharing Models
- **SharedLink**: Secure shareable links for threads and documents
  - Columns: id (UUID), target_type (thread/document), target_id (Integer), token (URL-safe secure token), expires_at (optional), created_at
  - Purpose: Public read-only access via secure token
  - Indexes: token, (target_type, target_id)

#### Project Models
- **Project**: Organize chat threads and resources
  - Columns: id, name (unique), description, icon, created_at, updated_at

#### Memory & Connector Models
- **MemoryEntry**: Memory silos (ephemeral, midterm, longterm)
- **ConnectorConfig**: Configuration for external service connectors (GitHub, GDrive, etc.)
- **ConnectorRun**: Track connector sync job executions
- **RawDocument**: Raw documents from connectors before processing
- **SyncJob**: Background sync job bookkeeping

#### Audit & Events
- **EventOutbox**: Durable event outbox for SSE/event replay
  - Columns: id (BigInteger), topic, payload (JSONB), status (pending/processed), tenant_id, created_at
  - Purpose: Store events for durability and replay

- **AuditLog**: Generic audit trail
  - Columns: id, event (create/update/delete/archive), entity, entity_id, user_id, timestamp
  - Indexes: timestamp DESC, (entity, entity_id)

#### Legacy Models (Deprecated)
- **Message**: Generic messages (most code uses ChatMessage instead)

#### Text-to-Speech
- **TTSOutput**: Text-to-speech synthesis outputs
  - Columns: id, project_id, thread_id, user_id, text, voice, provider, model, src_url, duration_seconds, created_at

### Database Base Class
```python
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass
```

---

## 3. API ROUTES FOR COLLABORATION & SHARING

### Documents Route
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/routes/documents.py`

**Endpoints:**

1. **POST /api/documents/autosave**
   - Request: `AutosaveRequest(thread_id: int, content: str)`
   - Response: `AutosaveResponse(ok: bool, document_id: str, relation: str)`
   - Logic:
     - Verify thread exists
     - Check if autosave document already exists for thread
     - Update existing or create new `GeneratedDocument` with format='md', model='autosave'
     - Create/update `ThreadDocument` link with relation='autosave'
     - Emit `document.autosave` event
   - Error Handling: 400 (validation), 404 (thread not found), 500 (errors)

2. **GET /api/threads/{thread_id}/documents**
   - Response: `Dict[ok, documents: Array[{id, title, relation, created_at}]]`
   - Logic:
     - Verify thread exists
     - Fetch all `ThreadDocument` links for thread
     - Retrieve document details from `GeneratedDocument`
     - Order by creation date (newest first)
   - Error Handling: 404 (thread not found), 500 (errors)

### Share Route
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/routes/share.py`

**Endpoints:**

1. **POST /api/share**
   - Request: `CreateShareRequest(target_type: str, target_id: int, expires_in_days: Optional[int])`
   - Response: `CreateShareResponse(ok: bool, token: str, url: str, expires_at: Optional[str])`
   - Logic:
     - Validate target_type (thread/document)
     - Verify target exists (ChatThread or GeneratedDocument or UploadedDocument)
     - Generate secure token: `secrets.token_urlsafe(32)` (43 chars)
     - Calculate expiry: `datetime.now(UTC) + timedelta(days=expires_in_days)`
     - Create `SharedLink` record with token and optional expiry
     - Emit `share.created` event
   - URL Format: `/share/{token}`
   - Error Handling: 400 (invalid target_type), 404 (target not found), 500 (errors)

2. **GET /api/share/{token}**
   - Response: `ShareContentResponse(ok: bool, target_type: str, target_id: int, content: Dict)`
   - Logic:
     - Find `SharedLink` by token
     - Validate token hasn't expired
     - Fetch target content (thread with messages or document details)
     - Return read-only content representation
     - Emit `share.accessed` event
   - Error Handling: 404 (token not found/expired), 500 (errors)

### Workspace Route
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/routes/workspace.py`

**Endpoint:**

1. **GET /api/workspace/{thread_id}**
   - Response: `Dict[thread, documents: Array, diagnostics]`
   - Logic:
     - Fetch thread metadata
     - Collect linked documents via `_collect_thread_documents()`
     - Fetch workspace diagnostics via Sensors
     - Return combined workspace state
   - Purpose: Hydrate workspace pane with full context

---

## 4. FRONTEND COMPONENTS

### CollaborativeNote Component
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/frontend/src/components/editor/CollaborativeNote.tsx`

**Props:**
```typescript
type CollaborativeNoteProps = {
  documentId: string;
  threadId: number;
  userId?: string;
  initialContent?: string;
  onContentChange?: (content: string) => void;
};
```

**Features:**
- WebSocket connection to `/api/collab/ws/{documentId}`
- Real-time content synchronization
- Presence indicators (colored avatars for active users)
- Connection status indicator (green/red dot)
- Autosave every 15 seconds to `/api/documents/autosave`
- Last autosave timestamp display
- Color-coded user avatars (5-color rotation)

**WebSocket Messages:**
- Send: `{content, user_id, timestamp}`
- Receive: `{type: "update" | "presence.join" | "presence.leave", payload/active_users}`

**State Management:**
- `content`: Current document content
- `activeUsers`: List of connected users with colors
- `isConnected`: WebSocket connection status
- `lastAutosave`: Timestamp of last autosave

**Styling:**
- Flex column layout, monospace font
- Header with connection status and presence avatars
- Textarea for editing
- Responsive design with border and padding

### ShareButton Component
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/frontend/src/components/ShareButton.tsx`

**Props:**
```typescript
type ShareButtonProps = {
  targetType: "thread" | "document";
  targetId: number;
};
```

**Features:**
- Button to create shareable links
- POST to `/api/share` with target_type and target_id
- Copy share link to clipboard automatically
- Toast notification with full URL
- Loading state during creation
- Error handling with user feedback

**Flow:**
1. User clicks "Share" button
2. POST to `/api/share` with target info
3. Receive secure token and URL
4. Copy full URL to clipboard: `{origin}/share/{token}`
5. Show success toast with URL for 3 seconds

### SharePage Component
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/frontend/src/pages/SharePage.tsx`

**Props:**
```typescript
type SharePageProps = {
  token: string;
};
```

**Features:**
- Fetch shared content via GET `/api/share/{token}`
- Display thread or document in read-only format
- Handle loading and error states
- Show thread with conversation or document with content
- Support for both GeneratedDocument and UploadedDocument types

**Content Display:**
- **Threads**: Title, summary, messages list with timestamps
- **GeneratedDocuments**: Title, formatted content, metadata
- **UploadedDocuments**: Filename, filesize, MIME type, download link

---

## 5. AUTHENTICATION & PERMISSION PATTERNS

### Auth Module
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/core/auth.py`

**AuthenticatedUser Dataclass:**
```python
@dataclass(frozen=True)
class AuthenticatedUser:
    id: str        # User identifier
    kind: str      # Authentication type
```

**Session Token Functions:**

1. **issue_session_token(subject="web", ttl_seconds=86400)**
   - Issues HMAC-signed opaque session token
   - Returns: `(token, expires_at_epoch_seconds)`
   - Token format: `base64_encode(payload.nonce.signature)`
   - Payload: `subject.exp.nonce`
   - Secret resolution order:
     1. GUARDIAN_SESSION_SECRET env var
     2. GUARDIAN_API_KEY env var
     3. Fallback: "dev-secret" (local dev only)

2. **verify_session_token(token: str)**
   - Validates HMAC-signed token
   - Returns: `(valid: bool, subject: Optional[str])`
   - Checks: signature, expiry, token format
   - Safe: uses `hmac.compare_digest()` for timing attacks

3. **extract_auth_identity(x_api_key, authorization, gc_session)**
   - Multi-method auth identity extraction
   - Accepts: X-API-Key header, Authorization header, session cookie
   - Returns: user identity string or None

**Auth Patterns:**
- API Key: `X-API-Key: {GUARDIAN_API_KEY}`
- Bearer Token: `Authorization: Bearer {session_token}`
- Session Cookie: `gc_session: {session_token}`
- All use constant-time comparison for security

**User Manager:**
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/core/user_manager.py`
- Centralized user management
- Used for user-scoped operations

### Permission Model
**Current State:**
- **Basic user_id ownership**: ChatThread.user_id, GeneratedDocument.user_id
- **No RBAC/ACL**: No roles or permission tables yet
- **Sharing via tokens**: SharedLink provides read-only public access without authentication
- **Future**: Could implement thread-level permissions, document sharing with specific users

### Event-Based Audit Trail
**EventOutbox Model:**
- Durably persists events in PostgreSQL
- Topics: `collab.update`, `document.autosave`, `share.created`, `share.accessed`
- Payloads: contextual data (document_id, user_id, thread_id, etc.)
- Status: pending, processed
- Tenant support for multi-tenancy

**AuditLog Model:**
- Generic audit trail for entity changes
- Tracks: event (create/update/delete/archive), entity type, entity_id, user_id, timestamp
- Full audit history of all changes

---

## 6. EVENT SYSTEM

### Event Bus Architecture
**Files:**
- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/core/event_bus.py` (main)
- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/sync/bus.py` (alternative)

**Durable Event Bus (event_bus.py):**
- Persists events to PostgreSQL `events_outbox` table
- In-memory fanout to subscribers
- Topics: arbitrary strings (e.g., "collab.update", "document.autosave")
- Configuration:
  ```python
  configure_event_store(store: ChatDB)  # Register durable backend
  configure_fallback_emitter(emitter)   # Fallback for no store
  ```
- Publishing:
  ```python
  emit_event(topic, payload, tenant_id="default")  # Durable + in-memory
  ```
- Subscribing:
  ```python
  queue = subscribe_in_memory()  # Returns asyncio.Queue
  message = await queue.get()    # {type, data, tenant_id}
  ```

**Event Topics Used:**
- `collab.update`: Client updates with active session count
- `document.autosave`: Autosaved document with document_id, thread_id
- `share.created`: Share link created with token, target, expiry
- `share.accessed`: Share link accessed with token and target info

---

## 7. TEST STRUCTURE

### Realtime Tests
**File:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/tests/realtime/test_collaboration_ws.py`

Tests:
- Multiple WebSocket connections per document
- Presence join/leave broadcasts
- Update propagation across clients
- Connection/disconnection handling
- Event emission verification

### Route Tests
**Files:**
- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/tests/routes/test_documents_autosave.py`
  - Autosave creation and updates
  - Event emission
  - Validation errors
  - Thread not found errors

- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/tests/routes/test_share_links.py`
  - Creating share links for threads/documents
  - Token generation and uniqueness
  - Expiry validation
  - Retrieving shared content
  - Error handling
  - Event emission

- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/tests/routes/test_thread_documents.py`
  - Thread-document linkage
  - Document retrieval

- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/tests/routes/test_workspace.py`
  - Workspace state aggregation

---

## 8. KEY FILE LOCATIONS SUMMARY

```
Backend Structure:
├── guardian/
│   ├── realtime/
│   │   └── collaboration.py          # WebSocket manager & endpoint
│   ├── routes/
│   │   ├── documents.py              # Autosave & document routes
│   │   ├── share.py                  # Share link routes
│   │   └── workspace.py              # Workspace aggregation
│   ├── db/
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   └── models_additions.py       # Proposed model additions
│   └── core/
│       ├── auth.py                   # Authentication & tokens
│       ├── event_bus.py              # Durable event system
│       └── user_manager.py           # User management

Frontend Structure:
├── frontend/src/
│   ├── components/
│   │   ├── editor/
│   │   │   └── CollaborativeNote.tsx # Real-time editor component
│   │   └── ShareButton.tsx           # Share link creator
│   └── pages/
│       └── SharePage.tsx             # Shared content viewer

Tests:
├── tests/
│   ├── realtime/
│   │   └── test_collaboration_ws.py  # WebSocket tests
│   └── routes/
│       ├── test_documents_autosave.py
│       ├── test_share_links.py
│       ├── test_thread_documents.py
│       └── test_workspace.py
```

---

## 9. DATA FLOW DIAGRAMS

### Collaborative Editing Flow
```
User 1                    WebSocket Server             User 2
   |                              |                        |
   |---[Connect WS]-------------->|                        |
   |<--[presence.join]------------|                        |
   |                              |<-----[Connect WS]------|
   |                              |------[presence.join]-->|
   |                              |<-----[presence.join]---|
   |---[{content, user_id}]------->|                        |
   |                              |------[update msg]----->|
   |<-----[update msg]------------|                        |
```

### Autosave Flow
```
CollaborativeNote Component         Backend API            Database
   |                                    |                       |
   |--[POST /api/documents/autosave]--->|                       |
   |                                    |--[Create/Update]----->|
   |                                    |   GeneratedDocument   |
   |                                    |--[Create]------------>|
   |                                    |   ThreadDocument link |
   |                                    |                       |
   |                                    |--[emit event]-------->|
   |<------[{ok, document_id}]---------|
   |                                    |
   | (repeat every 15 seconds)
```

### Share Link Creation Flow
```
ShareButton Component              Backend API            Database
   |                                   |                       |
   |--[POST /api/share]---------------->|                       |
   |  {target_type, target_id}          |                       |
   |                                   |--[Generate Token]     |
   |                                   |--[Create SharedLink]->|
   |                                   |--[emit event]-------->|
   |<--[{ok, token, url}]--------------|
   |                                   |
   | [Copy to clipboard]
   | Share: https://domain.com/share/{token}
```

### Share Link Access Flow
```
Anonymous User              Backend API                Database
   |                            |                           |
   |--[GET /share/{token}]----->|                           |
   |                            |--[Find SharedLink]------->|
   |                            |--[Validate Token/Expiry]  |
   |                            |--[Fetch Content]-------->|
   |                            |--[emit event]----------->|
   |<--[Thread/Document]--------|
   |                            |
   | [Read-only display]
```

---

## 10. INTEGRATION POINTS

### With Guardian API Server
- Database session injection via `configure_db()`
- Event bus configuration
- Route registration in main FastAPI app
- User authentication/authorization

### With PostgreSQL Database
- SQLAlchemy ORM for all model operations
- Prepared statements for SQL injection prevention
- Indexes on frequently queried columns
- Transactional consistency for autosave/linking

### With Frontend
- REST endpoints for CRUD operations
- WebSocket endpoint for real-time collaboration
- JSON payloads with consistent schema
- Error codes (400, 404, 500)

---

## 11. SECURITY CONSIDERATIONS

### WebSocket Security
- Currently: No explicit authentication on ws:// endpoint
- Recommendation: Extract user_id from cookie/token before accept

### Share Token Security
- 43-character URL-safe random tokens via `secrets.token_urlsafe(32)`
- Optional expiry with UTC timestamp validation
- One-time lookup (no session continuation)

### Authentication Security
- HMAC-SHA256 signed session tokens
- Constant-time comparison to prevent timing attacks
- Secret resolution from environment variables
- User-id validation via AuthenticatedUser dataclass

### Database Security
- No raw SQL execution in ORM code
- SQLAlchemy parameterized queries
- Soft deletes for documents (deleted_at timestamp)
- Audit trail for compliance

---

## 12. PERFORMANCE CONSIDERATIONS

### WebSocket Optimization
- Connection pooling per document (Set-based storage)
- Async broadcast with error recovery
- In-memory presence tracking
- Event emission separated from broadcast

### Database Optimization
- Composite indexes on common queries (thread_id, created_at)
- Descending indexes on updated_at for recency queries
- ThreadDocument indexes on relation and thread_id
- SharedLink token index for O(1) lookup

### Autosave Optimization
- 15-second debounce interval
- Update-or-create pattern (not per-keystroke)
- Single database roundtrip per interval
- Event emission on successful save

---

## 13. KNOWN LIMITATIONS & FUTURE WORK

### Current Limitations
1. **No RBAC/ACL**: Basic user_id ownership, no role-based access
2. **No operational transformation (OT)**: Last-write-wins semantics
3. **No conflict resolution**: No merge strategies for concurrent edits
4. **Single-tenant**: tenant_id defaults to "default"
5. **No edit history/diffs**: No document version tracking
6. **Simple presence**: Join/leave only, no cursor positions

### Suggested Enhancements
1. Implement fine-grained permissions (read/write/share)
2. Add document versioning with diff/merge capabilities
3. Implement Conflict-free Replicated Data Types (CRDTs) for true collaboration
4. Add cursor position and selection tracking
5. Implement multi-user mention/notifications
6. Add document change history with ability to revert

---

## 14. CONFIGURATION & DEPLOYMENT

### Environment Variables Used
- `GUARDIAN_SESSION_SECRET`: Session token signing secret (preferred)
- `GUARDIAN_API_KEY`: API key for authentication (fallback)
- `VITE_GUARDIAN_API_BASE`: Frontend API base URL (Vite env var)

### Database Setup
- PostgreSQL required (Postgres-only SQLAlchemy models)
- Alembic migrations for schema management
- No raw DDL creation in application code
- EventOutbox table for durable event storage

### FastAPI Integration
- WebSocket endpoint at `/api/collab/ws/{document_id}`
- REST endpoints under `/api/share`, `/api/documents`, `/api/workspace`
- Event bus configured at server startup
- Database session management via context managers

---

## 15. CONCLUSION

The Guardian codebase demonstrates a modern approach to real-time collaboration with:
- **Clean separation of concerns**: WebSocket, API routes, database models, components
- **Durable event sourcing**: PostgreSQL-backed event outbox for audit and replay
- **Simple but effective**: No CRDT complexity, suitable for initial release
- **Frontend-first UX**: CollaborativeNote component with presence and autosave
- **Secure sharing**: Token-based public links with optional expiry
- **Extensible architecture**: Event bus and route patterns support future features

The codebase is ready for expansion with permissions, versioning, and advanced OT/CRDT implementations.
