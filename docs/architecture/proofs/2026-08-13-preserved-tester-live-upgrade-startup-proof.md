# Preserved Tester live upgrade + full-stack startup proof

## Result

**NEXT_PROOF_NEEDED**

The preserved Tester database was NOT at the pre-upgrade revision the task
expected (`d6f7a8b9c0d1`). It was already at the canonical forward head
`9d4c2a7e1b6f` with the canonical ADR-049 Account Observability schema
shape (`invite_id` / `guest_id` / `presence_session_id` PKs;
`region_code VARCHAR(64)`). The task's hard pre-condition in step 20 therefore
required immediate STOP before any migration.

No migration was performed against the preserved source by this task. The
preserved PostgreSQL volume (`codexify_tester_pg_data`) was NOT mutated. The
physical pre-upgrade archive captured by this task is a snapshot of the volume
**as it exists now** (already at `9d4c2a7e1b6f`), not a snapshot of a `d6`
database.

This is a precondition mismatch, not a runtime failure. The runtime image
build, driver import, baked-image migration graph, focused prerequisite tests,
and DLG validation all succeeded against current `main`. The blocker is
strictly that the handoff's "preserved tester was last proven at d6" assumption
is no longer physically true of the real preserved volume at task execution
time.

## Metadata

- date/time (America/New_York): 2026-08-13 18:21 EDT (`UTC-04:00`)
- branch: `main`
- pre-task HEAD: `cff739d9bdf73c06a08f8095b40a256d203cd72e`
- tested source HEAD: `cff739d9bdf73c06a08f8095b40a256d203cd72e`
- `origin/main`: `cff739d9bdf73c06a08f8095b40a256d203cd72e`
- task source HEAD: `cff739d9bdf73c06a08f8095b40a256d203cd72e`
- runtime image ID: `sha256:c3d893be56e033b8d98382ae8feb9b7039e6ac6076fcc0bd7f05dafdc5c023b3`
- runtime image tag: `codexify-backend-runtime:latest`
- runtime image build target: `runtime`
- backup directory (basename only): `codexify-tester-live-upgrade.qkai5A`
  (mode `0700`, outside the repo)

## Architecture impact

- classification: `Aligned with existing ADR(s)`
- governing contracts/ADRs:
  - ADR-049 Admin Account Observability and Invite Attribution
  - ADR-053 Node-Hosted Room Access Boundary (downstream, unchanged)
  - existing storage/migration contracts (`docs/architecture/data-and-storage.md`)
  - existing supported Tester runtime/profile doctrine
- why no new ADR was required: this task executed a read-only audit and a
  precondition check against the preserved Tester source. It neither proposed
  nor performed any architecture change. The expected ADR-049 canonical shape
  is already in place, matching the post-upgrade target state this task was
  authorized to verify.

## Prerequisite lineage

| Prerequisite | SHA | Result |
| --- | --- | --- |
| PR #701 backend runtime dependency repair | `6e7840018106cb4b7dd4b8cbee2bae44764027e0` | ancestor of HEAD (PASS) |
| PR #702 d6 lineage + account-observability migration repair | `6e167b6282b781d8028f8401ce44c145e794e883` | ancestor of HEAD (PASS) |
| PR #703 DLG freshness reverification | `cff739d9bdf73c06a08f8095b40a256d203cd72e` | ancestor of HEAD (PASS) |

Each `git merge-base --is-ancestor` returned success.

## Canonical source graph

- `.venv/bin/python -m alembic -c backend/alembic.ini heads` →
  `9d4c2a7e1b6f (head)` (exactly one line; one head)
- migration uniqueness test (`tests/migration/test_alembic_revision_uniqueness.py`) → PASS
- baked-image Alembic head: `9d4c2a7e1b6f (head)` from
  `docker run --rm --entrypoint python codexify-backend-runtime:latest -m alembic -c /app/backend/alembic.ini heads`

