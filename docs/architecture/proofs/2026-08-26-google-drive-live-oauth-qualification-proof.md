# Google Drive Live OAuth Qualification Proof

Date: 2026-08-26

## Result

**BLOCKED — GOOGLE REJECTED THE AUTHORIZATION-CODE EXCHANGE; CALLBACK SUCCESS (REQUIREMENT 18) IS NOT PROVEN**

Real Google consent was obtained and the browser reached the canonical
`/api/connect/google-drive/callback` route, but the server-side
authorization-code exchange was rejected by Google's token endpoint. The
canonical Connection Instance therefore did **not** reach `connected`, no
credential material was persisted, and `GOOGLE DRIVE OAUTH PASS` is not
claimed.

Bounded sub-classification recorded by the canonical implementation:

`google_drive_authorization_failed`

Bounded operator-configuration finding (see "Bounded blocker classification"):

`NODE_OAUTH_CLIENT_SECRET_IS_STRUCTURALLY_MALFORMED`

This receipt records live authorization evidence only. It records no Drive
search, no Google Docs read, no Command Bus invocation, no Google write, no
migration, and no release-truth change.

## Source identity

| Item | Value |
| --- | --- |
| Worktree | `/Volumes/Dev_SSD/Codexify-main` |
| Branch | `main` |
| `QUALIFICATION_SOURCE` | `cc78c58f1ac81d92f458620ff9d4eefd337c5368` |
| `origin/main` observed once at task start | `7ea8bb4ed4422c491c4d3001decbf4ef7b4eba8a` |
| Rebase or merge in this task | none |

The delta from the qualification source to the observed `origin/main` contains
only `docs/` and `tests/` paths. No non-test, non-doc file differs. The only
seam-adjacent files are `tests/migration/test_alembic_revision_uniqueness.py`
and `tests/migration/test_d6_compatibility_bridge.py`, whose diff adds
assertions (canonical head constant plus Watchdog `down_revision` lineage
checks) and changes no migration, OAuth, identity/auth, Connections,
persistence, or Google routing implementation. Qualification therefore
continued on the frozen source that drives the running stack, and the moving
proof-only tip was not chased.

## Qualifying database identity

| Item | Evidence |
| --- | --- |
| Container | `codexify-db-1` (id `eff2e68e64fd`) |
| Compose project | `codexify` |
| Compose working dir | `/Volumes/Dev_SSD/Codexify-main` |
| Config files | `docker-compose.yml`, `docker-compose.override.yml` |
| Durable volume | `codexify_pg_data` |
| Containers referencing that volume | exactly one (`codexify-db-1`) |
| Engine | PostgreSQL 15.18 |
| Tester exclusion | `codexify_tester` project / `codexify_tester_pg_data` volume is a separate substrate and was not touched |
| Published port | `0.0.0.0:5433 -> 5432` |

This is the same dedicated qualifying substrate proven by
[`2026-08-26-google-drive-qualifying-database-migration-proof.md`](./2026-08-26-google-drive-qualifying-database-migration-proof.md)
(recorded there as container `codexify-db-1`, sole durable volume
`codexify_pg_data`, one container reference, tester explicitly excluded). It is
not `codexify_tester`.

| Requirement | Observed | Result |
| --- | --- | --- |
| Alembic revision before | `9c66e490a42b` | pass |
| `users` | `1` | pass |
| `projects` | `1` | pass |
| public base tables | `107` | consistent with the migration receipt's 106 + `notion_connection_credentials` |

No migration, stamp, DDL, or schema operation was performed by this task.

## Existing-row classification

One pre-existing `oauth_connections` row was read read-only. Only bounded
authority fields were inspected; nothing was decrypted and no ciphertext was
read or emitted.

| Bounded field | Observed |
| --- | --- |
| row id | `1` |
| owner (`user_id`) | `local` |
| canonical local user (`users.id`, sole row) | `local` |
| owner equality | **equal** |
| provider | `google_drive` |
| mode | `node_local` |
| status | `pending` |
| scopes | exactly `drive.metadata.readonly` + `documents.readonly` |
| encrypted access token | **null** |
| encrypted refresh token | **null** |
| expiry | null |
| `last_refresh_at` | null |
| `last_error` | null |
| `relay_grant_id` | null |
| created / updated | identical timestamps (`2026-08-26 17:27:18Z`) |

All PASS conditions in the task's classification gate held:

