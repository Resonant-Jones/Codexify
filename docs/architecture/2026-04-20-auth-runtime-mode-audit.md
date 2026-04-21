# Auth and Runtime Mode Audit After DB Reset

## Summary
This audit is read-only. It checks why Guardian can still resolve or accept a human-facing identity string as `user_id` after a database wipe, and whether auth, runtime mode, and Alembic state still cohere.

The current branch still behaves like a single-user local runtime by default. The backend accepts request-scoped `user_id` from the chat client in that mode, and the current chat UI is sending a browser-held display label as that field. That is the direct seam that can place a human-facing string into persistent ownership columns.

The live database is stamped at both Alembic heads. That state is real and worth tracking, but it is not the proximate cause of the `user_id` leakage observed here.

No code, migrations, or runtime behavior were changed in this audit.

## ADR impact
- Classification: Aligned with existing ADR(s)
- Governing ADRs: ADR-005 runtime mode and account boundary invariants, plus the current identity/runtime contracts that distinguish request identity from canonical ownership
- Brief reason: this is an audit only. It does not alter architecture, but it verifies whether the observed behavior still matches the accepted runtime-mode and ownership doctrine.

## Current-truth anchors
- Supported local-beta runtime on this branch is still `single_user` by default. `guardian/core/config.py:101-105` keeps `CODEXIFY_MULTI_USER_ENABLED=false`.
- After a fresh DB bootstrap, the only automatically seeded canonical user row is `users(id="local", username="local")`. Startup calls `get_or_create_default_user()` in `guardian/guardian_api.py:637-641`, and `guardian/core/user_manager.py` hard-codes `"local"` as the seed identity.
- Ownership fields are modeled as canonical `users.id` foreign keys, not as display labels. `guardian/db/models.py` shows that `projects.user_id` and the chat tables point at `users.id`.
- Multi-user auth is not release-ready on this branch. The runtime code requires a stable authenticated subject and a principal mapping in multi-user mode, but there is no scanned bootstrap path that seeds canonical `authenticated_principals` rows.
- This audit assumes the backend container, Postgres, and browser storage are separate runtime boundaries. It must not assume that a DB wipe also clears browser localStorage or sessionStorage.

## Invariants
1. Runtime mode is a bootstrap-level contract, not an incidental request-time side effect.
2. Display names and canonical ownership identifiers must not be conflated without an explicit contract.
3. Persistent ownership fields must not accept ad hoc human-facing identifiers unless that is the intentional canonical account model.
4. A fresh DB wipe changes bootstrap state, not architecture intent.
5. The audit must preserve the distinction between single-user local mode and true multi-user mode.
6. The audit must not recommend silent architecture drift.

## Evidence
### Commands run
- `git diff --check`
- `docker compose ps`
- `docker compose exec backend python -m alembic -c backend/alembic.ini heads`
- `docker compose exec backend python -m alembic -c backend/alembic.ini current`
- `docker compose exec backend python -m alembic -c backend/alembic.ini history`
- `rg -n` and `nl -ba` reads over `guardian/core/config.py`, `guardian/core/dependencies.py`, `guardian/core/user_manager.py`, `guardian/core/db.py`, `guardian/guardian_api.py`, `guardian/routes/chat.py`, `guardian/routes/admin.py`, `guardian/db/models.py`, `guardian/db/migrations/versions/`, and the frontend auth/chat/session files

### Alembic results
- `heads` returned two heads: `a5b6c7d8e9f0 (head)` and `f2b3c4d5e6f8 (head)`.
- `current` in the backend container returned the same two heads, so the live database in this workspace is already stamped at both heads.
- `history` shows both heads branch from `e3f2a1b4c5d6`:
  - `e3f2a1b4c5d6 -> a5b6c7d8e9f0`
  - `e3f2a1b4c5d6 -> f2b3c4d5e6f7 -> f2b3c4d5e6f8`

### Exact backend identity resolution path
- `guardian/core/dependencies.py:339-379`
  - In single-user mode, `X-User-Id` is only honored when explicit debug/local-dev override flags are enabled.
  - Otherwise `get_request_user_id()` falls back to the configured single-user identity.
- `guardian/core/dependencies.py:382-431`
  - In multi-user mode, the request must carry an authenticated subject and a stable account mapping.
  - In single-user mode, the request scope keeps `multi_user_enabled=False` and reuses the single-user fallback identity.
- `guardian/routes/chat.py:146-159`
  - `_resolve_thread_owner_hint()` returns the request payload `user_id` in single-user mode and enforces authenticated account identity only in multi-user mode.
- `guardian/routes/chat.py:2183-2238`
  - `chat_create_thread()` reads `payload.get("user_id")` and persists the resolved value to the thread record and audit log.

### Exact frontend path that can inject a human-facing identity into `user_id`
- `frontend/src/components/persona/layout/AppShell.tsx:981-992`
  - `userName` is read from and written back to `localStorage` as `cfy.userName`.
- `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx:332-345`
  - `SessionSpine` is keyed by `userId: (userName || "default").trim() || "default"`.
- `frontend/src/features/chat/GuardianChat.tsx:2525-2537`
  - New thread creation posts `user_id: normalizedUserId`, and `normalizedUserId` is derived from `userName`.
- `frontend/src/features/chat/GuardianChat.tsx:2651-2730`
  - Message creation also posts `user_id: normalizedUserId`, so the same browser-held label can flow into persisted chat ownership for new turns.
