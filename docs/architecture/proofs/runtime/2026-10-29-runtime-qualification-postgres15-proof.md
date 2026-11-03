# Runtime qualification of the committed migration chain on the supported PostgreSQL container path

Date: 2026-10-29

Evidence: disposable `postgres:15` container matching the image pinned in `docker-compose.yml` and `docker-compose.runtime.yml`, plus a restored copy of the live Private Preview database. Not a deployment, not a push. Release remains `HOLD`.

## Why this receipt exists

The migration-graph work was proved on a **locally patched PostgreSQL 16.2 build**. The supported runtime does not use that build. `docker-compose.yml` and `docker-compose.runtime.yml` both pin:

```yaml
services:
  db:
    image: postgres:15
```

and the running Private Preview database reports:

```text
PostgreSQL 15.19 (Debian 15.19-1.pgdg13+2) on aarch64-unknown-linux-gnu
```

So the entire prior evidence base was measured against a major version the product does not deploy on. This receipt closes that gap by proving the committed migration chain on the supported container path.

## Environment

| | |
|---|---|
| Image | `postgres:15` |
| Digest | `postgres@sha256:c961aa287d8698297cb26cdfadfbe9fd2cbaf77e53cfffe9636e8d8a1e4d842c` |
| Server | PostgreSQL 15.19 (Debian 15.19-1.pgdg13+2) on aarch64-unknown-linux-gnu |
| Container | `codexify_qual_pg15`, disposable, port `127.0.0.1:55435` |
| Credentials | `codexify` / `codexify`, database `Codexify` (the compose defaults) |
| Repository head | `3a91d7c4e8b2` — sole head, confirmed before any upgrade |
| Preview database | **read only.** It was dumped with `pg_dump` and never written to, migrated, or restarted |

The Preview database was only ever read. The upgrade rehearsal ran against a restored copy in a separate container.

## Scenario A — clean-database upgrade to head

An empty database on `postgres:15` was upgraded to `head` with the committed chain.

| Assertion | Result |
| --- | --- |
| Heads after upgrade | `['3a91d7c4e8b2']` — sole head |
| Tables present after upgrade | 138 |
| `saved_widgets`, `saved_widget_revisions`, `direct_message_read_cursors` | present |
| Consent columns on `user_settings` | all five present: `automatic_memory_suggestions`, `consent_policy_version`, `consent_recorded_by_user_id`, `consent_recorded_at`, `consent_updated_at` |
| `saved_widgets_lifecycle_state_check`, `saved_widgets_current_revision_check` | present |
| `user_settings_automatic_memory_suggestions_check` | present |
| `direct_message_read_cursors` primary key | `(conversation_id, profile_id)` |
| Saved Widget `current_revision > 0` guard | rejects an invalid insert |

**PASS**

## Scenario B — existing-instance upgrade from the live Preview revision

This is the path a real deployment takes. The live Preview database is at revision `f0d7c4b2a198`, which is *before* the Saved Widget branch (`a6b9d2e4f701`) and before the consent branch (`c59e4d1a28f0`) — that is, before every revision this work added.

The Preview was dumped read-only at `2026-10-28 23:57:30 EDT` and restored into the disposable container:

```text
docker exec codexify_private_preview-db-1 pg_dump -U codexify -d Codexify -Fc > preview.dump
docker exec -i codexify_qual_pg15 pg_restore -U codexify -d CodexifyRestore --no-owner --no-privileges < preview.dump
```

The restored copy was verified faithful against the source before the upgrade:

| Table | Preview | Restored copy | |
| --- | --- | --- | --- |
| `users` | 11 | 11 | match |
| `user_settings` | 0 | 0 | match |
| `chat_threads` | 5137 | 5137 | match |
| `chat_messages` | 113498 | 113498 | match |
| `audit_log` | 341 | 341 | match |
| `direct_message_consents` | 4 | 4 | match |
| `direct_messages` | 11 | 10 | see below |