`PREEXISTING_GOOGLE_DRIVE_ROW = ABANDONED_PENDING_OAUTH_STATE`

The row was **preserved**, not deleted. No pre-existing usable or ambiguous
Google credential existed to be silently adopted. None of the four blocking
dispositions applied: no credential material, not `connected`, correct owner,
and no ambiguous state.

Legacy Google authority pre-state:

| Query | Count |
| --- | ---: |
| `provider = 'google'` rows of any status | `0` |
| `provider = 'google'` active (`pending`/`connected`/`error`) | `0` |
| `provider = 'google_drive'` rows | `1` |
| `oauth_connections` total | `1` |

## Auth coherence

| Item | Value |
| --- | --- |
| Starting `GUARDIAN_AUTH_MODE` (`.env` + runtime) | `local` |
| Starting `CODEXIFY_MULTI_USER_ENABLED` (`.env` + runtime) | `true` |
| Starting effective `_auth_mode()` | `local` |
| Starting effective `_multi_user_mode_enabled()` | `True` |
| Starting effective `get_single_user_id()` | `local` |
| Reproduced blocker before change | `GET /api/connect/google-drive/status` → `401 Multi-user mode requires an authenticated session/JWT subject` |
| Reproduced blocker before change | `GET /api/connections/google_drive` → same `401` |

The authorized `.env` change was exactly one line:

```
line 30: CODEXIFY_MULTI_USER_ENABLED=true  ->  CODEXIFY_MULTI_USER_ENABLED=false
```

A full-file diff against a pre-change snapshot showed exactly that one line
changed (`30c30`) and no other key or value. `GUARDIAN_AUTH_MODE=local` was
preserved on line 19. `.env` remains untracked and git-ignored
(`.gitignore:12`); no `.env` content is committed and no secret value is
recorded in this receipt.

### Recreate result

`docker compose up -d --force-recreate backend frontend` completed. Backend and
frontend were recreated and reached `Healthy` / `Started`.

**Recorded deviation:** Compose dependency resolution also replaced the
`codexify-db-1` container (new container id `eff2e68e64fd`, created
`2026-08-27T01:43:24Z`) and ran the dependent `codexify-migrator-1` and
`codexify-model-prep-1`/`codexify-graph-init-1` one-shot services. This was
compose-orchestrated dependency behavior for the named services, not a manual
DB action. Bounded verification of the consequences:

- the durable volume remained `codexify_pg_data`, unchanged and not deleted;
- Alembic reported `9c66e490a42b` before and after, and the migrator log shows
  `upgrade heads` with no `Running upgrade` line — a no-op;
- the pre-existing OAuth row survived intact with its original `created_at`
  (`2026-08-26 17:27:18.994536+00`), so no row was recreated;
- `users`, `projects`, `chat_threads`, `chat_messages`, `messages`,
  `uploaded_documents`, `memory_entries`, and `oauth_connections` counts were
  unchanged;
- `seed_defaults.py` ran as part of the migrator step and created nothing
  (all counts unchanged).

No data loss, migration, or schema change occurred. This deviation is recorded
rather than presented as compliance with "do not recreate DB".

### Effective runtime configuration (recreated backend, not `.env` text)

| Item | Observed in `codexify-backend-1` |
| --- | --- |
| `GUARDIAN_AUTH_MODE` | `local` |
| `CODEXIFY_MULTI_USER_ENABLED` | `false` |
| `CODEXIFY_SINGLE_USER_ID` | `local` |
| `GUARDIAN_EXPOSURE_MODE` | empty (defaults to `local_safe`) |
| `_auth_mode()` | `local` |
| `_multi_user_mode_enabled()` | `False` |
| `get_single_user_id()` | `local` |
| `node_oauth_configured()` | `True` |
| `GET /health` | `200`, `status=ok`, `service=core` on port `8888` |

### Canonical local identity

`CANONICAL_LOCAL_USER_RESOLUTION = PASS`

`GET /api/connect/google-drive/status` was called through the ordinary
supported local path using only the local API-key boundary — no browser JWT, no
session cookie, and no `X-User-Id` spoofing. It returned `200` with
`state = pending`, which is only reachable when the resolved request user is
`local`, the sole owner of the pre-existing row. Any other resolved principal
would have returned `unconfigured`. The prior `401` is gone.

## Pre-auth Google status and Connections projection

`GET /api/connect/google-drive/status` → `200`

