# Stage 2K.6-prep-1 Runtime Dependency Proof

## Title

Stage 2K.6-prep-1 — close the proven backend runtime dependency-selection repair

## Date

2026-08-12

## Verdict

`PASS`

The canonical backend runtime dependency-selection defect is repaired: backend/requirements.txt is now deterministically staged and installed, a fresh no-cache runtime image successfully provides the existing psycopg2/psycopg3 dependency contract, and SQLAlchemy resolves the current postgresql:// PostgreSQL dialect without the former driver-load failure. The supported migrator now progresses into Alembic and stops on the independent pre-existing database migration-history reference d6f7a8b9c0d1, which is explicitly deferred to a separate migration-lineage reconciliation task.

## Diagnostic Outcome

`SUPPORTED_RUNTIME_DEPENDENCY_SELECTION_REPAIRED`

This verdict is deliberately narrower than supported-launcher readiness. It closes the dependency-selection defect only. Supported migration completion remains blocked by independent migration lineage.

## Base SHA

`6eb21f463770fd1ef492de36aa4272c6d50f5e8b`

`HEAD`, the task base, and the merge base were identical before the task commit.

## Branch / Worktree

- Branch: `codex/stage2k6-prep1-runtime-dependency`
- Worktree: `/private/tmp/codexify-stage2k6-prep1-runtime-dependency`

## Governing Architecture

- `docs/architecture/00-current-state.md` remains short-horizon release truth.
- `docs/architecture/config-and-ops.md` governs the local Docker Compose path, PostgreSQL configuration, and the distinction between runtime checks and supported proof.
- `docs/architecture/data-and-storage.md` keeps Postgres and Alembic history authoritative and prohibits treating direct history edits as migration execution.
- The Stage 2K.6 live repository-search proof at Git object `710eb2e88` established the original Docker dependency-selection defect and preserved the other live gates.
- `backend/requirements.txt` remains the canonical runtime dependency manifest for this Dockerfile.

## ADR Impact

Classification: `Aligned with existing ADR(s)`.

No accepted architecture, authority boundary, database URL, migration policy, schema, provider posture, or release promise changes. The Docker build now follows the existing canonical backend dependency contract. No new ADR is required.

## Original Stage 2K.6 Blocker

The supported Whoosh'd launcher previously reached the migrator, where SQLAlchemy resolved the existing unqualified `postgresql://` URL to its `psycopg2` driver and failed with:

`ModuleNotFoundError: No module named 'psycopg2'`

This blocked Alembic before migration execution.

## Pre-Repair Dependency Staging

The pre-repair Dockerfile used a multi-source copy:

`COPY requirements/ backend/requirements.txt* ./`

The external, non-repository evidence file `/private/tmp/stage2k6-prep1-pre-repair.Dockerfile` mechanically reproduced Docker's staging behavior. Its build contract required and established:

- `/tmp/backend/requirements.txt` was absent;
- `/tmp/all.txt` was present;
- `/tmp/requirements.txt` was present.

The evidence file has SHA-256 `40c0ee07fa1dc1c905558c0d82a55bafbd020262cef92a48959da2c34af926f7`. It is not part of this contribution and was not copied or staged.

## Canonical Backend Dependency Manifest

`backend/requirements.txt` is the canonical backend runtime manifest. It already declared both driver families:

- `psycopg2-binary>=2.9.9`
- `psycopg[binary]>=3.2.10`

The manifest is unchanged from the base SHA.

## Pre-Repair Selected Manifest

Because `./backend/requirements.txt` did not exist after the flattened multi-source copy, the candidate loop selected `./all.txt`, corresponding to `requirements/all.txt`.

That manifest provides psycopg3 but does not provide psycopg2. The selection defect, not a missing canonical declaration, caused the runtime driver failure.

## Root Cause

The builder attempted to select a nested canonical path after Docker had flattened the multi-source copy into `/tmp`. A permissive fallback then silently installed `requirements/all.txt`. Build success therefore concealed installation of the wrong dependency manifest.

## Dockerfile Repair

The repaired builder stage now has one deterministic dependency path:

`backend/requirements.txt` -> `/tmp/backend/requirements.txt` -> `pip install -r /tmp/backend/requirements.txt`