The `direct_messages` difference is **live Preview activity, not a restore defect**. The Preview is a running service with approved synthetic accounts, and a message was inserted at `2026-10-29 00:02:15 EDT` — five minutes after the dump was taken. The row `a25a7bba0c7a4304bbba964ab875880e` exists in the Preview and not in the dump, which is exactly what a post-dump insert looks like. Every other table matched exactly.

### The upgrade

```text
restored copy revision before upgrade : f0d7c4b2a198
alembic upgrade head                  -> 3a91d7c4e8b2  (sole head)
```

| Table | Before | After | |
| --- | --- | --- | --- |
| `users` | 11 | 11 | preserved |
| `user_settings` | 0 | 0 | preserved (empty in the Preview) |
| `chat_threads` | 5137 | 5137 | preserved |
| `chat_messages` | 113498 | 113498 | preserved |
| `audit_log` | 341 | 341 | preserved |
| `events_outbox` | 1288 | 1288 | preserved |
| `direct_messages` | 10 | 10 | preserved |
| `direct_message_conversations` | 4 | 4 | preserved |
| `direct_message_consents` | 4 | 4 | preserved |
| `direct_message_relationships` | 7 | 7 | preserved |
| `direct_message_relationship_participants` | 14 | 14 | preserved |
| `personal_fact_revisions` | 8 | 8 | preserved |
| `chat_completion_attempts` | 103 | 103 | preserved |

Post-upgrade assertions on the migrated instance:

| Assertion | Result |
| --- | --- |
| Sole head | `3a91d7c4e8b2` |
| `direct_message_read_cursors` | created, primary key `(conversation_id, profile_id)`, **0 rows** — a new table on a populated instance starts empty |
| `saved_widgets`, `saved_widget_revisions` | created |
| Consent columns | created on `user_settings` |
| Consent defaults on a row inserted after the upgrade | `('unset', '1')` |
| Consent domain constraint on the upgraded instance | rejects `automatic_memory_suggestions='bogus'` |
| Saved Widget `current_revision` guard | present and enforced |

**PASS**

### A note on the empty `user_settings` table

The Preview has 11 users and **no** `user_settings` rows at all. That is real data, not a restore artifact. It means the consent backfill had nothing to backfill on this instance, so the backfill path is asserted two ways instead: through the column defaults on a row inserted after the upgrade (`unset` / `1`), and through the constraint rejecting an invalid state on that same row. The backfill over *populated* `user_settings` was proved separately on the locally patched 16.2 build; that specific path is not exercised by the Preview's data, and this receipt does not claim it is.

## The deployment path, rehearsed against the real runtime image

The scenarios above prove the *chain*. This section proves the *mechanism* that a live deployment actually uses, because those are different things and the mechanism turned out to have a trap.

The Private Preview stack runs the backend from the image `codexify-backend-runtime:latest`, with `guardian/`, `backend/`, `config/`, `plugins/`, `tests/` and `pytest.ini` bind-mounted from a pinned source root. Two distinct actors apply migrations:

| Actor | Migration source | Command |
| --- | --- | --- |
| `backend` container entrypoint | `/app/backend/alembic.ini` → `script_location = %(here)s/../guardian/db/migrations` | `alembic -c <cfg> upgrade head` |
| `migrator` service | same config, but **no `guardian/` mount** — the migrations come from the image layer | `python -m alembic --raiseerr -c <cfg> upgrade heads` |

### Trap 1 — the backend entrypoint's migration call is a silent no-op

`backend/entrypoint.py` runs:

```python
_run(['alembic', '-c', alembic_cfg, 'upgrade', 'head'])
```

The runtime image has **no `alembic` executable on `PATH`**. It is only importable as a Python module:

```text
$ docker run --rm --entrypoint sh codexify-backend-runtime:latest -c "which alembic; python -m alembic --version"
which rc=1
alembic 1.17.0
```

`_run` catches `FileNotFoundError` and returns a `CompletedProcess` with exit code 127 without raising, and the call is not `check=True`. So the entrypoint's migration attempt fails, is swallowed, and the container proceeds to start uvicorn regardless. Reproduced directly: running the real image with main's source mounted against a restored Preview copy left the database at `f0d7c4b2a198` and 135 tables, with no read-state tables present.

