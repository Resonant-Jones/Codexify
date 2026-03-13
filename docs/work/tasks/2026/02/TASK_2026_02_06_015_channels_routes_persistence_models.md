# TASK-2026-02-06-015_channels_routes_persistence_models: Channels Routes + Persistence Models

- **Task-ID:** TASK-2026-02-06-015_channels_routes_persistence_models
- **Title:** Channels routes + persistence models (configs + allowlists + pairings + message audit)
- **Branch (expected):** `campaign/2026-02-06/loop-integrity-auth-and-defaults`
- **Commit mode:** **Two-phase**
  - **Commit A:** implementation (code + migrations + tests)
  - **Commit B:** docs finalize (this task artifact summary + campaign mapping)

## Objective

Add a minimal, auditable “channels” subsystem that:
1) Stores channel adapter configuration and allowlist/pairing state, and  
2) Persists inbound/outbound message events to a DB audit table,  
3) Exposes **auth-protected** CRUD routes for config + pairing management, plus a minimal messages list endpoint for debugging.

This is intentionally “boring but correct”: DB-backed + test-covered + minimal surface area.

## Scope

### In scope
- New `channels` routes module with CRUD for:
  - `channel_configs`
  - `channel_allowlists`
  - `channel_pairings`
  - `channel_messages` (audit log; create happens via code paths, list via route)
- SQLAlchemy models + Alembic migration(s)
- Tests for config CRUD + message persistence

### Out of scope
- Real Slack/Discord/Telegram network calls (that is Task 014).
- Real-time WS broadcasting (can be later; keep this task REST + DB).
- Complex RBAC / orgs / multi-tenant; keep to existing `X-User-Id` scoping conventions.

## Allowed files (STRICT)

Only modify/create files in this list:

- `guardian/routes/channels.py`
- `guardian/db/models.py` **or** the existing models module used for other tables in this repo (ONLY the one actually used)
- `guardian/db/migrations/versions/*.py`
- `guardian/tests/**/test_channels*.py` (create if missing)
- `docs/work/tasks/2026/02/TASK_2026_02_06_015_channels_routes_persistence_models.md`
- `docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md` (mapping update only)

If you discover the repo uses a different canonical location for models/migrations/tests, STOP and update this task artifact’s Allowed files list before editing anything else.

## Dependencies / Prereqs (run before edits)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
python --version
pytest --version || true
rg -n "include_router|APIRouter" guardian/routes || true
rg -n "alembic|migrations/versions" guardian/db guardian || true
```

Expected: working tree clean, and you can identify how routers + DB migrations are wired in this repo.

## Command checklist (deterministic)

### 1) Locate existing patterns (routes, auth dependency, DB wiring)

```bash
# find auth dependency helpers used by other routers (api key, user id)
rg -n "require_api_key|X-API-Key|X-User-Id|Depends\(" guardian/routes guardian/core guardian || true

# find where routers are registered
rg -n "include_router" guardian | head

# confirm existing migrations layout
ls -la guardian/db/migrations/versions | head

# locate existing test style / TestClient usage
rg -n "TestClient\(" guardian/tests tests || true
```

Record the discovered canonical patterns (paths + symbols) in the “Notes / Findings” section at the bottom.

### 2) Implement DB tables + models + migration

Implement the following tables with minimal columns (exact naming may adjust to existing conventions, but keep the intent):

- `channel_configs`
  - `id` (pk)
  - `user_id` (string; indexed)
  - `channel` (string; e.g., `slack`, `discord`, `telegram`)
  - `config_json` (json/text; opaque blob)
  - `created_at`, `updated_at`

- `channel_allowlists`
  - `id` (pk)
  - `user_id`
  - `channel`
  - `external_id` (string; e.g., slack user id / discord user id)
  - `label` (optional)
  - `created_at`

- `channel_pairings`
  - `id` (pk)
  - `user_id`
  - `channel`
  - `external_id`
  - `status` (string enum-ish: `pending|approved|revoked`)
  - `created_at`, `updated_at`

- `channel_messages`
  - `id` (pk)
  - `user_id`
  - `channel`
  - `direction` (`inbound|outbound`)
  - `external_id` (optional; message id)
  - `thread_id` (optional; local thread correlation)
  - `content` (text)
  - `meta_json` (json/text; optional)
  - `created_at`

Checklist:

```bash
# after implementing models + migration
git status --porcelain -uall
rg -n "channel_configs|channel_allowlists|channel_pairings|channel_messages" guardian/db guardian || true
```

### 3) Implement routes (auth-protected + user-scoped)

Implement `guardian/routes/channels.py` with an `APIRouter` and endpoints:

- `GET  /api/channels/configs` (list for user)
- `POST /api/channels/configs` (create/update per channel)
- `DELETE /api/channels/configs/{channel}` (delete config for channel)

- `GET  /api/channels/allowlist/{channel}`
- `POST /api/channels/allowlist/{channel}` (add entry)
- `DELETE /api/channels/allowlist/{channel}/{external_id}`

- `GET  /api/channels/pairings/{channel}`
- `POST /api/channels/pairings/{channel}` (create pairing request)
- `PATCH /api/channels/pairings/{channel}/{external_id}` (approve/revoke)

- `GET /api/channels/messages/{channel}` (list recent messages; bounded limit, default 50)

Rules:
- Enforce API key (same mechanism used by `/api/share` and `/api/documents/autosave`).
- Scope all reads/writes by `user_id` from headers.
- Return 404 for cross-user access when applicable (consistent with your security posture).

### 4) Tests

Add tests that verify:
- Creating a config and listing returns it for the same user.
- Other user cannot see it (expect empty list or 404 depending on endpoint shape).
- Creating a message audit record (via direct model/DB helper or route if implemented) persists and can be listed by user.
- Auth required: missing API key returns 401.

Commands:

```bash
pytest -q guardian/tests -k "channels" || true
```

If full test suite requires a DB that is unavailable locally, mark tests to use the project’s existing sqlite/test DB pattern (do not invent a new infrastructure). If that pattern is unclear, STOP and update Allowed files + checklist.

### 5) Final sanity checks

```bash
git diff --stat
git status --porcelain -uall
```

## Expected outputs (success signals)

- `pytest -q guardian/tests -k "channels"` passes (or deterministically skipped with documented reason + existing repo convention).
- A migration exists and references the new tables.
- Routes exist and are protected by the same API-key dependency used elsewhere.
- Message audit listing is bounded (default limit) and user-scoped.

## Rollback / cleanup

```bash
# revert local changes (DANGEROUS: will discard work)
git restore --staged .
git restore -- .
git clean -fd

