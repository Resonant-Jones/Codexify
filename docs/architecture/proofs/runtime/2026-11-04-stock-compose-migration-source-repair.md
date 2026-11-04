# Stock Compose migration-source repair — bounded receipt

> **Release posture: HOLD.** This receipt records a bounded implementation
> correction to the **stock** (non-launcher) Docker Compose startup and the
> evidence gathered for it. It does **not** qualify the stock startup, does not
> create or edit a qualification rubric or registry entry, and does not move
> any release gate. The stock startup's own qualification identity
> (`supported-compose-stock`) is still unwritten.

## Result

**Implementation correction: landed and independently verified.** The stock
Compose startup now executes the migration source baked into the runtime image
**only after proving that source describes this checkout**, and it fails closed
before applying anything when it does not. A stale image can no longer produce
a successful-looking startup, and the application cannot come up against a
schema it does not describe.

**Qualification: not performed.** No `supported-compose-stock` rubric, run, or
receipt exists. The stock startup remains unqualified.

| Question | Disposition |
| --- | --- |
| Starting SHA | `97778bedf5a1ec4a04fb2fbb968dafb0aed9582c` (`origin/main` at task start) |
| Source Alembic head at that SHA | `a7d4c9e2f1b3`, 135 revision files, single head |
| Pre-baked image migration head | `3a91d7c4e8b2`, 128 revision files — 7 revisions behind the source |
| Root cause | Confirmed empirically, not inferred (see [§3](#3-the-defect-confirmed)) |
| Mechanism | Image-baked migration source executed **only after** a SHA-256 coherence proof against this checkout; single-head requirement; direct PostgreSQL `alembic_version` readback |
| Stale-image behaviour | Migrator exits non-zero before any migration is applied; dependent services are not started |
| Focused tests | `tests/ops/test_stock_compose_migrator_contract.py` (19 tests) + `tests/ops/test_source_compose_supported_profile_contract.py` (3 tests) — see [§5](#5-proof-surfaces) |
| Disposable runtime proof | See [§6](#6-disposable-runtime-proof) |
| Launcher startup | Unchanged |
| Packaged runtime (`docker-compose.runtime.yml`) | Unchanged |
| Private Preview | Untouched — image tag, containers, volumes and database not modified |
| Qualification registry / rubric | Untouched; no status written |
| Release gate | **HOLD** |

## 1. Scope and boundary

- **Base:** `origin/main` at `97778bedf5a1ec4a04fb2fbb968dafb0aed9582c`.
- **Branch:** `fix/stock-migrator-01-migration-source-consistency`, in an
  isolated worktree.
- **Files changed:** `docker-compose.yml`,
  `backend/scripts/docker/run_migrator.py`,
  `tests/ops/test_stock_compose_migrator_contract.py` (new),
  `docs/architecture/00-current-state.md`,
  `docs/architecture/proofs/runtime/2026-11-04-stock-compose-migration-source-repair.md`
  (new).
- **Not touched:** `docker-compose.runtime.yml`, `backend/Dockerfile`, the
  qualification launcher (`scripts/whooshd_docker_smoke_up.sh`), existing
  migrations, `docs/qualification/rubrics/`, the generated qualification
  registry, `config/supported_profiles/`, the Private Preview lane, existing
  databases and volumes, and the host's Whoosh'd stack.
- **Runtime environment:** `DOCKER_CONTEXT=desktop-linux`; a synthetic,
  local-only env file was used for Compose interpolation. No real operator
  credential, cloud key, or connector configuration was present in any
  container this task started.

## 2. Why the defect existed

`backend/migrations` is a git symlink to `../guardian/db/migrations`, and
`backend/alembic.ini` sets:

```ini
script_location = %(here)s/../guardian/db/migrations
```

The stock migrator mounted only `./backend:/app/backend`, so
`/app/backend/migrations` resolved into **the image's baked** `guardian` tree.
The backend and the worker services mounted `./guardian:/app/guardian` from the
**host**, so they served the checkout's source while the migrator applied a
schema derived from whatever the image happened to carry. The migration
execution dependency is not only the migration files: `guardian/db/migrations/env.py`
imports `from guardian.db.models import Base`, so the model set is part of the
contract too.

The June-2026 commit `ced657c73` had removed the migrator's guardian mounts to
work around a macOS virtiofs `stat` bug, and `run_migrator.py` still described
the migrations directory as volume-mounted. The image was also consumed
silently: the stock compose sets `pull_policy: never` and builds only when the
image is missing, and the image carries no revision label.

## 3. The defect, confirmed

Two probes against the pre-baked `codexify-backend-runtime:latest`
(`sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55`),
reading the migration tree the container actually sees:

| Probe | Revision files | Revisions read by Alembic | Head |
| --- | --- | --- | --- |
| Image **without** a guardian mount (the stock migrator) | 130 | 128 | `3a91d7c4e8b2` |
| Image **with** this checkout's guardian mounted | 135 | 135 | `a7d4c9e2f1b3` |

The seven revisions the pre-baked image is missing:

- `a3115f64dda8_merge_guardian_coding_claim_and_campaign_heads.py`
- `a7d4c9e2f1b3_add_music_projects_table.py`
- `b7e2c4a1d903_add_campaign_continuation_authority_provenance.py`
- `c8e42a91d307_merge_guardian_coding_claim_and_main_heads.py`
- `d86f2a4b1c90_coding_run_claim_heartbeat.py`
- `d91e4fa6702b_add_inference_usage_events.py`
- `e42c7d0b9135_coding_run_worker_ownership.py`

The virtiofs `com.apple.provenance` `stat` failure that motivated the June-2026
mount removal **does not reproduce on this host**: all 140 migration files
carry the extended attribute, yet `os.path.exists` returns true for every one
of them, 0/40 probes failed, and Alembic's `ScriptDirectory` read all 135
revisions through the bind mount. The mount removal was therefore not the
cause here, and the repair does not depend on it.

## 4. The repair

The stock startup keeps its pre-baked image contract — `image`,
`pull_policy: never` and `build` are unchanged, and no source-build contract is
substituted. What changed is that the migrator now **proves** the image's
migration source describes this checkout before it applies anything.

**`docker-compose.yml`** — the migrator gains a read-only side mount and one
environment variable:

```yaml
      CODEXIFY_SOURCE_MIGRATIONS_DIR: /source-migrations
    volumes:
      - ./backend:/app/backend
      - type: bind
        source: ./guardian/db/migrations
        target: /source-migrations
        read_only: true
        bind:
          create_host_path: false
```

The checkout's migration source is mounted **only for comparison**. It is never
executed from, and `create_host_path: false` makes a missing checkout fail
loudly at container creation instead of silently mounting an empty directory.

**`backend/scripts/docker/run_migrator.py`** — three fail-closed gates, in
order:

1. **Coherence proof.** SHA-256 over `versions/*.py` in the effective
   (image-baked) migration source and in `CODEXIFY_SOURCE_MIGRATIONS_DIR`. Any
   revision missing on either side, any content mismatch, or any read error
   aborts the run before Alembic is invoked. The log names the offending
   revisions.
2. **Single head.** The effective migration source must resolve to exactly one
   Alembic head; zero heads and multiple heads both fail closed.
3. **Database readback.** After `alembic upgrade heads`, the migrator reads
   `SELECT version_num FROM alembic_version` directly from PostgreSQL and
   requires it to equal that head. A migration that did not land is a failure,
   not a successful exit.

The comparison only runs when `CODEXIFY_SOURCE_MIGRATIONS_DIR` is set. The
stock compose sets it; the packaged runtime migrator and the disposable
Private Preview migration proof (`scripts/ops/private_preview_database_migration_proof.sh`)
run the same script with no mounts and no such variable, so they are unaffected.

**Ordering.** The repair relies on the ordering that already exists in the
stock compose: `backend` depends on `migrator` with
`condition: service_completed_successfully`. No new mechanism was added, so a
non-zero migrator exit means the application services are never started.

**What was deliberately not done.** Mounting this checkout's guardian *over* the
migrator's own tree was rejected: it would have re-introduced the June-2026
virtiofs removal, and a stale image would still have looked successful while
running a checkout's migrations against a different application source.

## 5. Proof surfaces

| # | Proof surface | Classification | Result |
| --- | --- | --- | --- |
| 1 | Coherence comparison, stale image vs newer source (rejected, revision named) | Unit/contract test | PASS |
| 2 | Coherence comparison, matching source (accepted) | Unit/contract test | PASS |
| 3 | Coherence comparison, image ahead of source (rejected) | Unit/contract test | PASS |
| 4 | Coherence comparison, same revision with different content (rejected) | Unit/contract test | PASS |
| 5 | Missing migration source (rejected) | Unit/contract test | PASS |
| 6 | Migration source without revisions (rejected) | Unit/contract test | PASS |
| 7 | Multiple Alembic heads (rejected) | Unit/contract test | PASS |
| 8 | No Alembic head (rejected) | Unit/contract test | PASS |
| 9 | Migrator exits non-zero and never invokes Alembic on an incoherent source | Unit/contract test | PASS |
| 10 | `alembic_version` readback must equal the head (mismatch rejected) | Unit/contract test | PASS |
| 11 | DSN normalisation for `postgresql+psycopg` selectors | Unit/contract test | PASS |
| 12 | `backend` and the workers depend on `migrator: service_completed_successfully` | Static | PASS |
| 13 | Compose side-mount wiring, read-only, `create_host_path: false` | Static + Unit/contract test | PASS |
| 14 | Pre-baked image contract preserved (`image`/`build`/`pull_policy` unchanged) | Static + Unit/contract test | PASS |
| 15 | Application services serve this checkout's `guardian` | Static + Unit/contract test | PASS |
| 16 | Launcher startup unchanged | Static + Unit/contract test | PASS |
| 17 | Packaged runtime compose unchanged; no `run_migrator.py` in it | Static + Unit/contract test | PASS |
| 18 | Local-only provider contract and supported profile unchanged | Static + Unit/contract test | PASS |
| 19 | `docker compose config` resolves with a synthetic local-only env | Static | PASS |
| 20 | Documentation validator | Static | PASS |
| 21 | Stock-path runtime: source-matched image, migration applies the source head | Disposable runtime | PASS — [§6.2](#62-case-a--matching-source-matched-image) |
| 22 | Stock-path runtime: stale image fails closed, database stays unmigrated | Disposable runtime | PASS — [§6.3](#63-case-b--stale-pre-baked-image-isolated) |
| 23 | Stock-path runtime: backend does not start after a failed migrator | Disposable runtime | PASS — [§6.3](#63-case-b--stale-pre-baked-image-isolated) |

### 5.1 Test commands and results

Run from the isolated worktree at `97778bed`:

```
python -m pytest -v tests/ops/test_source_compose_supported_profile_contract.py \
                   tests/ops/test_stock_compose_migrator_contract.py
→ 22 passed

python -m pytest -v tests/test_whooshd_smoke_env_contract.py
→ 85 passed

python -m pytest -q tests/architecture/test_beta_release_boundary.py
→ 122 passed

docker compose --env-file <synthetic-local-only>.env -f docker-compose.yml config --quiet
→ exit 0

python scripts/validate_docs.py
→ exit 0

git diff --check
→ exit 0
```

## 6. Disposable runtime proof

**Classification: Disposable runtime. Executed — PASS.**

Ordinary stock Compose invocation only. `scripts/whooshd_docker_smoke_up.sh` was
not used, and no source-matched launcher image was injected as a substitute for
the stock behaviour: the image used in the passing case was **built from this
checkout** with the repository's own `backend/Dockerfile`, and the failing case
used the untouched pre-baked `codexify-backend-runtime:latest`.

### 6.1 Preflight

| Check | Result |
| --- | --- |
| Host physical capacity | `/Volumes/Dev_SSD` 931 GiB total; **1.5 GiB free** at preflight (100% capacity) — see [§8.1](#81-operational-residuals) |
| Docker VM capacity | `overlay` inside the Docker VM: 125.7 GiB total, 75.7 GiB used, **43.6 GiB available** |
| Clean source checkout | Worktree at `97778bedf5a1ec4a04fb2fbb968dafb0aed9582c`; only this task's authorized modifications present |
| Unique Compose projects | `stockmigrator01` (matching case), `stockmigrator01stale` (stale case) — no pre-existing volumes, networks, or containers under either name |
| No shared writable volumes | Project-scoped `stockmigrator01_pg_data` / `stockmigrator01stale_pg_data`; the shared `codexify_cli_home`, `hf_cache`, `neo4j_data`, `pg_data` volumes of other projects were **not** used, and the two proof projects were removed with `down -v` |
| Private Preview ownership overlap | None. The proof used the distinct tag `codexify-backend-runtime:stockmigrator01`; `codexify-backend-runtime:latest` (the Private Preview's tag) was **not** rebuilt, only read |
| Port collisions | The stock defaults collide with a devproxy already bound to `127.0.0.1:8888`. The proof used free loopback ports `15433` (postgres), `18899` (backend), `17474`/`17687` (neo4j), all verified free before the run |
| Exact image identity | matching: `sha256:80e23e814dbb76835bb6bbbf18871b82a54fd10e84a9bae58f0f24e9bbff5ac0` (created `2026-11-04T17:02:14Z`, 4,798,730,552 bytes); stale: `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55` (created `2026-10-29T13:02:16Z`, 4,637,971,185 bytes) |
| Baked migration source, matching image | `script_dir=/app/guardian/db/migrations`, `heads=['a7d4c9e2f1b3']`, 135 revisions, 135 version files |
| Baked migration source, stale image | `script_dir=/app/guardian/db/migrations`, `heads=['3a91d7c4e8b2']`, 128 revisions, 128 version files |

### 6.2 Case A — matching source-matched image

| Verification point | Observed |
| --- | --- |
| Migrator exit status | **0** |
| Coherence proof | `Migration source is coherent (135 revisions)` |
| Actual migration source executed | `/app/guardian/db/migrations` (image-baked), head `a7d4c9e2f1b3` |
| Alembic run | `alembic --raiseerr -c /app/backend/alembic.ini upgrade heads` |
| Migrator's own readback | `Verified alembic_version == a7d4c9e2f1b3` |
| **Direct PostgreSQL readback** | `select version_num from alembic_version` → `a7d4c9e2f1b3`; `select count(*)` → **1** |
| Single revision head | Confirmed — one row, equal to the single Alembic head |
| Matching intended source revision | Yes — the applied revision equals the checkout's head `a7d4c9e2f1b3` |
| Backend readiness after successful migration | `stockmigrator01-backend-1` became **healthy**; `GET /ping` → **HTTP 200** `{"status":"Guardian awake!"}` |
| Ordering | Compose started the backend only after the `migrator` service container had exited 0 (`service_completed_successfully`) |

### 6.3 Case B — stale pre-baked image, isolated

| Verification point | Observed |
| --- | --- |
| Migrator exit status | **1** |
| Diagnosis | `the migration source does not describe this checkout (effective_revisions=128, source_revisions=135, missing_from_source=[], extra_in_source=[…7 revisions…], content_mismatches=[], errors=[]); rebuild the backend image from this checkout before starting the stack` |
| Alembic invoked? | **No** — the comparison aborted before `alembic upgrade` |
| **Direct PostgreSQL readback** | `to_regclass('public.alembic_version')` → `ABSENT`; `select version_num from alembic_version` → *relation does not exist* — **nothing was migrated** |
| Backend readiness | **Never.** `docker compose up -d backend` exited **1** with `service "migrator" didn't complete successfully: exit 1`; the backend container was created but never started |
| Isolation | Separate project `stockmigrator01stale`; torn down with `down -v` |

The seven revisions named in the failure are exactly the seven the pre-baked
image is missing.

### 6.4 Postflight

- Private Preview: unchanged — same 13 containers, same uptime, backend image
  still `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55`.
- `codexify-backend-runtime:latest`: unchanged — the tag was read, never rebuilt.
- Both proof projects were removed with `down -v --remove-orphans`; no proof
  container, volume, or network remains.
- The proof image `codexify-backend-runtime:stockmigrator01` was removed after
  the run. Its identity is recorded above and its build layers remain in the
  BuildKit cache, so the image can be reproduced with the same command.

### 6.5 What the runtime proof does and does not establish

**Establishes:** on the stock Compose path, with the ordinary invocation, the
migrator applies exactly the checkout's migration head and proves it from the
database; and a stale image cannot reach a successful-looking startup, because
it fails closed before touching the schema and before the application starts.

**Does not establish:** any qualification of the stock startup. Gate A–H
coverage, provider-ledger evidence, browser behaviour, retrieval provenance and
restart recovery were **not** executed here and belong to the future
`supported-compose-stock` run.

### 6.6 Environment note

The first execution of this proof reached the migration gates but the backend
refused to start: the supported profile `v1-local-core-web-mcp` declares a
provider contract (`LOCAL_RUNTIME_PRESET=whooshd-mlx`, `LOCAL_COMPAT_FIRST=true`,
`LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd`, `LOCAL_PROVIDER_VENDOR=whooshd`) that the
stock Compose file does not itself supply, so a synthetic environment must
provide it. That is an operator-side environment requirement, not a migration
defect, and it was satisfied in the synthetic local-only env used for the
recorded run. No profile declaration, Compose file, or cloud/connector
configuration was changed to achieve it.

## 7. Boundaries preserved

- **Stock direct Compose startup** — repaired in place; no third startup
  mechanism was introduced.
- **Source-matched qualification launcher** — untouched. `scripts/whooshd_docker_smoke_up.sh`
  and its 85-test contract suite are unchanged and green.
- **Packaged `docker-compose.runtime.yml`** — untouched. Its migrator declares
  no volumes, runs the compiled runtime dispatcher
  (`/app/runtime/codexify-runtime migrator`), and uses Alembic's Python API
  against `/app/runtime/migrations`. It does not execute `run_migrator.py`, so
  the new comparison does not apply to it.
- **Private Preview** — untouched. It runs the shared
  `codexify-backend-runtime:latest` tag, so this task did **not** rebuild that
  tag; the runtime proof used a separate image tag and separate Compose
  projects.
- **Qualification authority** — no rubric written, no registry entry created or
  edited, no registry status changed by hand.
- **Supported profiles, cloud-provider configuration, connector configuration,
  host Whoosh'd, existing databases and volumes** — untouched.

## 8. Pre-existing failures (baseline, not caused by this change)

### 8.1 Operational residuals

- **Host volume capacity.** Building the proof image grew the Docker data image
  on `/Volumes/Dev_SSD` by roughly 8 GB; the file is sparse and does not shrink
  when the image tag is deleted, so the host went from 9.3 GiB to about 1.3 GiB
  free at 100% capacity. The proof image was removed, and both proof projects
  were torn down, but reclaiming the underlying allocation would require a
  global BuildKit prune or a Docker Desktop disk trim, neither of which this
  task is authorized to perform. **This is disclosed, not repaired.**
- **A second executor holds an unpushed branch** at
  `/Users/chriscastillo/.codex/worktrees/3164/Codexify-main`
  (`codex/stock-compose-migration-source`, `e50f5756e`) based on the same base
  commit and touching an overlapping `docker-compose.yml` plus its own
  `tests/test_stock_compose_migrator_contract.py` under `tests/` rather than
  `tests/ops/`. It was not pushed and was not touched by this task. The two
  approaches are equivalent in intent but differ in mechanism; the overlap is
  reported for the requester to arbitrate rather than merged unilaterally.

### 8.2 Baseline failures

These reproduce identically on the unmodified base commit
`97778bedf5a1ec4a04fb2fbb968dafb0aed9582c` and are recorded, not fixed:

| Command | Failure | Baseline? |
| --- | --- | --- |
| `python scripts/qualification/generate_registry.py --check` | `supported-compose: not current (config/supported_profiles/v1-music-producer.yaml); 12 reason(s)` — registry drift | Yes — identical on the unmodified base. The registry and rubric are outside this task's scope and were not regenerated. The `Qualification Contracts` workflow is path-filtered to `docs/qualification/**`, `scripts/qualification/**`, `tests/qualification/**` and its own file, none of which this change touches, so the drift does not gate this PR; it does gate any future change in those paths until the registry is regenerated under its own authority. |
| `pytest tests/ops/` (broader suite) | 4 failures: 3× `test_candidate_runtime_checkpoint.py`, 1× `test_codexify_tester_services.py::test_tester_status_accepts_a_running_account_import_worker` | Yes — identical set on the unmodified base. The tester failure is caused by this host sandbox blocking heredoc-created temporary files in `codexify_tester.sh`, not by product code. |

## 9. What this receipt does not claim

- It does not claim the stock Compose startup is **qualified**. The repair is
  implemented and verified; the qualification is a separate task with its own
  rubric, run, and receipt under `supported-compose-stock`.
- It does not claim a runtime PASS from tests alone. The disposable runtime
  evidence is reported in [§6](#6-disposable-runtime-proof) with its own
  classification, and the surfaces that were **not** executed — the stock
  startup's Gate A–H coverage beyond the migration gates — are named as such
  rather than being folded into the migration result.
- It does not claim anything about the live Private Preview database, which
  remains at `3a91d7c4e8b2`.
- It does not move the release gate. Release posture remains **HOLD**.
