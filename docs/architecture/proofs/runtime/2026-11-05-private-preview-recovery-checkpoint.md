# Private Preview recovery checkpoint — 2026-11-05

> **Release posture: HOLD.** This receipt records a **compatibility
> determination** for the existing Private Preview backup/restore helper
> against the live deployment, and a **HOLD-before-interruption** result. It
> does **not** interrupt the Preview, does **not** produce or retain a backup
> artifact, does **not** change any schema, does **not** modify the helper or
> its tests, and does **not** promote any release or qualification claim.

## Result

**Checkpoint verdict: HOLD before interruption.** The existing backup helper
**cannot** be executed compatibly against the live Private Preview deployment
as written. Requirement 2 ("establish a compatible backup invocation") fails on
two of its seven pre-conditions, both proven by read-only inspection. Because
the helper's Compose resolution does **not** reproduce the live deployment, the
procedure's own `up -d` steps would **recreate the Preview's own containers and
re-run the Preview's migrator against the live database** — an implicit
migration and a mutation of the deployment it is meant to protect. The task
specification's stop condition applies: *"HOLD before interruption if
compatibility or authorization is insufficient."*

**Nothing was executed against the Preview.** No container was stopped,
started, recreated or removed; no database was migrated, dumped or restored; no
scratch volume or container was created; no backup artifact exists. The
Private Preview was read throughout and remains healthy and unmodified.

| Requirement | Condition | Disposition |
| --- | --- | --- |
| 1 | Exact Preview schema identity established | **PASS** — serving revision `dece01821`, live PostgreSQL head `a7d4c9e2f1b3` |
| 2.1 | Candidate checkout's Alembic head matches live head | **PASS** for `origin/main`; **FAIL** for the operator checkout (`3a91d7c4e8b2`) |
| 2.2 | Helper present and its safety tests pass at that checkout | **PASS** — blob identical, `bash -n` clean, 6/6 pytest green |
| 2.3 | Resolved Compose project matches the intended project | **PASS** — resolves to `codexify_private_preview` |
| 2.4 | Image references and mounts cannot mutate another deployment | **FAIL** — the helper's resolution diverges from live on 13/18 services and would **recreate the Preview's own containers** |
| 2.5 | Backup directory resolves outside `Docker.raw` | **PASS** — `/Volumes/Dev_SSD/codexify-backups` resolves outside `Docker.raw` |
| 2.6 | Expected backup size fits the destination | **PASS** — ≈ 6.5 GB required vs 57 GiB free |
| 2.7 | Checkout cannot trigger an implicit migration or image rebuild | **FAIL** — the `migrator` service is in the helper's recreate set, with a *different* migration-source posture than live |
| 3 | Explicit operator approval precedes interruption | **NOT REACHED** — the gate was never approached; no approval was requested or assumed |
| 4 | A retained PostgreSQL/media checkpoint exists | **NOT MET** — no artifact was produced; producing one is unsafe under the present helper |
| 5 | Backup scope and uncovered data documented | **PASS** — §7, recorded prospectively |
| 6 | No release or qualification claim promoted | **PASS** — release posture unchanged at **HOLD** |

An additional defect, independent of the two failed conditions above, was found
and is recorded in §6.3: the helper's `START_SERVICES` set covers 8 of the
deployment's 13 long-running services.

## 1. Scope and boundary

- **Starting repository SHA:** `c28bc8f46e6896b9dec22d6cc7ba7696260c2b08`
  (`origin/main`). PRs #991 (stock Compose migration-source repair), #1000
  (frontend test stabilization), #1001 (Docker capacity readiness), #1002 and
  #1004 are merged into it.
- **Branch:** `docs/private-preview-recovery-checkpoint-20261105`, created from
  `origin/main` in an isolated worktree at `.worktrees/pc01-proof`. The only
  file staged by this task is this receipt.
- **Authorized file:** `docs/architecture/proofs/runtime/2026-11-05-private-preview-recovery-checkpoint.md`
  (this document).
