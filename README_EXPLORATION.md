# Guardian Codebase Exploration - Complete Documentation

This directory contains comprehensive documentation about the Guardian codebase, with focus on collaboration, realtime features, database structure, and authentication patterns.

## Documentation Files

### 1. QUICK_REFERENCE.md (Recommended Starting Point)
**Size:** 400 lines | **Format:** Cheat sheet
- Quick architecture overview diagram
- Critical files by purpose
- API endpoints at a glance
- Key database models
- Authentication patterns
- WebSocket message flow
- Event topics
- Configuration
- Security checklist
- Common use cases
- Debugging tips
- Next steps for enhancement

**Best for:** Developers needing quick answers, onboarding, implementation guides

---

### 2. CODEBASE_SUMMARY.md (Comprehensive Reference)
**Size:** 656 lines | **Format:** Detailed breakdown
- Executive summary
- Collaboration/realtime infrastructure details
- Database models with relationships and indexes
- API routes with request/response schemas
- Frontend components with prop types and features
- Authentication & permission patterns
- Event system architecture
- Test structure
- File location summary
- Data flow diagrams
- Integration points
- Security considerations
- Performance optimizations
- Known limitations & future work
- Configuration & deployment
- Conclusion

**Best for:** Understanding the full system, architecture decisions, future planning

---

### 3. FILE_STRUCTURE_MAP.txt (Visual Navigation)
**Size:** 314 lines | **Format:** Tree structure
- Backend collaboration & realtime files
- API routes breakdown
- Database ORM models with columns
- Authentication & authorization modules
- Event system files
- Frontend React components with features
- Test structure
- Database indexes organized by query type

**Best for:** Finding specific files, understanding module organization

---

## Key Discoveries

### Core Architecture
The Guardian codebase implements a modern real-time collaboration system with:

**Backend (Python/FastAPI):**
- WebSocket server for live document editing (`/guardian/realtime/collaboration.py`)
- RESTful APIs for autosave, sharing, and workspace management
- SQLAlchemy ORM models for PostgreSQL database
- Durable event bus with in-memory fanout for audit trails
- Session-based authentication with HMAC-SHA256 tokens

**Frontend (React/TypeScript):**
- CollaborativeNote component with WebSocket integration
- Real-time presence tracking with colored user avatars
- Autosave every 15 seconds with timestamp feedback
- Share button for generating secure tokens
- Read-only share page for anonymous access

**Database:**
- PostgreSQL with 20+ SQLAlchemy models
- ThreadDocument linkage model for flexible document association
- SharedLink model for secure public sharing with optional expiry
- EventOutbox for durable event sourcing
- AuditLog for compliance and debugging

### File Structure Summary

```
Key Backend Files:
├── guardian/realtime/collaboration.py (WebSocket endpoint & manager)
├── guardian/routes/documents.py (Autosave & document routes)
├── guardian/routes/share.py (Share link routes)
├── guardian/routes/workspace.py (Workspace aggregation)
├── guardian/db/models.py (All ORM models)
├── guardian/core/auth.py (Authentication)
└── guardian/core/event_bus.py (Event sourcing)

Key Frontend Files:
├── frontend/src/components/editor/CollaborativeNote.tsx (Real-time editor)
├── frontend/src/components/ShareButton.tsx (Share creator)
└── frontend/src/pages/SharePage.tsx (Share viewer)

Test Files:
├── tests/realtime/test_collaboration_ws.py
├── tests/routes/test_documents_autosave.py
└── tests/routes/test_share_links.py
```

### API Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `WS /api/collab/ws/{doc_id}` | Real-time collaboration | Optional |
| `POST /api/documents/autosave` | Save document | Required |
| `GET /api/threads/{id}/documents` | List linked documents | Required |
| `POST /api/share` | Create share token | Required |
| `GET /api/share/{token}` | Get shared content | Public |
| `GET /api/workspace/{id}` | Workspace state | Required |

### Database Models

Core models:
- `ChatThread`: Main conversation threads (user_id, title, summary, timestamps)
- `ChatMessage`: Messages in threads (role, content, created_at)
- `GeneratedDocument`: Autosave/generated content (content, format, model)
- `ThreadDocument`: Links documents to threads (relation: autosave/attached/reference)
- `SharedLink`: Secure public sharing (token, optional expiry)
- `EventOutbox`: Durable events for audit trail
- `AuditLog`: Entity change history

### Authentication Methods

1. **Session Token** (Recommended)
   - HMAC-SHA256 signed tokens
   - TTL: 24 hours default
   - Use: `Authorization: Bearer {token}` or `gc_session` cookie

2. **API Key** (Simple)
   - Use: `X-API-Key: {key}` header
   - From env: `GUARDIAN_API_KEY`

3. **Identity Extraction**
   - Supports multiple auth methods in single function
   - Returns `AuthenticatedUser` dataclass with id and kind

### Event Topics

