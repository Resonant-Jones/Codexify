# Guardian Delegation Phase 2A Clean DB Proof

- Date: 2026-05-26
- Branch: `codex/create-guardian-delegation-contract`
- HEAD commit before this task: `7587adcac3130e135ac32bcfc9193db52be66123`
- HEAD commit after this task: not available at proof-capture time; recorded in the final task output after commit
- Disposable Compose project: `codexify_guardian_delegation_dbproof`
- Final result: PASS

## Scope

This artifact proves the clean fresh-DB migration path for the Guardian Delegation Phase 2A schema seam on an isolated Docker Compose project.

It covers:

- the Compose DB healthcheck repair for Postgres readiness inside the DB container
- clean disposable Postgres volume bootstrap
- successful `migrator` execution on a clean database
- Alembic current heads after migration
- existence of the `guardian_delegation_intents` table after migration
- existence of the Phase 2A key columns on that table

It does not prove:

- Guardian Delegation Loop v1 completion
- Phase 2B context expansion
- thread reinjection
- Command Center mirroring
- approve/cancel lifecycle
- intent-spine unification
- broader release readiness

## What Was Being Proven

The containment review established that the upgraded DB migration path already passed, but the clean fresh-DB proof was blocked by Compose health behavior rather than a demonstrated Alembic failure.

This slice proves that:

1. the DB service becomes healthy in a clean disposable Compose project
2. the `migrator` can upgrade a clean database successfully
3. Alembic current reports the expected current heads
4. `guardian_delegation_intents` exists after migration with the expected Phase 2A columns

## What Was Not Being Proven

- no Guardian delegation runtime behavior changes
- no new route behavior
- no worker/provider/chat semantics
- no release-scope expansion

## Healthcheck Issue Summary

`docker-compose.yml` defines shared Postgres environment values under `x-postgres-env`, including:

- `PGHOST=db`

The `db` service inherited that environment and used this healthcheck pattern before the fix:

```sh
pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Inside the Postgres container, that command could resolve `PGHOST=db` instead of checking the local Postgres process directly. In the disposable proof project, Postgres was up locally, but Compose could keep the service unhealthy and block the `migrator` dependency chain.

## Exact Fix Applied

The DB healthcheck in `docker-compose.yml` was narrowed to an explicit local-host probe:

```sh
pg_isready -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

This keeps the shared Compose env structure intact and only repairs DB health reporting inside the DB container.

## Exact Commands Run

### Compose/config verification

```sh
docker compose config
```

### Disposable clean-DB proof setup

```sh
docker compose -p codexify_guardian_delegation_dbproof down -v --remove-orphans
docker compose -p codexify_guardian_delegation_dbproof up -d db redis neo4j
docker compose -p codexify_guardian_delegation_dbproof ps db
docker compose -p codexify_guardian_delegation_dbproof run --rm migrator
docker compose -p codexify_guardian_delegation_dbproof run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
```

### Table/column verification

The requested `docker compose exec -T db psql ...` inspection path was attempted during the proof window, but `docker compose exec` hit a local Docker API permission error in this tool environment after the disposable stack was up. Equivalent verification was completed on the same disposable project through one-off `migrator` containers that connected to the same Postgres service:

```sh
docker compose -p codexify_guardian_delegation_dbproof exec -T db psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\dt guardian_delegation_intents"
docker compose -p codexify_guardian_delegation_dbproof exec -T db psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\d guardian_delegation_intents"

docker compose -p codexify_guardian_delegation_dbproof run --rm --entrypoint python migrator -c "import os, psycopg2; conn=psycopg2.connect(os.environ['DATABASE_URL']); cur=conn.cursor(); cur.execute(\"select table_schema, table_name from information_schema.tables where table_name = 'guardian_delegation_intents' order by table_schema, table_name\"); rows=cur.fetchall(); print(rows); cur.close(); conn.close()"

docker compose -p codexify_guardian_delegation_dbproof run --rm --entrypoint python migrator -c "import os, psycopg2; conn=psycopg2.connect(os.environ['DATABASE_URL']); cur=conn.cursor(); cur.execute(\"select column_name, data_type, is_nullable from information_schema.columns where table_name = 'guardian_delegation_intents' order by ordinal_position\"); rows=cur.fetchall(); print(rows); cur.close(); conn.close()"
```

