# Private Preview deployment and live read-state qualification

Date: 2026-10-29

Serving revision: `5569f3f34` (published `origin/main`). Serving source root:
`/Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261029`, a clean
detached worktree of published `main`.

Live database before: revision `f0d7c4b2a198`, 135 tables.
Live database after: revision `3a91d7c4e8b2`, 138 tables, every pre-existing row preserved.

Release posture remains `HOLD`. This receipt qualifies one deployed surface — recipient-local
direct-message read state — against the running Private Preview. It does not qualify the
product.

## What this receipt establishes

The read-state feature is **deployed and live-qualified** on the Private Preview. The
migration chain that carries it has been applied to the live Preview database, the serving
application containers run the new code, and a two-account live test exercised the feature's
contract against the running service over HTTP.

This closes the gap left open by
[the runtime qualification proof](./2026-10-29-runtime-qualification-postgres15-proof.md),
which proved the chain and the mechanism but explicitly did not deploy anything.

## Deployment order, and why it is that order

The deployment required three steps in a specific order. Getting the order wrong produces a
stack that looks healthy and is not.

### 1. Rebuild the backend runtime image

The `migrator` service deliberately carries **no `guardian/` volume mount** — `docker-compose.yml`
explains that a macOS virtiofs stat bug makes `os.path.exists()` unreliable on mounted files, so
migration files come from the baked image instead. The image in use was built from commit
`57184dfbe` and contained 123 migration versions heading at `f0d7c4b2a198`, with **none** of the
Saved Widget, consent, or read-cursor revisions.

```text
$ docker run --rm --entrypoint sh codexify-backend-runtime:latest \
    -c "python -m alembic -c /app/backend/alembic.ini heads"
f0d7c4b2a198 (head)
```

So the image had to be rebuilt from the new source before the migration could see the new chain:

```text
$ docker buildx build --builder desktop-linux --load \
    -f backend/Dockerfile --target runtime -t codexify-backend-runtime:latest .

$ docker run --rm --entrypoint sh codexify-backend-runtime:latest \
    -c "ls /app/guardian/db/migrations/versions | wc -l; \
        python -m alembic -c /app/backend/alembic.ini heads"
128
3a91d7c4e8b2 (head)
```

The rebuild also exposed a defect in the build context. `.dockerignore` excluded neither
`.scratch` nor `.env.private-preview`, so a 9.7 GB scratch directory and a file holding the
Preview's session/JWT secrets and approved-email allowlist were both being shipped into the
build context on every build. `.dockerignore` now excludes `.scratch`, `.scratch.*`, and all
`.env.*` variants, with the checked-in `*.example` templates re-included. No application
behaviour changed.

### 2. Run the migrator

The `backend` container entrypoint does **not** migrate the database. `backend/entrypoint.py`
runs `alembic -c /app/backend/alembic.ini upgrade head` as a bare executable, but the runtime
image has no `alembic` on `PATH` — only `python -m alembic` works. `_run` catches the
`FileNotFoundError` and returns exit code 127 without raising, so the call fails silently and
the container starts uvicorn regardless.

Recreating the backend container therefore does **not** advance the schema. The `migrator`
service is the actor that does, and `backend/scripts/docker/run_migrator.py` resolves the
executable correctly.

```text
[Migrator] Using Alembic config: /app/backend/alembic.ini
[Migrator] alembic.ini script_location=%(here)s/../guardian/db/migrations
[docker] run: /usr/local/bin/python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
[Migrator] Running seed defaults
[Migrator] Done
```

Five revisions applied. The live database moved `f0d7c4b2a198` → `3a91d7c4e8b2`.

| Table | Before | After | |
| --- | --- | --- | --- |
| `users` | 13 | 13 | preserved |
| `chat_threads` | 5137 | 5137 | preserved |
| `chat_messages` | 113498 | 113498 | preserved |
| `audit_log` | 341 | 341 | preserved |
| `direct_messages` | 11 | 11 | preserved |
| `direct_message_conversations` | 4 | 4 | preserved |
| `direct_message_consents` | 4 | 4 | preserved |
| `direct_message_relationships` | 7 | 7 | preserved |
| `direct_message_relationship_participants` | 14 | 14 | preserved |
| Tables (public schema) | 135 | 138 | +3 read-state tables |