# if you need to back out only this task’s files, use explicit paths from Allowed files
```

## Commit plan

### Commit A (implementation)

Stage only implementation + tests + migrations (NO campaign/task doc mapping updates yet):

```bash
git status --porcelain -uall
git add \
  guardian/routes/channels.py \
  guardian/db \
  guardian/tests
git commit --no-verify -m "TASK-2026-02-06-015_channels_routes_persistence_models: channels routes + db models + audit log"
git log -1 --oneline
```

### Commit B (docs finalize + mapping)

Update this task artifact with:
- commands run + outcomes
- files changed summary
- commit hashes (A + B)
Then update the campaign mapping line.

```bash
git add \
  docs/work/tasks/2026/02/TASK_2026_02_06_015_channels_routes_persistence_models.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md
git commit --no-verify -m "TASK-2026-02-06-015_channels_routes_persistence_models: docs finalize + mapping"
git log -1 --oneline
```

## Campaign mapping line (required)

In `docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md` ensure this line exists and is filled after both commits:

- `TASK-2026-02-06-015_channels_routes_persistence_models -> [6b9c4bd7, 03ffca55]`

## Notes / Findings

(Write down discovered canonical patterns here during execution.)
- Auth dependency used: `guardian.core.dependencies.require_api_key` with router-level `dependencies=[Depends(require_api_key)]` (pattern used in `guardian/routes/cron.py` and `guardian/routes/browser.py`).
- Router registration location: `guardian/guardian_api.py` for main app routers (identified via `app.include_router(...)` list); this task only adds `guardian/routes/channels.py` per scope.
- DB/migration conventions: SQLAlchemy ORM models in `guardian/db/models.py`; Alembic migrations in `guardian/db/migrations/versions/*.py` with typed `revision` and `down_revision` module variables.
- Test DB conventions: route tests create a local in-memory SQLite DB with `StaticPool` and limited table creation, then inject via route `configure_db(...)` helper (same pattern as `tests/routes/test_cron_routes.py` and `guardian/tests/realtime/test_browser_routes_ws_hooks.py`).

### Commands run + outcomes
- Commands run:
  - `python --version`
  - `pytest --version || true`
  - `rg -n "include_router|APIRouter" guardian/routes || true`
  - `rg -n "alembic|migrations/versions" guardian/db guardian || true`
  - `rg -n "require_api_key|X-API-Key|X-User-Id|Depends\\(" guardian/routes guardian/core guardian || true`
  - `rg -n "include_router" guardian | head`
  - `ls -la guardian/db/migrations/versions | head`
  - `rg -n "TestClient\\(" guardian/tests tests || true`
  - `pytest -q guardian/tests -k "channels" || true`
  - `pytest -q guardian/tests/test_channels_routes.py -q`
  - `rg -n "channel_configs|channel_allowlists|channel_pairings|channel_messages" guardian/db guardian/routes/channels.py guardian/tests/test_channels_routes.py || true`
- Outcomes:
  - Added `channel_configs`, `channel_allowlists`, `channel_pairings`, and `channel_messages` ORM models in `guardian/db/models.py`.
  - Added migration `guardian/db/migrations/versions/f4e7c1a2b3d4_add_channel_tables.py`.
  - Added auth-protected user-scoped channels router `guardian/routes/channels.py` with configs/allowlist/pairings/messages endpoints.
  - Added focused route tests in `guardian/tests/test_channels_routes.py`; targeted test run passed (`3 passed`).
  - Broader selector `pytest -q guardian/tests -k "channels" || true` hit unrelated collection error in `guardian/tests/db/test_seed.py` (`NodeClassAlreadyDefined` in Neo model registry).
  - Commit A created: `6b9c4bd7`.
  - Commit B created: `03ffca55`.