- **Read-only references, not edited:**
  `scripts/ops/private_preview_backup_restore_proof.sh`,
  `tests/ops/test_private_preview_backup_restore_proof.py`. The helper's
  `source_alembic_revision == repository_alembic_revision` guard was **not**
  removed, weakened or reinterpreted.
- **Not touched:** application code, Compose files, migrations, the helper or
  its tests, qualification rubrics or registry, release-authority documents,
  Docker configuration, the Private Preview deployment, and every other
  agent's worktree.
- **Measurement window:** all live measurements were taken on **2026-11-06**
  (host clock 2026-11-06 14:34–14:40 EST / 19:34–19:40 UTC). See §2.1 for why
  the date matters.

## 2. Current identity

### 2.1 The deployment moved during this task — read this first

The Private Preview was **redeployed by another thread while this task was in
progress**, and the task's own starting premise (that `origin/main` and the
live database disagree on schema) **stopped being true partway through the
inspection**.

| Observation | At task start | At measurement time (2026-11-06 19:34 UTC) |
| --- | --- | --- |
| Live PostgreSQL Alembic revision | `3a91d7c4e8b2` | **`a7d4c9e2f1b3`** |
| Serving checkout | `.worktrees/private-preview-serving-20261029` @ `c8e72ef86` | **`.worktrees/private-preview-serving-20261106` @ `dece01821`** |
| Pinned serving source (`serving-source`) | `…-20261029` | **`…-20261106`** |
| Live container config-hashes | matched the 20261029 overlay resolution | **match the 20261106 overlay resolution (18/18)** |
| `origin/main` Alembic head | `a7d4c9e2f1b3` (≠ live) | **`a7d4c9e2f1b3` (== live)** |

Every identity claim in this receipt is taken from the **measured** live state
at the stated timestamp, never from the branch name or from `origin/main`. The
live revision was read directly from the database; the serving revision was
read from the operator's own serving-source pin and from the live containers'
own Compose labels and bind mounts.

Two consequences follow, and they are the substance of this receipt:

1. **Requirement 2.1 is now satisfiable.** `origin/main`'s Alembic head
   (`a7d4c9e2f1b3`) now equals the live database head. The schema-compatibility
   blocker that would have applied is **gone** — not because it was worked
   around, but because the deployment advanced to meet `main`.
2. **The remaining blockers are structural and do not move with the
   deployment.** The helper's Compose file set and its service-restart set are
   out of sync with the operator's own serving lifecycle, and that mismatch is
   independent of which revision is deployed.

### 2.2 Identity record

| Property | Value |
| --- | --- |
| `origin/main` | `c28bc8f46e6896b9dec22d6cc7ba7696260c2b08` |
| Preview serving revision | `dece0182163970b7d5de1b849306b52ac56030b7` |
| Serving checkout path | `/Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106` |
| Serving revision's Alembic head | `a7d4c9e2f1b3` |
| Live PostgreSQL Alembic revision | **`a7d4c9e2f1b3`** (read from `alembic_version`) |
| `origin/main`'s Alembic head | `a7d4c9e2f1b3` |
| Operator checkout's Alembic head | `3a91d7c4e8b2` (**behind live**) |
| Compose project | `codexify_private_preview` |
| Long-running services | **13** |
| One-shot services (exited 0) | **5** — `migrator`, `model-prep`, `graph-init`, `private-preview-auth-posture`, `e2e` |
| Named volumes | **9** (see §2.4) |
| Backup helper version | `SCRIPT_VERSION=1`, blob `ec7f6bbeab6c10b5b879b417b0eb1d400f78c2dd` |
| Helper blob on `origin/main` | **identical** (`ec7f6bbe…`) — the helper is unchanged between the operator checkout and `main` |
| Docker Desktop / engine / Compose | 4.98.0 / 29.9.2 client+server / v5.6.1 |
| Docker context | `desktop-linux` (`unix:///Users/chriscastillo/.docker/run/docker.sock`) |

### 2.3 Container image identities