A 140 MB `pg_dump` of the live database was taken before the migration and verified readable.
It was a rehearsal artifact and a rollback path, not a substitute for the migration.

### 3. Recreate the application containers

Only after the migration did the `backend`, workers, `frontend`, and `private-preview-origin`
containers get recreated on the new image and the new bind-mounted source.

**Step 3 alone does not migrate. Step 2 alone does not have the migrations.** Both are required,
in that order.

## The serving-source pin

The Private Preview runs from a *pinned* source root, not from the operator's checkout. The pin
lives at:

```text
~/Library/Application Support/Codexify/private-preview/serving-source
```

A `LaunchAgent` (`com.resonant.codexify-private-preview`, `StartInterval` 300 s) reconciles the
stack every five minutes against whatever the pin names. It also refuses to serve a checkout
with tracked modifications:

```bash
tracked_changes="$(git -C "$source_root" status --porcelain --untracked-files=no)"
if [[ -n "$tracked_changes" ]]; then
  echo "Serving checkout contains tracked modifications; refusing unreviewed Preview source" >&2
  return 1
fi
```

This matters for the deployment. The first deployment attempt updated the containers directly
and was **silently reverted** by the next LaunchAgent cycle, because the pin still named the old
worktree. The deployment is only durable once the pin is repointed and the agent has reconciled
against it.

The pin now reads:

```text
/Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261029
```

The agent's own guard passes on the new root: it is a readable Git worktree with no tracked
modifications, and it carries the `docker-compose.private-preview-serving.yml` third compose
file. Verified across a full reconciliation cycle — the backend's `/app/guardian` mount stayed
on the new source and the read-cursor model stayed present.

## Live two-account read-state test

Two synthetic accounts on the reserved `example.invalid` domain, provisioned through the
documented `private_preview_provision` path, with usernames claimed through
`PUT /api/profile/social-identity`. Sessions were driven over `http://127.0.0.1:8081`. Session
tokens and passwords were kept in mode-600 files outside the repository and were never printed.

**20 of 20 checks passed.**

| Check | Result |
| --- | --- |
| A discovers B's profile by username | PASS |
| A sends a contact request to B | PASS |
| B receives the request | PASS |
| B accepts the request | PASS |
| A holds a relationship with B | PASS |
| A opens a conversation with B | PASS |
| A sends 3 messages to B | PASS |
| **B sees `unread_count = 3` before reading** | PASS |
| **A sees `unread_count = 0` for their own sent messages (account isolation)** | PASS |
| **B advances its read cursor explicitly** | PASS |
| **B's `unread_count` drops to 0 after reading** | PASS |
| **Repeated read is idempotent (cursor never moves backward)** | PASS |
| **Read state persists across a fresh request (reload)** | PASS |
| **A new message makes B unread again (=1)** | PASS |
| **Watermark advances only to the message actually seen (1 remains)** | PASS |
| **4 concurrent reads all succeed and converge (`unread_count = 0`)** | PASS |
| **B's read cursor is not observable by A (no sender-visible receipt)** | PASS |
| Consent HTTP surface is quarantined by the preview profile (expected) | PASS |
| Consent columns are live with fail-closed defaults | PASS |
| An out-of-domain consent state is rejected by the constraint | PASS |

### The read cursor is participant-local

The single stored cursor row belongs to the **recipient**:

```text
conversation_id                          cursor_owner   last_read_message_id
3910a714080c4b9ebec8aa00bedb7e08        readstate-b    e9fe50691f36454dbf462d161554bb71
```

`readstate-a` — the sender — has no cursor row and observes no read state. A's view of the
conversation carries only `conversation_id`, `created_at`, `kind`, `latest_activity_at`,
`latest_message`, `origin`, `participants`, `peer`, `placement`, `relationship_id`, and
`unread_count`. There is no `read_cursor`, no `last_read_message_id`, no read receipt. The
sender cannot observe that the recipient read anything, and cannot advance their cursor.

### The watermark does not over-advance

The read request carries `last_read_message_id` — the caller's assertion of what they actually
saw. After B read all 3 messages, A sent a 4th. B then re-asserted the *first* message as their
watermark. The unread count settled at **1**, not 0: the cursor advanced to exactly the message
B had seen and no further. A message that arrived after the transcript was fetched was not
silently marked read.