| Field | Value |
| --- | --- |
| `connection_id` | `google_drive` |
| `state` | `pending` (expected; the pre-existing row exists) |
| `node_configured` | `true` |
| `scopes` | exactly `drive.metadata.readonly` + `documents.readonly` |
| `expires_at`, `last_refresh_at`, `error_kind` | null |

`GET /api/connections/google_drive` → `200`

| Field | Value |
| --- | --- |
| `category` | `knowledge` |
| `capabilities` | `content_read`, `content_search` |
| `implementation_state` | `implemented` |
| `oauth_provider_key` | `google_drive` |
| `oauth.connection.provider` / `.mode` / `.status` | `google_drive` / `node_local` / `pending` |
| `scopes` | exactly the two canonical read-only scopes |
| `setup_state` | `authenticating` |
| `oauth.launchable` / `.node_configured` | `true` / `true` |
| secret material in payload | none (`access_token`, `refresh_token`, `client_secret`, `code_verifier`, `encrypted` all absent) |

## OAuth application configuration

Verified from the recreated backend process without emitting any secret value.

| Item | Result |
| --- | --- |
| `GOOGLE_DRIVE_OAUTH_CLIENT_ID` | present, non-empty, length `72`, matches Google web-client shape |
| `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET` | present, non-empty, length `34` |
| `GOOGLE_DRIVE_OAUTH_REDIRECT_URI` | present, non-empty, `http://localhost:8888/api/connect/google-drive/callback` |
| Redirect path resolves to canonical callback | `true` |
| State signing secret available | `GUARDIAN_SESSION_SECRET` present |

The requirement-12 gate as literally specified (non-empty) passed. A stricter
structural check performed after the failure is recorded under "Bounded blocker
classification".

## OAuth start

`POST /api/connect/google-drive/start` was called **exactly once** through
canonical local identity. → `200`

| Requirement | Observed | Result |
| --- | --- | --- |
| connection id | `google_drive` | pass |
| state | `authenticating` | pass |
| authorization URL present | yes | pass |
| finite expiration | `600` seconds | pass |
| authorization endpoint | `https://accounts.google.com/o/oauth2/v2/auth` | pass |
| `response_type` | `code` | pass |
| PKCE method | `S256` | pass |
| `code_challenge` present | yes | pass |
| signed `state` present | yes | pass |
| `access_type` | `offline` | pass |
| `prompt` | `consent` | pass |
| `include_granted_scopes` | `false` | pass |
| requested scopes | exactly `https://www.googleapis.com/auth/drive.metadata.readonly` and `https://www.googleapis.com/auth/documents.readonly` | pass |
| `redirect_uri` | `http://localhost:8888/api/connect/google-drive/callback` | pass |
| parameter set | `access_type, client_id, code_challenge, code_challenge_method, include_granted_scopes, prompt, redirect_uri, response_type, scope, state` | no broader scope or extra authority parameter |

The authorization URL, signed state, `code_challenge`, PKCE verifier, and
client id/secret are not recorded here and were never written into the
repository. The URL was handed to the operator's browser without being emitted
to a durable artifact.

### Row state after the fresh `/start`

The same canonical row was reused, exactly as the implementation's
`user/provider/mode` upsert intends.

| Requirement | Observed |
| --- | --- |
| `GOOGLE_DRIVE_CONNECTION_ROW_COUNT` | `1` |
| row id | `1` (same row; `created_at` unchanged) |
| owner | `local` (canonical) |
| provider / mode | `google_drive` / `node_local` |
| status | `pending` |
| scopes | exact canonical pair |
| encrypted access / refresh token | null / null |
| legacy `google` rows | `0` |

No second Google Drive row was created and the row was not deleted.

## Backend process continuity

`BACKEND_PROCESS_CONTINUITY = PASS`

| Item | Before `/start` | After callback |
| --- | --- | --- |
| container id | `42f99370bccd` | `42f99370bccd` |
| container `StartedAt` | `2026-08-27T01:43:37.727896257Z` | `2026-08-27T01:43:37.727896257Z` |
| `RestartCount` | `0` | `0` |
| PID 1 kernel start ticks | `5645774` | `5645774` |

The same backend process that generated the PKCE verifier received the
callback. `BLOCKED — OAUTH PROCESS CONTINUITY LOST` does not apply. Focused
tests were later executed as separate `docker exec` / disposable-container
processes and did not restart the uvicorn process.