| Image | Digest |
| --- | --- |
| `codexify-backend-runtime:latest` (backend, 5 workers, origin) | `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55` |
| `codexify-worker-coding-runtime:latest` | `sha256:a3177274d0b5e90e4db762f6723b312ed57b6c1bf2f2aaa69995ce9ab735229b` |
| `postgres:15` | `sha256:c961aa287d8698297cb26cdfadfbe9fd2cbaf77e53cfffe9636e8d8a1e4d842c` |
| `neo4j:5` | `sha256:d9cfe82983d27f5a75b3aaae8f316d04f9a698a3b7f6103a508f7caf8362f255` |
| `redis:7-alpine` | `sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499` |
| `node:20-alpine` (frontend) | `node:20-alpine` tag; digest not pinned by the deployment |

### 2.4 Named volumes

`codexify_private_preview_pg_data`, `…_neo4j_data`, `…_chroma`,
`…_hf_cache`, `…_codexify_cli_home`, `…_corepack_cache`,
`…_e2e_pnpm_store`, `…_e2e_frontend_src_node_modules`,
`…_frontend_pnpm_store`.

Recorded identities (name + mountpoint) for the three data-bearing volumes:

```
codexify_private_preview_pg_data    |/var/lib/docker/volumes/codexify_private_preview_pg_data/_data    |local
codexify_private_preview_neo4j_data |/var/lib/docker/volumes/codexify_private_preview_neo4j_data/_data |local
codexify_private_preview_chroma      |/var/lib/docker/volumes/codexify_private_preview_chroma/_data      |local
```

### 2.5 Host and Docker capacity

| Property | Value |
| --- | --- |
| `/Volumes/Dev_SSD` | 931 GiB total, **57 GiB free (94% used)** |
| `/` (system volume) | 228 GiB total, **13 GiB free (51% used)** |
| `Docker.raw` | `/Volumes/Dev_SSD/offload/docker/Docker.raw`, 137,438,953,472 bytes |
| Docker engine root (guest) | `/var/lib/docker` |

`Docker.raw` was **resolved, not assumed** — it is the Docker Desktop data file
on the development volume, and it is the reason a backup destination on
`/Volumes/Dev_SSD` must be a *specific* path rather than the volume root.

## 3. The authoritative Compose invocation (established, not assumed)

The Private Preview's serving lifecycle is owned by the operator's own
autostart script, `~/Library/Application Support/Codexify/private-preview/codexify_private_preview_autostart.sh`.
When a serving-source pin is present, that script composes with **three**
files, **all taken from the pinned serving root**:

```bash
export CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT="$source_root"
COMPOSE_FILES=(
  --project-directory "$REPO_ROOT"                    # the operator checkout
  --env-file "$PRIVATE_PREVIEW_ENV_FILE"             # operator checkout
  -p "$PRIVATE_PREVIEW_PROJECT"                       # codexify_private_preview
  -f "$source_root/docker-compose.yml"
  -f "$source_root/docker-compose.private-preview.yml"
  -f "$source_root/docker-compose.private-preview-serving.yml"
)
```

This is corroborated by the live containers' own labels:

```
com.docker.compose.project.config_files =
  …/.worktrees/private-preview-serving-20261106/docker-compose.yml,
  …/.worktrees/private-preview-serving-20261106/docker-compose.private-preview.yml,
  …/.worktrees/private-preview-serving-20261106/docker-compose.private-preview-serving.yml
com.docker.compose.project.working_dir      = /Volumes/Dev_SSD/Codexify-main
com.docker.compose.project.environment_file = /Volumes/Dev_SSD/Codexify-main/.env.private-preview
```

**Verification.** Resolving that exact invocation and comparing its
`docker compose config --hash='*'` output against the live containers' own
`com.docker.compose.config-hash` labels reproduces **all 18 services
exactly**:

```
ALL_MATCH=YES (18/18)
```

The same invocation, run with `up -d --dry-run` over the helper's
`START_SERVICES` set, reports **0 `Recreate` lines** — it does not mutate the
deployment.

### 3.1 The deployment's bind topology is split-root

Live backend container bind mounts (abridged):

