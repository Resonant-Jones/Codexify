TASK-2026-02-08-002 — Add DB/index support for chronological queries

Goal: Make timeline retrieval fast + deterministic.
This change belongs in: the schema/migration layer (e.g. /guardian/db/models/... or your Alembic migrations), whichever is authoritative in Codexify.
Instructions:
 1. Add indexes:
 • (source_thread_id, turn_index)
 • (source_thread_id, source_created_at)
 2. Add uniqueness where safe:
 • source_message_id unique (or (source_thread_id, source_message_id) if needed)
 3. Ensure nullable behavior is safe for legacy rows (backfill strategy optional but do not implement backfill here unless trivial).

Tests: pytest -v (backend).
Git:
git add <schema_or_migration_files_here>
git commit -m "DB: index and constrain migrated message chronology fields"

Expected Output:
 • Schema/migration changes summary
 • Test results
 • Commit hash

# TASK-2026-02-08-002 — Add DB/index support for chronological queries

## Goal
Make timeline queries fast, deterministic, and safe for reruns by adding the minimal set of indexes/constraints needed for chronological access patterns.

## This change belongs in
The schema/migration layer that is authoritative in Codexify (models + migrations). Examples include:
- `/guardian/db/models/...`
- Alembic migration files (if used)

(Use the repo’s established migration mechanism; do not invent a new one.)

## Instructions

### 1) Add indexes for chronological access
Add the following indexes on the migrated message storage table (use the repo’s actual table/column names):

- Composite index: `(source_thread_id, turn_index)`
  - Supports fast “neighbor window” fetch by turn index within a thread.
- Composite index: `(source_thread_id, source_created_at)`
  - Supports fast chronological scans within a thread by timestamp.

Index requirements:
- These must be additive and non-destructive.
- Use the DB’s standard index creation path used elsewhere in the repo.
- Prefer concurrent/safe index creation if your migration system supports it.

### 2) Add uniqueness constraints for idempotent imports (where safe)
Add uniqueness so reruns do not duplicate imported rows.

Preferred (best):
- Unique on `source_message_id` if it is globally unique across all threads.

Fallback (safer if only unique per thread):
- Composite unique: `(source_thread_id, source_message_id)`

Constraint requirements:
- Do not guess: choose the option that matches your import format.
- If legacy data may violate the constraint, implement a safe path (see §3).

### 3) Legacy/null safety (no backfill in this task)
This task must not perform data backfills unless they are trivial and guaranteed safe.

Rules:
- If `turn_index` or `source_created_at` can be null for legacy rows:
  - Ensure indexes/constraints do not fail on nulls.
  - Prefer partial indexes where appropriate (e.g. `WHERE turn_index IS NOT NULL`), if your DB/migration tooling supports it.
- If uniqueness might be violated by existing rows:
  - Do not silently drop data.
  - Either:
    - (a) choose the composite uniqueness strategy, or
    - (b) make the constraint deferred/added only after a follow-up cleanup task (document the need explicitly in migration notes).

### 4) Scope boundary
- Do not change migration logic (TASK-001 handles ingestion fields).
- Do not change retrieval/rendering behavior.
- No data cleanup/backfill in this task (that would be a separate task).

## Tests
Backend tests:

```bash
pytest -v
```

## Post-run verification (required)
After applying the migration, validate:

- Index existence:
  - `(source_thread_id, turn_index)` index exists and is used by query plans for window fetches.
  - `(source_thread_id, source_created_at)` index exists and supports chronological scans.
- Uniqueness enforcement:
  - Attempting to insert a duplicate for the idempotency key fails (or is handled by upsert logic elsewhere).

(Use the repo’s actual table/column names and verification method—SQL queries, DB introspection, or migration tooling output.)

## Git
```bash
git add <schema_or_migration_files_here>
git commit -m "DB: index and constrain migrated message chronology fields"
```

## Expected Output
- Summary of schema/migration changes (indexes + constraints)
- Test results
- Commit hash