## Google consent and callback

| Step | Result |
| --- | --- |
| Authorization URL opened in operator browser | yes, `2026-08-27T01:47:26Z` |
| Google issued an authorization code | **yes** (proven by the recorded failure path, below) |
| Callback reached `/api/connect/google-drive/callback` | yes |
| Callback HTTP result | `401` with bounded detail `{"error": "google_drive_authorization_failed"}` |
| Callback `ok = true` | **no** |
| Connection state became `connected` | **no** |
| Bounded Drive metadata validation | **not reached** |
| Row transition observed | `pending` → `error` at `2026-08-27T01:50:28Z` |
| Persisted `last_error` | `google_drive_authorization_failed` |
| Encrypted access token after callback | **null** |
| Encrypted refresh token after callback | **null** |

### Why the code exchange, not consent, is the proven failure point

`guardian/connections/google_drive/oauth.py::complete_oauth` writes
`google_drive_authorization_failed` only from
`GoogleDriveOAuthAuthorizationError`. Along the callback path that code can
only originate in `_token_response`, which raises it when Google's token
endpoint returns HTTP `400`, `401`, or `403`. The alternative bounded codes
are therefore excluded by observation:

- an invalid or expired signed state raises `GoogleDriveOAuthStateError`
  **before** any row write, so the row would not have changed at all;
- provider denial at the consent screen (`error=` on the callback) would have
  persisted `google_drive_oauth_denied`;
- a missing authorization code would have persisted
  `google_drive_oauth_provider_error`.

Consequently: the signed state validated, a non-empty authorization code was
present, Google **granted** the exact canonical two-scope request, and the
server-side code exchange was then rejected by Google.

Google's own error body is deliberately not persisted by the implementation, so
the exact provider error string (`invalid_client`, `invalid_grant`,
`redirect_uri_mismatch`, …) is **not proven** by this receipt.

## Bounded blocker classification

### Which enumerated blocker applies

The first bounded blocker is at requirement 18: **callback success is not
proven**.

Requirement 17's enumerated blocker,
`BLOCKED — GOOGLE PROVIDER REJECTED THE CANONICAL READ-ONLY OAUTH GRANT`, is
**not** the proven cause and is explicitly not claimed: Google issued an
authorization code, which means the canonical read-only scope set was granted
at consent rather than refused for app-verification or provider-policy reasons.
Scopes were therefore **not** broadened, and no legacy Google authority was
substituted.

The row-disposition blockers
(`... CONTAINS CREDENTIAL MATERIAL`, `... ALREADY CONNECTED`,
`... WRONG OWNER`, `... REQUIRES EXPLICIT AUTHORITY DISPOSITION`) and
`BLOCKED — OAUTH PROCESS CONTINUITY LOST` all do not apply; each was checked
and passed.

### Bounded operator-configuration finding

A structural check of the node's OAuth application configuration, performed
after the failure and without emitting any secret value, found:

| Check | Observed | Canonical Google shape |
| --- | --- | --- |
| `GOOGLE_DRIVE_OAUTH_CLIENT_ID` length | `72` | `72` (`<numeric>-<32>.apps.googleusercontent.com`) — matches |
| `GOOGLE_DRIVE_OAUTH_CLIENT_ID` regex | matches | matches |
| `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET` prefix | `GOCSPX-` present | `GOCSPX-` |
| `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET` length | `34` | `35` (`GOCSPX-` + 28) |
| deficit | `1` character short | — |
| whitespace / quotes / `#` / non-URL-safe characters | none | — |
| raw `.env` value length at line 166 | `34` | — |

The value is 34 characters in the `.env` source itself, so the deficit was
introduced where the secret was recorded, not by dotenv or Compose parsing.

`NODE_OAUTH_CLIENT_SECRET_IS_STRUCTURALLY_MALFORMED`

This is a strong, bounded, structural finding consistent with a Google
`invalid_client` rejection (HTTP `401`) at the token endpoint. It is recorded as
a **structural** classification, not as a proven Google error code, because the
implementation intentionally does not persist the provider error body.

Repairing `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET` is outside this task's authorized
file scope: only `CODEXIFY_MULTI_USER_ENABLED` was authorized to change in
`.env`. No retry was attempted, because a retry under the same malformed client
credential cannot change the outcome and because requirement 13 authorized
exactly one `/start` call.