```
serving-root/guardian   -> /app/guardian      serving-root/backend   -> /app/backend
serving-root/config     -> /app/config        serving-root/plugins   -> /app/plugins
serving-root/tests      -> /app/tests         serving-root/docker    -> /app/docker
serving-root/pytest.ini -> /app/pytest.ini
operator-checkout/data/media   -> /app/data/media
operator-checkout/data/imports -> /app/data/imports
```

**Application code is served from the pinned serving root; durable data is
served from the operator checkout.** This split is the operator's deliberate
source-isolation posture and is the reason a backup helper must be able to
address both roots independently.

## 4. Why the existing helper is not compatible

The helper's Compose array is fixed (`scripts/ops/private_preview_backup_restore_proof.sh:23-30`):

```bash
COMPOSE=(
  docker compose
  --project-directory "${REPO_ROOT}"
  -p "${PROJECT_NAME}"
  --env-file "${ENV_FILE}"
  -f "${REPO_ROOT}/docker-compose.yml"
  -f "${REPO_ROOT}/docker-compose.private-preview.yml"
)
```

Two files, both from `REPO_ROOT`. There is **no parameter** for the serving
root, the third overlay file, or `CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT`.

### 4.1 The helper's resolution does not reproduce the live deployment

Resolved from the operator checkout (the only checkout that holds the live
`.env.private-preview`, `data/media`, `data/imports` and `.venv`), **13 of 18
services diverge** from the live config-hashes:

```
diverging: backend  e2e  frontend  migrator  model-prep  private-preview-origin
           worker-account-import  worker-chat  worker-chat-embed  worker-coding
           worker-document-embed  worker-voice  worker-warmup
matching:  db  graph-init  neo4j  private-preview-auth-posture  redis   (5/18)
```

Setting `CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT` does **not** help: neither
`docker-compose.yml` nor `docker-compose.private-preview.yml` references it
(`grep -c` returns `0` for both). `COMPOSE_FILE` is ignored when explicit `-f`
flags are passed, and `docker-compose.override.yml` is not auto-loaded once
`-f` is explicit.

Running the helper from the serving root instead fails immediately: that
checkout has no `.env.private-preview`, no `data/media`, no `data/imports` and
no `.venv/bin/python`.

### 4.2 The dry-run consequence (the decisive test)

`docker compose up -d --dry-run` over the helper's `START_SERVICES`, resolved
the way the helper resolves it, reports `Recreate` for **ten** of the
Preview's own containers:

```
codexify_private_preview-backend-1
codexify_private_preview-frontend-1
codexify_private_preview-migrator-1          <-- re-runs migrations
codexify_private_preview-model-prep-1
codexify_private_preview-private-preview-origin-1
codexify_private_preview-worker-account-import-1
codexify_private_preview-worker-chat-1
codexify_private_preview-worker-chat-embed-1
codexify_private_preview-worker-document-embed-1
codexify_private_preview-worker-warmup-1
```

This is the finding that makes the run **unacceptable**, for three independent
reasons:

1. It **mutates the deployment it is meant to protect.** The helper's
   procedure calls `compose stop` (line 394) and later `compose up -d
   "${START_SERVICES[@]}"` (line 553). Both act on the *Preview's own*
   containers. Under the helper's resolution they would be **recreated**, not
   merely restarted — a different container, different config hash, different
   migration posture, running the operator's serving code from a different
   root than the one the deployment was launched from.
2. It **re-runs the Preview's migrator** against the live database. The
   operator checkout's working-tree `docker-compose.yml` predates the stock
   migration-source repair, so the recreated `migrator` would run **without**
   the `CODEXIFY_SOURCE_MIGRATIONS_DIR` / `/source-migrations` comparison mount
   that the live deployment carries. That is precisely the implicit-migration
   path this task forbids: the live schema is `a7d4c9e2f1b3`, and a migrator
   whose source-posture has changed is not entitled to be run against it.
3. It **breaks the revision-equality guard's meaning.** The guard compares the
   *repository* head to the *source* revision. It would pass from a
   schema-compatible checkout — but it would pass while the procedure is
   simultaneously recreating the migrator, which is what the guard exists to
   prevent. Guard-passing is not evidence of safety here.

Under the authoritative three-file invocation (§3), the same dry-run reports
**0 `Recreate`**.