It uses an explicit single-source `COPY`, checks `os.path.isfile()` for the canonical path, and exits with `canonical backend requirements missing` if the file is absent. The repair contains no direct `pip install psycopg2`, no fallback candidate list, no dependency-version edit, and no database URL rewrite.

## Regression Coverage

`tests/ops/test_backend_runtime_dependency_contract.py` contains four focused checks for:

1. explicit canonical staging and installation;
2. removal of flattening and fallback selection;
3. preservation of the existing psycopg2/psycopg3 manifest declarations;
4. absence of direct driver installation or database URL rewrites.

Result: `4 passed`.

## Fresh No-Cache Image Build

Command:

`docker build --no-cache --target runtime -t codexify-backend-runtime:stage2k6-prep1-proof -f backend/Dockerfile .`

Result: PASS. Docker completed the fresh build and export in `211.0s`.

Runtime image identity:

- Tag: `codexify-backend-runtime:stage2k6-prep1-proof`
- Image ID: `sha256:6edb8d217ec1a69c34739577da0083811a2e4c2bae77b6d10247bbc58110c42a`
- Platform: `linux/arm64`

The build trace installed from `/tmp/backend/requirements.txt` and explicitly selected both `psycopg2-binary` and `psycopg`.

## Runtime Dependency Versions

Using the fresh image with an overridden Python entrypoint:

- psycopg2: `2.9.12 (dt dec pq3 ext lo64)`
- psycopg3: `3.3.4`
- SQLAlchemy: `2.0.44`
- Alembic: `1.17.0`

## psycopg2 Import Proof

PASS. `import psycopg2` succeeded in the fresh no-cache runtime image and reported `2.9.12 (dt dec pq3 ext lo64)`.

## psycopg3 Import Proof

PASS. `import psycopg` succeeded in the same image and reported `3.3.4`.

## SQLAlchemy PostgreSQL Dialect Proof

PASS. In the same image, SQLAlchemy constructed an engine from the nonconnecting dummy URL `postgresql://user:password@localhost/example`.

- Dialect: `postgresql`
- Driver: `psycopg2`
- Connection attempt: none
- Driver-load failure: none

## Supported Launcher Replay

The closeout packet supplied an already-established live supported-launcher result for:

`bash scripts/whooshd_docker_smoke_up.sh minimal --detach`

That run used the repaired runtime, progressed through driver loading into Alembic, and exited on the independent missing revision `d6f7a8b9c0d1`.

Current closeout replay limitation: the first local replay stopped before Compose resolution because this isolated worktree intentionally has no `.env`; it did not build, start the migrator, or reach Alembic. A second attempt to pass the canonical checkout's existing dotenv read-only into the same launcher was denied by the managed execution gate because the launcher broadly removes `codexify*` containers before starting a detached stack with machine-local secrets. No workaround was used. The current-session fresh-image import and dialect results are independently reproduced; the launcher-to-Alembic handoff remains task-supplied prior live evidence rather than a newly repeated observation.

The prescribed launcher's first preflight attempt removed eight stale `codexify` project containers. It did not use `down -v`, delete volumes, prune Docker state, run Tester, or run private preview.

## Former Driver Failure Status

`REPAIRED` for the dependency-selection contract.

The fresh runtime directly imports psycopg2 and SQLAlchemy directly loads the default PostgreSQL psycopg2 driver. The task-supplied launcher replay contains no psycopg2 import failure and no SQLAlchemy PostgreSQL driver-resolution failure.

## Migrator Progress

Task-supplied supported-launcher evidence shows the migrator now passes the former DBAPI load boundary and begins Alembic revision resolution.

This is progress evidence, not migration-completion evidence.

## Independent Migration-Lineage Blocker

Alembic stops because the preserved database references a revision that the canonical source graph cannot locate:

`Can't locate revision identified by 'd6f7a8b9c0d1'`

No lineage conclusion or repair is inferred in this task.

## Missing Revision ID

`d6f7a8b9c0d1`

## Migrator Exit Code

`1` in the task-supplied supported-launcher evidence.

Exit code `1` is the expected preserved-state outcome for this closeout and is not treated as dependency-selection failure.

## Seed Defaults Status

Not executed. `backend/scripts/docker/run_migrator.py` runs seed defaults only after Alembic upgrade succeeds; Alembic stops first on the missing historical revision.

## Alembic Source Head

`alembic -c backend/alembic.ini heads` reports one canonical source head:

`6e2b9c4a7d1f (head)`

Migration revision uniqueness also passes.

## Schema / Migration Immutability

- `git diff 6eb21f463770fd1ef492de36aa4272c6d50f5e8b -- guardian/db/migrations` is empty.
- No migration file, schema model, migrator source, or Alembic configuration changed.
- No migration was added, removed, rewritten, stamped, or replaced.
- No `alembic_version` row or other database migration history was queried or modified in this closeout.

## Compose / Env Immutability

- `docker-compose.yml` is unchanged.
- `docker-compose.whooshd-smoke.yml` is unchanged.
- No `.env` file was created, copied, edited, printed, or staged.
- Database URLs are unchanged.

## No Inference Confirmation

No chat completion, provider request, cloud call, Command Bus invocation, repository search, or other model inference was sent.

## Deferred Stage 2K.6 Blockers

1. migration lineage for `d6f7a8b9c0d1`;
2. local single-user supported-launcher posture;
3. Whoosh'd ModelInfo/capability qualification;
4. shared read-only backend/worker repository mount.

## What Was Proven

- the Docker staging defect existed;
- the dependency selector previously fell through to `requirements/all.txt`;
- the repair deterministically selects `backend/requirements.txt`;
- a fresh no-cache runtime build succeeds;
- psycopg2 is present;
- psycopg3 is present;
- SQLAlchemy `postgresql://` driver loading succeeds;
- task-supplied supported-launcher evidence progresses beyond the former dependency blocker.

## What Was Not Proven

- supported database migrations do not complete yet;
- `d6f7a8b9c0d1` lineage has not been reconciled;
- seed defaults do not execute because Alembic stops first;
- no database history has been stamped or changed;
- local single-user posture is not repaired;
- Whoosh'd capability qualification is not repaired;
- shared repository mount is not repaired;
- Stage 2K.6 live repository search is not rerun;
- no inference is sent;
- the supported-launcher result was not independently repeated in this closeout session because the isolated dotenv context was absent and the managed execution gate denied the secret-bearing broad-cleanup replay.

## Documentation Follow-Through

This proof receipt is the only documentation change. Current state, ADRs, architecture contracts, Compose, configuration, dependency manifests, migrations, and release claims remain unchanged. Migration-lineage reconciliation is explicitly handed to a separate atomic task.

## Final File Scope

Exactly three repository paths relative to base SHA `6eb21f463770fd1ef492de36aa4272c6d50f5e8b`:

- `backend/Dockerfile`
- `tests/ops/test_backend_runtime_dependency_contract.py`
- `docs/architecture/proofs/2026-08-12-stage2k6-prep1-runtime-dependency-proof.md`

The external file `/private/tmp/stage2k6-prep1-pre-repair.Dockerfile` is not in Git scope.

## Validation

- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/ops/test_backend_runtime_dependency_contract.py` — PASS, `4 passed`.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/migration/test_alembic_revision_uniqueness.py` — PASS, `1 passed`, one existing warning.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/alembic -c backend/alembic.ini heads` — PASS, sole head `6e2b9c4a7d1f`.
- fresh no-cache runtime image build — PASS.
- fresh-image psycopg2/psycopg3/SQLAlchemy/Alembic import proof — PASS.
- fresh-image SQLAlchemy `postgresql://` dialect proof — PASS, `postgresql / psycopg2`.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/architecture` — PASS, `394 passed`.
- `python3 scripts/validate_docs.py` — PASS.
- `make docs PYTHON=python3` — PASS; emitted the pre-existing duplicate `canonical-audit-live-proof-receipt` target warning.
- `python3 scripts/check_diagram_freshness.py` — PASS.
- `git diff --check` — PASS before and after receipt creation.
- `git diff --cached --check` — PASS for the exact three-file staged scope.

## Commit

Commit subject: `Fix backend runtime dependency selection`.

The full commit SHA is recorded in the task closeout after the exact three-file staged scope is verified.

## Exact Next Atomic Slice

`Stage 2K.6-prep-1B - audit and reconcile the supported Compose database migration lineage for the preserved alembic_version reference d6f7a8b9c0d1. Establish whether the revision is legitimate historical Codexify lineage, identify its exact migration source and ancestry relationship to canonical main, and choose an explicit safe reconciliation path without stamping, deleting history, or inventing a replacement revision until that lineage is proven.`
