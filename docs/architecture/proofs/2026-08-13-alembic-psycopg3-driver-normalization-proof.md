# Alembic psycopg3 driver normalization proof

## Result

**GO**

The canonical Codexify migrator now correctly uses the installed psycopg v3
SQLAlchemy dialect for driver-neutral `postgresql://` URLs. The Alembic
environment (`guardian/db/migrations/env.py`) normalizes a bare PostgreSQL URL
to `postgresql+psycopg://` before SQLAlchemy engine construction, for both the
`DATABASE_URL` environment path and the configured `sqlalchemy.url` path,
without changing the process-wide `DATABASE_URL` contract, without breaking
`seed_defaults.py`, without mutating the preserved tester database, and
without changing the migration graph (still exactly one head:
`9d4c2a7e1b6f`).

The canonical disposable Compose proof ran with **no ephemeral URL override**:
the migrator service received the unmodified driver-neutral
`DATABASE_URL=postgresql://...` from `docker-compose.yml`, exited 0, applied
all 101 migrations to the single head, and `seed_defaults.py` took its
Postgres path (default project `General` present). A second run was a no-op.

## Baseline

- Branch: `proof/chroma-startup-isolation`
- Pre-task HEAD: `653e58f61e54d09c96e78e3b3f7fd4e19f457899`
- Pre-task tracked worktree: clean
- Pre-task Alembic head: exactly one — `9d4c2a7e1b6f`
- Pre-task migration suite `tests/migration`: `111 passed, 29 skipped`

## Regression guard (per task brief)

Inspected at current HEAD:

- `guardian/db/migrations/env.py` — `_get_database_url()` passed the bare
  `postgresql://` URL straight into `sqlalchemy.url`; **no normalization**.
- `backend/scripts/docker/run_migrator.py` — pure wrapper around
  `alembic upgrade heads` + `seed_defaults.py`; no URL handling.
- `backend/scripts/seed_defaults.py` — connects via raw psycopg v3 (psycopg2
  fallback), `_is_pg()` accepts only `postgres://`/`postgresql://`; untouched.
- `docker-compose.yml` — `DATABASE_URL` is driver-neutral
  `postgresql://${POSTGRES_USER:-codexify}:${POSTGRES_PASSWORD:-codexify}@db:5432/${POSTGRES_DB:-Codexify}`;
  `GUARDIAN_DATABASE_URL` is the repo's own `postgresql+psycopg://` scheme.
- Backend runtime dependency declarations —
  `backend/requirements.txt` (canonical manifest copied into the runtime
  image) declares `psycopg[binary]>=3.2.10`; the runtime image ships
  psycopg 3.3.4.
- Migration tests — no driver-normalization test exists at HEAD.
  `tests/test_alembic_config_contract.py` (34 lines) covers only
  `alembic.ini` script_location pathing.
- Proof artifacts — `2026-08-13-account-observability-migration-compatibility-proof.md`
  records the migrator driver incompatibility as a separate, pre-existing
  defect and documents the ephemeral `postgresql+psycopg://` override used
  for its disposable proofs. `2026-08-13-d6f7a8b9c0d1-compatibility-bridge-proof.md`
  names the unmerged fix (`cb35d4e80`, branch
  `codex/alembic-psycopg3-runtime-driver-20260812`, proof
  `2026-08-12-alembic-psycopg3-driver-normalization-proof.md`).

Historical/unmerged fixes inspected (not blindly cherry-picked):

| Commit | Branch(es) | Shape |
| --- | --- | --- |
| `2113b5101` | `codex/2026-08-12-retire-obsolete-chroma-index` | new module `guardian/db/migration_url.py` + env.py wiring + `tests/ops/test_alembic_psycopg_driver_contract.py` |
| `cb35d4e80` / `4d5649473` / `13d2a28ce` | `codex/alembic-psycopg3-runtime-driver-20260812`, `codex/alembic-psycopg3-abaf-main-20260812`, `codex/alembic-psycopg3-current-main-20260812`, `codex/backend-schema-psycopg3-current-20260812` | new module `guardian/db/migration_driver.py` + env.py wiring + `tests/test_alembic_config_contract.py` (driver-contract variant) |

All are unmerged (`git merge-base --is-ancestor <commit> main` = false; HEAD's
env.py is unnormalized). None of the helper modules exists at HEAD
(`guardian/db/migration_url.py`, `guardian/db/migration_driver.py`, and the
symbol `normalize_alembic_database_url` have zero matches in the tree).

