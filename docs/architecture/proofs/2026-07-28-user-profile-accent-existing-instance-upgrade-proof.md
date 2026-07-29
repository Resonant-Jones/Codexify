# User Profile Accent Existing-Instance Upgrade Proof

## Title

Existing-instance preservation for the user accent migration.

## Final Outcome

**PASS** — the isolated, populated pre-accent User Profile survived a normal
alembic upgrade heads operation. The migration added the non-null
accent_color column, backfilled the existing row to default, preserved all
existing profile metadata and timestamps, installed the canonical database
constraint, and rejected invalid accent values.

The requested pre-upgrade target pair is graph-normalized below: in the
verified migration graph, b2c3d4e5f6a7 descends from e5f6a7b8c9d0, so Alembic
stores only b2c3d4e5f6a7 after applying the two requested targets. This is a
normal Alembic state; no stamp or manual version-table edit was used.

Execution window: 2026-07-29 09:54–09:58 EDT (13:54–13:58 UTC).

## Scope

This is a synthetic existing-instance upgrade proof on the supported Postgres
and migrator path. It proves durable schema migration and row preservation
only. It does not alter runtime behavior or widen any release claim.

## Repository Identity

- Repository: /Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify
- Starting branch: main
- Starting HEAD: 7bf93c8a274d742a33a862d53ccd817b2437244a
- Integration commit: c3289d11c94f8ea88921f68e2e5658f23f716c42
- Integration ancestry: PASS (git merge-base --is-ancestor exited 0)
- Starting worktree: clean (main...origin/main)

## Migration Graph

Migrator heads observed after docker compose build migrator:

~~~
b2c3d4e5f6a7 (head)
c8d9e0f1a2b3 (head)
~~~

Migration identity observed in the migrator image:

~~~
revision: c8d9e0f1a2b3
down_revision: e5f6a7b8c9d0
~~~

The graph inspection showed:

~~~
e5f6a7b8c9d0 -> a1c2d3e4f5b6 -> b2c3d4e5f6a7
e5f6a7b8c9d0 -> c8d9e0f1a2b3
~~~

Therefore e5f6a7b8c9d0 and b2c3d4e5f6a7 are the requested pre-accent
branch floor/target pair, but are not two independent stored Alembic heads.

## Isolated Proof Database

- Temporary database: codexify_accent_upgrade_proof_20260728
- Database service: existing healthy codexify-db-1 Postgres service
- Proof boundary: only the named temporary database was created, migrated,
  queried, and dropped
- Active database: read-only identity check returned Codexify
- Active volume: codexify_pg_data -> /var/lib/postgresql/data remained in place
- Active application database and volumes: untouched
- docker compose down -v: not run

## Pre-Upgrade State

The requested pre-upgrade targets were applied in order:

~~~
e5f6a7b8c9d0
b2c3d4e5f6a7
~~~

Alembic then reported the graph-normalized stored revision:

~~~
b2c3d4e5f6a7 (head)
~~~

The user_profiles.accent_color column count was 0, proving that the
pre-accent schema did not already contain the migrated column.

## Existing Fixture

The fixture was inserted using the actual pre-upgrade columns. The
post-migration ORM model was not used to manufacture the pre-migration schema.

~~~
user_id:      accent-upgrade-proof-user
username:     accent-upgrade-proof@example.invalid
display_name: Accent Upgrade Proof
avatar_url:   https://example.invalid/accent-upgrade-proof.png
timezone:     America/New_York
~~~

The pre-upgrade profile row was:

~~~
user_id          | accent-upgrade-proof-user
display_name     | Accent Upgrade Proof
avatar_url       | https://example.invalid/accent-upgrade-proof.png
timezone         | America/New_York
created_at       | 2026-07-29 13:56:43.525544+00
updated_at       | 2026-07-29 13:56:43.525544+00
~~~

Pre-upgrade profile count: 1.

Pre-upgrade metadata digest, excluding timestamps and accent_color:
53b6c42c305150d4af48de7ac165fa09.

## Upgrade Execution

The normal migration command was run against the temporary database only:

~~~
docker compose run --rm \
  -e DATABASE_URL="$proof_database_url" \
  --entrypoint python migrator \
  -m alembic --raiseerr \
  -c /app/backend/alembic.ini \
  upgrade heads
~~~

The command completed successfully and applied revision c8d9e0f1a2b3.
No seed-default command ran.

## Post-Upgrade Revisions

Alembic reported both expected current heads:

~~~
b2c3d4e5f6a7 (head)
c8d9e0f1a2b3 (head)
~~~

## Schema and Constraint Results

The resulting column inspection was:

~~~
column_name    | accent_color
data_type      | character varying(16)
is_nullable    | NO
column_default | NULL
~~~

The migration backfills existing rows but does not install a server default;
the proof assertion is the durable existing-row value, not a server-default
claim.

The canonical constraint was present:

~~~
conname: ck_user_profiles_accent_color
definition: CHECK (((accent_color)::text = ANY ((ARRAY['amber'::character varying, 'blue'::character varying, 'cyan'::character varying, 'default'::character varying, 'emerald'::character varying, 'rose'::character varying, 'slate'::character varying, 'violet'::character varying])::text[])))
~~~