### The unread projection is derived, not duplicated

```text
$ psql -c "select table_name from information_schema.tables
           where table_name like '%unread%'"
(no rows)
```

There is no unread-counter table. `unread_count` is computed from the messages and the
recipient's cursor, so there is no second persistence authority that could drift from the
cursor.

### Concurrent reads converge

Four simultaneous `POST .../read` calls for the same conversation all returned 200, and the
unread count settled at 0. The cursor update is serialized against the participant authority
row, so concurrent read advancement does not lose or double-apply.

### Consent

The consent HTTP surface (`/api/iddb/automatic-memory-suggestions`) is **deliberately
quarantined** in the Private Preview supported profile —
`config/supported_profiles/v1-whooshd-deepseek-web.yaml` lists `iddb` under `quarantined`. The
endpoint returns 404 on this profile by design, not by defect.

Consent enforcement was therefore asserted at the storage layer the Preview does expose. The
live database carries the account-owned consent columns with fail-closed defaults:

```text
automatic_memory_suggestions  character varying  'unset'::character varying
consent_policy_version        character varying  '1'::character varying
consent_recorded_at           timestamp with time zone
consent_recorded_by_user_id   character varying
consent_updated_at            timestamp with time zone
```

and the domain constraint rejects any state outside the declared set:

```text
ERROR: new row for relation "user_settings" violates check constraint
       "user_settings_automatic_memory_suggestions_check"
```

**What this receipt does not establish:** the consent *HTTP* surface was not exercised live,
because the Preview profile does not expose it. A profile that mounts `iddb` would be needed for
that. The storage-layer enforcement is proven; the endpoint behaviour is not.

## Restart recovery

The backend container was restarted and recovered cleanly:

```text
[Backend] Verifying required tables + alembic_version
[Backend] OK: alembic_version=3a91d7c4e8b2
```

The backend verifies the schema revision on every start. After the restart the read state was
still intact — `unread_count = 0` and the cursor row still present.

## Cleanup

The two synthetic accounts were removed: their direct-message state, their `user_profiles` rows,
and their `users` rows. `CODEXIFY_PREVIEW_APPROVED_EMAILS` was restored from a pre-change copy
and the restored `.env.private-preview` is byte-identical to that copy. The backend container was
recreated on the restored allowlist.

## What this receipt does not establish

- **The product is not qualified.** This is one deployed surface on the Private Preview. Release
  remains `HOLD` and the default Beta remains unqualified.
- **The consent HTTP surface was not exercised live**, because the Preview profile quarantines
  `iddb`. Storage-layer enforcement is proven; endpoint behaviour is not.
- **The unread badge was not verified in a browser.** The unread *projection* is proven at the
  API and storage layer, and the frontend unread code is served by the deployed `frontend`
  container, but no browser-rendered badge was inspected.
- **No crash-durability claim.** No assertion is made about acknowledged commits surviving a
  server crash.
- **The 279 inherited backend-suite failures and the 8-file stale canonical-head family remain
  unrepaired** by design. They were not re-run as part of this deployment.

## Release and ADR posture

No ADR change. No migration was rewritten, no revision identity altered, both merge revisions
remain graph-only. ADR-097 (existing DM consent), ADR-102 (Saved Widget identity/revision
boundary), ADR-103 (participant-local read state) and ADR-104 are unchanged. This deployment
exercises the contracts those ADRs define; it does not alter them.

## Reproduction

```sh
# 1. image
docker buildx build --builder desktop-linux --load \
  -f backend/Dockerfile --target runtime -t codexify-backend-runtime:latest .

# 2. migrator (the actor that actually advances the schema)
docker compose --project-directory "$REPO" --env-file "$REPO/.env.private-preview" \
  -p codexify_private_preview \
  -f "$SOURCE_ROOT/docker-compose.yml" \
  -f "$SOURCE_ROOT/docker-compose.private-preview.yml" \
  -f "$SOURCE_ROOT/docker-compose.private-preview-serving.yml" \
  up -d --no-deps --force-recreate migrator

# 3. application containers
docker compose ... up -d

# 4. confirm the pin names the new source, or the LaunchAgent reverts the deployment
cat ~/Library/Application\ Support/Codexify/private-preview/serving-source
```