Prior receipt gap worth noting for the KB:
[`2026-08-24-google-drive-local-oauth-config-readiness.md`](./2026-08-24-google-drive-local-oauth-config-readiness.md)
asserted only `present / nonempty / exactly once / redacted` for
`GOOGLE_DRIVE_OAUTH_CLIENT_SECRET`. Presence-only readiness checks cannot
detect a truncated credential.

## Final connection state

`GOOGLE_DRIVE_CONNECTION_ROW_COUNT = 1`

| Requirement | Observed | Result |
| --- | --- | --- |
| exactly one `google_drive` / `node_local` row | `1` | pass |
| owner equality with canonical local user | `local` = `local` | pass |
| provider | `google_drive` | pass |
| mode | `node_local` | pass |
| scopes | exact canonical pair | pass |
| status | `error` | **fail — `connected` required** |
| encrypted access token present | **no** | **fail** |
| encrypted refresh token present | **no** | **fail** |
| expiry populated | no | consistent with no token |
| `last_error` | `google_drive_authorization_failed` (bounded enumerated code) | safe |
| second canonical Google row created | no | pass |
| row deleted | no | pass |

No token value was decrypted, and no ciphertext was read or emitted.

### Legacy Google authority

| Query | Count | Result |
| --- | ---: | --- |
| `provider = 'google'` active (`pending`/`connected`/`error`) | `0` | pass |
| `provider = 'google'` any status | `0` | pass |

Legacy authority remains absent. No legacy GSuite path and no
`/api/connectors` route was invoked. The implementation's canonical legacy
retirement step was never reached, and it was not needed.

### Safe post-attempt projections

`GET /api/connect/google-drive/status` → `200`, `state = error`,
`node_configured = true`, exact canonical scopes, `error_kind =
google_drive_authorization_failed`, no secret material.

`GET /api/connections/google_drive` → `200`, `category = knowledge`,
capabilities `content_read` / `content_search`, `setup_state = error`,
`oauth.connection.status = error`, no token, secret, ciphertext, or raw error
text. The projection safely shows the failed authorization rather than
fabricating connected state.

## Persistence boundary

| Relation | Pre-auth | Post-auth | Delta |
| --- | ---: | ---: | ---: |
| `users` | 1 | 1 | 0 |
| `projects` | 1 | 1 | 0 |
| `chat_threads` | 0 | 0 | 0 |
| `chat_messages` | 0 | 0 | 0 |
| `messages` | 0 | 0 | 0 |
| `uploaded_documents` | 0 | 0 | 0 |
| `raw_documents` | 0 | 0 | 0 |
| `generated_documents` | 0 | 0 | 0 |
| `project_document_links` | 0 | 0 | 0 |
| `thread_documents` | 0 | 0 | 0 |
| `memory_entries` | 0 | 0 | 0 |
| `personal_facts` | 0 | 0 | 0 |
| `personal_fact_evidence` | 0 | 0 | 0 |
| `sync_jobs` | 0 | 0 | 0 |
| `connector_runs` | 0 | 0 | 0 |
| `connector_configs` | 0 | 0 | 0 |
| `openai_account_import_jobs` | 0 | 0 | 0 |
| `media_assets` | 0 | 0 | 0 |
| `uploaded_images` | 0 | 0 | 0 |
| `events_outbox` | 0 | 0 | 0 |
| `command_runs` | 0 | 0 | 0 |
| `command_run_events` | 0 | 0 | 0 |
| `oauth_connections` | 1 | 1 | 0 |
| `google_drive` rows | 1 | 1 | 0 |
| active legacy `google` rows | 0 | 0 | 0 |
| `notion_connection_credentials` | 0 | 0 | 0 |

A direct diff of the pre-auth and post-auth count captures was empty:
`COUNT_DELTA=NONE`.

The only state change in the entire database is the single canonical OAuth
row's `status` (`pending` → `error`), `last_error`, and `updated_at`. No
provider content was imported, embedded, remembered, indexed, or persisted, and
no new second canonical Google row appeared.

## Final structural integrity

| Requirement | Observed |
| --- | --- |
| Alembic revision | `9c66e490a42b` |
| `users` | `1` |
| `projects` | `1` |
| public base tables | `107` |
| `oauth_connections.user_id` → `users.id` orphans | `0` |
| `projects.user_id` → `users.id` orphans | `0` |
| `chat_threads.user_id` → `users.id` orphans | `0` |
| `chat_messages.thread_id` → `chat_threads.id` orphans | `0` |
| `notion_connection_credentials.user_id` → `users.id` orphans | `0` |
| DDL or migration performed by this task | none |

