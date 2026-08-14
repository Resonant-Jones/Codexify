# Preserved Tester canonical startup + authenticated viability proof

## Result

**NEXT_PROOF_NEEDED**

The preserved Tester database IS already canonical at `9d4c2a7e1b6f`
with canonical ADR-049 Account Observability shape and passes bounded
FK/orphan integrity. The canonical migrator ran successfully and exited 0
against the already-current database. The canonical Tester lifecycle starts
the dependent services (`db`, `neo4j`, `redis`, `tailscale-codexify-test`)
to healthy, and `desired_state=enabled` is set.

However, the supported `backend` container repeatedly exits with status `3`
during initialization, immediately after the
`backend.rag.embedder [embedder] backend=sentence_transformer model=/models/bge-large-en-v1.5`
log line. The Rust panic message is:

```text
thread '<unnamed>' panicked at rust/sqlite/src/db.rs:157:42:
range start index 10 out of range for slice of length 9
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

This panic is reproducible across three independent lifecycle attempts in
this task. Because the backend never reaches the FastAPI serving loop,
`/health`, `/health/chat`, and authenticated `GET /api/dashboard/snapshot`
could not be exercised. The required-service health gate therefore cannot
be satisfied.

Per the task's failure posture: a single first material blocker is recorded
and not repaired inside this task.

## Metadata

- date/time (America/New_York): 2026-08-13 18:56 EDT (`UTC-04:00`)
- branch: `main`
- pre-task HEAD: `dec85ac839550a9fcfd25ee73304e1d83eb71fb3`
  (the prior proof receipt commit, locally available as prerequisite evidence)
- tested source HEAD: `dec85ac839550a9fcfd25ee73304e1d83eb71fb3`
- `origin/main`: `cff739d9bdf73c06a08f8095b40a256d203cd72e`
- prior local proof commit `dec85ac...`: AVAILABLE
  (`git cat-file -e dec85ac839550a9fcfd25ee73304e1d83eb71fb3^{commit}` → 0)
- runtime image: same `codexify-backend-runtime:latest` baked by the prior
  task at SHA-256 `c3d893be56e033b8d98382ae8feb9b7039e6ac6076fcc0bd7f05dafdc5c023b3`
  (not rebuilt by this task; current main source matches `origin/main` for
  all runtime/migration/Compose/auth files)

## Architecture impact

- classification: `Aligned with existing ADR(s)`
- governing ADRs/contracts:
  - ADR-049 Admin Account Observability and Invite Attribution (canonical
    schema verified)
  - ADR-053 Node-Hosted Room Access Boundary (downstream, unchanged)
  - existing storage/migration contracts (`docs/architecture/data-and-storage.md`)
  - existing supported Tester runtime/profile doctrine
  - Guardian authentication/session authority
  - `docs/architecture/guardian-dashboard-snapshot-contract.md`
- reason: this task exercised already-accepted runtime/migration/auth/
  dashboard contracts against the real preserved Tester source. It proposed
  no architecture change. The observed Rust panic is a runtime defect in
  the existing embedder / ChromaDB rust-binding initialization, not an
  architecture, schema, identity, semantics, or contract concern.

## Current preserved-state truth

- preserved volume: `codexify_tester_pg_data` (driver `local`,
  created `2026-07-25T19:13:17Z`, intact at task end)
- current Alembic revision: `9d4c2a7e1b6f` (one row, verified twice:
  once pre-startup, once post-startup)
- canonical schema classification: **canonical ADR-049 / `canonical_v2`**
  - `account_observability_invite_links` PK: `invite_id`
  - `account_observability_guest_identities` PK: `guest_id`
  - `account_observability_presence_sessions` PK: `presence_session_id`
  - `account_observability_presence_sessions.region_code`: `VARCHAR(64)`

Explicit statement: the current preserved database was already canonical
before this task and no d6 → head migration was attempted here. The
migrator ran successfully as a no-op (or near-no-op) and exited 0.

## Historical-state note

Earlier fresh read-only snapshots of the same named preserved volume
observed `d6f7a8b9c0d1`:

- `2026-08-12-d6f7a8b9c0d1-migration-lineage-audit.md` Path A: isolated
  copy of the preserved volume reported `d6f7a8b9c0d1`
- `2026-08-13-d6f7a8b9c0d1-compatibility-bridge-proof.md` Path C: backup-
  derived clone reported `d6f7a8b9c0d1` as the source revision

The live preserved volume subsequently advanced to `9d4c2a7e1b6f`. The
exact actor/time of that advance is not established by this task and is
not required to evaluate the current task's goal. No fresh evidence in
this task's bounded logs narrows the actor.

## Recovery backups

Physical archive (read-only tar.gz of preserved volume):

- filename: `codexify_tester_pg_data-pre-upgrade.tar.gz`
- path: `/private/tmp/codexify-tester-live-upgrade.qkai5A/codexify_tester_pg_data-pre-upgrade.tar.gz`
- size: `295,575,601` bytes
- SHA-256: `c278158f31f940e2a00ec735e76f58358a5867471774392fc9f851e1602aed3f`
- reuse status: REUSED (verified by `shasum -a 256` exact match against the
  prior task's expected SHA-256)

Logical pg_dump backup (custom format, `pg_dump --no-owner --no-privileges`):

- filename: `codexify-tester-canonical-pre-startup.dump`
- path: `/private/tmp/codexify-tester-live-upgrade.qkai5A/codexify-tester-canonical-pre-startup.dump`
- size: `134,431,625` bytes
- SHA-256: `201b1032c21754d250766eae0d23379cc88e28922f1034bfffdf03703c2cbb7d`
- `pg_restore -l` validation: PASS (executed via `postgres:15` image;
  942 TOC lines, 931 TOC entries)

Both backups retained at task end (mode 0700 parent directory).

## Canonical data baseline (pre-startup)

Read from `codexify_tester_pg_data` via the db-only baseline instance,
bounded `count(*)` only, no row bodies.

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

## Canonical schema verification

- Alembic revision: `9d4c2a7e1b6f` (exactly one row in `alembic_version`)
- Account Observability canonical shape: PASS
  - `invite_id` PK on `account_observability_invite_links`
  - `guest_id` PK on `account_observability_guest_identities`
  - `presence_session_id` PK on `account_observability_presence_sessions`
  - `region_code` = `VARCHAR(64)`
- ThreadSpace presence: PASS (all three tables present)
- Hosted Room presence: PASS (all three tables present)
- `repository_bindings`: present, 0 rows

## Integrity proof

Catalog and bounded orphan checks against the live canonical database:

| Constraint / check | Result |
| --- | --- |
| Public FK constraints | 113 |
| Public CHECK constraints | 894 |
| Public UNIQUE constraints | 41 |
| Canonical `account_observability_*` PKs present | t / t / t |
| Orphaned `chat_messages.thread_id` | 0 |
| Orphaned `chat_messages.user_id` | 0 |
| Orphaned `chat_threads.user_id` | 0 |
| Orphaned `chat_threads.project_id` | 0 |
| Orphaned `chat_threads.parent_id` | 0 |
| Orphaned `hosted_room_invites.room_id` | 0 |
| Orphaned `hosted_room_participants.room_id` | 0 |
| Orphaned `hosted_room_participants.invitation_id` | 0 |
| Orphaned `hosted_room_participants.bound_account_id` | 0 |
| Orphaned `hosted_rooms.owner_account_id` | 0 |
| Orphaned `hosted_rooms.backing_thread_id` | 0 |
| Orphaned `repository_bindings.project_id` | 0 |
| Orphaned `account_observability_account_metadata.user_id` | 0 |
| Orphaned `account_observability_account_metadata.acquisition_invite_id` | 0 |
| Orphaned `account_observability_account_metadata.prior_guest_id` | 0 |
| Orphaned `account_observability_presence_sessions.user_id` | 0 |
| Orphaned `account_observability_presence_sessions.guest_id` | 0 |
| Orphaned `account_observability_presence_sessions.invite_id` | 0 |
| Orphaned `account_observability_guest_identities.first_invite_id` | 0 |
| Orphaned `account_observability_invite_links.created_by_user_id` | 0 |

Integrity: PASS. No data repair attempted.

## Canonical startup

- lifecycle command: `scripts/ops/codexify_tester.sh up`
- migrate outcome: SUCCESS
  - `[Migrator] Using Alembic config: /app/backend/alembic.ini`
  - `[docker] run: /usr/local/bin/python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads`
  - migrator container exited `0`
  - `seed_defaults.py` invoked and logged normally
  - `[Migrator] Done`
- post-startup Alembic revision: `9d4c2a7e1b6f` (unchanged)
- pre-startup Alembic revision: `9d4c2a7e1b6f` (unchanged)
- no manual stamp: confirmed (no `alembic stamp` invoked anywhere in
  this task)
- no DBAPI error: confirmed (migrator connected successfully; Alembic
  graph loaded; upgrade heads ran without DBAPI failure)
- no missing revision: confirmed (the canonical head is present in the
  baked image and recognized by Alembic)

## Data preservation across startup

Row counts were captured before the canonical `up` and again after the
backend's repeated crashes. They match exactly:

| Table | Pre-startup | Post-startup |
| --- | ---: | ---: |
| `users` | 18 | 18 |
| `projects` | 3 | 3 |
| `chat_threads` | 5,061 | 5,061 |
| `chat_messages` | 112,507 | 112,507 |
| `hosted_rooms` | 1 | 1 |
| `hosted_room_invites` | 1 | 1 |
| `hosted_room_participants` | 3 | 3 |
| `account_observability_account_metadata` | 14 | 14 |
| `repository_bindings` | 0 | 0 |
| Alembic revision | `9d4c2a7e1b6f` | `9d4c2a7e1b6f` |

No unexplained row-count change. No Hosted Room row loss. No Account
Observability row loss. `seed_defaults.py` was invoked but produced no
canonical-table mutation against the already-canonical state.

## Required services

After `scripts/ops/codexify_tester.sh up` and three independent retries
that included the canonical lifecycle and a direct `up -d backend`:

| Service | State | Healthy |
| --- | --- | --- |
| `db` | running | true |
| `neo4j` | running | true |
| `backend` | exited (3) | false |
| `redis` | running | true |
| `frontend` | created | false |
| `worker-chat` | created | false |
| `worker-document-embed` | created | false |
| `worker-chat-embed` | created | false |
| `worker-warmup` | created | false |
| `worker-account-import` | created | false |
| `tailscale-codexify-test` | running | true (subject to tailscale auth posture) |

The `backend` crash cascades: Compose marks `worker-*` and `frontend` as
`created` and never advances them because they depend on a healthy
backend.

## Health

- `/health`: NOT EXERCISED — backend exited before FastAPI served
- `/health/chat`: NOT EXERCISED — backend exited before FastAPI served
- observed curl result during a brief startup window where the port was
  bound but the app had not yet served:
  `curl: (52) Empty reply from server` (no HTTP status, no body)

## Startup logs (bounded)

Migrator (relevant lines):

```text
[Migrator] Using Alembic config: /app/backend/alembic.ini
[Migrator] Cleared Python caches under /app/backend: dirs=0, files=0
[Migrator] Cleared guardian migration caches: dirs=2, files=0
[Migrator] alembic.ini script_location=%(here)s/../guardian/db/migrations
[docker] run: /usr/local/bin/python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
INFO  [alembic.env] ...
INFO  [alembic.runtime.migration] Context impl ...
INFO  [alembic.runtime.migration] Will assume ... DDL.
[Migrator] Running seed defaults
[docker] run: /usr/local/bin/python /app/backend/scripts/seed_defaults.py
...
[Migrator] Done
```

Backend (relevant lines; redacted log_event values are bounded:

```text
[env] dotenv loaded (in order): ...
[db] Using PostgreSQL chatlog DB DSN=...
[routers] Router registration complete (beta_core_only=False)
[webui-basic] ... not found, skipping UI mount
INFO: Started server process [1]
[config] Coherence mode selected: CODEXIFY_CONFIG_SOURCE=...
[embedder] embedding model=/models/bge-large-en-v1.5
[embedder] backend=sentence_transformer model=/models/bge-large-en-v1.5
thread '<unnamed>' panicked at rust/sqlite/src/db.rs:157:42:
range start index 10 out of range for slice of length 9
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
ERROR: ...
ERROR: ...
```

No environment variables, credentials, tokens, or session material were
included in the captured logs above.

Classified error category: Rust panic in a third-party ChromaDB rust-binding
(`rust/sqlite/src/db.rs:157:42`). The panic occurs during embedder
initialization. The Rust module is loaded by the ChromaDB client used by
`backend.rag.embedder` for the `sentence_transformer` backend.

Reproducibility: the same panic message and exit code 3 were observed on
three independent startup attempts (one initial lifecycle, two direct
`up -d backend` retries) within this task.

## Authenticated application proof

NOT EXERCISED. The supported authentication flow was not reached because
the backend never started. No login was attempted. No session was
established. `GET /api/dashboard/snapshot` was not issued. No token,
cookie, or session material was recorded.

For reference, the dashboard snapshot contract regression suite
(`tests/routes/test_dashboard_snapshot.py`) was re-run against the current
source and PASSED with 7/7 cases. This does NOT exercise the live route
against the preserved Tester; it only re-validates the in-process
contract against the canonical test fixtures.

## Hosted Room status

- Hosted Room durable rows preserved: YES (1 room / 1 invite / 3
  participants unchanged pre vs. post startup attempt).
- Hosted Room owner/guest runtime semantics were NOT exercised: true.
- Stage 2K.6 Hosted Room replay remains the next task on GO: deferred
  pending the resolver of this task's blocker.

## Release impact

No beta surface widening. No architecture change. No runtime source file
change. No migration file change. No model file change. No ADR change.
This proof only inspected, started, and refused to claim GO because of
the reproducible backend startup failure.

## Recovery posture

- physical backup retained at:
  `/private/tmp/codexify-tester-live-upgrade.qkai5A/codexify_tester_pg_data-pre-upgrade.tar.gz`
  (mode 0700 parent directory, outside the repo)
  - SHA-256: `c278158f31f940e2a00ec735e76f58358a5867471774392fc9f851e1602aed3f`
- logical `pg_dump` retained at:
  `/private/tmp/codexify-tester-live-upgrade.qkai5A/codexify-tester-canonical-pre-startup.dump`
  (mode 0700 parent directory, outside the repo)
  - SHA-256: `201b1032c21754d250766eae0d23379cc88e28922f1034bfffdf03703c2cbb7d`
- recovery required: NO (no migration was attempted; volume intact; row
  counts unchanged)
- Tester state at task end:
  - desired_state: `enabled`
  - db: running (healthy)
  - neo4j: running (healthy)
  - redis: running (healthy)
  - tailscale-codexify-test: running (subject to tailscale auth posture)
  - backend: exited (3)
  - frontend, worker-chat, worker-chat-embed, worker-document-embed,
    worker-warmup, worker-account-import: `created` (Compose never
    advanced them because backend is unhealthy)
  - net: lifecycle reports `tester_status=degraded`

## Limitations

- no Hosted Room owner/guest replay (out of scope by task design)
- no broader release qualification
- no inference quality claim
- no claim beyond the bounded evidence captured in this task
- the historical actor responsible for the prior `d6f7a8b9c0d1` →
  `9d4c2a7e1b6f` advance remains unknown
- the canonical backend startup path through `sentence_transformer`
  embedder + ChromaDB rust-binding panics reproducibly; the exact
  upstream cause and any Codexify-side mitigation are deferred to a
  separate atomic task
- no login was attempted; no authenticated `/api/dashboard/snapshot`
  call was made; the dashboard contract was only validated in-process by
  `tests/routes/test_dashboard_snapshot.py` (7/7 pass)

## Exact precondition that blocked GO

The single first material blocker is:

```text
backend container exits with status 3 during initialization.
Panic: thread '<unnamed>' panicked at rust/sqlite/src/db.rs:157:42:
range start index 10 out of range for slice of length 9
```

This is the only blocker for this task. It blocks:

- `/health` (backend did not serve)
- `/health/chat` (backend did not serve)
- all `worker-*` and `frontend` startup (depend on healthy backend)
- `tester_status=healthy` (one required service unhealthy)
- authenticated `GET /api/dashboard/snapshot` (no service to call)

The migration graph, Alembic head, source Alembic identity, baked
runtime image, dependency drivers, prerequisite test suites, DLG,
required-service health gate for db / neo4j / redis / tailscale, FK
integrity, orphan checks, canonical schema shape, and bounded data
preservation all PASS.

## Repository diff hygiene

- `git status --short` before commit: only the new proof receipt
- `git diff --check`: PASS (empty diff)
- `git diff --name-only`: empty (no source diffs before commit)
- authorized edit (this file):
  `docs/architecture/proofs/2026-08-13-preserved-tester-canonical-startup-auth-proof.md`

## Validation suite re-run (post this task)

- `tests/ops/test_backend_runtime_dependency_contract.py`: 4 passed
- `tests/migration/test_d6_compatibility_bridge.py`: 11 passed
- `tests/migration/test_account_observability_compatibility_normalization.py`: 10 passed
- `tests/migration/test_alembic_revision_uniqueness.py`: 1 passed
- `tests/routes/test_dashboard_snapshot.py`: 7 passed
- `scripts/knowledge_graph/validate_and_generate_dlg.py validate`: PASS
  (result: `pass`, repository_revision `dec85ac839550a9fcfd25ee73304e1d83eb71fb3`)
- `.venv/bin/python -m alembic -c backend/alembic.ini heads`: `9d4c2a7e1b6f (head)`
- `make docs PYTHON=.venv/bin/python`: PASS
  - `scripts/validate_docs.py`: "Docs validation passed: required
    architecture docs, README links, and source headings verified."
  - `scripts/check_diagram_freshness.py`: "Diagram freshness check passed:
    no runtime source drift detected and matrix decisions are valid."
- `scripts/ops/codexify_tester.sh status` post-task: `desired_state=enabled,
  tester_status=degraded` (matching the above required-services table)

## Proof artifact

- path: `docs/architecture/proofs/2026-08-13-preserved-tester-canonical-startup-auth-proof.md`
- verdict: `NEXT_PROOF_NEEDED`

## Exact next task recommendation

Authorize **one** atomic follow-up task whose sole purpose is to resolve
the reproducible backend startup panic:

```text
thread '<unnamed>' panicked at rust/sqlite/src/db.rs:157:42:
range start index 10 out of range for slice of length 9
```

The panic originates inside the ChromaDB Rust binding used by the
sentence-transformer embedder during backend initialization. The follow-up
task should:

1. Characterize the panic deterministically: capture `RUST_BACKTRACE=1`
   output from a single backend startup attempt, identify which ChromaDB
   Rust binding version is loaded, and identify the SQLite database that
   the Rust binding is opening (likely a ChromaDB-side SQLite store, not
   the Codexify Postgres DB).
2. Determine whether the panic is recoverable through configuration
   (e.g. recreating the relevant ChromaDB SQLite store, pinning a
   different ChromaDB Python binding version, or changing the embedder
   backend configuration) without changing accepted architecture,
   migration policy, or release posture.
3. Apply the minimum fix needed to allow the supported `backend`
   container to start successfully against the already-canonical
   preserved Tester database.
4. Re-run this proof's success chain from step 24 onward to issue the
   eventual `GO` verdict.

The follow-up must NOT:

- edit migrations, schema models, runtime code, Compose, dependencies,
  or any accepted architecture;
- perform Hosted Room owner/guest replay;
- widen the supported beta surface;
- reset or recreate the preserved `codexify_tester_pg_data` volume.

## What Axis should add to his KB

1. The preserved Tester source is canonical and integrity-clean: Alembic
   head `9d4c2a7e1b6f`, canonical ADR-049 Account Observability shape
   (`invite_id`/`guest_id`/`presence_session_id` PKs,
   `region_code VARCHAR(64)`), all bounded FK/orphan checks pass, row
   counts match the previously proven preserved dataset.
2. The canonical migrator runs successfully and exits `0` against the
   already-current database. No d6 → head migration was required or
   attempted by this proof.
3. The canonical Tester lifecycle brings `db`, `neo4j`, `redis`, and
   `tailscale-codexify-test` to healthy. The `backend` container crashes
   reproducibly during initialization with a Rust panic in the ChromaDB
   SQLite binding (`rust/sqlite/src/db.rs:157:42: range start index 10
   out of range for slice of length 9`). This blocks the eventual `GO`
   for `GET /api/dashboard/snapshot`.
4. `tests/routes/test_dashboard_snapshot.py` passes 7/7 against current
   `main` source; the dashboard snapshot contract itself is sound. The
   blocker is the embedder / ChromaDB binding initialization, not the
   dashboard route.
5. Bounded logical `pg_dump` and physical `tar.gz` recovery backups of
   the preserved source were captured at
   `/private/tmp/codexify-tester-live-upgrade.qkai5A/`, validated by
   `pg_restore -l` and exact SHA-256 match respectively, and retained
   outside the repo at task end.
6. The historical actor that advanced the live preserved volume from
   `d6f7a8b9c0d1` to `9d4c2a7e1b6f` remains unidentified by this task
   and is not required for the next proof.
