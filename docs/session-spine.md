# Session Spine

Status: implemented
Scope: multi-tab chat session state (tabs, active tab, per-tab model, per-tab draft)

## 1) Concepts and scope

Codexify now uses three storage layers for chat state:

1. UI local memory (React):
- Runtime state owned by `SessionSpine` in `frontend/src/state/session/SessionSpine.ts`.
- Fast reads for rendering `SessionRail` and active composer draft.

2. Redis session cache (ephemeral, shared):
- Session cache API at `guardian/routes/ui_session.py` (`/api/ui/session`).
- Keyed by user + device, TTL-bound, safe to expire.

3. Postgres durable truth:
- Threads/messages/receipts remain durable in backend DB routes.
- Redis loss does not delete thread/message history.

Session state is different from auth session:
- Session state here means UI tab/model/draft cache.
- Auth/session security is still enforced by API key dependency (`require_api_key`) on `/api/ui/session`.

## 2) Session state contract

Type contract is defined in `frontend/src/state/session/types.ts`.

```ts
type TabId = string;

type SessionTab = {
  tabId: TabId;
  threadId?: string;
  title?: string;
  modelId: string;
  createdAt: string;
  updatedAt: string;
};

type SessionState = {
  deviceId: string;
  userId: string;
  tabs: SessionTab[];
  activeTabId: TabId;
  drafts?: Record<TabId, string>;
  version: number;
  updatedAt: string;
};
```

Current schema/version constants:
- `SESSION_SCHEMA_VERSION = 1`
- `DEFAULT_MODEL_ID = "default"`

## 3) Invariants

Implemented invariants in `SessionSpine`:

1. Single writer at UI boundary:
- UI components dispatch intents (`tabOpen`, `tabClose`, `tabActivate`, `tabReorder`, `tabSetModel`, `tabSetDraft`, `tabSetThread`).
- Direct mutation of `SessionState` is not done in UI components.

2. Session cache is discardable/reconstructible:
- Redis stores convenience UI state only.
- Durable thread/message data remains in Postgres-backed chat routes.

3. Atomic mutation boundary inside spine:
- Each intent mutates a working copy, normalizes state, then replaces in-memory snapshot once.
- Persistence is write-through or debounced write-behind to Redis.

4. Model is per-tab:
- `modelId` is stored on each `SessionTab`.
- New tabs inherit active tab model (or `DEFAULT_MODEL_ID` when no active tab).

5. Always at least one tab:
- State is never persisted with zero tabs.
- Closing the last tab creates a replacement tab and keeps session valid.

6. Drafts are per-tab:
- Stored in `state.drafts[tabId]`.
- Empty/whitespace draft removes that tab draft entry.

7. Stream/run scoping in this slice:
- No explicit tabId/runId stale-token guard is implemented in this SessionSpine slice.
- Completion routing still follows existing thread-level chat flow.

## 4) Redis keyspace and TTL policy

Namespace/version:
- `ui:v1`

Exact key pattern:
- `ui:v1:{urlencoded_user_id}:{urlencoded_device_id}:session`
- Built by `make_session_key()` in `guardian/routes/ui_session.py`.
- No separate `draft:{tabId}` key is implemented in this slice; drafts live inside the same session payload.

Value schema:
- Redis value is raw JSON of `SessionState` (not wrapped envelope).
- API response envelope is `{ "ok": true, "state": <SessionState|null> }`.
- `PATCH /api/ui/session` applies a shallow top-level merge (`{**current, **patch}`) before validation.
- Backend write validation rejects payloads that cannot satisfy the minimum-one-tab invariant.
- Backend normalizes invalid `activeTabId` to the first valid tab.

TTL policy:

Frontend intent-side defaults (`frontend/src/state/session/types.ts`):
- `SESSION_TTL_SECONDS = 1209600` (14 days) for open tabs/session state.
- `SESSION_DRAFTS_TTL_SECONDS = 2592000` (30 days) when any draft exists.

Backend clamp (`guardian/routes/ui_session.py`):
- `UI_SESSION_MIN_TTL_SECONDS` default `60`
- `UI_SESSION_TTL_SECONDS` default `1209600` (14 days)
- `UI_SESSION_MAX_TTL_SECONDS` default `2592000` (30 days)
- Any request TTL is clamped into `[MIN, MAX]`.

Data loss classification:
- Safe to lose: open tabs order, active tab, per-tab model.
- Sad-to-lose (but still cache-only): per-tab drafts.
- Not stored here: threads/messages/receipts (durable elsewhere).

## 5) Hydration and rehydration

Startup path (`GuardianChatWithSidebar`):

1. Build `SessionSpine` with:
- `userId = (userName || "default").trim() || "default"`
- `deviceId = localStorage["cfy.deviceId"]` (generated UUID if missing)
- `store = RedisSessionStateStore`

2. Hydrate from Redis:
- `spine.hydrate({ threadId: routeThreadId, modelId: "default" })`
- If the store read fails (network/Redis/API error), hydrate logs and falls back to default state.

3. Fallback when Redis has no state:
- Create one default tab (optional route thread id attached).
- Persist fallback state immediately.

Corrupt/invalid Redis payload handling:
- Corrupt JSON on GET: backend deletes key and returns `state: null`.
- Structurally invalid state: treated as `state: null`.
- Frontend `normalizeState()` enforces tab list, active tab validity, draft-tab consistency.

