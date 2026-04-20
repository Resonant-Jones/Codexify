# Auth and Runtime Mode Audit After DB Reset

**Date:** 2026-04-20
**Type:** Read-only architecture and runtime-boundary audit
**Scope:** Auth, runtime-mode, and Alembic state after a fresh database wipe

---

## Summary

This audit investigates why Guardian may resolve or accept a human-facing identity string as `user_id` after a DB reset, and whether the current migration/auth/runtime-mode state is coherent. Three concrete findings emerge:

1. **Alembic has two unmerged heads** (`a5b6c7d8e9f0` and `f2b3c4d5e6f8`), which is an accidental fork — not an expected merge topology. A fresh DB bootstrap cannot apply all migrations without a merge migration.
2. **In single-user mode, a human-facing `X-User-Id` header can flow into persistent ownership fields** (`chat_threads.user_id`, `chat_messages.user_id`, etc.) when `DEBUG` or `LOCAL_DEV` environment flags are enabled. This is by design in `guardian/core/dependencies.py:369-374` but creates a conflation risk between display labels and canonical ownership identifiers.
3. **The intended runtime mode after a fresh DB bootstrap is `single_user`** (`CODEXIFY_MULTI_USER_ENABLED` defaults to `False` in `guardian/core/config.py:101-105`). The canonical seed user is `users(id="local", username="local")`, created both by migration `f2b3c4d5e6f8` and by startup code in `guardian_api.py:638`.

The current auth/session path is internally consistent for single-user mode, but the multi-head Alembic state blocks any clean bootstrap and must be resolved before multi-user work can proceed.

---

## ADR Impact

- **Classification:** Aligned with existing ADR(s)
- **Governing ADRs:**
  - **ADR-005: Runtime Mode and Account Boundary Invariants** (`docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md`) — defines `single_user` vs `multi_user` modes, bootstrap-only mode selection, and the AccountBoundary concept.
  - **ADR-003: Message Identity vs Request Identity** — relevant to the distinction between `user_id` as a request-time identity claim vs a persistent ownership field.
  - **ADR-002: Dual State Machine Model** — relevant to the separation of provider runtime state from request execution state.
- **Brief reason:** This audit does not silently change architecture. It determines whether current behavior aligns with accepted runtime-mode and ownership doctrine. The multi-head Alembic state is a structural concern that affects the bootstrap contract defined in ADR-005.

---

## Current-Truth Anchors

### What is true now about supported local-beta runtime
- **Proved by code:** `CODEXIFY_LOCAL_ONLY_MODE=true` and `ALLOW_CLOUD_PROVIDERS=false` are the default in `guardian/core/config.py:95-100`. The supported path is local Docker Compose with local-only provider policy.
- **Proved by code:** `CODEXIFY_MULTI_USER_ENABLED` defaults to `False` (`guardian/core/config.py:101-105`), meaning the current supported runtime is single-user.

### What is true now about DB bootstrap after wipe
- **Proved by code:** Migration `f2b3c4d5e6f8` (`guardian/db/migrations/versions/f2b3c4d5e6f8_add_user_id_to_core_entities.py:46-52`) inserts `INSERT INTO users (id, username, created_at) VALUES ('local', 'local', NOW()) ON CONFLICT (id) DO NOTHING`.
- **Proved by code:** `guardian_api.py:638` calls `get_or_create_default_user(guardian_db)` at startup, which creates `User(id="local", username="local")` via `guardian/core/user_manager.py:38-46`.
- **Proved by code:** The `users` table is created by migration `f2b3c4d5e6f7` which depends on `e3f2a1b4c5d6` (authenticated_principals table).

### What is true now about ownership fields and account boundaries
- **Proved by code:** `chat_threads.user_id` has a FK to `users.id` with `ondelete="CASCADE"` (`guardian/db/models.py:309-311`).
- **Proved by code:** `chat_messages.user_id` has a FK to `users.id` with `ondelete="CASCADE"` (`guardian/db/models.py:384-386`).
- **Proved by code:** `projects.user_id` has a FK to `users.id` (`guardian/db/models.py:114-116`).
- **Proved by code:** In single-user mode, `get_request_user_scope()` returns `RequestUserScope(user_id=get_request_user_id(...), subject_id=None, account_id=None, multi_user_enabled=False)` (`guardian/core/dependencies.py:426-431`).
- **Proved by code:** `get_request_user_id()` returns the `X-User-Id` header value when `DEBUG` or `LOCAL_DEV` is enabled, otherwise falls back to `get_single_user_id()` which returns `CODEXIFY_SINGLE_USER_ID` env var or `"local"` (`guardian/core/dependencies.py:339-379`).