### 4.3 `REPO_ROOT` couples four independent things

`REPO_ROOT` is derived from the script's own location (line 9) and then
determines, with no override:

| Line | Derived from `REPO_ROOT` | Must resolve to |
| --- | --- | --- |
| 9 | `REPO_ROOT` | a checkout at the **live** schema head `a7d4c9e2f1b3` |
| 10 | `ENV_FILE` | the **live** `/Volumes/Dev_SSD/Codexify-main/.env.private-preview` |
| 12 | `MEDIA_ROOT` | the **live** `/Volumes/Dev_SSD/Codexify-main/data/media` (5.6 GB, 8,995 files) |
| 13 | `IMPORT_ROOT` | the **live** `/Volumes/Dev_SSD/Codexify-main/data/imports` (53,870 files) |
| 15 | `PYTHON_BIN` | an interpreter with **Alembic** installed |

Today **no single checkout satisfies all five.** The operator checkout holds
the env file, the live data roots and a working `.venv`, but its Alembic head
is `3a91d7c4e8b2` — behind the live `a7d4c9e2f1b3`. `origin/main` satisfies the
schema head but holds none of the env file, data roots or virtualenv. The
helper's own guard at lines 304–308 would stop it before any mutation in that
case, which is the correct behaviour, but it means the checkpoint **cannot be
produced at all** today.

### 4.4 The service-restart set is incomplete

```bash
START_SERVICES=(
  backend frontend worker-chat worker-chat-embed worker-document-embed
  worker-warmup worker-account-import private-preview-origin
)
```

Eight services. The deployment has **thirteen** long-running services. Missing
from the list: **`worker-coding`** and **`worker-voice`** (plus `db`, `neo4j`
and `redis`, which come up only transitively).

The helper calls `compose stop` with no service list (line 394) — that stops
**all** services — and then restarts only `START_SERVICES` (line 553). Under
either resolution, **`worker-coding` and `worker-voice` would be stopped and
never brought back.** The Preview would not return to its original posture, and
the task's acceptance criterion 8 ("Preview returns to its original healthy
posture") would fail on a completed run.

### 4.5 The serving overlay is not in the repository

`docker-compose.private-preview-serving.yml` is **absent from `origin/main`**.
It exists only as an **untracked** file inside the serving worktree
(sha256 `678e8cf1f04d4e2f94a6d79c812961d4d5819946eabd7bc85fb899be74a9e1cf`).
Tracked history for it exists only on the `codex/private-preview-*` branches
(`5cfe3efb9`, `5057c6b39`), neither of which is an ancestor of `origin/main`.

So even a corrected helper running from `origin/main` has no tracked way to
name the third Compose file.

## 5. What the guard did and did not do

The task states plainly: *"Do not remove the revision-equality guard. Do not
reinterpret a behind-schema database as permission to migrate it."* Neither
was done, and neither was needed to reach this verdict.

The guard was **not** the blocker. Measured outcomes:

| Checkout | Repository head | Live head | Guard verdict |
| --- | --- | --- | --- |
| `origin/main` @ `c28bc8f4` | `a7d4c9e2f1b3` | `a7d4c9e2f1b3` | would **pass** |
| Serving root @ `dece01821` | `a7d4c9e2f1b3` | `a7d4c9e2f1b3` | would **pass** |
| Operator checkout @ `45f1cac86` | `3a91d7c4e8b2` | `a7d4c9e2f1b3` | would **fail** (correctly) |

The guard remains exactly as written and was not exercised in either direction,
because no run was attempted. The blockers are the Compose file set, the
`REPO_ROOT` coupling and the service-restart set — **not** the guard.

> **Method note.** Alembic heads in this receipt were computed with the real
> Alembic CLI (`python -m alembic -c backend/alembic.ini heads`), not by
> scanning `down_revision` text. A regex scan of `down_revision` is wrong for
> multi-parent merge revisions and produced a false "match" during the initial
> inspection of this task.

## 6. Smallest required correction (reported, not applied)

