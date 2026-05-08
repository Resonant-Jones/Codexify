# Tool Jobs Cleanup Live Proof - 2026-04-28

**Artifact date/time:** 2026-04-28  
**Runtime path:** supported local Docker Compose stack with `db`, `redis`, `neo4j`, and `migrator`  
**Proof class:** schema cleanup live proof  
**Scope:** dedicated `tool_jobs` removal proof only

## 1. Scope

This artifact proves that the dedicated cleanup migration for the legacy `tool_jobs` table behaves correctly on the supported local Docker Compose path.

It covers:

* downgrade from cleanup head `d7e8f9a0b1c2` to pre-cleanup mergepoint `b3c4d5e6f7a8`
* restoration of the historical `tool_jobs` table shape on downgrade
* re-upgrade from `b3c4d5e6f7a8` to cleanup head `d7e8f9a0b1c2`
* confirmation that `tool_jobs` is absent after cleanup
* confirmation that canonical command-bus durability tables remain present:

  * `command_runs`
  * `command_run_events`

It does **not** prove:

* clean-start bootstrap for the full runtime
* assistant completion or upload -> embed -> retrieve behavior
* packaged runtime behavior
* worker or backend feature correctness beyond this schema seam

## 2. Environment

| Item                                 | Value                                  |
| ------------------------------------ | -------------------------------------- |
| Artifact date                        | 2026-04-28                             |
| Runtime path                         | local Docker Compose                   |
| Database                             | Postgres in Compose                    |
| Compose services used for this proof | `db`, `redis`, `neo4j`, `migrator`     |
| Cleanup migration under test         | `d7e8f9a0b1c2_drop_tool_jobs_table.py` |
| Pre-cleanup revision used for proof  | `b3c4d5e6f7a8`                         |

## 3. Purpose of this Proof

The repo already removed the live `ToolJob` ORM surface and documented `tool_jobs` as historical residue. This proof closes the remaining live-schema question:

* can the cleanup migration faithfully restore the historical table on downgrade?
* can it remove the table again on upgrade?
* does it leave the canonical command-bus durability tables intact?

This artifact exists so the answer is based on live runtime evidence rather than code inspection alone.

## 4. Exact Commands Run

### A. Downgrade to the pre-cleanup mergepoint

```bash
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini downgrade b3c4d5e6f7a8
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt tool_jobs"
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d tool_jobs"
```

### B. Re-upgrade to current heads

```bash
docker compose run --rm migrator
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt tool_jobs"
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt command_runs"
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt command_run_events"
```

## 5. Observed Downgrade Results

The downgrade completed successfully:

```text
INFO  [alembic.runtime.migration] Running downgrade d7e8f9a0b1c2 -> b3c4d5e6f7a8, drop legacy tool_jobs table
```

Revision state after downgrade:

```text
f2b3c4d5e6f9 (head)
b3c4d5e6f7a8 (mergepoint)
```

`tool_jobs` existed after downgrade:

```text
List of relations
 Schema |   Name    | Type  |  Owner
--------+-----------+-------+----------
 public | tool_jobs | table | codexify
```

Observed restored table shape:

```text
Table "public.tool_jobs"
    Column    |           Type           | Collation | Nullable | Default
--------------+--------------------------+-----------+----------+---------
 id           | character varying(36)    |           | not null |
 tool_name    | text                     |           | not null |
 status       | text                     |           | not null |
 request_json | jsonb                    |           | not null |
 result_json  | jsonb                    |           |          |
 error        | text                     |           |          |
 error_json   | jsonb                    |           |          |
 created_at   | timestamp with time zone |           | not null | now()
 updated_at   | timestamp with time zone |           | not null | now()

Indexes:
    "tool_jobs_pkey" PRIMARY KEY, btree (id)
    "ix_tool_jobs_created_at" btree (created_at)
    "ix_tool_jobs_status" btree (status)

Check constraints:
    "tool_jobs_status_check" CHECK (
      status = ANY (
        ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text]
      )
    )
```

### Downgrade verdict

**PASS**

The cleanup migration’s downgrade path restored the historical `tool_jobs` table with the expected:

* columns
* primary key
* indexes
* status check constraint

## 6. Observed Re-Upgrade Results

The re-upgrade completed successfully:

```text
INFO  [alembic.runtime.migration] Running upgrade b3c4d5e6f7a8 -> d7e8f9a0b1c2, drop legacy tool_jobs table
[Migrator] Done
```

Revision state after re-upgrade:

```text
d7e8f9a0b1c2 (head)
f2b3c4d5e6f9 (head)
```

`tool_jobs` was absent after re-upgrade:

```text
Did not find any relation named "tool_jobs".
```

Canonical command-bus durability tables remained present:

```text
List of relations
 Schema |     Name     | Type  |  Owner
--------+--------------+-------+----------
 public | command_runs | table | codexify
```

```text
List of relations
 Schema |        Name        | Type  |  Owner
--------+--------------------+-------+----------
 public | command_run_events | table | codexify
```

### Re-upgrade verdict

**PASS**

The cleanup migration’s upgrade path removed `tool_jobs` cleanly while preserving the canonical command-bus durability tables.

## 7. Overall Verdict

Status: **PASS**

This proof demonstrates that the `tool_jobs` cleanup migration is live-proven on the supported local Docker Compose path for this schema seam.

What is now proven:

* downgrade from cleanup head restores the historical `tool_jobs` table
* restored table shape matches the intended historical schema contract
* re-upgrade removes `tool_jobs` cleanly
* `command_runs` and `command_run_events` remain intact

What this artifact does **not** claim:

* that broader beta release proof is complete
* that fresh live proof for assistant completion, upload -> embed -> retrieve, and health surfaces is no longer required
* that packaged-runtime proof is covered by this artifact

## 8. Operational Interpretation

This artifact closes the specific storage-truth gap around legacy `tool_jobs` cleanup.

It supports the narrower claim that:

* the schema cleanup is implemented
* the rollback path is sound
* the forward path is sound
* the command-bus durability tables are not collateral damage

This artifact should be read as **schema-seam proof**, not as a substitute for the broader current-`main` release evidence pack.

## 9. Suggested Follow-Through

* Keep this artifact alongside the existing migration proof set.
* Reference it when discussing the closure of the historical `tool_jobs` cleanup.
* Do not widen the release claim beyond this seam without fresh current-`main` live proof for:

  * assistant completion
  * upload -> embed -> retrieve
  * health surfaces
  * supported-profile alignment
