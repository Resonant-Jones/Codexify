# Guardian Codebase - Quick Reference Card

## 🚀 Key Architecture Overview

```
Frontend (React)              Backend (FastAPI)           Database (PostgreSQL)
═════════════════════         ═════════════════════       ═════════════════════
CollaborativeNote ────WS────> /api/collab/ws/ ───────┐
   │                          [Broadcast updates]      │
   │                                                   │ ThreadDocument
   │                          CollaborationManager    └──> GeneratedDocument
   │
   ├──POST autosave────> /api/documents/autosave
   │                     [Create/Update + Event]
   │
   └──POST share────────> /api/share
                          [Generate Token + Link]

SharePage (anonymous)
   └──GET /api/share/{token}
      [Read-only access]
```

---

## 📂 Critical Files (by purpose)

### Collaboration/Realtime
- **WebSocket Manager**: `/guardian/realtime/collaboration.py` (202 lines)
  - Class: `CollaborationManager`
  - Endpoint: `POST /api/collab/ws/{document_id}`
  - Features: Connect, disconnect, broadcast, presence tracking

### Autosave/Documents
- **Documents API**: `/guardian/routes/documents.py` (264 lines)
  - POST `/api/documents/autosave` - Create/update autosave documents
  - GET `/api/threads/{thread_id}/documents` - List linked documents
  - Model: `GeneratedDocument`, `ThreadDocument`

### Sharing
- **Share API**: `/guardian/routes/share.py` (315 lines)
  - POST `/api/share` - Create secure share tokens
  - GET `/api/share/{token}` - Access shared content
  - Model: `SharedLink` (UUID, token, optional expiry)

### Database
- **ORM Models**: `/guardian/db/models.py` (514 lines)
  - `ChatThread`, `ChatMessage`, `Project`
  - `GeneratedDocument`, `UploadedDocument`
  - `ThreadDocument` (many-to-many linkage)
  - `SharedLink` (for public sharing)
  - `EventOutbox`, `AuditLog` (for events/audit)

### Authentication
- **Auth Module**: `/guardian/core/auth.py`
  - `AuthenticatedUser` dataclass
  - `issue_session_token()`, `verify_session_token()`
  - `extract_auth_identity()` (API key, bearer, cookie)

### Events
- **Event Bus**: `/guardian/core/event_bus.py` (136 lines)
  - Durable PostgreSQL backend + in-memory fanout
  - Topics: `collab.update`, `document.autosave`, `share.created`, `share.accessed`
  - `emit_event(topic, payload, tenant_id)`

### Frontend Components
- **Collaborative Editor**: `/frontend/src/components/editor/CollaborativeNote.tsx` (296 lines)
  - WebSocket to `/api/collab/ws/{documentId}`
  - Autosave every 15 seconds
  - Presence avatars with colors

- **Share Button**: `/frontend/src/components/ShareButton.tsx` (113 lines)
  - POST `/api/share` - Create share link
  - Copy to clipboard + toast notification

- **Share Page**: `/frontend/src/pages/SharePage.tsx` (100+ lines)
  - GET `/api/share/{token}` - Display shared content
  - Read-only rendering of threads/documents

---

## 🔌 API Endpoints at a Glance

| Method | Endpoint | Purpose | Auth | Returns |
|--------|----------|---------|------|---------|
| WS | `/api/collab/ws/{doc_id}` | Real-time collab | Optional | JSON messages |
| POST | `/api/documents/autosave` | Save document | Yes | `{ok, document_id, relation}` |
| GET | `/api/threads/{id}/documents` | List docs | Yes | `{ok, documents[]}` |
| POST | `/api/share` | Create token | Yes | `{ok, token, url, expires_at}` |
| GET | `/api/share/{token}` | Get shared | No | `{ok, target_type, content}` |
| GET | `/api/workspace/{id}` | Workspace state | Yes | `{thread, documents, diagnostics}` |

---

## 🗄️ Key Database Models

### ChatThread (core chat entity)
```python
id (PK) | user_id | title | summary | project_id (FK) | parent_id (FK)
archived_at | created_at | updated_at
Relationships: messages[], parent, children[]
```