Versioning strategy:
- Schema key lives in payload (`version` field) and namespace (`ui:v1`).
- Breaking schema changes should bump namespace (for example `ui:v2`) and schema version.

## 6) Intent contract

Implemented intents and transitions:

1. `TAB_OPEN(threadId?, title?)` (`tabOpen`)
- Creates a new tab.
- Sets `activeTabId` to the new tab.
- New tab `modelId` inherits active tab model, else default.
- Current UI wiring passes active thread id/title when opening a tab.

2. `TAB_CLOSE(tabId)` (`tabClose`)
- Removes tab and tab draft.
- If closed tab was active, activates previous tab index (or first).
- If it was the last tab, creates replacement tab.

3. `TAB_ACTIVATE(tabId)` (`tabActivate`)
- Sets `activeTabId` if tab exists.

4. `TAB_REORDER(tabId[])` (`tabReorder`)
- Reorders known tabs by provided id order.
- Missing ids are appended in original order.

5. `TAB_SET_MODEL(tabId, modelId)` (`tabSetModel`)
- Trims `modelId`; blank resolves to default.
- Updates tab `updatedAt`.

6. `TAB_SET_DRAFT(tabId, text)` (`tabSetDraft`)
- Debounced persist (`300ms`).
- Stores/removes per-tab draft text.

Additional implemented intent used by layout sync:
- `TAB_SET_THREAD(tabId, threadId?, title?)` (`tabSetThread`)
- Keeps tab metadata aligned with active thread selection.
- `threadId` may be unset for a "new chat" tab and is handled as an explicit no-thread state.

## 7) Draft persistence policy

Implemented policy:
- Drafts are cache-backed in Redis as part of `SessionState.drafts`.
- Presence of any draft upgrades session TTL request to draft TTL window (30 days).
- No Postgres draft checkpoint is implemented in this slice.

Compatibility fallback:
- `Composer` still has thread-scoped `sessionStorage` fallback when no controlled draft callback is provided.
- In Guardian chat integration, controlled draft callback is provided by SessionSpine path.

## 8) Failure modes and recovery

Expected behavior:

1. Redis unavailable:
- `/api/ui/session` returns `503`.
- Persistence failures log warning (`[session] failed to persist state`).
- If state is already hydrated, UI continues using local in-memory state.
- If initial hydrate fails from cold start, SessionSpine immediately initializes a default in-memory state.

2. Redis empty/expired:
- Hydration creates default state; user can continue immediately.

3. Corrupt cached value:
- Backend clears bad JSON key on read and returns null state; frontend rebuilds default.

4. Draft/session cache loss:
- Open-tab context and drafts can disappear.
- Thread/message history remains intact from durable backend store.

## 9) Debugging and operations

Required env/config:
- `REDIS_URL` (shared Redis connection, default `redis://redis:6379/0`)
- `UI_SESSION_TTL_SECONDS`
- `UI_SESSION_MAX_TTL_SECONDS`
- `UI_SESSION_MIN_TTL_SECONDS`
- `GUARDIAN_API_KEY` (for protected session API routes)

Inspect via API:

```bash
curl -sS \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/ui/session?user_id=<user>&device_id=<device>" | jq
```

Inspect Redis keys:

```bash
redis-cli --scan --pattern 'ui:v1:*:*:session'
```

Build exact scoped key (matches backend URL encoding):

```bash
USER_ID='user@example.com'
DEVICE_ID='device:1'
ENC_USER="$(python -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1].strip(), safe=\"\"))' "$USER_ID")"
ENC_DEVICE="$(python -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1].strip(), safe=\"\"))' "$DEVICE_ID")"
redis-cli GET "ui:v1:${ENC_USER}:${ENC_DEVICE}:session"
```

Scoped clear (safe):

```bash
redis-cli DEL "ui:v1:${ENC_USER}:${ENC_DEVICE}:session"
```

Bulk clear only UI session cache keys:

```bash
redis-cli --scan --pattern 'ui:v1:*:*:session' | xargs -r redis-cli DEL
```

Simulate Redis restart:

```bash
docker compose restart redis
```

Expected UX after restart/flush:
- Reload starts from default single-tab session.
- Existing persisted threads/messages still load from backend history.

## 10) What changed and why

- Tabs moved into a dedicated session layer, not app navigation.
- Session Pill Rail is rendered inside Guardian chat shell and driven by SessionSpine selectors/intents.
- Rail UX refinement: when only one tab exists, the tab-pill strip is hidden while the utility cluster stays visible (model picker, new tab, overflow).
- Close affordance is only shown when multiple tabs are visible.
- Benefits: snappier local tab switching, consistent single-writer state semantics, and correct per-tab model/draft behavior across reloads on the same device.

## 11) Implementation references

Frontend:
- `frontend/src/state/session/types.ts`
- `frontend/src/state/session/SessionStateStore.ts`
- `frontend/src/state/session/SessionSpine.ts`
- `frontend/src/components/SessionRail/SessionRail.tsx`
- `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`
- `frontend/src/features/chat/GuardianChat.tsx`
- `frontend/src/features/chat/components/Composer.tsx`

Backend:
- `guardian/routes/ui_session.py`
- `guardian/guardian_api.py`
- `guardian/queue/redis_queue.py`

Tests:
- `frontend/src/test/session-spine.test.ts`
- `tests/routes/test_ui_session_routes.py`
