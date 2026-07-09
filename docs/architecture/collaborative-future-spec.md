# Collaborative Features — Future Spec (Parked)

> **Status:** Spec parked. Not scheduled for implementation.  
> **Prerequisites:** [Collaborative features architecture](./collaborative-features.md), [Implementation plan](./collaborative-implementation-plan.md) (Adaptations 1–4).  
> **Trigger:** These should be implemented only after Adaptations 1–4 are shipped and stable.

---

## Feature 5: Role-Scoped Share Links

### Current state

`SharedLink` tokens always grant read-only access (`can_edit: false`). The `POST /api/share` endpoint creates links with optional `expires_in_days` but no role parameter.

### Target

Share links carry a role (`viewer` | `collaborator` | `owner`) that determines what the recipient can do in a live collaborative session.

### What to build

#### 5a. Schema change

```sql
ALTER TABLE shared_links ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'viewer';
ALTER TABLE shared_links ADD CONSTRAINT shared_links_role_check
  CHECK (role IN ('viewer', 'collaborator', 'owner'));
```

Migration: new Alembic revision adding the column with a safe default.

#### 5b. API changes

`POST /api/share` accepts a new field:

```json
{
  "target_type": "thread",
  "target_id": 42,
  "expires_in_days": 7,
  "role": "collaborator"   // new: viewer | collaborator | owner
}
```

`GET /api/share/{token}` returns `role` in the response.

#### 5c. Permission enforcement

When a user joins via a shared link token, `CollaborationManager.verify_access()` maps the role to a permissions dict:

| Role | can_edit | can_comment | can_manage_access |
|------|----------|-------------|-------------------|
| `viewer` | false | false | false |
| `collaborator` | true | true | false |
| `owner` | true | true | true |

This requires adding the `role` column to the `SharedLink` DB model and extending the `verify_access` method in `guardian/realtime/collaboration.py`.

#### 5d. UI

`ShareButton` component (`frontend/src/components/ShareButton.tsx`) gains a role dropdown. Share link URL stays the same (`/share/{token}`) but the server now returns permissions alongside content.

### Integration with collaborative chat

When a user opens a shared thread link and the thread has an active collaborative session (other users present), they join with the role specified in the token. This is the bridge between the static share page and the live collaborative experience.

### Files

| File | Change |
|------|--------|
| `guardian/db/models.py` | Add `role` column to `SharedLink` |
| New Alembic migration | Add column |
| `guardian/routes/share.py` | Accept `role` in create, return in get |
| `guardian/realtime/collaboration.py` | Map link role → permissions in `verify_access` |
| `frontend/src/components/ShareButton.tsx` | Role selector UI |
| Tests | Permission mapping, API validation |

---

## Feature 6: Annotations & Comment Threads

### Current state

The `CollaborativeNote` has no annotation support. The `can_comment` boolean exists on `CollaborationPermission` but no server-side or protocol path enforces or uses it. Chat messages have no comment threading.

### Target

Collaborators can attach threaded comments to:
1. Specific messages in a shared chat thread
2. Specific ranges/positions in a collaborative document

Comments support replies and can be resolved/unresolved.

### Protocol

New WebSocket events (relayed by `CollaborationManager.broadcast()`):

```json
// Add a comment
{ "type": "annotation_added", "annotation": {
    "id": "uuid",
    "messageId": "msg-123",       // or documentId + position
    "text": "This needs review",
    "author": { "userId": "...", "name": "..." },
    "createdAt": 1720000000000,
    "resolved": false,
    "replies": []
}}

// Reply to a comment
{ "type": "annotation_reply", "annotationId": "uuid", "reply": {
    "id": "uuid",
    "text": "Fixed in latest commit",
    "author": { ... },
    "createdAt": 1720000001000
}}

// Resolve / unresolve
{ "type": "annotation_resolved", "annotationId": "uuid", "resolved": true }
```

### State management

Follow Claude's pattern of **optimistic updates**:
1. User submits comment → UI updates immediately.
2. Comment is sent over WebSocket → server broadcasts to all.
3. Sender receives the server-confirmed event → state is already correct (idempotent).

State shape:

```typescript
// Keyed by messageId (chat) or documentId+position (docs)
annotations: Record<string, CollabAnnotation[]>

interface CollabAnnotation {
  id: string;
  messageId: string;
  text: string;
  author: { userId: string; name: string; color: string };
  createdAt: number;
  resolved: boolean;
  replies: AnnotationReply[];
}
```

