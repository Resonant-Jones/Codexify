# Collaborative Features — Architecture & Operations

> **Status:** Documenting current implementation as of 2026-07-04.  
> **Scope:** Codexify's own collaborative editing, presence, and federation systems.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [CollaborationManager (Backend)](#collaborationmanager-backend)
4. [Document Collaboration WebSocket Protocol](#document-collaboration-websocket-protocol)
5. [WebSocket RPC Subsystem](#websocket-rpc-subsystem)
6. [Permissions & Access Control](#permissions--access-control)
7. [Audit Logging](#audit-logging)
8. [Shared Links](#shared-links)
9. [Federation (Cross-Node)](#federation-cross-node)
10. [CollaborativeNote (Frontend Component)](#collaborativenote-frontend-component)
11. [Database Schema](#database-schema)
12. [File Inventory](#file-inventory)
13. [Known Limitations](#known-limitations)

---

## Overview

Codexify has three collaborative subsystems built into its own codebase:

| Subsystem | Location | Purpose |
|-----------|----------|---------|
| **Document Collaboration** | `guardian/realtime/collaboration.py` | Real-time multi-user document editing via WebSocket with presence, permissions, and audit logging |
| **WebSocket RPC** | `guardian/ws/` | General-purpose authenticated WebSocket RPC with protocol validation, rate limiting, and topic-based pub/sub |
| **Federation** | `guardian/federation/` | Cross-node relay sessions for collaboration between separate Codexify instances |

The frontend counterpart is the `CollaborativeNote` component (`frontend/src/components/editor/CollaborativeNote.tsx`).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                              │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │  CollaborativeNote                                            │   │
│  │  - Native WebSocket to /api/collab/ws/<documentId>            │   │
│  │  - Real-time text sync (update messages)                      │   │
│  │  - Presence display (colored avatars)                         │   │
│  │  - Autosave every 15s (POST /documents/autosave)              │   │
│  │  - Audit trail (GET /api/collab/<id>/audit)                   │   │
│  │  - Read-only enforcement (permissions.can_edit == false)      │   │
│  │  - Access denied screen (WS close code 1008)                  │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                    WebSocket (ws:// or wss://)
                    REST (autosave, audit trail)
                                   │
┌──────────────────────────────────┴───────────────────────────────────┐
│                     Guardian Backend (FastAPI)                        │
│                                                                      │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐   │
│  │  /api/collab/ws/*   │  │  /api/ws/rpc                        │   │
│  │  (Document collab)  │  │  (General RPC with auth, rate       │   │
│  │                     │  │   limiting, topic pub/sub)           │   │
│  └────────┬───────────┘  └──────────────┬───────────────────────┘   │
│           │                              │                           │
│  ┌────────┴──────────────────────────────┴───────────────────────┐   │
│  │  CollaborationManager                                           │   │
│  │  - Connection registry per document                             │   │
│  │  - Presence tracking (join/leave)                               │   │
│  │  - Update broadcasting                                          │   │
│  │  - Permission verification against DB                           │   │
│  │  - Audit event logging                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  FederationManager                                               │  │
│  │  - Cross-node relay sessions (bidirectional WS forwarding)       │  │
│  │  - JWT-based session tokens                                      │  │
│  │  - Signed node manifests for peer verification                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Database (PostgreSQL)                                           │  │
│  │  - collaboration_permissions  (per-document access control)      │  │
│  │  - collaboration_audit_log    (audit trail for all events)       │  │
│  │  - shared_links               (time-expiring access tokens)      │  │
│  │  - ws_audit_log               (RPC request auditing)             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## CollaborationManager (Backend)

**File:** `guardian/realtime/collaboration.py`

The `CollaborationManager` is a singleton class managing WebSocket connections for collaborative document editing.

### State

```python
class CollaborationManager:
    active: dict[str, set[WebSocket]]       # doc_id → connected WebSockets
    presence: dict[str, set[str]]            # doc_id → active user IDs
    permissions: dict[str, dict[str, dict]]  # doc_id → user_id → {can_edit, can_comment}
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `connect(doc_id, ws, user_id)` | Accept WebSocket, register in active set, add to presence, broadcast `presence.join` |
| `disconnect(doc_id, ws, user_id)` | Remove from active/presence, broadcast `presence.leave`, clean up empty documents |
| `broadcast(doc_id, message)` | Send a JSON message to every connected WebSocket for a document. Automatically cleans up disconnected clients |
| `verify_access(doc_id, user_id, token, session)` | Check access via SharedLink token or CollaborationPermission DB row. Returns `(is_authorized, permissions_dict)` |
| `log_audit_event(doc_id, user_id, action, payload, session)` | Insert a `CollaborationAuditLog` row |
| `get_active_sessions()` | Count of documents with active connections |
| `get_session_user_count(doc_id)` | Count of active users in a document session |

### Lifecycle

```
Client connects                Server
    │                            │
    │── WS /api/collab/ws/<id> ─►│
    │                            │── Accept WS
    │◄───────────────────────────│
    │                            │
    │── receive_json (handshake)─►│  { user_id, token }
    │                            │── verify_access()
    │                            │── If denied: close(1008, "access_denied"), emit event
    │                            │── log_audit_event("access_denied")
    │                            │
    │                            │── connect() → broadcast presence.join
    │                            │── log_audit_event("presence.join")
    │                            │
    │   (edit loop)              │
    │── receive_json (update) ──►│
    │                            │── Check permissions.can_edit
    │                            │── If denied: log_audit_event("update_denied"), skip
    │                            │── Hash content, log_audit_event("update")
    │                            │── broadcast() to all clients
    │                            │── emit_event("collab.update")
    │                            │
    │   (disconnect)             │
    │   WebSocketDisconnect      │
    │                            │── log_audit_event("presence.leave")
    │                            │── disconnect() → broadcast presence.leave
```

### REST Endpoint

```
GET /api/collab/{document_id}/audit?limit=100
```

Returns paginated audit log entries for a document.

---

## Document Collaboration WebSocket Protocol

### Endpoint

```
ws://<host>/api/collab/ws/{document_id}?token=<optional_shared_link_token>
```

### Client → Server

**Initial handshake** (first message after connect):
```json
{
  "user_id": "user-abc",
  "token": "optional-override-token"
}
```

**Content update:**
```json
{
  "type": "update",
  "content": "new document text...",
  "user_id": "user-abc",
  "timestamp": "2026-07-04T12:00:00Z"
}
```

### Server → Client

**Presence join:**
```json
{
  "type": "presence.join",
  "user_id": "user-abc",
  "active_users": ["user-abc", "user-xyz"]
}
```

**Presence leave:**
```json
{
  "type": "presence.leave",
  "user_id": "user-xyz",
  "active_users": ["user-abc"]
}
```

**Content update (broadcast to all clients):**
```json
{
  "type": "update",
  "payload": {
    "type": "update",
    "content": "new document text...",
    "user_id": "user-abc",
    "timestamp": "2026-07-04T12:00:00Z"
  },
  "user_id": "user-abc"
}
```

### Close Codes

| Code | Meaning |
|------|---------|
| `1008` | Policy violation — access denied (no valid permission or shared link) |
| `1011` | Internal error — collaboration not configured (`_db is None`) |

---

## WebSocket RPC Subsystem

**Location:** `guardian/ws/`

A separate, general-purpose authenticated WebSocket RPC channel at `/api/ws/rpc`. This is distinct from the document collaboration WebSocket and uses a different protocol.

### Components

| File | Purpose |
|------|---------|
| `auth.py` | Authenticate connections via query param (`api_key`/`token`) or initial auth frame |
| `protocol.py` | Pydantic models for `RPCRequest`, `RPCResponse`, `RPCEvent`. Payload size enforcement |
| `rate_limiter.py` | Token bucket rate limiter with optional Redis backend, fallback to in-memory |
| `manager.py` | `WSConnectionManager` — connection registry with topic-based pub/sub subscriptions |
| `methods.py` | RPC method registry using decorators (`@rpc_method`). `dispatch_rpc_method()` |
| `router.py` | WebSocket route wiring |

### RPC Frame Types

```python
# Client → Server
class RPCRequest:
    type: "request"
    id: str              # correlation ID (1-128 chars)
    method: str          # method name
    params: dict

# Server → Client (success)
class RPCResponse:
    type: "response"
    id: str | None
    result: dict | None
    error: dict | None

# Server → Client (async event)
class RPCEvent:
    type: "event"
    topic: str
    payload: dict
```

### Authentication

1. **Query param**: `?api_key=...` or `?token=...` → validated via `verify_api_key()`
2. **Auth frame**: First message `{"type":"auth","api_key":"..."}` → validated with 5s timeout
3. **Close codes**: `4401` (unauthorized), `4400` (invalid frame)

### Rate Limiting

- **Token bucket** algorithm with configurable capacity and refill rate
- **Redis backend** (optional): falls back to in-memory if Redis unavailable
- **Per-key tracking**: keys derived from `api_key:{token}` or connection ID
- **Settings**: `WS_RPC_RATE_LIMIT_CAPACITY`, `WS_RPC_RATE_LIMIT_REFILL_PER_SECOND`

### Connection Limits

- **Max connections**: `WS_RPC_MAX_CONNECTIONS` (close code `4429` when exceeded)
- **Idle timeout**: `WS_RPC_IDLE_TIMEOUT_SECONDS` (close code `4408`)
- **Payload limit**: `GUARDIAN_WS_MAX_PAYLOAD_BYTES` (default 65536, close code `4409`)

### Audit Logging

Every RPC request is logged to `ws_audit_log` with:
- `connection_id`, `identity` (masked API key), `method`, `params_hash` (SHA-256), `status` (ok/error), `duration_ms`

---

## Permissions & Access Control

**Model:** `guardian/db/models.py` → `CollaborationPermission`

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `document_id` | String(36) | UUID of the document |
| `user_id` | String(255) | User identifier |
| `can_edit` | Boolean | Whether user can modify content (default: false) |
| `can_comment` | Boolean | Whether user can comment (default: true) |
| `granted_by` | String(255) | User who granted the permission |
| `created_at` | TIMESTAMP | When permission was created |

### Indexes

- `ix_collab_perms_doc_user` — unique composite index on `(document_id, user_id)`
- `ix_collab_perms_document` — for listing all permissions on a document
- `ix_collab_perms_user` — for listing all documents a user can access

### Access Verification Flow

```
verify_access(doc_id, user_id, token, session)
    │
    ├── token provided?
    │   └── Check SharedLink table
    │       └── Match? → (True, {can_edit: false, can_comment: true})
    │
    └── Check CollaborationPermission table
        └── Match? → (True, {can_edit: perm.can_edit, can_comment: perm.can_comment})
        └── No match → (False, None)
```

Shared link access is always **read-only** (`can_edit: false`). Direct permissions grant the configured `can_edit`/`can_comment` capabilities.

---

## Audit Logging

**Model:** `guardian/db/models.py` → `CollaborationAuditLog`

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | BigInteger (PK) | Auto-increment |
| `document_id` | String(36) | UUID of the document |
| `user_id` | String(255) nullable | User who performed the action |
| `action` | String(64) | Action type |
| `payload` | JSONB nullable | Action-specific metadata |
| `timestamp` | TIMESTAMP | When the event occurred |

### Action Types

| Action | Trigger |
|--------|---------|
| `presence.join` | User connects to document |
| `presence.leave` | User disconnects |
| `update` | Content change (content hashed via SHA-256, stored as 16-char hex prefix) |
| `update_denied` | Edit attempt blocked by permissions |
| `access_denied` | Connection rejected by `verify_access` |
| `permission.granted` | (Future) — when a permission is added |
| `permission.revoked` | (Future) — when a permission is removed |

### Content Privacy

Content is **never stored in plaintext** in the audit log. Updates store only a SHA-256 hash of the content (truncated to 16 hex characters) in `payload.content_hash`.

### Indexes

- `ix_collab_audit_doc` — by document ID
- `ix_collab_audit_doc_timestamp` — composite on `(document_id, timestamp)` for time-ordered queries
- `ix_collab_audit_user` — by user ID

---

## Shared Links

**Model:** `guardian/db/models.py` → `SharedLink`

Time-expiring access tokens for threads or documents.

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | String(36) PK | UUID |
| `target_type` | String(32) | `'thread'` or `'document'` |
| `target_id` | Integer | ID of the thread or document |
| `token` | String(64) UNIQUE | URL-safe secure token |
| `expires_at` | TIMESTAMP nullable | When the link expires (null = never) |
| `created_at` | TIMESTAMP | When the link was created |

### Constraint

```
CHECK (target_type IN ('thread', 'document'))
```

### Expiry Check

The `verify_access` method checks that `expires_at` is either `NULL` (never expires) or in the future. Expired links result in access denial.

### Thread-Document Mapping

**Model:** `thread_documents`

Links threads to their documents for collaboration context.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `thread_id` | Integer (FK → chat_threads.id) | Thread reference |
| `document_id` | String(36) | UUID of the document |
| `relation` | String(64) | `'autosave'`, `'attached'`, or `'reference'` |
| `created_at` | TIMESTAMP | When the mapping was created |

---

## Federation (Cross-Node)

**Location:** `guardian/federation/`

Enables collaboration across separate Codexify instances by establishing relay channels between federated nodes.

### Components

| File | Purpose |
|------|---------|
| `manager.py` | `FederationManager` — lifecycle management for relay sessions |
| `manifest.py` | `NodeManifest` — signed node identity, `verify_manifest()`, `generate_keypair()` |
| `graph_model.py` | Federation awareness graph representation |
| `graph_sync.py` | Graph synchronization between nodes |
| `routes/federation.py` | REST endpoints for session exchange |
| `routes/federation_context.py` | Context retrieval for federated sessions |

### RelaySession

```python
@dataclass
class RelaySession:
    relay_id: str
    token: str             # JWT session token
    source_node_id: str
    target_node_id: str
    document_id: str
    thread_id: str | None
    created_at: datetime
    expires_at: datetime | None
    source_ws: WebSocket | None   # Connection to source node
    target_ws: WebSocket | None   # Connection to target node
    active_users: Set[str]
```

### Session Lifecycle

```
Node A                          FederationManager                    Node B
  │                                    │                               │
  │── POST /session/request ──────────►│                               │
  │   { document_id, thread_id,        │                               │
  │     target_node_id }               │                               │
  │                                    │── verify manifests ───────────►│
  │                                    │◄── accept/reject ──────────────│
  │◄── relay_id + token ───────────────│                               │
  │                                    │                               │
  │── WS /relay/{relay_id} ───────────►│◄── WS /relay/{relay_id} ──────│
  │   (source_ws)                      │   (target_ws)                 │
  │                                    │                               │
  │   ═══════ bidirectional forwarding ═══════════════════════════════ │
  │   ← presence, updates, autosave →  │   ← presence, updates →       │
  │                                    │                               │
  │   (disconnect)                     │   (disconnect)                │
  │                                    │── cleanup relay session       │
```

Messages are forwarded bidirectionally between source and target WebSocket connections. The relay carries presence updates, content changes, and autosave events.

---

## CollaborativeNote (Frontend Component)

**File:** `frontend/src/components/editor/CollaborativeNote.tsx`

### Props

```typescript
interface CollaborativeNoteProps {
  documentId: string;
  threadId: number;
  userId?: string;          // default: "anonymous"
  initialContent?: string;
  onContentChange?: (content: string) => void;
  authToken?: string;
}
```

### Connection

The component connects to `ws://<guardian_host>/api/collab/ws/<documentId>`, sending an initial handshake:

```json
{ "user_id": "<userId>", "token": "<authToken>" }
```

### Features

| Feature | Implementation |
|---------|---------------|
| **Real-time sync** | Sends `{type: "update", content, user_id, timestamp}` on each change. Receives updates from server and applies them |
| **Presence** | Tracks `activeUsers[]` from `presence.join`/`presence.leave` messages. Assigns stable colors from a 5-color palette |
| **Autosave** | POST to `/documents/autosave` every 15 seconds via Axios. Shows "Saved Ns ago" or error indicator |
| **Audit trail** | Fetches from `GET /api/collab/<documentId>/audit?limit=100`. Toggleable history panel |
| **Permissions** | Reads `permissions.can_edit` state. Disables textarea and shows 🔒 "Read-only" badge when false |
| **Access denied** | Renders full-screen "Access Denied" panel on WebSocket close code `1008` |
| **Connection status** | Green/red dot indicator with "Live Editing" / "Offline" labels |

### UI States

1. **Normal (editing)** — Textarea enabled, live presence avatars, autosave indicator
2. **Read-only** — Textarea disabled with gray background, 🔒 badge, "Read-only mode" placeholder
3. **Access Denied** — Full-screen panel with title and message, no editor shown
4. **Offline** — Red connection dot, "Offline" label, editor still accessible

### Tests

- `frontend/src/components/editor/__tests__/CollaborativeNote.test.tsx` — 8 unit tests covering rendering, connection, updates, presence, callbacks, autosave, unmount, and error handling
- `frontend/tests/CollaborativePermissions.test.tsx` — 12+ tests for read-only mode, audit trail display, access denied, presence display, autosave feedback, and connection states

---

## Database Schema

### Tables

```
collaboration_permissions
├── id                  INTEGER PK (auto-increment)
├── document_id         VARCHAR(36) NOT NULL
├── user_id             VARCHAR(255) NOT NULL
├── can_edit            BOOLEAN DEFAULT false
├── can_comment         BOOLEAN DEFAULT true
├── granted_by          VARCHAR(255) NOT NULL
├── created_at          TIMESTAMP DEFAULT now()
└── INDEXES: (document_id, user_id) UNIQUE, (document_id), (user_id)

collaboration_audit_log
├── id                  BIGINT PK (auto-increment)
├── document_id         VARCHAR(36) NOT NULL
├── user_id             VARCHAR(255)
├── action              VARCHAR(64) NOT NULL
├── payload             JSONB
├── timestamp           TIMESTAMP DEFAULT now()
└── INDEXES: (document_id), (document_id, timestamp), (user_id)

shared_links
├── id                  VARCHAR(36) PK (UUID)
├── target_type         VARCHAR(32) NOT NULL  -- 'thread' or 'document'
├── target_id           INTEGER NOT NULL
├── token               VARCHAR(64) UNIQUE NOT NULL
├── expires_at          TIMESTAMP  -- NULL = never expires
├── created_at          TIMESTAMP DEFAULT now()
└── CHECK: target_type IN ('thread', 'document')

thread_documents
├── id                  INTEGER PK (auto-increment)
├── thread_id           INTEGER FK → chat_threads.id
├── document_id         VARCHAR(36) NOT NULL
├── relation            VARCHAR(64) DEFAULT 'autosave'  -- 'autosave','attached','reference'
├── created_at          TIMESTAMP DEFAULT now()
└── CHECK: relation IN ('autosave', 'attached', 'reference')

ws_audit_log
├── id                  BIGINT PK (auto-increment)
├── connection_id       VARCHAR(128)
├── identity            VARCHAR(128)  -- masked API key
├── method              VARCHAR(128)
├── params_hash         VARCHAR(64)   -- SHA-256 of JSON params
├── status              VARCHAR(16)   -- 'ok' or 'error'
├── duration_ms         INTEGER
├── timestamp           TIMESTAMP DEFAULT now()
└── INDEXES: (connection_id, timestamp), (identity) -- approximate
```

### Migration

**File:** `guardian/db/migrations/versions/13a4a6dc5ba1_add_collaboration_and_sharing_tables.py`

- **Revision:** `13a4a6dc5ba1`
- **Down revision:** `83c2f0bb0dfa`
- **Created:** 2026-01-26
- **Adds:** `collaboration_audit_log`, `collaboration_permissions`, `shared_links`, `thread_documents`
- **Checks for existence** before creating tables and indexes (idempotent)
- **Downgrade** drops only these four tables, leaving unrelated schema intact

---

## File Inventory

### Backend (Guardian)

| File | Purpose |
|------|---------|
| `guardian/realtime/__init__.py` | Module init, exports `CollaborationManager` and `router` |
| `guardian/realtime/collaboration.py` | Core: `CollaborationManager` class, WebSocket handler, audit REST endpoint |
| `guardian/ws/__init__.py` | WS module init |
| `guardian/ws/auth.py` | WebSocket authentication (query param or initial auth frame) |
| `guardian/ws/protocol.py` | Pydantic models: `RPCRequest`, `RPCResponse`, `RPCEvent`, size enforcement |
| `guardian/ws/rate_limiter.py` | Token bucket rate limiter (memory + optional Redis) |
| `guardian/ws/manager.py` | `WSConnectionManager` — connection registry with topic subscriptions |
| `guardian/ws/methods.py` | RPC method registry (`@rpc_method` decorator), `dispatch_rpc_method()` |
| `guardian/ws/router.py` | WebSocket RPC route wiring |
| `guardian/routes/websocket.py` | Canonical `/api/ws/rpc` endpoint with audit logging |
| `guardian/routes/federation.py` | Federation session exchange REST endpoints |
| `guardian/routes/federation_context.py` | Cross-node context retrieval |
| `guardian/federation/__init__.py` | Module init, lazy-loads `FederationManager` |
| `guardian/federation/manager.py` | `FederationManager` — relay session lifecycle |
| `guardian/federation/manifest.py` | `NodeManifest`, signing, verification, key generation |
| `guardian/federation/graph_model.py` | Federation awareness graph |
| `guardian/federation/graph_sync.py` | Graph sync between nodes |
| `guardian/db/models.py` | `CollaborationPermission`, `CollaborationAuditLog`, `SharedLink`, `WSAuditLog`, `thread_documents` |
| `guardian/db/migrations/versions/13a4a6dc5ba1_*.py` | Alembic migration for collaboration tables |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/components/editor/CollaborativeNote.tsx` | Collaborative document editor React component |
| `frontend/src/components/editor/__tests__/CollaborativeNote.test.tsx` | Unit tests for the component (8 tests) |
| `frontend/tests/CollaborativePermissions.test.tsx` | Permission and audit trail tests (12+ tests) |

### Tests (Backend)

| File | Purpose |
|------|---------|
| `tests/realtime/__init__.py` | Test module init |
| `tests/realtime/conftest.py` | Test fixtures, model imports for collaboration tests |
| `tests/realtime/test_collaboration_ws.py` | WebSocket manager: connect, disconnect, broadcast, presence |
| `tests/realtime/test_collaboration_permissions.py` | Permission verification, shared link auth, audit logging |
| `tests/federation/test_context_retrieval.py` | Federation context tests |
| `tests/federation/test_federated_session_exchange.py` | Federation session exchange tests |
| `tests/federation/test_awareness_graph.py` | Federation awareness graph tests |

---

## Known Limitations

1. **CollaborationManager is in-memory** — The `active`, `presence`, and `permissions` dicts live in process memory. On server restart, all active collaboration sessions are lost. Permissions are re-queried from the DB on each new connection, but presence state is ephemeral.

2. **No CRDT/OT conflict resolution** — Content updates are last-write-wins. There's no operational transform or CRDT for concurrent editing. The server broadcasts raw content replacements, not deltas.

3. **Separate WebSocket protocols** — The document collaboration WebSocket (`/api/collab/ws/*`) uses a simple ad-hoc protocol, while the RPC WebSocket (`/api/ws/rpc`) uses a structured request/response protocol. These are not unified.

4. **No annotation/comment threads in current protocol** — The `CollaborativeNote` frontend and `CollaborationManager` backend handle presence + content sync, but do not currently expose annotation/comment threading through the WebSocket. The `can_comment` permission field exists in the DB but has no corresponding server-side enforcement path in the current collaboration handler.

5. **Shared links are always read-only** — Tokens from the `SharedLink` table always grant `can_edit: false`. There is no mechanism for creating editable shared links.

6. **Federation requires manual setup** — Cross-node collaboration requires explicit session exchange via REST endpoints before WebSocket relay is established. There's no auto-discovery or mesh formation.

7. **Autosave is frontend-driven** — The frontend POSTs to `/documents/autosave` on a 15-second timer. There is no server-side debounce, versioning, or conflict detection on autosave.
