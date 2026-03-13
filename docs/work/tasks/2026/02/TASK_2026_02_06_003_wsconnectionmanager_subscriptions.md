# TASK-2026-02-06-003_wsconnectionmanager_subscriptions: WSConnectionManager + Subscriptions

## TASK METADATA
- Campaign-ID: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Task-ID: TASK-2026-02-06-003_wsconnectionmanager_subscriptions
- Title: WSConnectionManager + subscriptions (central registry + topic pub/sub)
- Task artifact (current): docs/work/tasks/2026/02/TASK_2026_02_06_003_wsconnectionmanager_subscriptions.md
- Task artifact (preferred canonical path): docs/work/tasks/2026/02/TASK_2026_02_06_003_wsconnectionmanager_subscriptions.md
- Risk: MED

## Objective
Create a deterministic, centralized WebSocket connection registry with topic subscriptions and targeted broadcast, then wire it into the existing in-memory event relay path so realtime events can be routed only to subscribed clients.

## Scope
### In-scope
- Implement a `WSConnectionManager` with:
  - register/unregister connections
  - subscribe/unsubscribe by topic
  - broadcast to a topic (only subscribed clients)
  - safe cleanup on disconnect
- Wire an event relay listener using `subscribe_in_memory()` to fan out events through the manager.
- Add focused tests covering:
  - subscribe/unsubscribe correctness
  - broadcast routes to correct clients only

### Out-of-scope
- Any persistence of subscriptions (DB/Redis) beyond in-memory.
- Auth or permission changes (unless strictly required for tests to pass and stays within Allowed Files).
- Frontend/UI changes.

## Allowed files (STRICT)
> Do not modify files outside this list.

- guardian/ws/manager.py
- guardian/ws/__init__.py (only if needed to export the manager)
- guardian/realtime/event_relay.py (or the existing module that defines/uses `subscribe_in_memory()`; update the path once confirmed)
- tests/realtime/test_ws_manager.py (new test file is allowed)
- docs/work/tasks/2026/02/TASK_2026_02_06_003_wsconnectionmanager_subscriptions.md
- docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

## Dependencies / Prereqs (NO GUESSING)
Run these to confirm the code locations before editing:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# REQUIRED: clean tree before starting
git status --porcelain -uall

# Confirm where subscribe_in_memory lives and what consumes it
rg -n "def subscribe_in_memory\(|subscribe_in_memory\(" guardian tests

# Confirm existing websocket-related code (if any)
rg -n "WebSocket|websocket|WSConnection|connection manager" guardian/ws guardian/realtime guardian/routes tests

# Confirm current realtime tests layout
ls -la tests/realtime || true
```

**Expected outputs (prereqs):**
- `git status --porcelain -uall` prints nothing.
- `rg` results show a concrete file path for `subscribe_in_memory()`.

## Command checklist (exact)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree
git status --porcelain -uall

# 1) Find the authoritative relay file path for subscribe_in_memory
rg -n "def subscribe_in_memory\(|subscribe_in_memory\(" guardian

# 2) Implement manager
# Edit: guardian/ws/manager.py

# 3) Wire manager into relay
# Edit: guardian/realtime/event_relay.py (or the discovered file)

# 4) Add tests
# Edit/Add: tests/realtime/test_ws_manager.py

# 5) Run targeted tests
python -m pytest -q tests/realtime/test_ws_manager.py

# 6) Ensure only allowed files changed
git status --porcelain -uall
```

## Expected outputs (success signals)
- `python -m pytest -q tests/realtime/test_ws_manager.py` exits 0.
- Tests explicitly verify:
  - Subscriptions are topic-scoped.
  - Broadcast only reaches subscribed connections.
  - Unregister removes a connection from all topics.
- `git status --porcelain -uall` shows changes only within Allowed files.

## Rollback / cleanup
```bash
# If you touched a wrong file or need to revert changes:
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git restore --staged --worktree \
  guardian/ws/manager.py \
  guardian/ws/__init__.py \
  guardian/realtime/event_relay.py \
  tests/realtime/test_ws_manager.py

git status --porcelain -uall
```

## Commit plan (MANUAL; index.lock workaround)
**Commit mode:** two-phase

### Commit A (implementation)
- Commit message EXACT:
  - `TASK-2026-02-06-003_wsconnectionmanager_subscriptions: ws manager + topic pubsub`

- Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# Stage only implementation + tests
git add \
  guardian/ws/manager.py \
  guardian/ws/__init__.py \
  guardian/realtime/event_relay.py \
  tests/realtime/test_ws_manager.py

git status --porcelain -uall

git commit --no-verify -m "TASK-2026-02-06-003_wsconnectionmanager_subscriptions: ws manager + topic pubsub"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
- Commit message EXACT:
  - `TASK-2026-02-06-003_wsconnectionmanager_subscriptions: docs finalize + mapping`

- Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git add \
  docs/work/tasks/2026/02/TASK_2026_02_06_003_wsconnectionmanager_subscriptions.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-003_wsconnectionmanager_subscriptions: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Mapping
- Campaign mapping line format (EXACT):
  - `TASK-2026-02-06-003_wsconnectionmanager_subscriptions -> [6f7f2404, f2452481]`

## Notes
- Filename contains a `+` which is non-canonical. Do **not** rename during implementation unless explicitly allowed by campaign/task scope. If you want to normalize it, do it as a docs-only task using `git mv`.

## Summary (fill after completion)
- What changed:
  - Added `guardian/ws/manager.py` with register/unregister/subscribe/unsubscribe/topic broadcast and stale connection cleanup.
  - Added `guardian/realtime/event_relay.py` that consumes `event_bus.subscribe_in_memory()` and fans out by topic through `WSConnectionManager`.
  - Updated `guardian/ws/__init__.py` to export `WSConnectionManager`.
  - Added `tests/realtime/test_ws_manager.py` covering subscription scoping, broadcast targeting, unregister cleanup, and relay forwarding.
- Commands run:
  - `git status --porcelain -uall`
  - `rg -n "def subscribe_in_memory\\(|subscribe_in_memory\\(" guardian tests -S`
  - `rg -n "WebSocket|websocket|WSConnection|connection manager" guardian/ws guardian/realtime guardian/routes tests -S`
  - `python -m pytest -q tests/realtime/test_ws_manager.py` (failed: `No module named pytest` under python3.13)
  - `pytest -q tests/realtime/test_ws_manager.py` (passed)
- Test results:
  - `pytest -q tests/realtime/test_ws_manager.py` -> 4 passed
- Final mapping:
  - TASK-2026-02-06-003_wsconnectionmanager_subscriptions -> [6f7f2404, f2452481]
