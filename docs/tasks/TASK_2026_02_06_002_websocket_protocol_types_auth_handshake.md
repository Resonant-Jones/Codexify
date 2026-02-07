## TASK-2026-02-06-002 — WebSocket Protocol Types + Auth Handshake

**Goal:** Create WS framing + connection auth that reuses existing API-key verification logic.

**Deliverables:**

* `guardian/ws/protocol.py`:

  * `RPCRequest`, `RPCResponse`, `RPCEvent`
  * message validation + bounded payload size checks
* `guardian/ws/auth.py`:

  * handshake strategy (query param OR first message)
  * reject unauthenticated connection with appropriate close code

**Security:**

* Enforce **max payload size**
* No method dispatch before auth completes

**Tests:**

* unauthenticated connect rejected
* malformed frame rejected
* oversized payload rejected

---

# TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake

## TASK METADATA
- Campaign-ID: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Task-ID: TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake
- Title: WebSocket protocol types + auth handshake
- Task artifact: docs/tasks/TASK_2026_02_06_002_websocket_protocol_types_auth_handshake.md
- Risk: MED
- Owner: resonant_jones

## Objective
Introduce a minimal, validated WebSocket message framing layer and a deterministic authentication handshake that reuses the existing API-key verification logic, so **no WS method dispatch can occur before auth** and payloads are bounded.

## Scope
### In-scope
- Add WS message envelope/types with validation and size limits.
- Add WS auth handshake that verifies an API key using the same logic as HTTP API key enforcement.
- Add tests for: unauthenticated connect rejected, malformed frame rejected, oversized payload rejected.

### Out-of-scope
- Implementing business-method dispatch / RPC handlers beyond a stub.
- Changing any HTTP auth semantics.
- Adding new persistent storage or DB schema.

## Allowed files (STRICT)
> Do not edit files outside this list.

- guardian/ws/protocol.py
- guardian/ws/auth.py
- guardian/ws/__init__.py
- guardian/ws/router.py
- guardian/core/dependencies.py
- tests/realtime/test_websocket_auth_handshake.py
- tests/realtime/test_websocket_protocol_validation.py
- docs/tasks/TASK_2026_02_06_002_websocket_protocol_types_auth_handshake.md
- docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md
## Dependencies / Prereqs (NO GUESSING)
Run these first and capture outputs in the Summary if anything is surprising.

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# clean tree required
git status --porcelain -uall

# confirm existing ws-related code paths
rg -n "websocket|WebSocket|/ws|ws/" guardian tests -S

# confirm how API key auth is currently enforced
rg -n "require_api_key|X-API-Key|GUARDIAN_API_KEY" guardian/core/dependencies.py guardian/routes -S
```

## Execution plan
### Step-by-step commands (copy/paste)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree before starting
git status --porcelain -uall

# 1) discover existing websocket entrypoints (do not edit during discovery)
rg -n "WebSocket\(|websocket\(|include_router\(|/ws" guardian -S

# 2) implement protocol + auth within allowed files only
# - Add a strict message schema (request/response/event) with validation.
# - Enforce max payload size at the earliest possible point.
# - Ensure auth completes (API key verified) before any method dispatch.

# 3) run targeted tests
pytest -q tests/realtime/test_websocket_auth_handshake.py tests/realtime/test_websocket_protocol_validation.py

# 4) confirm only allowed files changed
git status --porcelain -uall
```

## Expected outputs (success signals)
- `pytest` exits 0 for the two new/updated realtime WS test files.
- Unauthenticated WS connection attempt is rejected (close code is deterministic and asserted in tests).
- Malformed frames are rejected (deterministic error path asserted).
- Oversized payload is rejected before any parsing/dispatch and asserted.
- `git status --porcelain -uall` shows modifications **only** in the Allowed files list.

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard local changes (only use if you need to abort)
git restore --staged --worktree \
  guardian/ws/protocol.py \
  guardian/ws/auth.py \
  guardian/ws/__init__.py \
  guardian/ws/router.py \
  guardian/core/dependencies.py \
  tests/realtime/test_websocket_auth_handshake.py \
  tests/realtime/test_websocket_protocol_validation.py \
  docs/tasks/TASK_2026_02_06_002_websocket_protocol_types_auth_handshake.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git status --porcelain -uall
```

## Commit plan (MANUAL)
### Commit mode
- two-phase

### Commit A (implementation)
- Commit message (EXACT):
  - `TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake: ws protocol + auth handshake`

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  guardian/ws/protocol.py \
  guardian/ws/auth.py \
  guardian/ws/__init__.py \
  guardian/ws/router.py \
  guardian/core/dependencies.py \
  tests/realtime/test_websocket_auth_handshake.py \
  tests/realtime/test_websocket_protocol_validation.py

git commit --no-verify -m "TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake: ws protocol + auth handshake"

git log -1 --oneline

git status --porcelain -uall
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - `TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake: docs finalize + mapping`

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  docs/tasks/TASK_2026_02_06_002_websocket_protocol_types_auth_handshake.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Mapping
- TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake -> [bef02d9c, 3dd76be1]

## Notes
- Close codes: prefer a stable, test-assertable close code for auth failure vs validation failure.
- Reuse existing API key logic rather than re-implementing parsing/verification.

## Summary (fill after completion)
- Changed files:
  - guardian/ws/__init__.py
  - guardian/ws/auth.py
  - guardian/ws/protocol.py
  - guardian/ws/router.py
  - tests/realtime/test_websocket_auth_handshake.py
  - tests/realtime/test_websocket_protocol_validation.py
- Commands run:
  - rg discovery checks for auth/router/lifespan/queue/tests references (per checklist)
  - pytest -q tests/realtime/test_websocket_auth_handshake.py tests/realtime/test_websocket_protocol_validation.py
- Test results:
  - 5 passed
- Commit A: bef02d9c
- Commit B: 3dd76be1
- Final mapping:
  - TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake -> [bef02d9c, 3dd76be1]