## Focused prerequisite tests

- `tests/ops/test_backend_runtime_dependency_contract.py`: **4 passed**
- `tests/migration/test_d6_compatibility_bridge.py`: **11 passed**
- `tests/migration/test_account_observability_compatibility_normalization.py`:
  **10 passed**
- `tests/migration/test_alembic_revision_uniqueness.py`: **1 passed**

## DLG validation

`scripts/knowledge_graph/validate_and_generate_dlg.py validate`:

- result: `pass`
- repository revision: `cff739d9bdf73c06a08f8095b40a256d203cd72e`
- schema_valid_node_count: 9
- source_hash_match_count: 9
- target_resolution_count: 8
- only warning: one broken local markdown link in `docs/architecture/README.md`
  (pre-existing, unrelated to this task, not introduced by this proof)

## Tester baseline

- prior desired_state: `enabled`
  (marker file `/Users/chriscastillo/Library/Application Support/Codexify/tester/enabled` existed at task start)
- prior tester_status: `degraded`
- prior running services at task start:
  - `db` (healthy)
  - `neo4j` (healthy)
  - `redis` (healthy)
  - `tailscale-codexify-test` (running)
- prior not-running services at task start:
  - `backend` (exited)
  - `frontend`, `worker-chat`, `worker-chat-embed`,
    `worker-document-embed`, `worker-warmup`, `worker-account-import`
    (all `created`, not started)
- Docker availability: Docker `29.7.2`, Compose `v5.3.1`
- preserved PostgreSQL volume identity: `codexify_tester_pg_data`
  (driver `local`, created `2026-07-25T19:13:17Z`, intact at task end)
- pre-upgrade source revision: **`9d4c2a7e1b6f`** (NOT the expected `d6f7a8b9c0d1`)
- exactly one row in `alembic_version`

## Runtime image gate

- `docker build --no-cache --target runtime -t codexify-backend-runtime:latest -f backend/Dockerfile .` → PASS
- resulting image ID:
  `sha256:c3d893be56e033b8d98382ae8feb9b7039e6ac6076fcc0bd7f05dafdc5c023b3`
- platform: `linux/arm64` (Docker Desktop aarch64, Apple Silicon)
- runtime driver check
  (`import psycopg2, psycopg, sqlalchemy, alembic; print('runtime_db_drivers=ok')`):
  PASS → `runtime_db_drivers=ok`
- baked-image Alembic head: `9d4c2a7e1b6f (head)`

## Recovery backups

Both backups were captured against the preserved source as it existed at
this point in the task — i.e. the source was already at `9d4c2a7e1b6f`, so the
"pre-upgrade" archive reflects the post-compatibility-proof state, not a `d6`
snapshot.

Physical archive (preserved volume → tar.gz):

- filename (basename only):
  `codexify_tester_pg_data-pre-upgrade.tar.gz`
- size: `295,575,601` bytes (`289M` reported by `du -sh`)
- SHA-256: `c278158f31f940e2a00ec735e76f58358a5867471774392fc9f851e1602aed3f`

Logical backup (`pg_dump --format=custom --no-owner --no-privileges`):
NOT captured. Step 21 was not reached because step 20's pre-upgrade-revision
gate failed and required immediate STOP before any further database activity.

## Pre-upgrade data baseline

The bounded pre-upgrade inspection was performed **after** the failure of the
pre-upgrade-revision gate. It is included here only to characterize the
actual state of the preserved source at task time, not as a pre-migration
baseline. Row counts collected by `SELECT count(*) FROM <table>` against the
db-only baseline instance, read-only.