- `frontend/src/components/settings/SettingsView.tsx:156-160`
  - ChatGPT import uploads still set `X-User-Id: userName || "user"`.
- `frontend/src/lib/authState.ts:55-77`
  - Auth state is read from `sessionStorage` under `guardian.auth.token`, so browser auth state survives a DB wipe.

### Exact bootstrap/default user behavior
- `guardian/core/user_manager.py:11-52`
  - The default user id resolves to `"local"`, and the helper creates `User(id="local", username="local")` when missing.
- `guardian/guardian_api.py:637-641`
  - Startup calls `get_or_create_default_user(guardian_db)`.
- `guardian/core/db.py:47-51`, `guardian/core/db.py:134-149`, `guardian/core/db.py:552-589`
  - The DB adapter also collapses missing `user_id` to `"local"` when creating projects and messages.
- `guardian/db/migrations/versions/f2b3c4d5e6f7_add_users_table.py:1-32`
  - Creates the `users` table.
- `guardian/db/migrations/versions/f2b3c4d5e6f8_add_user_id_to_core_entities.py:1-118`
  - Seeds `users('local','local')` and backfills `user_id` on the core ownership tables to `local`.

### Exact multi-head interpretation
- The Alembic graph is a real dual-head graph, not a single-head merge topology.
- The live DB currently tolerates that state because it is already stamped at both heads.
- I did not prove from code alone whether this fork was intentionally preserved or simply left unresolved.
- For auth/runtime-mode work, it is a maintenance concern, but it is not the proximate source of the `user_id` issue.

### Validation results
- `git diff --check` passed.
- `python -m alembic -c backend/alembic.ini heads`, `current`, and `history` were validated through the backend container and returned the dual-head state described above.
- No automated tests apply.

## Findings
1. Chat thread and message creation still allow a human-facing browser label to become persistent ownership in single-user mode.
   - `frontend/src/features/chat/GuardianChat.tsx:2525-2537` and `:2651-2730` derive `user_id` from `userName`.
   - `guardian/routes/chat.py:2183-2238` persists that request value when multi-user mode is off.
   - This is the direct seam that can place a display label into `chat_threads.user_id` and related chat ownership fields.

2. Browser state can survive a DB wipe and keep feeding stale identity into new requests.
   - `frontend/src/components/persona/layout/AppShell.tsx:981-992` persists `cfy.userName` in localStorage.
   - `frontend/src/state/session/SessionSpine.ts:63-74` keys frontend session state by that same `userId`.
   - `frontend/src/lib/authState.ts:55-77` keeps auth state in sessionStorage.
   - A DB wipe does not clear either browser storage area.

3. The auth path is coherent for single-user local mode, but multi-user bootstrap is still incomplete.
   - `guardian/core/config.py:101-105` keeps multi-user disabled by default.
   - `guardian/core/dependencies.py:339-431` requires authenticated subject plus stable account mapping only when multi-user is enabled.
   - `guardian/routes/admin.py:240-305` mints a session subject `"web"`, but the scanned code does not show a canonical principal-seeding flow for `authenticated_principals`.

4. The Alembic graph is a real multi-head fork and should be treated as a maintenance item, not the proximate cause of the ownership leak.
   - `heads`, `current`, and `history` all show the same dual-head state.
   - The live DB is already at both heads, so this fork is operationally tolerated right now.

## Most likely root cause
The proximate cause is the UI-label-to-ownership seam, not the migration graph.

In the current single-user posture, the frontend stores `userName` in browser localStorage and reuses it as the `user_id` field for chat thread and message creation. The backend chat route accepts that request field in single-user mode and writes it into persistent ownership. Because browser storage survives a DB wipe, any stale display label can continue to flow into `chat_threads.user_id` after the database is reset.

The dual-head Alembic state is separate. It is real and should be normalized, but the live database already carries both heads, so it is not the immediate explanation for why a human-facing identity string can still land in ownership fields.

## Not yet proven
1. Whether the operator environment that triggered the bad write had `DEBUG` or `LOCAL_DEV` enabled.
2. Whether clearing browser localStorage and sessionStorage on the same machine would eliminate the symptom immediately.
3. Whether any other frontend surfaces besides chat, import, or command-bus flows also treat `userName` as canonical identity.
4. Whether the dual-head Alembic graph was intentionally preserved as a branchpoint or left unresolved by accident.

## Recommended immediate path
1. Keep the branch on coherent `single_user` local mode first.
2. Stop treating the display label `userName` as a canonical ownership identifier in chat payloads.
3. Defer multi-user bootstrap until there is a real canonical principal path that does not depend on browser UI state.
4. Normalize the Alembic branch topology separately, after the identity seam is clarified.

## Recommended follow-up implementation tasks
1. Split display label from ownership identity in the frontend chat path.
   - Files: `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/lib/api.ts`

2. Make backend chat ownership reject or normalize ad hoc `user_id` when multi-user mode is disabled.
   - Files: `guardian/routes/chat.py`, `guardian/core/dependencies.py`, `guardian/core/db.py`

3. Add an explicit canonical principal bootstrap path for multi-user mode, or keep multi-user fail-closed until one exists.
   - Files: `guardian/core/user_manager.py`, `guardian/guardian_api.py`, `guardian/db/migrations/versions/`

4. Add regression coverage for stale browser state after DB reset and for the current dual-head Alembic expectation.
   - Files: frontend tests around chat/session bootstrap and migration checks under `tests/`
