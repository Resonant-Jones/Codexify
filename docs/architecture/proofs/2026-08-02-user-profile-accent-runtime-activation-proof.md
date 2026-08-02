# User Profile Accent Runtime Activation Proof

## Title

Prove user accent persistence through an internal-only live profile.

## Final Outcome

**go** — the internal-only backend User Profile API was mounted, authenticated,
validated, and shown to persist the canonical `violet` accent across destruction
and recreation of the backend process. The value was restored to `default`
before cleanup.

This is a backend API proof only. It does not widen the supported beta promise.

## Scope

This proof uses the new proof-only supported profile
`v1-user-profile-accent-proof` and an isolated temporary Postgres database. It
proves the account-owned `accent_color` contract through the live
`/api/user/profile` route, including authentication, canonical-token rejection,
and durable readback after backend replacement.

The default `v1-local-core-web-mcp` profile, migration, route implementation,
frontend, Chrome extension, persona, memory, provider, queue, worker, and
release contracts were not changed.

## Repository identity

- Repository: `/Users/chriscastillo/.codex/worktrees/aaba/Codexify-main`
- Branch: `codex/prove-accent-persistence-live`
- HEAD: `50721d0f51c4b8c0d61bfb398b733624d22872f4`
- `origin/main`: `50721d0f51c4b8c0d61bfb398b733624d22872f4`
- `git merge-base --is-ancestor origin/main HEAD`: PASS
- `git fetch origin`: PASS after retrying outside the managed sandbox because
  shared worktree `FETCH_HEAD` metadata was initially not writable
- Initial worktree: clean
- Final tracked scope: the three authorized files in this task only

## ADR impact

Classification: **aligned with existing ADR(s)**.

Governing sources:

- ADR-005 Runtime Mode and Account Boundary Invariants
- Remote Account Access and User Profile Contract
- Config and Ops supported-profile governance
- Data and Storage
- Canonical User Profile accent tokens in `guardian/user_profile_tokens.py`

This proof activates no public route and changes no accepted account, identity,
schema, or release contract. No new ADR is required.

## Current-truth anchors

- The accent migration and canonical token registry already exist.
- Existing-row migration preservation was previously proven in the dated
  existing-instance upgrade proof.
- `/api/user/profile` exists in backend code but is quarantined by the default
  supported profile.
- An `internal_only` supported-profile route is mounted but removed from
  generated OpenAPI.
- Chrome extension rehydration and UI persistence remain unproven.

## Invariants checked

- The default supported profile was not changed.
- The proof profile classifies `user_profile` as `internal_only`.
- All other route classifications and all services, provider contract,
  extension posture, and criticality data match the default profile.
- Route sets do not overlap.
- Only canonical accent tokens are accepted.
- Invalid updates do not change the previously persisted valid token.
- The active application database and its volume were not targeted by
  migration, seed, profile, or cleanup commands.
- No `docker compose down -v` was run.
- No Alembic stamp or manual `alembic_version` edit was used.
- No Chrome extension or frontend behavior is claimed.

## Proof profile posture

`config/supported_profiles/v1-user-profile-accent-proof.yaml` reports:

- `name`: `v1-user-profile-accent-proof`
- `surface`: `internal-proof-only-local-docker-compose-webui`
- `route_status("user_profile")`: `internal_only`
- Default profile `route_status("user_profile")`: `quarantined`
- Provider, services, extensions, criticality, and all other route postures:
  identical to `v1-local-core-web-mcp`

The new profile-contract test also checks that the default profile file is
byte-for-byte equal to its HEAD version.

## Isolation boundary

- Compose file: `docker-compose.yml`
- Shared dependencies started: existing `db` and `redis` services only
- Temporary proof database:
  `codexify_user_profile_accent_runtime_proof_20260802`
- Dedicated proof user: `accent-runtime-proof-user-20260802`
- One-off backend host port: `18888`
- Active database identity before/after: `Codexify|16384`
- Active Postgres volume: `codexify_pg_data`
- Proof database count after cleanup: `0`
- Proof backend container count after cleanup: `0`

The proof database was created, migrated, seeded with only the named proof user,
queried, and dropped. The active application database and volumes were not
modified or destroyed.

The proof-only override supplied the plain `postgresql://` form to the backend
startup readiness helper, while retaining the SQLAlchemy
`postgresql+psycopg://` form for `GUARDIAN_DATABASE_URL`. The default provider
contract was also supplied explicitly because the local `.env` endpoint did not
match the profile contract. The backend startup environment used the existing
repository-supported `mock` embedding backend and FAISS vector store only to
avoid unrelated local SentenceTransformer/Chroma SQLite startup panics. These
settings were untracked proof-container accommodations; they do not change the
profile file or claim embedding support.

## Exact commands

The following command classes were run without printing API keys, passwords,
complete database URLs, session secrets, or other secret material:

```sh
git fetch origin
git status --short --branch --untracked-files=all
git rev-parse HEAD
git rev-parse origin/main

docker compose -f docker-compose.yml up -d db redis
docker compose -f docker-compose.yml build backend migrator
docker compose -f docker-compose.yml run --rm --no-deps \
  --entrypoint sh backend -lc \
  'printf "%s" "${GUARDIAN_DATABASE_URL:-${DATABASE_URL:-}}"'

docker compose -f docker-compose.yml exec -T db sh -lc \
  'dropdb --if-exists -U "$POSTGRES_USER" \
  codexify_user_profile_accent_runtime_proof_20260802 && \
  createdb -U "$POSTGRES_USER" \
  codexify_user_profile_accent_runtime_proof_20260802'

docker compose -f docker-compose.yml run --rm --no-deps \
  -e DATABASE_URL="$PROOF_DATABASE_URL" \
  -e GUARDIAN_DATABASE_URL="$PROOF_DATABASE_URL" migrator

docker compose -f docker-compose.yml run -d --no-deps \
  --service-ports backend

docker rm -f "$PROOF_BACKEND_ID"
docker compose -f docker-compose.yml run -d --no-deps \
  --service-ports backend

docker compose -f docker-compose.yml exec -T db sh -lc \
  'dropdb --if-exists -U "$POSTGRES_USER" \
  codexify_user_profile_accent_runtime_proof_20260802'
```

The live probes were fresh Python HTTP-client processes. They asserted health
profile identity, OpenAPI path absence, authenticated GET/PATCH behavior,
invalid-token statuses, and post-restart readback.

## Migration result

The normal migrator completed successfully against the temporary database.
Alembic current reported:

```text
d0e1f2a3b4c6 (head) (mergepoint)
```

The existing accent migration and database constraint were therefore present
on the isolated runtime database before the HTTP proof.

## Health and route-mount result

- `/health`: HTTP 200
- Health payload identified `v1-user-profile-accent-proof`
- Backend logs recorded `user_profile` enabled as internal-only
- Authenticated profile route was reachable through the one-off backend

## OpenAPI internal-only result

`/openapi.json` returned HTTP 200 and did not contain
`/api/user/profile` in its `paths` mapping.

## Initial profile GET

Authenticated `GET /api/user/profile` returned HTTP 200 with:

```text
profile.accent_color=default
```

## Canonical PATCH

Authenticated `PATCH /api/user/profile` with `{"accent_color":"violet"}`
returned HTTP 200 and `violet`. A subsequent GET in the same process also
returned `violet`.

## Invalid-token rejection

Both invalid updates were rejected with HTTP 422:

| Payload | Status | Previously persisted value |
|---|---:|---|
| `not-a-color` | 422 | `violet` |
| `linear-gradient(red, blue)` | 422 | `violet` |

The follow-up GET confirmed that rejected requests did not alter the valid
persisted token.

## Backend restart

The first one-off backend container was destroyed with `docker rm -f` and a new
one-off backend container was created from the same built backend image and
proof-only override.

## Post-restart persistence

The fresh HTTP client process returned:

```text
GET /api/user/profile -> 200, profile.accent_color=violet
PATCH {"accent_color":"default"} -> 200
final GET -> 200, profile.accent_color=default
```

This proves durable backend persistence across backend process replacement.

## Cleanup

- The proof value was restored to `default` before teardown.
- The proof backend container was removed.
- The temporary proof database was dropped and verified absent.
- No proof backend container remained.
- The active database identity remained `Codexify|16384`.
- The active volume `codexify_pg_data` remained present.
- The temporary Compose override was removed.
- No active application database or volume was destroyed.

## Validation results

Passed:

```text
.venv/bin/python -m pytest -v \
  tests/config/test_user_profile_accent_proof_profile.py \
  tests/core/test_supported_profile.py \
  tests/contracts/test_user_profile_accent_tokens.py \
  tests/auth/test_user_profile_session_surface.py
43 passed, 2 warnings

git diff --check
```

The system `python3 -m pytest` command was not applicable because that system
Python had no pytest; the repository `.venv` supplied the requested runtime and
passed the complete suite.

## Known limitations

- This proves the backend API slice only.
- The proof used mock embeddings and FAISS in the isolated proof container to
  bypass unrelated local SentenceTransformer/Chroma startup failures. It does
  not prove embedding or retrieval behavior.
- Chrome extension loading, reconnect behavior, selector state, and UI
  rehydration remain unproven.
- No release-support or default-beta claim is made.
- The local `.env` is not shell-source-compatible because an unquoted value
  caused `source .env` to fail; the named API-key assignment was loaded without
  printing its value, and the runtime itself loaded Compose-managed env values.

## Documentation follow-through

This dated proof artifact is the only documentation change. The default
supported profile and `docs/architecture/00-current-state.md` were not updated.
The proof does not widen the supported beta release promise.

## Next proof

Run a separate internal-only Chrome extension proof covering accent loading,
selection, reconnect, and second-session rehydration against the proof backend.

## Git commit

The commit hash is recorded in the task closeout because recording it here
would change the artifact hash.