### Disposable teardown

```sh
docker compose -p codexify_guardian_delegation_dbproof down -v --remove-orphans
```

## Observed DB Health Result

Observed DB health after the fix:

```text
NAME                                        IMAGE         COMMAND                  SERVICE   CREATED          STATUS                    PORTS
codexify_guardian_delegation_dbproof-db-1   postgres:15   "docker-entrypoint.s…"   db        12 seconds ago   Up 11 seconds (healthy)   0.0.0.0:5433->5432/tcp, [::]:5433->5432/tcp
```

This is the key closure condition for the original review finding: the disposable DB became `healthy` without any override file or mutation of the normal dev project.

## Observed Migrator Result

Observed `migrator` success on the clean database:

```text
INFO  [alembic.runtime.migration] Running upgrade 384dde1f793c -> 7c21f0a4b8de, add guardian_delegation_intents
[Migrator] Running seed defaults
2026-05-26 22:36:29,247 - seed_defaults - INFO - [Seed] Seeding complete.
[Migrator] Done
```

The full migration walk upgraded the clean DB through both current branches and completed successfully.

## Observed Alembic Heads

Observed Alembic current state after migration:

```text
7c21f0a4b8de (head)
aa4c2e7f91b3 (head)
```

## Observed `guardian_delegation_intents` Table Existence

Observed table presence on the disposable clean database:

```text
[('public', 'guardian_delegation_intents')]
```

## Observed Key Columns

Observed column inventory:

```text
[('intent_id', 'character varying', 'NO'),
 ('thread_id', 'integer', 'NO'),
 ('source_message_id', 'bigint', 'NO'),
 ('project_id', 'integer', 'YES'),
 ('interaction_mode', 'character varying', 'NO'),
 ('approval_mode', 'character varying', 'NO'),
 ('approval_state', 'character varying', 'NO'),
 ('approval_source', 'character varying', 'NO'),
 ('acceptance_status', 'character varying', 'NO'),
 ('intent_status', 'character varying', 'NO'),
 ('run_id', 'character varying', 'YES'),
 ('plan_summary', 'jsonb', 'NO'),
 ('context_basis', 'jsonb', 'NO'),
 ('created_at', 'timestamp with time zone', 'NO'),
 ('updated_at', 'timestamp with time zone', 'NO')]
```

Key Phase 2A columns are present:

- `intent_id`
- `thread_id`
- `source_message_id`
- `project_id`
- `interaction_mode`
- `approval_mode`
- `approval_state`
- `approval_source`
- `acceptance_status`
- `intent_status`
- `run_id`
- `plan_summary`
- `context_basis`
- `created_at`
- `updated_at`

## Proof Window

- Proof start observed: `2026-05-26T22:36:07Z`
- Proof end observed: `2026-05-26T22:37:42Z`

## Normal Dev Volume Safety

Normal dev volumes were not destroyed.

Only the disposable project `codexify_guardian_delegation_dbproof` was brought down with `-v --remove-orphans`, and only the disposable volumes `codexify_guardian_delegation_dbproof_pg_data` and `codexify_guardian_delegation_dbproof_neo4j_data` were removed.

## Caveats

- The proof validates clean DB migration and accurate Compose DB health behavior for the Phase 2A table only.
- It does not change or prove Guardian delegation runtime behavior beyond this schema/ops seam.
- `docker compose exec` was unreliable in this tool environment during the proof window, returning a Docker API permission error after the disposable stack was already running. Equivalent disposable-project verification was completed via one-off `migrator` containers on the same network and database.

## Verdict

PASS

The fresh-DB proof harness is repaired: the disposable DB becomes healthy, the clean database migrates successfully, Alembic current reports the expected heads, and the Phase 2A `guardian_delegation_intents` table exists with the expected columns.