Per the task's instruction — *"If code changes are necessary, stop and report
the smallest required correction and its ADR impact"* — the following is
reported rather than applied. **No file outside the authorized receipt was
modified.**

### 6.1 Compose file set — add the serving overlay

Add the pinned serving root as a third `-f` and export the source root, so
that the helper resolves the deployment exactly as the operator's own autostart
script does. Measured, this single change is what closes Requirement 2.4 and
2.7:

```
docker compose --project-directory /Volumes/Dev_SSD/Codexify-main \
  --env-file /Volumes/Dev_SSD/Codexify-main/.env.private-preview \
  -p codexify_private_preview \
  -f <checkout-at-live-head>/docker-compose.yml \
  -f <checkout-at-live-head>/docker-compose.private-preview.yml \
  -f /Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106/docker-compose.private-preview-serving.yml
```

with `CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT` set to the serving root. Verified
against the live deployment: **18/18 config-hashes match, 0 `Recreate`.**

The base files must come from a checkout at the live head: `origin/main`'s
`docker-compose.yml` and the serving root's are byte-identical
(`ce39e889a5e6…`), but the **operator checkout's working-tree copy is not**
(`48d34f360221…`) — it predates the stock migration-source repair, which is
exactly the `migrator`/`backend` divergence measured in §4.1.

### 6.2 Decouple `REPO_ROOT` from the data, env and interpreter roots

`MEDIA_ROOT`, `IMPORT_ROOT`, `ENV_FILE` and `PYTHON_BIN` need independent
overrides (mirroring the existing `PRIVATE_PREVIEW_ENV_FILE` and
`CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR` patterns), so the helper can run from a
checkout at the live schema head while archiving the live `data/media` and
`data/imports`. Without this, §4.3 leaves the checkpoint unreachable.

### 6.3 Extend `START_SERVICES` to the full long-running set

Add `worker-coding` and `worker-voice`. Without this the procedure leaves two
of the Preview's thirteen long-running services stopped (§4.4).

### 6.4 Track the serving overlay

`docker-compose.private-preview-serving.yml` must exist in a tracked
revision, or the helper must resolve it from the pinned serving root at
runtime. Today it exists only as an untracked file in one worktree (§4.5).

### 6.5 ADR impact

| Correction | Changes | ADR adjudication |
| --- | --- | --- |
| 6.1 Compose file set | **Recovery authority**: the helper would take its Compose file set and source root from the operator's serving lifecycle rather than from its own checkout | **Requires separate architectural adjudication** — this is a change to backup authority and to how persistent state is addressed |
| 6.2 `REPO_ROOT` decoupling | **Persistent-state ownership**: the helper would archive the live data roots from a different checkout than the one it runs from | **Requires separate architectural adjudication** — same clause |
| 6.3 `START_SERVICES` | Recovery procedure completeness | Within the existing recovery doctrine; no new authority |
| 6.4 Tracking the overlay | Source-isolation posture made durable | Aligned with ADR-069's source-isolation boundary; a repository-tracked copy of an operator-owned overlay should be reviewed on its own merits |

This receipt itself promotes **no** release or qualification claim, and the
**release posture remains HOLD**. Correcting the helper is a prerequisite for
`QUAL-STOCK-01` only in the sense that a checkpoint must exist and be verified
before the qualification can claim the Preview was protected.

## 7. Evidence boundaries — what a checkpoint would and would not protect

**No checkpoint artifact exists**, so the following is the *prospective* scope
of the helper's procedure as written. It is recorded so that no future reader
mistakes a PostgreSQL-and-media checkpoint for a complete deployment backup.

