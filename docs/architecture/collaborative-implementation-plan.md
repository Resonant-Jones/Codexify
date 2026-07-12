# Collaborative Infrastructure — Implementation Plan

> **Status:** Proposed. First 4 adaptations from the [gap analysis](./collaborative-features.md).  
> **Prerequisite reading:** `docs/architecture/collaborative-features.md`

---

## Current State

Codexify's collaborative surface currently spans:

| Layer | What exists | Transport |
|-------|-----------|-----------|
| **Document editing** | `CollaborativeNote` — real-time WebSocket sync, presence, autosave, audit trail | Raw `new WebSocket()` per `useEffect` |
| **Chat sharing** | `SharePage` — read-only thread/document views via tokenized URLs | REST (`GET /api/share/{token}`) |
| **Live events** | `useLiveEvents` — SSE-based event stream for message arrivals, task status | SSE via `liveEventsHub` singleton |
| **Chat UI** | `GuardianChat` — all state managed inline (3000+ lines), no extracted collaboration hooks | Polling + SSE |

**The gap:** Everything works, but each subsystem reinvents connection management. The `CollaborativeNote` has no reconnect logic. The chat has no real-time presence awareness between concurrent viewers. No component outside `GuardianChat` can answer "who else is here?"

---

## Adaptation 1: Robust WebSocket Client Wrapper

### Target

Replace raw `new WebSocket()` usage in `CollaborativeNote` (and future co-presence connections) with a resilient client that handles reconnect, keepalive, and typed event dispatch.

### What to build

A new file: `frontend/src/lib/wsClient.ts`

```typescript
// Public API surface (implementation inspired by Claude's CollabSocket pattern)
class WsClient {
  constructor(url: string, options?: WsClientOptions);
  connect(): void;
  disconnect(): void;
  send(payload: unknown): void;
  on(eventType: string, handler: (data: any) => void): () => void;
  readonly isConnected: boolean;
  onConnectionChange?: (connected: boolean) => void;
}

interface WsClientOptions {
  maxReconnectAttempts?: number;   // default: 5
  baseReconnectDelayMs?: number;   // default: 1000
  pingIntervalMs?: number;         // default: 30_000
  token?: string;                  // auth token appended as query param
  onUnauthorized?: () => void;     // called on 4401 close
}
```

### Where it plugs in

1. **`CollaborativeNote`** — Replace inline `ws.current = new WebSocket(wsUrl)` with a `WsClient` instance. The existing `onopen`, `onmessage`, `onclose`, `onerror` handlers map directly to `on()` subscriptions and `onConnectionChange`.

2. **Future co-presence** — When chat co-presence is added (see Adaptation 2), a second `WsClient` instance connects to a `/api/collab/presence/{threadId}` endpoint for typing indicators and user list sync.

### Key design decisions

- **No framework dependency.** `WsClient` is a plain TypeScript class, not a React hook. This keeps it testable in isolation and usable outside React (e.g., service workers, future mobile).
- **Event dispatch follows the Codexify pattern.** Instead of Claude's 20 typed event interfaces, use the existing string-keyed `subscribe`/`unsubscribe` pattern already used by `useLiveEvents`. This keeps the API familiar.
- **Reconnect uses exponential backoff with a cap**, matching the Guardian's existing retry patterns in `useChat`.
- **Ping/pong is client-initiated** — the server just echoes back. No server changes needed.

### Server changes

None required. The `CollaborationManager` already handles accept/close/message. The `WsClient` class works with any WebSocket server.

### Files changed

| File | Change |
|------|--------|
| `frontend/src/lib/wsClient.ts` | **New.** Core class. |
| `frontend/src/lib/__tests__/wsClient.test.ts` | **New.** Unit tests covering connect, reconnect, ping, event dispatch, disconnect. |
| `frontend/src/components/editor/CollaborativeNote.tsx` | Replace raw WebSocket with `WsClient`. |

### Verification

1. Open `CollaborativeNote` on two browser tabs.
2. Kill the Guardian server. Both tabs show "Offline".
3. Restart Guardian. Both tabs auto-reconnect within ~15s (1s + 2s + 4s + 8s max).
4. Edits made after reconnect sync correctly.

---

## Adaptation 2: Typing Indicators

### Target

Show when collaborators are actively typing in either the chat composer or the collaborative document editor.

### What to build

#### 2a. Protocol events

Add two events to the document collaboration WebSocket protocol (already handled by `CollaborationManager.broadcast()`):

```json
// Client → Server (then broadcast to others)
{ "type": "typing_start", "user_id": "user-abc" }
{ "type": "typing_stop",  "user_id": "user-abc" }
```

For chat co-presence, add a new presence endpoint (see Adaptation 4) that also supports these events.

#### 2b. Frontend hook: `useTypingIndicator`

```typescript
// frontend/src/hooks/useTyping.ts
function useTyping(wsClient: WsClient, userId: string) {
  // Debounce: send "typing_start" on first keystroke,
  // hold for 2s of inactivity, then send "typing_stop"
  return {
    notifyTyping: () => void,   // call on each keystroke
    typingUsers: string[],      // other users currently typing
  };
}
```

