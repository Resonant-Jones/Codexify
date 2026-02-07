## TASK-2026-02-06-012 — Browser Routes + WS Hooks

**Goal:** REST + WS interop (approvals & status broadcast).

**Deliverables:**

* `guardian/routes/browser.py` endpoints
* WS events:

  * `browser.approval.requested`
  * `browser.approval.decided`
  * `browser.session.updated`

**Tests:**

* event emission on approval requested/decided

---

# TASK-2026-02-06-012 — Browser Routes + WS Hooks

- **Task-ID:** TASK-2026-02-06-012_browser_routes_ws_hooks
- **Title:** Browser Routes + WS Hooks (REST + WS interop)
- **Goal:** Add REST endpoints for browser automation *and* emit WebSocket events for approval + session status so the UI/clients can observe lifecycle changes.
- **Commit mode:** two-phase
  - **Commit A:** implementation + tests
  - **Commit B:** docs finalize + campaign mapping update

---

## Background

The control-plane needs a thin REST surface for browser session lifecycle + approvals, but also needs **real-time** visibility. This task establishes the HTTP endpoints and wires **WS events** so clients can subscribe and react.

### WS events (must exist + be emitted)

- `browser.approval.requested`
- `browser.approval.decided`
- `browser.session.updated`

Event payloads should be bounded + JSON-serializable. Include IDs and minimal status fields (no large blobs).

---

## Allowed files (STRICT)

Only modify/create files in this exact allowlist:

- `guardian/routes/browser.py`
- `guardian/realtime/`**`**`**` (new/existing modules only under this directory)
- `guardian/db/models/`**`**`**` (ONLY if a model is required for a minimal session/approval identifier)
- `guardian/db/migrations/`**`**`**` (ONLY if you add a DB model/table)
- `guardian/tests/`**`**`**` (tests for browser routes + ws emission)
- `docs/tasks/TASK_2026_02_06_012_browser_routes_ws_hooks.md`
- `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md` (mapping line only)

If implementation *requires* touching any file outside this list: **STOP** and update this task artifact first.

---

## Dependencies / prereqs

Run these from repo root:

```bash
python --version
node --version || true
pnpm --version || true

git status --porcelain -uall
```

Repo must be on the campaign branch and working tree clean before starting Commit A.

---

## Command checklist

### 1) Locate existing realtime + router patterns (no edits)

```bash
# confirm where routers are registered
rg -n "include_router\(" guardian | head -n 50

# locate existing websocket / realtime entrypoints
rg -n "websocket|WebSocket|ws\b|subscribe|broadcast|event" guardian/realtime guardian/routes guardian/core || true

# locate existing approval concepts (if any)
rg -n "approval|approve|denied|decision" guardian || true
```

### 2) Implement REST routes

Implement `guardian/routes/browser.py` with a minimal, auditable REST surface.

Required endpoints (exact paths can follow existing conventions, but must be stable + documented in this artifact after implementation):

- Create/start session (returns session id + status)
- Get session status (by id)
- Request approval for an action (creates approval request id)
- Decide approval (approve/deny + optional reason)

Auth: reuse the canonical API-key dependency used by other protected routes.

### 3) Emit WS events

Wire emission for the three events:

- When an approval is created/requested → `browser.approval.requested`
- When an approval is decided → `browser.approval.decided`
- When a session state changes (created/started/stopped/error) → `browser.session.updated`

### 4) Add tests (required)

Add tests that prove:

- Creating an approval triggers `browser.approval.requested`
- Deciding approval triggers `browser.approval.decided`
- Updating session triggers `browser.session.updated`

Test strategy can be either:

- patch/mock the event emitter/broadcast function and assert it’s called with correct event name + payload, OR
- use an in-memory websocket test client if the repo already has a pattern.

Commands:

```bash
# run the narrowest test set that covers the new behavior
pytest -q guardian/tests -k "browser or approval or realtime or websocket" || true
```

(If the repo’s test infrastructure requires a different entrypoint, update this checklist with the exact working command and keep it narrow.)

### 5) Sanity checks

```bash
git status --porcelain -uall

git diff --stat
```

---

## Expected outputs (success signals)

- REST routes exist under `guardian/routes/browser.py` and are mounted by the app.
- WS events are emitted for the three required event names.
- Tests exist and pass locally for the new event emission behavior.
- `git status --porcelain -uall` is clean after Commit B.

---

## Rollback / cleanup

If you need to abort before Commit A:

```bash
git restore --staged --worktree -- .
git status --porcelain -uall
```

If you need to undo only the browser-related edits during development:

```bash
git restore -- guardian/routes/browser.py
# plus any new realtime/tests files you touched
```

---

## Commit plan

### Commit A (implementation + tests)

Stage ONLY code + tests (no campaign/task doc edits other than updating this artifact’s “Commands run + outcomes” section if you must capture evidence after the fact).

```bash
# adjust paths to match what actually changed (must stay within Allowed files)
git add guardian/routes/browser.py guardian/realtime guardian/tests

git commit --no-verify -m "TASK-2026-02-06-012_browser_routes_ws_hooks: browser routes + ws event hooks"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)

```bash
git add \
  docs/tasks/TASK_2026_02_06_012_browser_routes_ws_hooks.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-012_browser_routes_ws_hooks: docs finalize + mapping"

git log -1 --oneline
```

Update the campaign mapping line to:

- `TASK-2026-02-06-012_browser_routes_ws_hooks -> [4b32590b, 42e546d6]`

---

## Commands run + outcomes (fill during execution)

- Commands run:
  - `git status --porcelain -uall`
  - `rg -n "include_router\\(" guardian | head -n 50`
  - `rg -n "websocket|WebSocket|ws\\b|subscribe|broadcast|event" guardian/realtime guardian/routes guardian/core || true`
  - `rg -n "approval|approve|denied|decision" guardian || true`
  - `pytest -q guardian/tests -k "browser or approval or realtime or websocket" || true`
  - `pytest -q guardian/tests/realtime/test_browser_routes_ws_hooks.py`
- Results:
  - Added browser approval request/session endpoints in `guardian/routes/browser.py`.
  - Wired event emissions for `browser.approval.requested`, `browser.approval.decided`, and `browser.session.updated`.
  - Added tests in `guardian/tests/realtime/test_browser_routes_ws_hooks.py`; targeted test file passed (`3 passed`).
  - Broad test selector hit an unrelated collection error in `guardian/tests/db/test_seed.py` (`NodeClassAlreadyDefined` between `guardian.db.neo` and `guardian.graph.models`).
  - Commit A created: `4b32590b`.
  - Commit B created: `42e546d6`.
- Notes / deviations:
  - `guardian/guardian_api.py` router registration was not changed in this task because it is outside the strict allowed-file list.