### UI components

| Component | Purpose |
|-----------|---------|
| `AnnotationBadge` | Small pill on message bubbles showing unresolved count. Amber when unresolved, gray when all resolved. |
| `AnnotationThread` | Popover listing all comments + replies on a message. Reply input at bottom. |
| `AnnotationDot` | Inline marker in CollaborativeNote showing a comment exists at a position. |

### Server changes

The `CollaborationManager` already broadcasts arbitrary JSON — no new server infrastructure is needed. The audit log already supports JSONB payloads for annotation events. For persistence, a `collaboration_annotations` table can be added later; initially they can be ephemeral (session-only).

### Files

| File | Change |
|------|--------|
| `frontend/src/components/collaboration/AnnotationBadge.tsx` | **New.** |
| `frontend/src/components/collaboration/AnnotationThread.tsx` | **New.** |
| `frontend/src/features/chat/components/MessageBubble.tsx` | Add AnnotationBadge |
| `frontend/src/components/editor/CollaborativeNote.tsx` | Wire annotation events |
| `guardian/realtime/collaboration.py` | Handle annotation events in message loop |
| Tests | Optimistic update behavior, broadcast verification |

---

## Feature 7: Cursor Ghost Rendering

### Current state

Adaptation 4 adds cursor position tracking in the protocol. But there's no visual rendering of remote cursors.

### Target

Colored carets with user name tags float over the textarea, showing exactly where each collaborator's cursor is.

### What to build

```typescript
// frontend/src/components/collaboration/CursorGhost.tsx

function CursorGhost({ textareaRef }: { textareaRef: RefObject<HTMLTextAreaElement> }) {
  const { cursors, users } = usePresence(wsClient);

  // For each remote cursor:
  // 1. Call measureCursorPosition(textarea, cursor.position)
  // 2. Render a colored caret + name tag at the pixel position

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {renderedCursors.map(({ user, top, left }) => (
        <motion.div
          key={user.userId}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute flex flex-col items-start"
          style={{ top, left }}
        >
          <div className="w-0.5 h-4" style={{ backgroundColor: user.color }} />
          <div className="px-1 py-0.5 rounded text-[9px] font-semibold text-white"
               style={{ backgroundColor: user.color }}>
            {user.name}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
```

### Integration

`CursorGhost` overlays the `<textarea>` in `CollaborativeNote`. It's rendered as a sibling in the same positioned container, with `pointer-events-none` so it doesn't interfere with text selection.

### Prerequisites

Requires Adaptation 4 (cursor positions in protocol) to be complete. Cannot be built before cursor data flows end-to-end.

### Files

| File | Change |
|------|--------|
| `frontend/src/components/collaboration/CursorGhost.tsx` | **New.** |
| `frontend/src/components/editor/CollaborativeNote.tsx` | Mount CursorGhost as textarea overlay |
| `frontend/src/components/collaboration/__tests__/CursorGhost.test.tsx` | Cursor positioning, animation, cleanup |

---

## Feature 8: Tool Approval Workflow

### Current state

Codexify has no interactive tool approval in collaborative sessions. The agent task system runs asynchronously through the queue/worker pipeline, not in a real-time approval flow.

### Target

When an agent (Guardian, Persona) requests a potentially destructive action during a collaborative session, collaborators can approve or deny it in real time.

### Applicability assessment

⚠️ **Low applicability to current Codexify architecture.** Claude Code's tool approval is tightly coupled to its synchronous agent loop — the agent pauses, the UI shows the pending tool, a human clicks Approve/Deny, the agent resumes.

Codexify's agent tasks run asynchronously through the queue (`backend/`) and worker. There's no real-time "pause and wait for approval" mechanism. Adding this would require:

1. A synchronous agent execution mode (major architectural change)
2. A tool approval queue that blocks agent progress
3. UI for pending approvals in collaborative sessions

### Recommendation

**Do not implement until there's a concrete use case.** If Codexify later adds an interactive agent mode (e.g., a "pair programming" session where the agent asks before running commands), this feature becomes relevant. At that point, the protocol patterns from Claude Code (pending → approve/deny → resume) are a clean reference implementation.

### What to reference when building