All events are durable (stored in PostgreSQL) and broadcast in-memory:

- `collab.update`: WebSocket client updates (includes document_id, user_id)
- `document.autosave`: Document autosave with document_id
- `share.created`: Share link creation with token
- `share.accessed`: Share link access with token

### WebSocket Message Flow

**Presence Tracking:**
```json
// Client joins
→ {type: "presence", user_id: "user1", action: "join"}
← {type: "presence.join", user_id: "user1", active_users: [...]}

// Client updates content
→ {content: "...", user_id: "user1", timestamp: "..."}
← {type: "update", payload: {...}, user_id: "user1"}

// Client leaves
→ {type: "presence", user_id: "user1", action: "leave"}
← {type: "presence.leave", user_id: "user1", active_users: [...]}
```

### Security Features

- HMAC-SHA256 session tokens with timing-safe comparison
- 43-character URL-safe random tokens for share links
- Optional expiry with UTC timestamp validation
- Soft deletes on documents (not hard deletes)
- Full audit trail of all entity changes
- SQLAlchemy ORM (no raw SQL)

### Performance Optimizations

- WebSocket connection pooling per document (Set-based storage)
- Async broadcast with error recovery
- In-memory presence tracking (no database queries)
- Database indexes on (thread_id, created_at), updated_at DESC
- SharedLink token index for O(1) lookup
- 15-second autosave debounce interval

## How to Use These Documents

### For Quick Answers
1. Start with **QUICK_REFERENCE.md**
2. Use Ctrl+F to search for specific topics
3. See "Common Use Cases" section for implementation patterns

### For Understanding Architecture
1. Read the Executive Summary in **CODEBASE_SUMMARY.md**
2. Review data flow diagrams (section 9)
3. Check integration points (section 10)

### For Finding Code
1. Use **FILE_STRUCTURE_MAP.txt** to locate files
2. Cross-reference with line counts
3. Use absolute paths for file operations

### For Implementation
1. Review the relevant use case in QUICK_REFERENCE.md
2. Read the full file documentation in CODEBASE_SUMMARY.md
3. Check test files for examples
4. Use Debugging Tips section for validation

## Current Feature Status

### Implemented
- Real-time WebSocket collaboration
- Document autosave with 15-second debounce
- Thread-document linkage (autosave/attached/reference relations)
- Secure share tokens with optional expiry
- Session-based authentication with HMAC tokens
- Durable event sourcing with PostgreSQL backend
- Presence tracking with colored avatars
- Workspace aggregation endpoint

### Not Yet Implemented
- WebSocket authentication (anyone can connect, but no permission checks)
- CRDT/Operational Transformation (last-write-wins semantics)
- Document version history
- Role-based access control (RBAC)
- User-level permissions on threads
- Real-time notifications/mentions
- Cursor position tracking
- Offline support

## Integration Points

The system integrates with:
- **FastAPI**: Web framework for REST + WebSocket
- **SQLAlchemy**: ORM for database abstraction
- **PostgreSQL**: Primary data store
- **React**: Frontend framework
- **Pydantic**: Request/response validation
- **Asyncio**: Async programming model

## Performance Characteristics

- WebSocket connections: In-memory set per document
- Autosave: One database roundtrip per 15 seconds
- Share link lookup: O(1) via token index
- Presence updates: O(n) where n = connected users per document
- Event emission: Async, non-blocking

## Security Considerations

**What's Secure:**
- Share tokens are cryptographically random
- Session tokens are HMAC-signed
- Audit trail for compliance
- No raw SQL injection risks

**What Needs Work:**
- WebSocket endpoint doesn't verify user identity
- Share tokens don't include user restrictions
- No rate limiting on API endpoints
- Basic user_id ownership (no granular permissions)

## Next Steps

For feature development:
1. Add WebSocket authentication before accept()
2. Implement document versioning
3. Add permission model for threads
4. Implement CRDT for true collaborative editing
5. Add real-time notifications

See **QUICK_REFERENCE.md** section "Next Steps for Enhancement" for detailed roadmap.

---

## Document Metadata

- **Created:** 2025-11-09
- **Last Updated:** 2025-11-09
- **Total Documentation:** 1,370 lines
- **Coverage:** Collaboration, realtime, autosave, sharing, auth, events, tests
- **Focus:** Architecture, implementation, troubleshooting

## Questions?

Refer to the appropriate document:
- "What does this endpoint do?" → FILE_STRUCTURE_MAP.txt or QUICK_REFERENCE.md API table
- "How does WebSocket work?" → CODEBASE_SUMMARY.md section 1 or QUICK_REFERENCE.md WebSocket flow
- "Where's the share link code?" → FILE_STRUCTURE_MAP.txt or /guardian/routes/share.py
- "How do I add a feature?" → QUICK_REFERENCE.md "Common Use Cases"
- "What's the full architecture?" → CODEBASE_SUMMARY.md or QUICK_REFERENCE.md diagram