Aggregate integrity results:

~~~
total_profiles  | 1
null_accents    | 0
invalid_accents | 0
~~~

## Existing-Row Preservation

| Assertion | Pre-upgrade | Post-upgrade | Result |
|---|---:|---:|---|
| user_profiles row count | 1 | 1 | PASS |
| metadata digest | 53b6c42c305150d4af48de7ac165fa09 | 53b6c42c305150d4af48de7ac165fa09 | PASS |
| user_id | accent-upgrade-proof-user | accent-upgrade-proof-user | PASS |
| display_name | Accent Upgrade Proof | Accent Upgrade Proof | PASS |
| avatar_url | https://example.invalid/accent-upgrade-proof.png | https://example.invalid/accent-upgrade-proof.png | PASS |
| timezone | America/New_York | America/New_York | PASS |
| created_at | 2026-07-29 13:56:43.525544+00 | 2026-07-29 13:56:43.525544+00 | PASS |
| updated_at | 2026-07-29 13:56:43.525544+00 | 2026-07-29 13:56:43.525544+00 | PASS |
| accent_color | absent | default | PASS |

## Invalid-Value Rejection

The prescribed invalid value linear-gradient(red, blue) was rejected by
PostgreSQL at the varchar(16) boundary. A second invalid value within the
column length, not-a-color, was rejected directly by the named check
constraint:

~~~
ERROR: new row for relation "user_profiles" violates check constraint
       "ck_user_profiles_accent_color"
~~~

The valid value remained default after both rejected updates.

## Exact Commands

The proof used these command classes, with credentials kept in Compose-managed
environment variables and the proof URL kept in a shell variable:

~~~
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --branch --untracked-files=all
git merge-base --is-ancestor c3289d11c94f8ea88921f68e2e5658f23f716c42 HEAD

docker compose build migrator
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini heads
docker compose run --rm --entrypoint sh migrator -lc 'grep -E "^(revision|down_revision)" ...'
docker compose exec -T db sh -lc 'dropdb --if-exists ...; createdb ...'
docker compose run --rm -e DATABASE_URL="$proof_database_url" --entrypoint python migrator -m alembic -c /app/backend/alembic.ini upgrade e5f6a7b8c9d0
docker compose run --rm -e DATABASE_URL="$proof_database_url" --entrypoint python migrator -m alembic -c /app/backend/alembic.ini upgrade b2c3d4e5f6a7
docker compose run --rm -e DATABASE_URL="$proof_database_url" --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
# seed the specified users and user_profiles rows with psql
# capture pre-upgrade row, count, and metadata digest
docker compose run --rm -e DATABASE_URL="$proof_database_url" --entrypoint python migrator -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
# capture post-upgrade revisions, schema, constraint, row, digest, and aggregates
# attempt linear-gradient(red, blue), then not-a-color, with psql
docker compose exec -T db sh -lc 'dropdb --if-exists -U "$POSTGRES_USER" codexify_accent_upgrade_proof_20260728'
docker compose exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) ..."'
~~~

No Alembic stamp was run. alembic_version was not manually edited. No
migration, model, route, frontend, Compose, or supported-profile file was
edited.

## Proof Classification

- synthetic existing-instance upgrade proof
- supported Postgres and migrator path
- not a production snapshot
- not live API proof
- not Chrome rehydration proof
- not export/restore proof
- not a release expansion

## Limitations

- This is not a production snapshot or a historical upgrade sweep.
- It proves the durable database transition only.
- Live /api/user/profile availability under an authorized runtime profile is
  deferred.
- Chrome panel reload, reconnect, and second-client rehydration are deferred.
- Export/restore behavior is deferred.
- The exact two-entry pre-upgrade alembic current output requested by the task
  is not a valid stored state because e5f6a7b8c9d0 is an ancestor of
  b2c3d4e5f6a7; the proof records the observed graph-normalized state rather
  than manufacturing one with a stamp or manual version edit.

## Cleanup

The temporary database was dropped with dropdb --if-exists and verified absent:

~~~
pg_database count for codexify_accent_upgrade_proof_20260728: 0
~~~

The active Codexify database and codexify_pg_data volume were not dropped,
recreated, or modified by the proof. No docker compose down -v was run.

## ADR Impact

Classification: **aligned with existing ADRs/contracts**.

Governing sources:

- ADR-005 Runtime Mode and Account Boundary Invariants
- Remote Account Access and User Profile Contract
- Account Export + Restore Contract
- Data and Storage
- existing migration-proof doctrine

This proof changes no runtime behavior, schema, route, frontend, Compose file,
or supported profile. It records evidence for the already-landed
account-scoped preference migration.

## Documentation Follow-Through

Updated only this proof artifact. docs/architecture/00-current-state.md
was not updated because this proof does not expand the release claim. Live API,
Chrome rehydration, and export/restore proof remain explicitly deferred.

## Git Commit

One documentation-only commit records this artifact. The final commit hash is
reported in the task closeout because changing the artifact changes the hash.