### GeneratedDocument (autosave/generated content)
```python
id (UUID, PK) | project_id (FK) | thread_id (FK) | user_id
title | content | format (txt/md/docx/pdf/html/json) | model (e.g., 'autosave')
created_at | updated_at | deleted_at (soft delete)
```

### ThreadDocument (linkage model)
```python
id (PK) | thread_id (FK, CASCADE) | document_id (UUID)
relation (autosave/attached/reference) | created_at
Indexes: thread_id, (thread_id, relation), document_id
```

### SharedLink (for secure sharing)
```python
id (UUID, PK) | target_type (thread/document) | target_id
token (unique, 64 chars, URL-safe) | expires_at (nullable)
created_at
Indexes: token, (target_type, target_id)
```

### EventOutbox (durable events)
```python
id (BigInteger, PK) | topic | payload (JSONB) | status (pending/processed)
tenant_id | created_at
```

---

## 🔐 Authentication Patterns

### Session Token (Recommended)
```python
# Issue
token, expires_at = issue_session_token(subject="web", ttl_seconds=86400)

# Verify
valid, subject = verify_session_token(token)

# Use in header
Authorization: Bearer {token}
# Or cookie
gc_session: {token}
```

### API Key (Simple)
```python
X-API-Key: {GUARDIAN_API_KEY}
```

### Identity Extraction
```python
user_id = extract_auth_identity(
    x_api_key=header("X-API-Key"),
    authorization=header("Authorization"),
    gc_session=cookie("gc_session")
)
```

---

## 📡 WebSocket Message Flow

### Presence Tracking
```javascript
// Client connects
ws.send({user_id: "user123", action: "join"})

// Server broadcasts to all clients
{
  type: "presence.join",
  user_id: "user123",
  active_users: ["user123", "user456"]
}
```

### Content Updates
```javascript
// Client sends content
ws.send({content: "new content", user_id: "user123", timestamp: "..."})

// Server broadcasts
{
  type: "update",
  payload: {content: "new content", user_id: "user123", timestamp: "..."},
  user_id: "user123"
}
```

### Presence Leave
```javascript
// On disconnect
{
  type: "presence.leave",
  user_id: "user123",
  active_users: ["user456"]
}
```

---

## 🎯 Event Topics (Audit Trail)

| Topic | When | Payload |
|-------|------|---------|
| `collab.update` | WebSocket client update | `{document_id, user_id, active_sessions}` |
| `document.autosave` | Document autosaved | `{thread_id, document_id}` |
| `share.created` | Share link created | `{share_id, target_type, target_id, token}` |
| `share.accessed` | Share link retrieved | `{share_id, token, target_type, target_id}` |

---

## ⚙️ Configuration

### Environment Variables
```bash
# Required for sessions
GUARDIAN_SESSION_SECRET=<secret>        # Or fallback to GUARDIAN_API_KEY
GUARDIAN_API_KEY=<key>

# Frontend
VITE_GUARDIAN_API_BASE=https://api.example.com

# Database (implicit)
DATABASE_URL=postgresql://user:pass@host:5432/db
```

### Database Setup
```bash
# Uses Alembic for migrations
alembic upgrade head

# Key tables auto-created:
# - chat_threads, chat_messages
# - generated_documents, uploaded_documents
# - thread_documents (linkage)
# - shared_links (for sharing)
# - events_outbox (for event durability)
# - audit_log (for compliance)
```

---

## 📊 Data Relationships

```
ChatThread (user owns)
├── ChatMessage[] (thread contains)
├── Project (optional)
├── ThreadDocument[]
│   └── GeneratedDocument or UploadedDocument
└── SharedLink[] (anyone with token can view)

GeneratedDocument (autosave or generated)
├── Project (optional)
├── ChatThread (optional)
└── ThreadDocument[] (links to threads)

SharedLink (public access)
├── target_type: "thread" | "document"
├── target_id: references ChatThread or Document ID
├── token: secure URL-safe 43-char string
└── expires_at: optional expiration

EventOutbox (event sourcing)
├── topic: "collab.update" | "document.autosave" | "share.created" | "share.accessed"
├── payload: JSONB context
└── status: "pending" | "processed"
```

---

## 🧪 Testing Quick Links