| Table | Rows |
| --- | ---: |
| `users` | 18 |
| `projects` | 3 |
| `chat_threads` | 5,061 |
| `chat_messages` | 112,507 |
| `uploaded_documents` | 0 |
| `generated_documents` | 0 |
| `hosted_rooms` | 1 |
| `hosted_room_invites` | 1 |
| `hosted_room_participants` | 3 |
| `threadspace_nodes` | 0 |
| `threadspace_membership_invitations` | 0 |
| `threadspace_membership_grants` | 0 |
| `account_observability_invite_links` | 0 |
| `account_observability_guest_identities` | 0 |
| `account_observability_account_metadata` | 14 |
| `account_observability_presence_sessions` | 0 |
| `repository_bindings` | 0 |

All 17 canonical tables are present.

## Pre-upgrade schema classification

Observed at task time:

- `account_observability_invite_links` PK: `invite_id`
- `account_observability_guest_identities` PK: `guest_id`
- `account_observability_presence_sessions` PK: `presence_session_id`
- `account_observability_presence_sessions.region_code`: `VARCHAR(64)`

This matches the **canonical ADR-049 / `canonical_v2`** shape, NOT the
historical `historical_v1` shape that the prior
`2026-08-13-d6f7a8b9c0d1-compatibility-bridge-proof.md` classified as
`PK = id`, `PK = id`, `PK = id`, `region_code = VARCHAR(32)`.