```
Claude Code pattern:
  server → "tool_use_pending" { toolUseId, toolName, toolInput }
  client → "tool_use_approved" { toolUseId }
  client → "tool_use_denied"  { toolUseId }
  server → broadcast result to all clients

Codexify would add:
  guardian/realtime/tool_approval.py  — approval queue per session
  frontend/src/components/collaboration/ToolApprovalDialog.tsx
```

---

## Feature 9: Ownership Transfer

### Current state

Codexify has no concept of session ownership. Permissions are per-document via `CollaborationPermission` rows. There's no "this person owns the session" model.

### Target

A session owner can transfer ownership to another collaborator. The new owner gains full permissions; the previous owner is demoted to collaborator.

### Applicability assessment

⚠️ **Partially applicable.** Codexify's permission model is document-centric (not session-centric). Adding session ownership would require:

1. A concept of "session" beyond the WebSocket connection group (currently ephemeral in `CollaborationManager`)
2. An `owner_user_id` field on some session record
3. Ownership transfer events that update both the session state and the `CollaborationPermission` rows

### Recommendation

**Tie this to session persistence.** If Codexify adds persistent sessions (e.g., a session record in the DB that survives server restarts), ownership is a natural field on that record. Until then, ownership transfer is premature.

### What to reference when building

```
Claude Code pattern:
  client → "ownership_transferred" { newOwnerId, previousOwnerId }
  server → update session owner
  server → broadcast to all: old owner becomes collaborator, new becomes owner

Codexify would add:
  DB: sessions table with owner_user_id
  guardian/realtime/session_ownership.py
  frontend: "Transfer ownership" in ShareButton / session settings
```

---

## Feature 10: Message Streaming Events

### Current state

Codexify uses **polling** (snapshot refresh every N ms) and **SSE** (`useLiveEvents`) for real-time message updates. SSE delivers task completion events, not message content deltas. The chat shows messages after polling fetches the full message list.

### Target

As the LLM generates a response, the output streams character-by-character to all connected clients in real time.

### Applicability assessment

⚠️ **Low applicability.** Codexify's LLM inference currently goes through the backend worker pipeline. The response is written to the DB when complete, then picked up by the polling mechanism. Streaming would require:

1. The worker to write partial responses during generation (not currently supported)
2. A streaming transport from worker → Guardian → WebSocket to clients
3. Client-side delta rendering (accumulating partial content)

This is a significant backend change, and the current polling approach is functional. The visual benefit (seeing the response type out vs. appear all at once) is noticeable but not essential.

### Recommendation

**Only implement if streaming inference is added to the worker pipeline.** SSE already exists for task status events — extending it to carry content deltas is the natural path. The Claude Code `message_streaming` event (`{ messageId, delta, done }`) is a clean protocol reference.

### What to reference when building

```
Claude Code pattern:
  server → "message_streaming" { messageId: "msg-1", delta: "partial text", done: false }
  server → "message_streaming" { messageId: "msg-1", delta: "", done: true }  // terminal
  client accumulates deltas per messageId until "done: true"

Codexify would extend:
  guardian SSE stream to carry "message_delta" events
  useChat streamingDraft to update per-message content incrementally
  frontend rendering to show partial markdown during streaming
```

---

## Dependency Map

```
Adaptation 1 (WsClient) ──── Foundation for ALL below
  │
  ├── Adaptation 2 (Typing Indicators)
  ├── Adaptation 3 (Context Provider)
  ├── Adaptation 4 (Cursor Protocol) ─── prerequisite for Feature 7
  │
  └── Feature 5 (Role-Scoped Share Links) ─── independent, needs DB migration
  │
  └── Feature 6 (Annotations) ─── uses WsClient, benefits from Context
  │
  └── Feature 7 (Cursor Ghosts) ─── requires Adaptation 4
  │
  └── Feature 8 (Tool Approval) ─── requires synchronous agent mode (not planned)
  │
  └── Feature 9 (Ownership Transfer) ─── requires session persistence (not planned)
  │
  └── Feature 10 (Message Streaming) ─── requires streaming inference (not planned)
```

---

## Priority When Unparking

When these features are revisited, implement in this order:

1. **Feature 5** (Role-scoped share links) — Unblocks collaborative chat by letting shared links grant edit access.
2. **Feature 6** (Annotations) — Highest user-visible value for collaborative editing.
3. **Feature 7** (Cursor ghosts) — Visual polish that depends on Adaptation 4 being complete.
4. **Features 8–10** — Only when their architectural prerequisites are met.