| Test File | Coverage |
|-----------|----------|
| `tests/realtime/test_collaboration_ws.py` | WebSocket connect/disconnect, broadcasts, presence |
| `tests/routes/test_documents_autosave.py` | Autosave create/update, validation, events |
| `tests/routes/test_share_links.py` | Share link create/retrieve, expiry, errors |
| `tests/routes/test_thread_documents.py` | Document linkage |
| `tests/routes/test_workspace.py` | Workspace aggregation |

---

## 🚨 Security Checklist

- [ ] WebSocket requires authenticated user (not yet implemented)
- [ ] Share tokens are 43-character URL-safe random
- [ ] Share tokens expire (optional but recommended)
- [ ] Session tokens use HMAC-SHA256
- [ ] Constant-time comparison for secrets (`hmac.compare_digest`)
- [ ] Soft deletes on documents (deleted_at)
- [ ] Audit log tracks all entity changes
- [ ] No raw SQL (all via SQLAlchemy ORM)

---

## 🎓 Common Use Cases

### Add a new collaboration feature
1. Edit `CollaborativeNote.tsx` to send new message type
2. Handle in `CollaborationManager.broadcast()` or WebSocket endpoint
3. Emit event via `event_bus.emit_event(topic, payload)`
4. Create test in `tests/realtime/test_collaboration_ws.py`

### Add document version history
1. Create new model `DocumentVersion` in `models.py`
2. Foreign key to `GeneratedDocument`
3. Add route in `documents.py` to list/restore versions
4. Emit `document.version` event on save

### Add user permissions
1. Create `Permission` or `SharedUser` model in `models.py`
2. Foreign key to `ChatThread` and user_id
3. Check permission before returning content in routes
4. Update test fixtures for permission checks

### Add real-time notifications
1. Subscribe to event bus: `queue = subscribe_in_memory()`
2. In FastAPI endpoint, use SSE to stream events
3. Frontend listens to `/api/events/stream` (new endpoint)
4. Emit events normally, subscribers receive in real-time

---

## 🔍 Debugging Tips

### View active WebSocket sessions
```python
# In CollaborationManager
manager.get_active_sessions()  # Returns count of docs with active connections
manager.get_session_user_count(doc_id)  # Returns user count for doc
```

### Check event durability
```python
# Query events_outbox table
SELECT * FROM events_outbox
WHERE status = 'pending'
ORDER BY created_at DESC;

# Fetch since last_id
from guardian.core import event_bus
events = event_bus.fetch_events_after(last_id=100, limit=50)
```

### Trace autosave flow
```python
# 1. Check if GeneratedDocument exists
SELECT * FROM generated_documents
WHERE model = 'autosave' AND thread_id = ?;

# 2. Check ThreadDocument link
SELECT * FROM thread_documents
WHERE thread_id = ? AND relation = 'autosave';

# 3. Check event emission
SELECT * FROM events_outbox
WHERE topic = 'document.autosave'
ORDER BY created_at DESC;
```

### Validate share token
```python
# 1. Check SharedLink exists and hasn't expired
SELECT * FROM shared_links
WHERE token = ?
AND (expires_at IS NULL OR expires_at > NOW());

# 2. Verify target exists
SELECT * FROM chat_threads WHERE id = target_id;
-- OR
SELECT * FROM generated_documents WHERE id = target_id;
```

---

## 📚 Documentation Files

- `CODEBASE_SUMMARY.md` - Full detailed breakdown (15 sections, 500+ lines)
- `FILE_STRUCTURE_MAP.txt` - Visual tree of all key files
- `QUICK_REFERENCE.md` - This file (cheat sheet)

---

## 🎯 Next Steps for Enhancement

1. **Authentication on WebSocket**: Add user verification before accept()
2. **CRDT Implementation**: Replace last-write-wins with Yjs/Automerge
3. **Document Versioning**: Track changes, allow restore to prior versions
4. **Permissions Model**: Add RBAC for thread-level access control
5. **Real-time Notifications**: WebSocket/SSE for user mentions, shares
6. **Conflict Resolution**: Multi-user merge strategies
7. **Cursor Tracking**: Show other users' cursor positions
8. **Offline Support**: Service Worker + IndexedDB for offline editing