## Validation

| Surface | Command | Result |
| --- | --- | --- |
| Focused Google Drive connection suite | `python -m pytest -v tests/connections/test_google_drive_connection.py` inside the live backend runtime | **9 passed** |
| Narrow local-auth / Connections seam | `python -m pytest -v tests/connections/ tests/core/test_multi_user_auth_mode.py tests/identity/test_request_user_scope_contract.py tests/identity/test_user_id_propagation.py` inside the live backend runtime | **44 passed** |
| Host-interpreter attempt | same focused command on the macOS host Python 3.14 | collection error: `No module named 'fastapi'`; environmental, not a code failure. Tests were therefore executed in the canonical backend runtime image. |
| Disposable `--network none` runner attempt | same focused command in a throwaway container from `codexify-backend-runtime:latest` | aborted at lifespan on offline `BAAI/bge-large-en-v1.5` resolution; environmental, unrelated to this seam. Superseded by the in-runtime run above. |
| Unrelated supported-profile drift | not run in this task | The Qwen/Gemma `tests/core/test_supported_profile.py` assertion drift recorded in the prior migration receipt was **not** repaired and was **not** exercised here; it remains a separately tracked, unrelated failure. |
| Docs corpus | `python3 scripts/validate_docs.py` | **pass** — "required architecture docs, README links, and source headings verified" (exit 0) |
| Whitespace | `git diff --check` | **pass** (exit 0, no output) |
| Worktree | `git status --short --untracked-files=all` | this receipt is the only staged change |
| Secret scan of this receipt | value-and-pattern scan against the live `.env` and Google credential shapes | **pass** — no client id, client secret, API key, session secret, authorization URL, signed state, PKCE challenge, authorization code, access token, or refresh token literal is present |

### Unrelated pre-existing worktree conditions (left untouched)

Two unrelated working-tree conditions existed alongside this task and were
deliberately **not** staged, restored, or modified:

- ` M docs/architecture/proofs/2026-08-25-local-immutable-image-retention-classification-proof.md`
  — modified before this task began.
- ` D "docs/DEV_LOG/2026-08-26/Dev Log - 2026-08-26.md"` — the file and its
  parent directory are absent from the working tree. `git add` of this receipt
  incidentally picked the deletion up during an index refresh; it was
  immediately unstaged with `git restore --staged` so that only this receipt is
  committed. The cause of the deletion is outside this task and is **not**
  claimed to be known.

## Explicit exclusions

- No Drive content search: `GET /api/knowledge/google-drive/search` was never
  called and `op::google_drive_content_search` was never invoked. Google search
  calls: `0`.
- No Google Docs read: `GET /api/knowledge/google-drive/read/{object_id}` was
  never called. Docs reads: `0`.
- No Command Bus invocation: `0` (`command_runs` and `command_run_events`
  remained `0`).
- No Google write, mutation, or revocation of any kind.
- No disconnect and no reconnect.
- No legacy GSuite path and no `/api/connectors` call.
- No migration, stamp, or schema change.
- No source implementation, migration, supported-profile, Compose, ADR, or
  current-state file was edited.
- No OAuth state, authorization code, client secret, PKCE verifier, access
  token, or refresh token entered this receipt or the repository.

## Authority and release impact

ADR impact: **aligned with ADR-005, ADR-069, ADR-071, and ADR-075 — no new ADR
required.** This task exercised already-accepted semantics: canonical local
identity owns the connection, provider credentials remain server-owned,
OAuth is user-scoped, Connections remained a read-only projection rather than a
credential authority, Google Drive remained read-only, and legacy
Google/GSuite authority remained quarantined and absent.

Release-truth impact: **NONE — this attempted to prove live authorization only;
authorization did not complete, and Google Drive search, Docs read, lifecycle
reconnect, and release promotion remain separately gated.** Google Drive
remains unqualified in `docs/architecture/00-current-state.md`.

## Remaining gate

Before this qualification can be rerun, an authorized operator task must repair
`GOOGLE_DRIVE_OAUTH_CLIENT_SECRET` so that the node holds the complete Google
OAuth client secret, then restart the qualification from a fresh `/start`. The
existing canonical row may again be safely reused; it currently carries
`status = error` with null token fields and no credential authority.