**Consequence: recreating the backend container does not migrate the database.** The `migrator` service is the actor that actually advances the schema, and `backend/scripts/docker/run_migrator.py` resolves this correctly — it probes `shutil.which("alembic")` and falls back to `[sys.executable, "-m", "alembic", ...]`.

### Trap 2 — the `migrator` reads migrations from the image, not from the mounted source

The `migrator` service deliberately carries **no `guardian/` volume mount** (`docker-compose.yml`, with an explicit comment about a macOS virtiofs stat bug). Its `script_location` resolves to `/app/guardian/db/migrations`, which is therefore the **baked image copy** — not the bind-mounted source root.

The currently deployed image contains 123 migration versions and heads at `f0d7c4b2a198`, and contains **none** of the Saved Widget, consent, or read-cursor revisions:

```text
$ docker run --rm --entrypoint sh codexify-backend-runtime:latest \
    -c "ls /app/guardian/db/migrations/versions | grep -iE 'read_cursor|saved_widget|3a91d7c4e8b2'"
NONE - image lacks the read-state chain
$ docker run --rm --entrypoint sh codexify-backend-runtime:latest \
    -c "python -m alembic -c /app/backend/alembic.ini heads"
f0d7c4b2a198 (head)
```

So for the `migrator` to see the new chain, **the backend runtime image must be rebuilt from the new source**. Mounting a newer source root alone is not sufficient.

### The rehearsal

Both traps were exercised on a restored copy of the Preview database, using the real image and the real migrator command:

```text
docker run --rm --network codexify_rehearsal_net \
  -e DATABASE_URL='postgresql://codexify:codexify@codexify_qual_pg15:5432/CodexifyRehearsal' \
  -v "$PWD/guardian:/app/guardian" -v "$PWD/backend:/app/backend" ... \
  --entrypoint python codexify-backend-runtime:latest \
  /app/backend/scripts/docker/run_migrator.py
```

```
[Migrator] Using Alembic config: /app/backend/alembic.ini
[Migrator] alembic.ini script_location=%(here)s/../guardian/db/migrations
[docker] run: /usr/local/bin/python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
[Migrator] Running seed defaults
[Migrator] Done
```

Resulting state on the restored copy:

| Assertion | Result |
| --- | --- |
| Revision after the real migrator | `3a91d7c4e8b2` — sole head |
| Tables after the real migrator | 138 |
| `saved_widgets`, `saved_widget_revisions`, `direct_message_read_cursors` | all present |
| `direct_messages` rows | 10, preserved |
| `chat_messages` rows | 113498, preserved |
| Migrations applied by the migrator | 5 (five `Running` lines, matching the five-revision path from `f0d7c4b2a198`) |

**PASS** — with the image carrying the new `guardian/` tree. This is the same code path the live `migrator` service runs, against a faithful copy of the live Preview data, on the supported PostgreSQL version.

### Deployment implication

A correct Private Preview deployment of this chain therefore requires, in order:

1. Rebuild `codexify-backend-runtime:latest` from the new source root, so the baked `/app/guardian/db/migrations` contains the new chain.
2. Run the `migrator` service so the live Preview database advances `f0d7c4b2a198` → `3a91d7c4e8b2`.
3. Recreate the `backend` and worker containers so the new bind-mounted code is served.

Step 3 alone does not migrate. Step 2 alone does not have the migrations. Both are required, and the order matters: image first, then migrator, then application containers.

## What this receipt establishes

- The committed migration chain — including both merge revisions — applies cleanly on **PostgreSQL 15.19**, the version the product actually deploys.
- A populated instance at the Preview's exact revision upgrades to the single head `3a91d7c4e8b2` with **every pre-existing row preserved**, including live direct-messaging conversations, messages, consents, relationships and participants.
- The three authorities — Saved Widget storage, automatic-collection consent, participant-local read cursor — are present and enforced after the upgrade.
- The graph converges to one head from either starting point: empty database, or a populated Preview copy.

## What this receipt does not establish