### What is not yet true about release-readiness of multi-user auth
- **Proved by code:** `CODEXIFY_MULTI_USER_ENABLED` defaults to `False`. Multi-user mode requires `AuthenticatedPrincipal` rows mapping `subject_id` to `account_id` (`guardian/db/models.py` AuthenticatedPrincipal model, `guardian/core/dependencies.py:301-336`), but no seed data or bootstrap path for these rows exists in the current codebase.
- **Working theory:** Multi-user auth is not release-ready because there is no login/register UI, no session/JWT issuance path, and no default `AuthenticatedPrincipal` seed data.

### What this audit may and must not assume
- **May assume:** The `users` table and `user_id` FK columns on core entities are the intended canonical ownership model.
- **Must not assume:** That the current multi-head Alembic state is intentional. It is an accidental fork with no merge migration.
- **Must not assume:** That `X-User-Id` header conflation with `user_id` is safe in production. It is only gated behind `DEBUG`/`LOCAL_DEV` flags.

---

## Invariants

1. **Runtime mode is a bootstrap-level contract, not an incidental request-time side effect.** — `CODEXIFY_MULTI_USER_ENABLED` is read at module load time in `dependencies.py:225-230`, not per-request.
2. **Display names and canonical ownership identifiers must not be conflated without an explicit contract.** — The `X-User-Id` → `user_id` path in single-user mode with `DEBUG` enabled violates this invariant by allowing arbitrary strings into `chat_threads.user_id`.
3. **Persistent ownership fields must not accept ad hoc human-facing identifiers unless that is the intentional canonical account model.** — The `users` table with `id` as a `String(255)` primary key (`guardian/db/models.py:55`) means any string can be a valid `user_id` if the FK constraint is satisfied.
4. **A fresh DB wipe changes bootstrap state, not architecture intent.** — The architecture intent (ADR-005) remains `single_user` by default.
5. **The audit must preserve the distinction between single-user local mode and true multi-user mode.** — The code paths are distinct: `get_request_user_scope()` branches on `_multi_user_mode_enabled()` (`dependencies.py:393-431`).
6. **The audit must not recommend silent architecture drift.** — All findings are tied to specific code paths.

---

## Evidence

### Exact commands run for read-only inspection

```
python -m alembic -c backend/alembic.ini heads
  → a5b6c7d8e9f0 (head)
  → f2b3c4d5e6f8 (head)

python -m alembic -c backend/alembic.ini current
  → Failed: DATABASE_URL not configured (expected — no running DB)

python -m alembic -c backend/alembic.ini history
  → Full migration graph confirmed (see analysis below)

git diff --check
  → Clean (no whitespace errors)
```

### Exact Alembic inspection results

**Two heads detected:**
- `a5b6c7d8e9f0` — "add capability grants foundation" (depends on `e3f2a1b4c5d6`)
- `f2b3c4d5e6f8` — "assign user ownership to core entities" (depends on `f2b3c4d5e6f7` → `e3f2a1b4c5d6`)

**Branch point:** `e3f2a1b4c5d6` — "add authenticated principals table" is a branchpoint with two downstream paths:
- Path A: `e3f2a1b4c5d6` → `f2b3c4d5e6f7` (users table) → `f2b3c4d5e6f8` (user_id on core entities) — **HEAD**
- Path B: `e3f2a1b4c5d6` → `a5b6c7d8e9f0` (capability grants foundation) — **HEAD**

**No merge migration exists** between these two heads. This is an **accidental fork**.

**The rest of the migration graph is well-structured** with proper merge migrations at earlier branchpoints (e.g., `d4b7f1a9c3e2`, `e9a4c1b8d2f7`, `83c2f0bb0dfa`, `c7a253a50757`).

### Exact request-identity resolution path in backend code

**Single-user mode path** (`guardian/core/dependencies.py:339-379`):
1. `get_request_user_id()` is called with `X-User-Id` header, `Authorization` header, and `gc_session` cookie.
2. If `_multi_user_mode_enabled()` is `False` (default):
   - If `X-User-Id` is present AND (`DEBUG` or `LOCAL_DEV` is `True`): return the `X-User-Id` value as-is.
   - Otherwise: return `get_single_user_id()` which reads `CODEXIFY_SINGLE_USER_ID` env var or defaults to `"local"`.

**Multi-user mode path** (`guardian/core/dependencies.py:354-366`):
1. Requires authenticated subject from `Authorization` bearer token or `gc_session` cookie.
2. Looks up `account_id` from `authenticated_principals` table by `subject_id`.
3. Returns `account_id` as the `user_id`.
4. Returns 401 if no authenticated subject or no account mapping exists.