| Data surface | Covered by the helper | Notes |
| --- | --- | --- |
| PostgreSQL (`…_pg_data`) | **Yes** | `pg_dump --format=custom --no-owner --no-acl`; restored into an isolated scratch database on a `network: none` scratch volume, then removed |
| Durable media (`data/media`) | **Yes** | `tar` archive plus a per-file SHA-256 manifest; file count and manifest digest compared after restore |
| Import staging (`data/imports`) | **No** — **count only** | The helper records `import_staging_file_count` (53,870 files) and asserts no job is in `receiving`/`queued`/`running`. **No import content is archived.** Import staging is *not* recoverable from a checkpoint |
| Neo4j data (`…_neo4j_data`) | **No** | 516 MB of graph data, unprotected |
| Chroma data (`…_chroma`) | **No** | 1.8 GB vector store, unprotected |
| Redis (`…_redis`) | **No** | Unprotected |
| `…_hf_cache` (3.7 GB), `…_corepack_cache`, `…_e2e_pnpm_store` (630 MB), `…_e2e_frontend_src_node_modules`, `…_frontend_pnpm_store`, `…_codexify_cli_home` | **No** | Rebuildable caches and tool state, unprotected |
| Application code | **No** | Not a data surface; recovered from Git |

**Stated plainly: a checkpoint produced by this helper would be a PostgreSQL +
durable-media checkpoint. It would not be a complete deployment backup.**
Neo4j, Chroma and Redis hold live state that this procedure does not protect,
and import staging content would not be recoverable from it. The helper does
assert that no account-import job is left incomplete, which bounds the
import-staging exposure — but it does not remove it.

## 8. Operator approval gate

**Status: NOT REACHED — no approval was requested, assumed, or granted.**

The gate was never approached, because Requirement 2 failed before it. No
Preview interruption was proposed to the operator, and none occurred. There is
no command, checkout, destination, interruption window or recovery procedure
to approve, because none was executed and no executable one could be produced
from the helper as written.

Had compatibility been established, the destination that satisfies Requirement
2.5 would have been `/Volumes/Dev_SSD/codexify-backups` — outside
`Docker.raw` (`/Volumes/Dev_SSD/offload/docker/Docker.raw`), outside the
repository (the helper rejects a backup root inside `REPO_ROOT`, lines
318–320), and not one of the broad roots the helper refuses (lines 321–325).
Required capacity ≈ 6.5 GB against 57 GiB free.

## 9. Validation results

Read-only validation, run at the receipt branch (`origin/main` base):

| Command | Outcome |
| --- | --- |
| `bash -n scripts/ops/private_preview_backup_restore_proof.sh` | **PASS** (no output) |
| `python -m pytest -v tests/ops/test_private_preview_backup_restore_proof.py` | **PASS** — `6 passed in 0.34s` |
| `python scripts/validate_docs.py` | **PASS** (recorded in §11) |
| `git diff --check` | **PASS** (no whitespace errors) |

The helper's own safety tests pass at `origin/main`. Their passing is a
necessary but **not sufficient** condition for compatibility: they cover the
helper's internal invariants, and cannot detect that the helper's Compose
resolution does not match the deployed topology. That gap is exactly what §4
exposes.

Live proof steps (backup artifact hash and size, scratch restore, restored
Alembic revision, table-count agreement, media integrity, volume-identity
comparison, health readback) were **not run** — they are downstream of an
approval that was never reached.

## 10. Preview integrity readback

The Private Preview was **read only** throughout this task and was not
interrupted.

| Check | Result |
| --- | --- |
| Long-running services | **13 / 13 running**; `db`, `backend`, `worker-coding`, `neo4j`, `redis` report healthy |
| One-shot services | **5 / 5 exited 0** |
| Live PostgreSQL revision | `a7d4c9e2f1b3` (read directly from `alembic_version`) |
| Named volumes | 9 present, identities as recorded in §2.4 |
| Container config-hashes | unchanged, 18/18 matching the authoritative invocation (§3) |
| Restore containers / volumes created by this task | **0** |
| Backup artifacts created | **0** |
| Schema changes applied | **none** |
| Application code deployed | **none** |

## 11. Closeout