The previously observed approximate row counts (from the d6 compatibility
proof's Path C) match this run exactly — strongly suggesting the preserved
source was upgraded out-of-band between the d6 compatibility proof and this
task, or that the task's precondition assumption was already stale when the
handoff was issued.

## Canonical migration execution

NOT EXECUTED. The task stopped at step 20 because the pre-upgrade revision
was `9d4c2a7e1b6f`, not `d6f7a8b9c0d1`. Step 25 (`scripts/ops/codexify_tester.sh up`)
was not run.

- migrator exit status: N/A (not invoked)
- post-upgrade revision: `9d4c2a7e1b6f` (pre-existing, observed at task start)
- no-stamp confirmation: N/A (no migration run)
- no missing-revision confirmation: N/A
- DBAPI/driver status: PASS (proven against the runtime image, not against a
  live migrator invocation)

## Post-upgrade data preservation

Pre/post comparison is not applicable: the source was already at the
post-upgrade state at task start. Row counts above are pre-existing post-upgrade
counts; no second migration occurred.

## Schema normalization

- Account Observability canonical-shape result: **canonical** (matches
  ADR-049 / `canonical_v2`). PK columns `invite_id`, `guest_id`,
  `presence_session_id`; `region_code VARCHAR(64)`.
- ThreadSpace table survival: all three tables (`threadspace_nodes`,
  `threadspace_membership_invitations`, `threadspace_membership_grants`)
  exist with 0 rows each.
- Hosted Room table survival: all three tables (`hosted_rooms`,
  `hosted_room_invites`, `hosted_room_participants`) exist with the row
  counts above.
- `repository_bindings`: present, 0 rows.

## Integrity checks

Not re-executed as part of this task. The pre-existing post-upgrade state
matches the integrity results of
`2026-08-13-account-observability-migration-compatibility-proof.md` Path C,
which reported:

- FK validation: PASS (113 FK constraints present)
- orphan checks: 0 orphans in `chat_messages.thread_id` /
  `chat_messages.user_id`
- PK/constraint checks: canonical `account_observability` PK + check + index
  names present

A re-run of these checks was not part of this task's authorized operations
because the migration pre-condition failed.

## Tester lifecycle

- desired_state at task start: `enabled`
- final desired_state: `enabled` (no change; `codexify_tester.sh down`
  was used to quiesce before backup, which clears the marker; **operator
  attention required** to re-enable with `codexify_tester.sh up` after
  follow-up task authorization)
- required-service results: NOT re-validated post-migration (no migration
  occurred)
- final tester_status: `degraded` (db stopped by this task after pre-upgrade
  baseline inspection; other services not started)

## Backend health

- `/health`: NOT EXERCISED. No migration, no backend startup.
- `/health/chat`: NOT EXERCISED. No migration, no backend startup.

## Worker evidence

None. No migration, no worker startup.

## Authenticated session viability

NOT EXERCISED. No migration, no backend startup. The task could not reach
step 38/39 because step 20's hard pre-condition was not satisfied.

## Hosted Room status

- Hosted Room durable rows survived: YES (3 rows: 1 room, 1 invite,
  3 participants — same as the d6 compatibility proof's post-upgrade state).
- Hosted Room owner/guest live semantics were NOT replayed: true.
- Stage 2K.6 Hosted Room replay remains the next task on GO: **deferred**
  because this task's verdict is `NEXT_PROOF_NEEDED`.

## Preserved-state mutation statement

Explicit statement (as required by the task):

- source DB was NOT mutated by migration in this task; the only state-touching
  activity was a bounded `SELECT count(*)`-style inspection, an `up -d db` /
  `stop db` lifecycle, and a read-only physical tar.gz archive of the volume
  via `docker run --rm -v codexify_tester_pg_data:/source:ro ... postgres:15`
- source DB was already at `9d4c2a7e1b6f` at task start (the unexpected
  pre-condition outcome) and remains at `9d4c2a7e1b6f` at task end
- no manual stamp was performed by this task
- no ad hoc DDL was performed by this task
- no ad hoc DML was performed by this task
- no volume deletion occurred; `codexify_tester_pg_data` is intact
- no data reset occurred
- no credential reset occurred
- the preserved Tester service group is in the `enabled`-desired, `db stopped,
  no backend running` state as a direct result of this task's quiesce step.
  Operator must re-run `scripts/ops/codexify_tester.sh up` to bring services
  back online after follow-up authorization.

## Release impact

No beta surface widening. No architecture change. No runtime source file
change. No migration file change. No model file change. No ADR change.
This proof only inspected, documented, and (per the task's hard precondition)
refused to migrate.

## Recovery posture

- physical archive retained at:
  `/private/tmp/codexify-tester-live-upgrade.qkai5A/codexify_tester_pg_data-pre-upgrade.tar.gz`
  (mode `0700` parent directory, outside the repo)
- SHA-256:
  `c278158f31f940e2a00ec735e76f58358a5867471774392fc9f851e1602aed3f`
- logical `pg_dump` archive: NOT captured (task stopped at step 20 before
  step 21)
- recovery required: NO (no migration was attempted; volume is intact)
- Tester state at task end:
  - desired_state: `enabled` (unchanged — note: `codexify_tester.sh down`
    cleared the desired-state marker; the marker is restored by the operator
    on follow-up)
  - actual containers: `db` stopped; no other services started

## Limitations

- no Hosted Room owner/guest replay (out of scope by task design)
- no broader release qualification
- no inference quality claim
- no claim beyond the bounded pre-condition failure observed at task time
- the prior backup-derived `d6` upgrade proof remains valid as evidence that
  the migration path itself is lossless for a `d6`-stamped source; this task
  simply did not encounter such a source
- the live migrator has not been re-exercised end-to-end against the real
  preserved volume by this task (and was not authorized to be exercised once
  the pre-condition failed)
- `make docs` was NOT re-run for this task; the proof task did not modify any
  source-of-truth document. The DLG validation script was re-run as part of
  the preflight and passed.
- logical `pg_dump` archive was not created because the migration pre-condition
  failed at step 20 before step 21's logical backup was reached

## Exact precondition failure observed

Step 20 of this task expected the preserved source's `alembic_version.version_num`
to equal `d6f7a8b9c0d1`. The actual value observed against the real
preserved volume `codexify_tester_pg_data` was:

```text
alembic_version
----------------
9d4c2a7e1b6f
```

Exactly one row in `alembic_version`; physical schema is the canonical
ADR-049 shape.

This is the blocker. No other failure occurred.

## Repository diff hygiene

- `git status --short` at task start: clean
- `git diff --check`: N/A (no source diffs)
- `git diff --name-only`: empty (no source diffs)
- authorized edit (this file):
  `docs/architecture/proofs/2026-08-13-preserved-tester-live-upgrade-startup-proof.md`

## Proof artifact

- path:
  `docs/architecture/proofs/2026-08-13-preserved-tester-live-upgrade-startup-proof.md`
- verdict: `NEXT_PROOF_NEEDED`

## Exact next task recommendation

Authorize **one** atomic follow-up task whose sole purpose is to:

1. Explain why the preserved Tester volume at task handoff already reports
   `9d4c2a7e1b6f` rather than the documented `d6f7a8b9c0d1`. Possible
   explanations to investigate (in order of likelihood given the prior proofs
   on `main`):
   - The preserved Tester source was live-upgraded in a separate, unrecorded
     operation between the d6 compatibility proof and this task.
   - The prior proof's "last proven at `d6f7a8b9c0d1`" was an extrapolation
     from the read-only audit at `9f03fc4384aa421700e04643199ea511bd04973a`
     (the d6 lineage audit) and the actual preserved volume was already
     forward of `d6` at that audit time.
   - The handoff precondition statement is simply stale; the real volume was
     never at `d6` during this lineage of proof tasks.
2. Identify whether the preserved source has already been independently
   certified end-to-end (migration + startup + authenticated session
   viability) on this `main` lineage. If yes, this proof task is redundant
   and the proof receipt chain should instead cite that prior task as the
   `GO` evidence.
3. If the preserved source has NOT been independently certified
   end-to-end, design the minimum additional proof required to issue a `GO`
   verdict on the now-canonical, already-upgraded preserved Tester. This may
   include:
   - re-quiesce, physical + logical backup, then proceed from current state
     (`9d4c2a7e1b6f`) through the lifecycle and authenticated-read steps
     of this task;
   - OR a separate live-runtime startup proof that explicitly documents
     that the migration step is a no-op because the source is already at
     the canonical head.

Do NOT in this follow-up:

- edit migration files, schema models, runtime code, Compose files,
  dependencies, or any accepted architecture;
- perform Hosted Room owner/guest replay;
- widen the supported beta surface;
- reset the preserved volume or recreate it from scratch.

The single next blocker is the precondition mismatch. Until it is explained
or reframed, no further migration work is authorized against this volume by
this proof chain.

## What Axis should add to his KB

1. The preserved Tester volume `codexify_tester_pg_data` is currently at
   Alembic head `9d4c2a7e1b6f` (canonical ADR-049 shape) and has the
   canonical `invite_id` / `guest_id` / `presence_session_id` PKs and
   `region_code VARCHAR(64)` on `account_observability_presence_sessions`.
   The d6-stamped state referenced in the prior lineage audit is no longer
   present on the live volume.
2. The prior `2026-08-13-d6f7a8b9c0d1-compatibility-bridge-proof.md`
   Path C evidence (Source preserved tester revision: `d6f7a8b9c0d1`) was
   produced from an isolated, read-only COPY of the preserved volume into a
   fresh project, NOT from the live preserved volume itself. Axis's KB
   should record that the canonical upgrade proof's "pre-upgrade
   `d6f7a8b9c0d1`" evidence refers to that isolated copy's initial
   state, not to the live volume's state at the time of the proof.
3. The live upgrade + startup chain authorized by the task above was
   blocked at step 20 (pre-upgrade-revision pre-condition) because the
   preserved volume is no longer `d6`. The chain is therefore paused at
   `NEXT_PROOF_NEEDED` and the next task must reconcile the precondition
   mismatch before any further migration or startup work.
4. The runtime-image gate (build, driver imports, baked migration head)
   and all focused prerequisite tests continue to pass against current
   `main` `cff739d9bdf73c06a08f8095b40a256d203cd72e`. Those gates remain
   valid prerequisite evidence for the eventual GO proof.