**Request scope path** (`guardian/core/dependencies.py:382-431`):
- Single-user: `RequestUserScope(user_id=get_request_user_id(...), subject_id=None, account_id=None, multi_user_enabled=False)`
- Multi-user: `RequestUserScope(user_id=account_id, subject_id=subject_id, account_id=account_id, multi_user_enabled=True)`

### Exact frontend/session/request path that can inject `user_id`

**Frontend API layer** (`frontend/src/lib/api.ts:198-223`):
- `applyAuthHeaders()` sets `Authorization: Bearer <token>` if a stored auth token exists, otherwise sets `X-API-Key` from runtime/dev API key.
- **No `X-User-Id` header is set by the frontend API layer.** The frontend does not inject `X-User-Id` into chat completion requests.

**Command bus invoke** (`frontend/src/lib/api.ts:392-405`):
- `invokeCommandBus()` sets `X-User-Id: payload.actor.id` — this is the only frontend path that explicitly sets `X-User-Id`.

**SessionSpine** (`frontend/src/state/session/SessionSpine.ts:445-467`):
- `SessionSpine` is constructed with a `userId` config parameter.
- The `userId` is used for session state storage keys (`${userId}:${deviceId}`) and for persisted state.
- **The `userId` is NOT sent as an HTTP header to the backend.** It is purely a frontend session concern.

**Conclusion:** The frontend does not inject `X-User-Id` into chat requests. The only path for `X-User-Id` to reach the backend is through direct API calls (e.g., curl, Postman, or the command bus invoke path).

### Exact expected bootstrap/default user behavior

**Migration-level** (`guardian/db/migrations/versions/f2b3c4d5e6f8_add_user_id_to_core_entities.py:46-52`):
```sql
INSERT INTO users (id, username, created_at)
VALUES ('local', 'local', NOW())
ON CONFLICT (id) DO NOTHING
```

**Startup-level** (`guardian_api.py:638`, `guardian/core/user_manager.py:19-52`):
```python
get_or_create_default_user(guardian_db)
# Creates: User(id="local", username="local", created_at=<now>)
```

**After a clean DB wipe and migration/bootstrap, the only expected user row is:**
- `users(id="local", username="local", created_at=<timestamp>)`

**No `authenticated_principals` rows are created automatically.** The `e3f2a1b4c5d6` migration only creates the table structure.

### Explicit statement on multi-head Alembic state

**The two-head state (`a5b6c7d8e9f0` and `f2b3c4d5e6f8`) is SUSPICIOUS and likely accidental.** There is no merge migration joining these two branches. Both branches descend from `e3f2a1b4c5d6` (authenticated_principals table) but diverge:
- The auth/identity branch (`f2b3c4d5e6f7` → `f2b3c4d5e6f8`) adds the `users` table and backfills `user_id` on core entities.
- The capability grants branch (`a5b6c7d8e9f0`) adds `capability_tiers` and `capability_grants` tables.

A fresh `alembic upgrade head` on an empty database would fail because Alembic cannot resolve which head to apply when there are multiple heads with no merge migration.

---

## Findings

### Finding 1: Multi-head Alembic state blocks clean bootstrap
- **Severity:** High
- **Evidence:** `alembic heads` returns two heads. No merge migration exists.
- **Impact:** A fresh DB wipe + `alembic upgrade head` will fail. The `migrator` service in Docker Compose will not start cleanly.
- **File:** `guardian/db/migrations/versions/` — no merge migration after `a5b6c7d8e9f0` and `f2b3c4d5e6f8`.

### Finding 2: `X-User-Id` header can flow into persistent ownership in single-user mode with debug flags
- **Severity:** Medium
- **Evidence:** `guardian/core/dependencies.py:369-374` — when `DEBUG` or `LOCAL_DEV` is `True`, any `X-User-Id` header value is returned as the effective `user_id`.
- **Impact:** If `DEBUG=true` and a caller sends `X-User-Id: "John Doe"`, then `chat_threads.user_id = "John Doe"` will be persisted. This violates the invariant that display names and canonical ownership identifiers must not be conflated.
- **Mitigation present:** The debug flag gate (`_allow_user_header_override()`) prevents this in production. But it is a latent risk during local development.

### Finding 3: Frontend does not inject `X-User-Id` into chat requests
- **Severity:** Low (positive finding)
- **Evidence:** `frontend/src/lib/api.ts` — the Axios interceptor sets `Authorization` or `X-API-Key` but never `X-User-Id`. The only exception is `invokeCommandBus()` which sets `X-User-Id: payload.actor.id`.
- **Impact:** Stale frontend session state cannot inject a stale `user_id` into chat requests. The `SessionSpine.userId` is purely a frontend concern.