Verdict: **NOT ALREADY SATISFIED** — no criterion of the four holds at HEAD.
Per the task's authorized-file list, the implementation file is
`guardian/db/migrations/env.py` only; the historical fix shape (a new shared
helper module) was therefore NOT recreated here. The normalization lives as
an env.py-local function; a future extraction into a shared module (for the
separate backend startup seam) is a distinct, separately authorized task.

## ADR impact

- Classification: `Aligned with existing ADR(s)`
- Governing ADR(s): none pin a PostgreSQL Python driver. The ADR index
  (1–65) was inspected; the only "driver" reference is unrelated
  ("Decision drivers" in ADR-064). ADR-031 (Continuity Phase A Storage
  Migration Gate) governs storage-migration proof, not SQLAlchemy driver
  selection.
- Reason: this task repairs the implementation of the already-accepted
  Postgres/Alembic runtime contract (`DATABASE_URL` is a Postgres DSN for
  migrations per `docs/architecture/config-and-ops.md`). It changes no
  persistence meaning, schema meaning, migration lineage, supported database
  technology, or upgrade semantics.

## The repaired seam

```text
external runtime contract
DATABASE_URL=postgresql://...        (unchanged, driver-neutral)

              |
              v

guardian/db/migrations/env.py
normalize_alembic_database_url()     (env.py-local; both URL sources)

              |
              v

SQLAlchemy URL
postgresql+psycopg://...             (psycopg v3 dialect)

              |
              v

installed psycopg v3 (3.3.4 in runtime image)
```

Implementation (single file, `guardian/db/migrations/env.py`):

- New module-level `normalize_alembic_database_url(url)`:
  - `postgresql://...` → `postgresql+psycopg://...` (scheme prefix only;
    every byte after it preserved).
  - Explicit `postgresql+psycopg://` and `postgresql+psycopg2://` → unchanged.
  - Any other scheme or non-string input → unchanged.
- `_get_database_url()` now normalizes both sources — the `DATABASE_URL`
  environment variable and the `alembic.ini` `sqlalchemy.url` setting — then
  sets the normalized value via `config.set_main_option("sqlalchemy.url", ...)`
  and returns it, so offline mode (`context.configure(url=...)`) and online
  mode (`engine_from_config`) both see the psycopg v3 dialect.
- `os.environ["DATABASE_URL"]` is never modified: seed/runtime consumers
  keep the original driver-neutral contract. `seed_defaults.py` (separate
  process) therefore takes its Postgres path (`_is_pg()` accepts the bare
  scheme), with no SQLite fallback.

`backend/scripts/docker/run_migrator.py`, `backend/scripts/seed_defaults.py`,
`docker-compose.yml`, `docker-compose.tester.yml`, `.env.tester`, existing
migrations, revision identifiers, Hosted Room runtime code, frontend code,
and ADRs were not modified.

## Focused test

New file: `tests/migration/test_alembic_psycopg3_driver_normalization.py`
(14 tests, DB-free, no network I/O, no psycopg2 import attempt):

- Pure-function contract: bare URL → `+psycopg` scheme; user/password/host/
  port/database suffix preserved; query string preserved; percent-encoded
  credential bytes preserved; explicit `+psycopg` and `+psycopg2` unchanged;
  non-Postgres scheme unchanged; non-string input unchanged.
- SQLAlchemy resolution: `make_url` reports drivername `postgresql+psycopg`;
  `create_engine(..., poolclass=NullPool)` resolves dialect driver `psycopg`
  without connecting.
- Environment wiring (env.py executed via `runpy` against a faked offline
  alembic context): `DATABASE_URL` path normalized into `sqlalchemy.url` and
  the offline `configure(url=...)`; `alembic.ini` path normalized the same
  way; explicit `+psycopg` URL passes through; and the process-wide
  `DATABASE_URL` environment variable remains byte-identical after env.py
  runs.

Result: `14 passed`.

## Validation

- Focused test: `14 passed`.
- Full migration suite `tests/migration` + runtime dependency contract
  (`tests/ops/test_backend_runtime_dependency_contract.py`):
  `129 passed, 29 skipped` (baseline 111 + 14 new + 4 dep contract;
  no regressions, no failures).
- Alembic graph: exactly one head, `9d4c2a7e1b6f` (unchanged).
- `make docs` (validate_docs.py + check_diagram_freshness.py): pass.
- `git diff --check`: clean.
- In-image probe (runtime image built for this proof):
  - Image: `codexify-backend-runtime:r1p1c-psycopg3-proof` (built from this
    worktree; the shared `latest` tag was not touched).
  - Probe result: input `postgresql://probe_user:***@db:5432/Codexify` →
    normalized `postgresql+psycopg://...`; `env_unchanged: True`;
    `drivername: postgresql+psycopg`; `dialect.driver: psycopg`;
    `psycopg_version: 3.3.4`; no connection made.