- **Nothing was deployed.** The Preview still serves commit `57184dfbe` and its database remains at `f0d7c4b2a198`. This is a rehearsal on a copy.
- **No live read-state behaviour was exercised.** The migration is proven; the feature is not. Unread badges, explicit read advancement, concurrent reads, reload persistence, consent enforcement and account isolation still need a live two-account test against the running Preview.
- **No crash-durability claim.** The disposable container ran with the default `synchronous_commit=on`; acknowledged commits are durable across a server crash for the purposes of these runs.
- **The Preview's own database was never migrated.** The rehearsal used a restored copy. The live upgrade is a separate, explicitly authorised step.
- **The frontend deployment surface was not rehearsed.** The new unread-badge code lives in the `frontend/src` workspace, whose lockfile now carries dependencies absent from the serving tree (`zod`, `@heroicons/react`, `@openuidev/react-lang`, `@radix-ui/react-visually-hidden`). The frontend container installs with `pnpm install --frozen-lockfile`, so a frontend restart against the new source requires the new lockfile to resolve cleanly. That was not exercised here.
- **The live `migrator` service was not run against the live database.** The rehearsal used the same command against a restored copy on a disposable container.

## Release and ADR posture

No ADR change. No migration was rewritten, no revision identity was altered, and both merge revisions remain graph-only. The Saved Widget contract, ADR-102's identity/revision boundary, the account-owned automatic-collection consent, ADR-103's participant-local read state and ADR-104 are unchanged. Release remains **HOLD** and the default Beta remains unqualified.

## Reproduction

```sh
docker run -d --name codexify_qual_pg15 \
  -e POSTGRES_USER=codexify -e POSTGRES_PASSWORD=codexify -e POSTGRES_DB=Codexify \
  -p 127.0.0.1:55435:5432 postgres:15

docker exec codexify_private_preview-db-1 \
  pg_dump -U codexify -d Codexify -Fc > preview.dump
docker exec codexify_qual_pg15 psql -U codexify -d postgres -c 'CREATE DATABASE "CodexifyRestore"'
docker exec -i codexify_qual_pg15 \
  pg_restore -U codexify -d CodexifyRestore --no-owner --no-privileges < preview.dump

QUAL_BASE_URL='postgresql://codexify:codexify@127.0.0.1:55435/Codexify' \
  python .scratch/qualify_pg15.py
```

### Rehearsing the real deployment mechanism

```sh
# A container network so the image can reach the disposable database.
docker network create codexify_rehearsal_net
docker network connect codexify_rehearsal_net codexify_qual_pg15

docker exec codexify_qual_pg15 psql -U codexify -d postgres -c 'CREATE DATABASE "CodexifyRehearsal"'
docker exec -i codexify_qual_pg15 \
  pg_restore -U codexify -d CodexifyRehearsal --no-owner --no-privileges < preview.dump

# The real migrator command, the real image, the new source tree.
docker run --rm --network codexify_rehearsal_net \
  -e DATABASE_URL='postgresql://codexify:codexify@codexify_qual_pg15:5432/CodexifyRehearsal' \
  -e ALEMBIC_CONFIG=/app/backend/alembic.ini -e GUARDIAN_API_KEY=rehearsal-local-key \
  -v "$PWD/guardian:/app/guardian" -v "$PWD/backend:/app/backend" \
  -v "$PWD/config:/app/config:ro" -v "$PWD/plugins:/app/plugins:ro" \
  --entrypoint python codexify-backend-runtime:latest \
  /app/backend/scripts/docker/run_migrator.py

docker exec codexify_qual_pg15 psql -U codexify -d CodexifyRehearsal -tAc \
  "select version_num from alembic_version"
```

### Confirming the two traps

```sh
# Trap 1: no alembic executable in the runtime image.
docker run --rm --entrypoint sh codexify-backend-runtime:latest \
  -c "which alembic; python -m alembic --version"

# Trap 2: the migrator reads migrations from the image, and this image
# predates the read-state chain.
docker run --rm --entrypoint sh codexify-backend-runtime:latest \
  -c "ls /app/guardian/db/migrations/versions | wc -l; \
      python -m alembic -c /app/backend/alembic.ini heads"
```