### Finding 4: No `AuthenticatedPrincipal` seed data exists
- **Severity:** Medium (for multi-user readiness)
- **Evidence:** Migration `e3f2a1b4c5d6` creates the `authenticated_principals` table but inserts no rows. No startup code creates seed principal mappings.
- **Impact:** If `CODEXIFY_MULTI_USER_ENABLED=true` is set on a fresh DB, all requests will fail with 401 because no subject→account mapping exists.

### Finding 5: `users` table FK is the canonical ownership boundary
- **Severity:** Informational (confirming design intent)
- **Evidence:** `chat_threads.user_id`, `chat_messages.user_id`, `projects.user_id`, `memory_entries.user_id`, `uploaded_documents.user_id` all have FK to `users.id` with `ondelete="CASCADE"`.
- **Impact:** The schema is consistent with ADR-005's AccountBoundary concept. All core entities are owned by a `users.id`.

### Finding 6: Single-user mode is internally consistent
- **Severity:** Informational (confirming design intent)
- **Evidence:** In single-user mode, `get_request_user_scope()` returns `user_id` from `get_single_user_id()` (defaulting to `"local"`), which matches the seed user created by migration and startup code.
- **Impact:** The single-user path is coherent. The `"local"` user exists, and all requests resolve to it.

### Finding 7: Browser storage cannot inject stale identity into backend requests
- **Severity:** Low (positive finding)
- **Evidence:** `SessionSpine` stores `userId` in browser storage for session state persistence, but this value is never sent as an HTTP header. The frontend API layer uses `Authorization` or `X-API-Key` for auth.
- **Impact:** After a DB wipe, the browser may have stale session state, but it cannot cause the backend to use a stale `user_id` for ownership.

---

## Most Likely Root Cause

**The immediate cause of any `user_id` resolution confusion after a DB reset is the multi-head Alembic state.** If migrations cannot be applied cleanly, the `users` table may not exist, which means:

1. FK constraints on `chat_threads.user_id`, `chat_messages.user_id`, etc. will fail.
2. The `get_or_create_default_user()` startup call will fail silently (caught by `guardian_api.py:639-641`).
3. Any request that tries to persist data with `user_id="local"` will fail with a FK violation.

If migrations *do* apply (e.g., on an existing DB that was already past the branchpoint), then the system works correctly in single-user mode with `user_id="local"`.

**Secondary cause:** If `DEBUG=true` or `LOCAL_DEV=true` is set, any `X-User-Id` header value flows through to persistent ownership fields. This is by design but creates a conflation risk.

---

## Not Yet Proven

1. **Whether the multi-head Alembic state is intentional or accidental.** — The migration history shows careful merge migrations at earlier branchpoints, suggesting the current two-head state is an oversight. But only the author of `a5b6c7d8e9f0` can confirm intent.
2. **Whether `alembic upgrade head` fails on a truly empty database.** — Cannot be proven without a running Postgres instance. The `current` command failed due to missing `DATABASE_URL`, which is expected in this audit context.
3. **Whether the `capability_grants` tables (`a5b6c7d8e9f0`) are wired into any runtime path.** — The ORM models exist (`CapabilityGrant`, `CapabilityTier` in `guardian/db/models.py`), but no route or service code was found that reads or writes these tables during this audit.
4. **Whether `AuthenticatedPrincipal` rows are ever created at runtime.** — The `_resolve_account_id_for_subject()` function in `dependencies.py:301-336` reads from this table, but no code path was found that inserts rows into it. This suggests multi-user mode is structurally incomplete.

---

## Recommended Immediate Path

**Restore coherent single-user local mode first.** The multi-head Alembic state must be resolved before any multi-user bootstrap can proceed.

1. **Create a merge migration** that joins `a5b6c7d8e9f0` and `f2b3c4d5e6f8` into a single head. This is a no-op migration (empty `upgrade()`/`downgrade()`) that simply declares both revisions as `down_revision`.
2. **Verify clean bootstrap** on an empty database: `docker compose down -v && docker compose up --build` should succeed with all migrations applied.
3. **Confirm single-user coherence:** After bootstrap, verify that `users` table contains exactly one row (`id="local"`), and that chat completion works with `user_id="local"` on all persisted entities.
4. **Defer multi-user bootstrap** until the merge migration is applied and single-user mode is proven on the current branch tip.

---

## Recommended Follow-Up Implementation Tasks

