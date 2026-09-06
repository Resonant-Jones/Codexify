# Persona private-preview live migration

Date: 2026-09-06
Result: **PASS**

`PERSONA_PRIVATE_PREVIEW_DB_UPGRADED`

`APPLICATION_DEPLOYMENT_REQUIRED_BEFORE_RECONCILIATION_RESUME`

## Authority and source

This task explicitly authorized the live database upgrade following the
[successful clone rehearsal](./2026-09-06-persona-private-preview-migration-rehearsal-proof.md).
Source: clean `feature/persona-studio` at
`b85774e78642a9c3d962009f5c63c893e0245443`.
Canonical configuration: `backend/alembic.ini` and `guardian/db/migrations`.
The single-head graph and baked artifact both proved the exact path:

`b2c8d0e3f5a7 → c3d9e1f4a6b8 → d4e0f2a5b7c9`.

Database container identity matched the rehearsal:
`01d246fa2e1a31859c3e34f84138220ec10566966313932e51644e9bfa755936`.
The existing `codexify_private_preview_pg_data` volume was preserved; no
container/volume deletion, database stamping, or manual schema repair occurred.

## Maintenance boundary

Before maintenance, `/health` and `/health/chat` were healthy. Both stack and
tunnel LaunchAgents were loaded and desired-up was present. The stack's
configured root remained `/Volumes/Dev_SSD/Codexify-main`; the old backend image
was `sha256:d104c21e12666f51c62ed623db94c10a801a1808fe96bc2a2cfbc79ea4be5042`.
Full non-secret pre/post container and image inventories are in the restricted
external receipt.

Only `com.resonant.codexify-private-preview` was unloaded from `gui/501`.
`com.resonant.codexify-private-preview-tunnel` remained loaded throughout and
the desired-up marker was not cleared. The project service set other than
PostgreSQL was stopped through Compose, including frontend, origin, backend,
workers, and auxiliary services. Inspection proved only the existing database
container remained running before checkpointing and before each migration.

Compose used project `codexify_private_preview`, project directory
`/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main`, and the existing
secure env file at the prior root. That file was supplied to Compose without
printing or copying its contents. No Persona application services were built
or deployed by this task; only the canonical shared backend migrator image was
built. No old application service was restarted.

## Fresh rollback checkpoint

Checkpoint created and validated before live schema mutation:

`/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/codexify-persona-migration-rehearsal.08qzdrlb/live-20260906T222805Z`

- Capture completed: `2026-09-06T22:28:30Z`.
- Source revision: `b2c8d0e3f5a7`.
- Custom-format dump size: **3,333,556 bytes**.
- Dump SHA-256: `510fd0a781febbd4a3e33d6b52405ddac46b533164cec5ba08e391e90a9dd04f`.
- `pg_dump --format=custom --no-owner --no-acl`: exit 0.
- `pg_restore --list`: exit 0; structurally valid archive.
- Directory mode `0700`; dump, logs, manifests, driver, and receipt mode `0600`,
  verified after execution. No content or credentials are committed.

This is a fresh maintenance-window checkpoint, not reuse of the rehearsal
snapshot. Its original-column manifest independently measured **111 tables /
5,595 rows**, excluding Alembic's ledger. The dump is retained at
`private-preview-source.dump` within that directory. Retention is in the
external temporary backup location used by rehearsal, not a claim of long-term
backup durability or a new restore rehearsal.

## Artifact and canonical migration

`docker compose ... build migrator` used the existing canonical backend
Dockerfile `runtime` target. Qualified image ID:

`sha256:b80ed0e0ba85363665699e3bdf1f29b5c86e6733d40d240f3c31d20b49ee7b98`.

A network-isolated Python invocation inside that image resolved the canonical
Alembic configuration, asserted the sole target head, and asserted both ordered
migration revisions before the live command ran.

Both live invocations used the existing Compose `migrator` service with
`run --rm --no-deps`, retaining its canonical Python entrypoint and
`/app/backend/scripts/docker/run_migrator.py` command. The service's backend
script bind came from the Persona worktree and migration files came from the
qualified baked image. The service database target remained the existing
project database. No application dependencies were started.

- First migrator exit: **0**.
- Final live revision: **`d4e0f2a5b7c9`**.
- Second canonical migrator exit: **0**; revision unchanged.
- Both canonical runs included their normal seed-defaults step. No stamp,
  workaround, fallback bootstrap, or manual repair was used.

## Preservation and readback

The same algorithm as rehearsal records original columns in ordinal order,
projects every row through those columns with PostgreSQL `row_to_json`, sorts
UTF-8 row bytes deterministically, and hashes newline-framed rows with SHA-256.
Duplicates remain represented. Detailed manifests remain outside Git.

| Gate | Result |
| --- | --- |
| Original tables before / after / no-op | 111 / 111 / 111 |
| Original rows before / after / no-op | 5,595 / 5,595 / 5,595 |
| Original-column count/digest differences | 0 after upgrade; 0 after no-op |
| Missing original tables/columns | 0 |
| Added tables | `persona_profile_revisions`, `persona_profile_bindings` only |
| Added original-table columns | `persona_profiles.current_revision`, `chat_threads.active_profile_revision` only |
| Unvalidated public constraints | 0 |
| Full post-upgrade manifest equality across no-op | exact, including added columns/tables |

Original-column manifest SHA-256:
`ac6329e9555557f279fcdcb1d04540c0e05cc2ba95883c4d6b95fc9c016a62b8`.

Target readback contains 113 non-ledger tables and 5,598 rows: three legacy
profiles gained revision rows; no binding row was assigned in this
multi-account database. This matches the inspected migration's fail-closed
single-account binding rule. No ownership recovery or account-specific Persona
visibility is implied. Browser saves/readback remain unproven.

## Final operator posture and rollback

- Existing PostgreSQL container remains running at `d4e0f2a5b7c9`.
- All old private-preview application/frontend/origin/worker services remain
  stopped; only PostgreSQL is running in this Compose project.
- Stack reconciler remains **unloaded**.
- Tunnel agent remains **loaded**; desired-up remains **present**.
- Fresh rollback checkpoint retained. No rollback occurred or was needed.
- Origin health is intentionally unavailable during this handoff; pre-upgrade
  health was good. Database readback, not old application startup, proves the
  post-migration state.

**Operator warning:** do not resume periodic reconciliation or restart the old
application lineage. Deploy and qualify the matching Persona runtime first.

## Validation and limits

`python3 scripts/validate_docs.py`, working diff check, and staged diff check
passed. Only this receipt and `00-current-state.md` changed. ADR-082 manifest,
immutable revision, server-owned binding, account, and runtime-authority
invariants remain intact. Original user data was preserved exactly; only
Alembic-governed schema/backfill state changed. No migration, script, Compose,
profile, frontend, or runtime source was edited. No release support advances.

Warnings: Docker build metadata was initially sandbox-denied; an approved
escalated build succeeded before migration. No migration or preservation
failure occurred. Pi was not used for this live mutation task under the skill's
production-operation boundary; no credentials or database content were delegated.

Next prerequisite: deploy the matching Persona branch runtime, qualify its
lineage and config mount, prove `/api/persona-profiles`, and then run
authenticated browser save/readback before restoring periodic reconciliation.