#### 2c. UI component: `<TypingIndicator>`

```typescript
// frontend/src/components/collaboration/TypingIndicator.tsx
function TypingIndicator({ userIds, userColors }: Props) {
  // Renders "Alice, Bob are typing…" with animated dots.
  // Displays up to 3 colored initial circles.
  // Gracefully returns null when no one is typing.
}
```

### Where it plugs in

- **`CollaborativeNote`** — Add `<TypingIndicator>` above the textarea footer. Call `notifyTyping()` in the `onChange` handler before broadcasting the content update.
- **`Composer` (GuardianChat)** — Once co-presence is wired (Adaptation 4), add `<TypingIndicator>` above the composer footer.

### Server changes

None for document collaboration — `CollaborationManager.broadcast()` already forwards arbitrary JSON. For chat co-presence, a thin presence WebSocket handler is needed (see Adaptation 4).

### Files changed

| File | Change |
|------|--------|
| `frontend/src/hooks/useTyping.ts` | **New.** Debounced typing notification hook. |
| `frontend/src/components/collaboration/TypingIndicator.tsx` | **New.** Visual indicator component. |
| `frontend/src/components/editor/CollaborativeNote.tsx` | Wire typing indicator + notifyTyping call. |
| `frontend/src/hooks/__tests__/useTyping.test.ts` | **New.** Debounce behavior, start/stop events. |

### Verification

1. User A and User B open the same document in CollaborativeNote.
2. User A types — User B sees "User A is typing…" within the debounce window.
3. User A stops — after 2s, indicator disappears.
4. Three users type simultaneously — indicator shows all three names.

---

## Adaptation 3: React Context Provider for Collaboration State

### Target

Extract collaboration awareness from `GuardianChat` and `CollaborativeNote` into a shared context so any component can access presence, connection status, and typing state without prop drilling.

### What to build

#### 3a. Collaboration context

```typescript
// frontend/src/contexts/CollaborationContext.tsx

interface CollaborationState {
  // Connection
  isConnected: boolean;
  connectionStatus: 'connected' | 'connecting' | 'disconnected';

  // Presence
  activeUsers: Array<{ userId: string; name: string; color: string }>;
  typingUserIds: string[];

  // Actions (for components that produce events)
  notifyTyping: () => void;
  stopTyping: () => void;
}

const CollaborationContext = createContext<CollaborationState | null>(null);

function CollaborationProvider({ documentId, userId, userName, children }: Props) {
  // Wires WsClient (Adaptation 1) + useTyping (Adaptation 2)
  // into a single context value.
  // Presence updates come from the WebSocket via "presence.join" / "presence.leave".
}

function useCollaboration(): CollaborationState | null {
  // Returns null when no provider is mounted (graceful degradation).
}
```

#### 3b. Integration points

| Component | What it consumes | What it provides |
|-----------|-----------------|-----------------|
| `CollaborativeNote` | Presence avatars, typing state | Content updates, typing notifications |
| `GuardianChat` / `Composer` | Presence avatars in header, typing state in composer footer | Message sends |
| `Header` / `AppShell` | Active user count, connection status dot | Nothing — read-only consumer |
| `Sidebar` | "N users viewing this thread" | Nothing — read-only consumer |

### Design decisions

- **Follows the `useLiveEvents` pattern** — a singleton hub per tab, with `subscribe()` returning an unsubscribe function. The context is a convenience wrapper, not the source of truth.
- **Graceful null return** — `useCollaboration()` returns `null` when no provider is mounted. Components check `if (!collab) return null`. This means collaboration is purely additive — no existing code breaks.
- **Does not own the WebSocket** — the `WsClient` instance is created outside and passed in. This keeps the context testable with a mock client.

### Server changes

None. The context is purely a frontend refactor.

### Files changed

| File | Change |
|------|--------|
| `frontend/src/contexts/CollaborationContext.tsx` | **New.** Provider + hook. |
| `frontend/src/contexts/__tests__/CollaborationContext.test.tsx` | **New.** Context rendering with mock WsClient. |
| `frontend/src/components/editor/CollaborativeNote.tsx` | Simplify: consume context instead of managing own state. |
| `frontend/src/features/chat/GuardianChat.tsx` | Wrap with provider, consume presence in header. |
| `frontend/src/components/layout/Header.tsx` | Add presence avatars via `useCollaboration()`. |

### Verification

1. Mount `CollaborationProvider` in the app shell.
2. Open a document in `CollaborativeNote` — presence avatars appear in the header.
3. Open a second tab — both tabs show 2 active users.
4. Component using `useCollaboration()` without a provider receives `null` — no crash.

---

## Adaptation 4: Cursor Positions in Protocol + Presence State

### Target

Broadcast cursor positions so that remote users' cursors are visible in collaborative documents. This is the prerequisite for cursor ghost rendering (parked in the spec doc as a future feature).

### What to build