1. **Create Alembic merge migration** for heads `a5b6c7d8e9f0` and `f2b3c4d5e6f8`.
   - Files: `guardian/db/migrations/versions/<new_rev>_merge_auth_and_capability_heads.py`
   - `down_revision = ("a5b6c7d8e9f0", "f2b3c4d5e6f8")`
   - Empty `upgrade()`/`downgrade()`.

2. **Add `AuthenticatedPrincipal` seed data for multi-user readiness.**
   - When `CODEXIFY_MULTI_USER_ENABLED=true` on a fresh DB, create a default principal mapping: `subject_id="local"`, `account_id="local"`.
   - Files: `guardian/core/user_manager.py` or a new `guardian/core/principal_bootstrap.py`.

3. **Audit `X-User-Id` header usage across all routes.**
   - Confirm that only `get_request_user_id()` and `get_request_user_scope()` consume this header.
   - Consider renaming the debug flag to something more explicit (e.g., `ALLOW_USER_ID_HEADER_OVERRIDE`).

4. **Add startup-time migration coherence check.**
   - In `guardian_api.py` startup, verify that `alembic heads` returns exactly one head. Log a warning if multiple heads are detected.

5. **Wire `capability_grants` into a runtime path or quarantine the tables.**
   - If `CapabilityGrant`/`CapabilityTier` are intended for future use, document that in an ADR.
   - If they are orphaned, add a drop migration.

---

## Documentation Follow-Through

- **`docs/architecture/00-current-state.md`:** No update required. The current-state file correctly describes single-user mode as the default and does not claim multi-user readiness.
- **`docs/architecture/README.md`:** This audit note should be added to the KB map as a reference for future auth/runtime-mode work.
- **Other architecture docs:** No updates required. The findings confirm that the existing docs (ADR-005, identity-and-runtime-mode.md, chat-runtime-contract.md) accurately describe the intended architecture. The gap is in migration graph coherence, not in documentation.

---

## Validation

```
git diff --check
  → Clean (no whitespace errors)

python -m alembic -c backend/alembic.ini heads
  → a5b6c7d8e9f0 (head)
  → f2b3c4d5e6f8 (head)
  → TWO HEADS DETECTED — merge migration required

python -m alembic -c backend/alembic.ini current
  → Failed: DATABASE_URL not configured (expected — no running DB in audit context)

python -m alembic -c backend/alembic.ini history
  → Full migration graph confirmed. Two-head state verified. All earlier merge migrations present.

No automated tests apply — this is a read-only audit with no code changes.
```

---

## Files Examined (Non-Exhaustive)

| File | Role in Audit |
|------|---------------|
| `guardian/core/dependencies.py` | Auth mode resolution, `get_request_user_id()`, `get_request_user_scope()`, `_multi_user_mode_enabled()` |
| `guardian/core/config.py` | `CODEXIFY_MULTI_USER_ENABLED` default, settings model |
| `guardian/core/db.py` | GuardianDB adapter, `_default_user_id()`, project/thread/message persistence |
| `guardian/core/pgdb.py` | PgDB adapter, `_default_user_id()`, thread/message persistence |
| `guardian/core/user_manager.py` | `get_or_create_default_user()` — seed user creation |
| `guardian/guardian_api.py` | Startup lifecycle, `get_or_create_default_user()` call, router inclusion |
| `guardian/routes/chat.py` | `_request_account_id()`, `_resolve_thread_owner_hint()`, `_scope_query_user_id()` |
| `guardian/db/models.py` | `User`, `ChatThread`, `ChatMessage`, `Project`, `MemoryEntry` — all with `user_id` FK |
| `guardian/db/migrations/versions/f2b3c4d5e6f7_add_users_table.py` | Creates `users` table |
| `guardian/db/migrations/versions/f2b3c4d5e6f8_add_user_id_to_core_entities.py` | Adds `user_id` columns, backfills with `"local"`, creates FKs |
| `guardian/db/migrations/versions/e3f2a1b4c5d6_add_authenticated_principals_table.py` | Creates `authenticated_principals` table (branchpoint) |
| `guardian/db/migrations/versions/a5b6c7d8e9f0_add_capability_grants_foundation.py` | Creates `capability_tiers`, `capability_grants` tables (second head) |
| `frontend/src/lib/api.ts` | Axios interceptor, auth header injection, `invokeCommandBus()` |
| `frontend/src/lib/runtimeConfig.ts` | Runtime config resolution, auth mode coercion |
| `frontend/src/state/session/SessionSpine.ts` | Session state management, `userId` config, browser storage |
| `docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md` | ADR-005 — runtime mode contract |
| `docs/architecture/identity-and-runtime-mode.md` | Runtime mode invariants document |
| `docs/architecture/00-current-state.md` | Current operational state |
