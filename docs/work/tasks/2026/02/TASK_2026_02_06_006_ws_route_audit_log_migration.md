# TASK-2026-02-06-006_ws_route_audit_log_migration: WS Route + Audit Log Migration

- **Task-ID:** TASK-2026-02-06-006_ws_route_audit_log_migration
- **Title:** WS Route + audit log migration
- **Branch:** `campaign/2026-02-06/guardian-parity-control-plane`
- **Goal:** Productionize the WebSocket endpoint and add a DB-backed audit trail that records both success and failure.

## Scope

### In scope
- Implement (or finalize) `guardian/routes/websocket.py` as the canonical FastAPI WebSocket entrypoint.
- Add a DB model + migration for an audit log table:
  - `ws_audit_log`: `connection_id`, `identity`, `method`, `params_hash`, `status`, `duration_ms`, `created_at`
- Ensure router registration and any lifespan/startup wiring needed to make the WS route active.
- Add focused tests:
  - successful call writes an audit row
  - failed call writes an audit row with `status="error"`

### Out of scope
- New product features beyond the audit log and WS stability.
- Refactors unrelated to websocket routing, audit logging, or the minimal persistence layer required.

## Allowed files (STRICT)

Only edit files in this list:

- `guardian/routes/websocket.py`
- `guardian/guardian_api.py`
- `guardian/db/models.py` **or** the repo’s existing WS/Realtime models file (use the existing convention; do not create a new models module unless it already exists)
- `guardian/db/migrations/versions/*.py` (one new migration file for `ws_audit_log`)
- `tests/realtime/test_websocket_route_audit.py`
- `docs/work/tasks/2026/02/TASK_2026_02_06_006_ws_route_audit_log_migration.md` (this artifact, Commit B only)
- `docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md` (mapping line update, Commit B only)

If you discover required changes outside this list, STOP and escalate with evidence (path + reason).

## Dependencies / prereqs

Run these before making changes:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# locate existing websocket plumbing + router registration
rg -n "websocket|WebSocket\\b|@router\\.websocket|include_router\\(.*websocket|WS" guardian || true

# identify DB + migrations toolchain (alembic or similar)
rg -n "alembic|migrations/versions" guardian || true

# (optional) discover existing audit/event logging patterns
rg -n "audit_log|audit.*table|params_hash|sha256\\(" guardian || true
```

## Command checklist (deterministic)

### 1) Confirm current WS route shape + auth dependency

```bash
# show the websocket route file if it exists
ls -la guardian/routes | rg "websocket" || true
sed -n '1,220p' guardian/routes/websocket.py 2>/dev/null || true

# locate router registration
rg -n "include_router\\(.*websocket|from guardian\\.routes\\.websocket" guardian || true
```

**Expected output:** You can point to the exact module where routers are registered, and confirm whether the WS route is already included.

### 2) Implement WS audit log persistence

Implementation rules:
- Each WS request/command should record **exactly one** audit row, regardless of success/failure.
- `identity` should be the resolved caller identity (API key owner / user id / subject) using the existing auth mechanism.
- `params_hash` should be a deterministic hash of request params (stable JSON canonicalization). If the codebase already has a helper, reuse it.
- `duration_ms` should be measured around handler execution.

### 3) Add migration

```bash
# Confirm how migrations are created in this repo (examples)
ls -la guardian/db/migrations/versions | tail -n 10

# If alembic is used, generate a migration with a clear message (adjust command to repo conventions)
# Example (ONLY if repo uses alembic):
# alembic revision -m "add ws audit log" 
```

**Expected output:** A new migration exists under `guardian/db/migrations/versions/` that creates `ws_audit_log` with the columns listed above.

### 4) Add/adjust tests

Add tests that prove:
- A successful WS interaction writes a row with `status="ok"` (or equivalent non-error status).
- A failing WS interaction writes a row with `status="error"`.

If the repo has no WS test harness yet, prefer a unit-level approach:
- call the WS handler function(s) directly (or the underlying “message dispatch” function) with a fake connection/request context.
- assert audit insert call(s) or DB rows.

### 5) Run required checks

```bash
# backend tests (pick the narrowest test selection that covers new work)
pytest -q guardian/tests -k "websocket or ws_audit or audit_log" 
pytest -q tests/realtime/test_websocket_route_audit.py