#### 4a. Protocol events

Add one event to the document collaboration protocol:

```json
// Client → Server (then broadcast to all others)
{
  "type": "cursor_update",
  "user_id": "user-abc",
  "position": 42,
  "selection_start": 10,
  "selection_end": 42
}
```

#### 4b. Server-side presence state

Extend `CollaborationManager.presence` from `set[str]` (user IDs) to include cursor state:

```python
# guardian/realtime/collaboration.py

class PresenceEntry:
    user_id: str
    cursor_position: int | None = None
    cursor_selection_start: int | None = None
    cursor_selection_end: int | None = None
    is_typing: bool = False
    last_activity: float  # timestamp

# presence: dict[str, dict[str, PresenceEntry]]
#           doc_id → user_id → entry
```

The `broadcast()` method already handles arbitrary JSON — the server just relays cursor events unchanged. The `PresenceEntry` is for potential future server-side awareness (e.g., "who was last active").

#### 4c. Frontend hook: `usePresence`

```typescript
// frontend/src/hooks/usePresence.ts

interface CursorState {
  userId: string;
  position: number;
  selectionStart?: number;
  selectionEnd?: number;
}

function usePresence(wsClient: WsClient) {
  return {
    users: Map<string, CollabUser>,      // all active users
    cursors: Map<string, CursorState>,   // per-user cursor positions
    sendCursorUpdate: (pos: number, selStart?: number, selEnd?: number) => void,
  };
}
```

This hook listens for `presence.join`, `presence.leave`, and `cursor_update` events and maintains immutable state maps (copy-on-write). The immutable pattern from Claude's `presence.ts` is the right approach — prevents stale closure bugs in React.

#### 4d. Cursor measurement utility

```typescript
// frontend/src/lib/cursorMeasurement.ts
function measureCursorPosition(
  textarea: HTMLTextAreaElement,
  offset: number
): { top: number; left: number } {
  // Mirror-div technique: create a hidden div matching textarea CSS,
  // populate with text up to offset, measure span position.
  // Framework-agnostic, pure DOM utility.
}
```

### Server changes

Minimal. The `CollaborationManager` needs:

1. Extend `connect()` and `disconnect()` to store a `PresenceEntry` instead of a bare user ID string.
2. Handle `cursor_update` events in the WebSocket message loop (store position, broadcast unchanged).
3. Include cursor positions in `presence.join` broadcasts so late joiners see current cursor positions.

These are additive — no existing behavior changes.

### Files changed

| File | Change |
|------|--------|
| `guardian/realtime/collaboration.py` | Extend presence tracking to `PresenceEntry` dataclass. Handle `cursor_update`. |
| `frontend/src/hooks/usePresence.ts` | **New.** Presence hook with cursor state. |
| `frontend/src/lib/cursorMeasurement.ts` | **New.** DOM utility for textarea cursor positioning. |
| `frontend/src/hooks/__tests__/usePresence.test.ts` | **New.** Immutable state transitions, cursor updates. |
| `frontend/src/components/editor/CollaborativeNote.tsx` | Wire `sendCursorUpdate` on selection/cursor changes. |

### Verification

1. User A and User B open the same document.
2. User A moves cursor to position 50 — server broadcasts `cursor_update`.
3. User B's `usePresence` hook receives the event and updates `cursors` map.
4. `measureCursorPosition(textarea, 50)` returns correct pixel coordinates.
5. No visual cursor ghosts yet (that's a future feature) — verify data flow only.

---

## Execution Order & Dependencies

```
Adaptation 1 (WsClient) ─────────────────────────────────────────────┐
  │                                                                    │
  ├──► Adaptation 2 (Typing) ── depends on WsClient for transport     │
  │                                                                    │
  ├──► Adaptation 3 (Context) ── depends on WsClient for transport    │
  │                                                                    │
  └──► Adaptation 4 (Cursors) ── depends on WsClient for transport    │
                               ── depends on CollaborationManager      │
                                  changes (server-side presence)       │
```

**Recommended order:** 1 → 2 → 3 → 4

- **Adaptation 1 first** because it's the foundation everything else uses. Can be done and merged independently.
- **Adaptations 2 and 3 in parallel** after 1 lands. They touch different files and can be developed concurrently.
- **Adaptation 4 last** because it requires server-side changes and benefits from the context already being in place.

Each adaptation ships independently and adds value without the others.

---

## Cost Estimate

| Adaptation | Frontend effort | Backend effort | Test effort | Risk |
|-----------|----------------|---------------|-------------|------|
| 1. WsClient | Medium (new class + rewrite CollaborativeNote) | None | Low | Low — class is isolated |
| 2. Typing | Low (hook + component) | None (for docs; see spec for chat) | Low | Low |
| 3. Context | Medium (new provider, refactor consumers) | None | Medium | Medium — touches GuardianChat |
| 4. Cursors | Medium (hook, utility, protocol) | Low (extend dict → dataclass) | Medium | Low |

Total: ~3–5 days of focused work for all four, with each shippable independently.