- Pre-existing limitation (out of scope, proven pre-existing at HEAD
  `653e58f61` on a detached worktree): `alembic upgrade --sql` (offline mode)
  fails on the inspector-based `9d4c2a7e1b6f` migration with
  `NoInspectionAvailable ... MockConnection`. Offline SQL generation is not
  part of the canonical migrator path (`run_migrator.py` runs online
  `upgrade heads`) and the failure reproduces identically without this
  change.

## Disposable Compose proof (canonical path, no ephemeral override)

- Isolated project: `codexify_r1p1c_psycopg3_proof` (fresh volumes, host
  ports removed via a `/tmp`-only override; image pointed at the proof tag).
- The migrator service environment was validated with
  `docker compose config --format json` BEFORE the run:
  `DATABASE_URL=postgresql://codexify:***@db:5432/Codexify` — driver-neutral,
  unchanged from `docker-compose.yml`. No `postgresql+psycopg` override was
  present anywhere.
- Run 1 (canonical `run_migrator.py`, exit 0):
  - `[Migrator] Using Alembic config: /app/backend/alembic.ini`
  - `alembic --raiseerr -c ... upgrade heads` completed; 101 `Running upgrade`
    lines (full clean-start chain base → `9d4c2a7e1b6f`).
  - `[Migrator] Running seed defaults` → `seed_defaults.py` connected via its
    Postgres path (driver-neutral URL recognized) and completed.
  - `[Migrator] Done`
- Post-run verification (psql against the disposable db):
  - `alembic_version = 9d4c2a7e1b6f` (the single canonical head)
  - `projects` row present: `1:General` — seeding succeeded on Postgres
    (the previous ephemeral-override proofs observed the SQLite fallback
    side effect; with the canonical fix, `_is_pg()` sees the original
    driver-neutral URL and the seed runs normally).
- Run 2 (idempotence, exit 0): zero `Running upgrade` lines; seed re-ran
  idempotently.
- Teardown: `down -v` on the disposable project only.

## Migration graph and schema

- No migration file was created, rewritten, reordered, squashed, or
  replaced. Revision identifiers unchanged. Lineage unchanged.
- Single head `9d4c2a7e1b6f` before and after.

## Preserved tester safety

- The preserved tester database was not started, mounted, written, stamped,
  upgraded, or deleted. No read-only copy was even needed: the proof is a
  clean-start disposable database.
- No container or volume of the preserved `codexify_tester` project was
  touched; the shared `codexify-backend-runtime:latest` image tag was not
  rebuilt or modified.

## Release impact

No release-support expansion. This repairs the canonical migrator boot
prerequisite; it does not widen the supported install path, provider
posture, or beta surface. The preserved friends/family tester upgrade may
proceed as its own separately authorized task now that the migrator boot
prerequisite is closed.

## DLG freshness consequence (expected, separate follow-on)

This task's authorized docs edits (`00-current-state.md` content update and a
new proof file under `docs/architecture/proofs/`) change the canonical source
bytes of DLG nodes. `tests/architecture` was verified BEFORE the docs edit at
pristine HEAD `653e58f61` (both `test_current_nine_node_corpus_validates` and
`test_validator_cli_runs_without_runtime_services` pass), and fails AFTER the
edit with `corpus.code = "content_hash_mismatch"` on the `00-current-state.md`
node. This is the repo's known pattern: DLG freshness reverification is a
separate task (`architecture-control-plane-freshness-reverification`, variant
B: recompute `content_hash` + freshness metadata) that lands as its own
commit — the precedent is commit `4f3b977cf` after the account-observability
repair. DLG/knowledge-graph files were NOT modified here (not authorized).

The `check_diagram_freshness.py` review-marker warning fires only while the
docs change is uncommitted (the check diffs HEAD vs the working tree); a
committed clean tree passes, and CI does not run the freshness script in
base-ref mode. Per repo precedent, the `Diagram Review Marker:` lines were
not touched (still dated 2026-08-11).

## Limits and non-goals honored

- No modification to `run_migrator.py`, `seed_defaults.py`,
  `docker-compose.yml`, `docker-compose.tester.yml`, `.env.tester`, existing
  migrations, revision identifiers, Hosted Room runtime code, frontend code,
  or ADRs.
- No second normalization seam: no new shared helper module was created
  (the task authorizes `env.py` only); the backend startup schema-verification
  seam (`run_backend.py`) remains a separate, separately authorized task.
- No DLG/knowledge-graph edit (freshness reverification after this proof
  lands is the repo's separate follow-on task).
- No preserved tester mutation, no manual stamp, no provider inference, no
  secret material emitted.