1. **Starting SHA** — `c28bc8f46e6896b9dec22d6cc7ba7696260c2b08` (`origin/main`).
2. **Preview serving revision** — `dece0182163970b7d5de1b849306b52ac56030b7`, checkout `.worktrees/private-preview-serving-20261106`, pinned by the operator's `serving-source` file and corroborated by the live containers' Compose labels and bind mounts.
3. **Live PostgreSQL head** — `a7d4c9e2f1b3` (equals the serving revision's head and `origin/main`'s head).
4. **Compatible backup checkout** — **none exists.** `origin/main` is schema-compatible but lacks the live env file, data roots and virtualenv; the operator checkout holds those but is behind the live head (`3a91d7c4e8b2`). The helper additionally cannot express the deployment's third Compose file. See §4 and §6.
5. **Backup scope** — none produced. The helper's prospective scope is PostgreSQL + durable media only; Neo4j, Chroma, Redis, the remaining named volumes and import-staging *content* would be unprotected (§7).
6. **Approval status** — **NOT REACHED.** No operator approval was requested or granted; no Preview interruption occurred.
7. **Backup artifact location and hash** — **none.** No artifact was created.
8. **Isolated restore results** — **not performed.** No scratch database, container or volume was created.
9. **Preview health and integrity readback** — 13/13 long-running services up and healthy, 5/5 one-shots exited 0, revision `a7d4c9e2f1b3` unchanged, 9 named volumes intact, 18/18 config-hashes unchanged, 0 restore artifacts created, no schema change, no deployment (§10).
10. **Remaining unprotected data** — Neo4j (516 MB), Chroma (1.8 GB), Redis, `hf_cache` (3.7 GB), `e2e_pnpm_store` (630 MB) and the remaining caches/tool volumes; import staging content (53,870 files — count recorded only) (§7).
11. **Validation results** — `bash -n` PASS; `pytest` 6 passed; `validate_docs.py` PASS; `git diff --check` PASS (§9).
12. **ADR impact** — this receipt claims none. The **required** corrections in §6.1 (recovery authority: Compose file set and source root) and §6.2 (persistent-state ownership: `REPO_ROOT` decoupling) require **separate architectural adjudication**; §6.3 and §6.4 do not. No release or qualification claim is promoted; posture remains **HOLD**.
13. **Commit and PR** — see §12.
14. **NEXT-PROOF-NEEDED** — **QUAL-STOCK-01** (independent `supported-compose-stock` runtime qualification), gated on a corrected and verified helper so that a retained checkpoint exists before the qualification claims the Preview was protected.

## 12. Reproduction

All commands were run read-only with `DOCKER_CONTEXT=desktop-linux`.

```bash
P=/Volumes/Dev_SSD/Codexify-main
WT26=$P/.worktrees/private-preview-serving-20261106

# identity
git -C $P rev-parse origin/main
git -C $WT26 rev-parse HEAD
docker exec codexify_private_preview-db-1 psql -U codexify -d Codexify -Atc \
  "select version_num from alembic_version"
docker volume ls --format '{{.Name}}' | grep '^codexify_private_preview_'

# true Alembic heads (never regex-scan down_revision)
$P/.venv/bin/python -m alembic -c $WT26/backend/alembic.ini heads
$P/.venv/bin/python -m alembic -c $P/backend/alembic.ini heads

# the decisive oracle: does the invocation reproduce the live deployment?
CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT=$WT26 docker compose --project-directory $P \
  --env-file $P/.env.private-preview -p codexify_private_preview \
  -f $WT26/docker-compose.yml -f $WT26/docker-compose.private-preview.yml \
  -f $WT26/docker-compose.private-preview-serving.yml config --hash='*'
# compare each value against:
docker inspect <container> --format \
  '{{index .Config.Labels "com.docker.compose.config-hash"}}'

# the decisive mutation test: will this invocation recreate containers?
CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT=$WT26 docker compose --project-directory $P \
  --env-file $P/.env.private-preview -p codexify_private_preview \
  -f $WT26/docker-compose.yml -f $WT26/docker-compose.private-preview.yml \
  -f $WT26/docker-compose.private-preview-serving.yml \
  up -d --dry-run backend frontend worker-chat worker-chat-embed \
  worker-document-embed worker-warmup worker-account-import private-preview-origin
#   -> 0 Recreate lines
```

`docker compose config --hash='*'` plus `up -d --dry-run` is the read-only
oracle for this deployment: it answers *"would this invocation recreate
containers or re-run the migrator?"* without touching anything. Use it before
any Preview interruption, always.