# always show status
git status --porcelain -uall
```

**Expected output:** tests pass (or are deterministically skipped with a documented reason), and `git status` shows only intended files.

## Rollback / cleanup

If you need to abort local changes:

```bash
# discard working tree changes

git restore --staged --worktree -- \
  guardian/guardian_api.py \
  guardian/routes/websocket.py \
  guardian/db/models.py \
  tests/realtime/test_websocket_route_audit.py \
  guardian/db/migrations/versions

git status --porcelain -uall
```

If a migration was created but should be removed:

```bash
# remove the migration file explicitly (replace with the real filename)
rm -f guardian/db/migrations/versions/*ws_audit_log*.py

git status --porcelain -uall
```

## Commit mode

Two-phase commits:
- **Commit A:** implementation + tests + migration
- **Commit B:** docs finalize (this task artifact + campaign mapping)

## Commit messages (EXACT)

### Commit A (implementation)
- `TASK-2026-02-06-006_ws_route_audit_log_migration: websocket route + ws audit log persistence`

### Commit B (docs finalize + mapping)
- `TASK-2026-02-06-006_ws_route_audit_log_migration: docs finalize + mapping`

## Manual git command blocks (copy/paste)

### Commit A

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# stage ONLY allowed implementation files (adjust if your model/migration/test paths differ, but keep it strict)
git add \
  guardian/guardian_api.py \
  guardian/routes/websocket.py \
  guardian/db/models.py \
  guardian/db/migrations/versions \
  tests/realtime/test_websocket_route_audit.py

git commit --no-verify -m "TASK-2026-02-06-006_ws_route_audit_log_migration: websocket route + ws audit log persistence"

git log -1 --oneline
```

### Commit B

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  docs/work/tasks/2026/02/TASK_2026_02_06_006_ws_route_audit_log_migration.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-006_ws_route_audit_log_migration: docs finalize + mapping"

git log -1 --oneline
```

## Campaign mapping line

Update the campaign file mapping when Commit A and Commit B hashes exist:

- `TASK-2026-02-06-006_ws_route_audit_log_migration -> [55cf078d, d55fc7c9]`

## Notes / findings (fill during execution)

- **Router registration location:** `guardian/guardian_api.py` via `app.include_router(websocket_routes.router)`
- **Auth dependency used (path + symbol):** `guardian/ws/auth.py` via `authenticate_websocket()` in `guardian/routes/websocket.py`
- **Audit log model location:** `guardian/db/models.py` -> `class WSAuditLog(Base)` (`__tablename__ = "ws_audit_log"`)
- **Migration filename:** `guardian/db/migrations/versions/90d9b9177a0e_add_ws_audit_log.py`
- **Tests added/updated:** `tests/realtime/test_websocket_route_audit.py`
- **Commands run + results:**
  - `pytest -q tests/realtime/test_websocket_route_audit.py` -> pass (`2 passed`)
  - `pytest -q tests/realtime/test_websocket_auth_handshake.py tests/realtime/test_websocket_protocol_validation.py tests/realtime/test_websocket_rpc_methods.py` -> pass (`7 passed`)

## Summary

- **Commit A:** `55cf078d` (`TASK-2026-02-06-006_ws_route_audit_log_migration: websocket route + ws audit log persistence`)
- **Implementation outcome:** Canonical websocket route now persists one audit row per handled request with `status`, `params_hash`, and `duration_ms`.
- **Final mapping (pending Commit B):**
  - `TASK-2026-02-06-006_ws_route_audit_log_migration -> [55cf078d, d55fc7c9]`
