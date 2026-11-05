# Stock Compose migration-source consistency — Gate B proof (2026-11-05)

> **Release posture: HOLD.** This receipt records the bounded **Gate B** runtime
> proof of the **stock** (`docker compose up`) Docker Compose startup at one
> exact source revision. It does **not** qualify the stock startup, does not
> create or edit a qualification rubric or registry entry, does not move any
> release gate, and does not touch the live Private Preview database.

## Result

**Stock Gate B: PASS on the evaluated revision, including the mismatch refusals.**

Driven by the ordinary `docker compose` invocation against a disposable
task-owned Compose project and its own PostgreSQL database, the stock startup
brought the database to the evaluated checkout's single Alembic head and
started the backend against that schema. A stale pre-baked image, a same-head
image with different revision content, and a same-head source with a modified
migration environment each failed closed — before any migration was applied,
and before the application was started.

| Question | Disposition |
| --- | --- |
| Evaluated revision | `68c9e52361c5b6169dd18d5d44b39495f7a15f49` (`origin/main`) |
| Branch | `fix/stock-compose-migration-source-gate-b-20261105` (task-owned, unpushed) |
| Startup method | Stock `docker compose` (not `scripts/whooshd_docker_smoke_up.sh`) |
| Source Alembic head at that revision | `a7d4c9e2f1b3`, 135 revision files, single head |
| Implementation correction | Already landed by merged PR #991 (`e571f94b3`); **not re-implemented here** |
| Case A — matching image | **PASS** — migrator exit 0, `alembic_version` = head, exactly one row, backend healthy, `/ping` 200 |
| Case B — stale pre-baked image | **PASS (refusal)** — migrator exit 1, nothing migrated, application never started |
| Case C1 — same head, different revision content | **PASS (refusal)** — migrator exit 1, nothing migrated, application never started |
| Case C2 — same head, different migration environment | **PASS (refusal)** — migrator exit 1, nothing migrated, application never started |
| Source-matched launcher | Unchanged and untouched |
| Packaged runtime (`docker-compose.runtime.yml`) | Unchanged and untouched |
| Private Preview | Untouched — read-only inspection only; image digest unchanged |
| Qualification registry / rubric | Untouched; no status written |
| Release gate | **HOLD** |

## 1. Scope, revision and method

- **Base:** `origin/main` at `68c9e52361c5b6169dd18d5d44b39495f7a15f49`,
  fetched at the start of the task.
- **Branch:** `fix/stock-compose-migration-source-gate-b-20261105`, created
  fresh from that base in an isolated worktree at
  `/Volumes/Dev_SSD/Codexify-main/.worktrees/stock-gate-b-20261105`.
- **Startup method:** the ordinary **stock** Compose invocation,
  `docker compose -p <project> -f docker-compose.yml up -d db migrator
  backend`, against this checkout. `scripts/whooshd_docker_smoke_up.sh` was
  **not** used, and no source-matched launcher image was injected as a
  substitute for the stock behaviour.
- **Isolation:** each case ran in its own disposable Compose project with its
  own project-scoped PostgreSQL volume, its own network, and its own
  loopback ports. No shared volume, container, database or port was used.
- **Environment:** a synthetic, local-only `.env` was written into the
  checkout for Compose interpolation. It contains **no** operator credential,
  **no** cloud key and **no** connector configuration; every value is a
  generated placeholder.

## 2. Current-truth anchors, revalidated

The Task Spec's anchors were re-checked against the evaluated revision rather
than assumed.

| Spec anchor | Revalidated result |
| --- | --- |
| `origin/main` includes merged #996, #998, #999 | **True** — and it also includes **#991**, which had already merged this task's correction, plus #1000 |
| "The stock migrator retains its backend-only bind mount" | **False at this revision.** The stock migrator retains `./backend:/app/backend` *and* adds a read-only `./guardian/db/migrations` comparison mount at `/source-migrations` |
| "The stock backend retains its Guardian and backend source mounts" | **True** |
| "The latest reported migration head is `d91e4fa6702b`" | **Stale.** The graph at this revision resolves to **135** revision files with the single head **`a7d4c9e2f1b3`**. `d91e4fa6702b` is one revision below it. `docs/architecture/00-current-state.md` already records this correction |
| "The previously qualified launcher is not the stock startup" | **True**, and preserved here |
| "Release remains HOLD" | **True**; unchanged by this task |

Head resolution was computed twice, independently: by parsing `revision` /
`down_revision` out of all 135 `guardian/db/migrations/versions/*.py` files
(135 parsed, 0 unparsed, 1 head, 0 multi-head), and by the repository's own
`tests/migration/test_alembic_revision_uniqueness.py` (4 passed).

## 3. Root cause, verified in source

`backend/migrations` is a git symlink to `../guardian/db/migrations`, and
`backend/alembic.ini` sets:

```ini
script_location = %(here)s/../guardian/db/migrations
```

`%(here)s` is `backend/`, so the effective migration directory is
`/app/guardian/db/migrations` inside the container. Under the **pre-#991**
stock arrangement the migrator mounted only `./backend:/app/backend`, so that
path resolved into the **image's baked** `guardian` tree, while the `backend`
and worker services mounted `./guardian:/app/guardian` from the **host** and
served the checkout's source. The stock stack therefore applied a schema
derived from whatever revision the image happened to carry, against an
application built from a different revision. A successful migrator exit did
not establish that the database had reached the head the serving application
requires — and `backend/scripts/docker/run_backend.py` only *logs*
`OK: alembic_version=…` without comparing it to the source's expected head, so
the divergence was invisible.

Measured on this host, the pre-baked image `codexify-backend-runtime:latest`
(`sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55`,
created `2026-10-29T13:02:16Z`) carries **128** revisions with the single head
**`3a91d7c4e8b2`** — seven revisions behind the evaluated checkout's 135 /
`a7d4c9e2f1b3`.

## 4. What is already in the tree (audit of merged PR #991)

The correction this Task Spec asks for was **already implemented and merged**
before this task began, by **PR #991**
(`fix/stock-migrator-01-migration-source-consistency`, merge commit
`e571f94b3`, merged `2026-11-05T10:03:35Z`), whose branch head carried its own
dated receipt at
`docs/architecture/proofs/runtime/2026-11-04-stock-compose-migration-source-repair.md`.

This task therefore **did not re-implement the correction**. Re-implementing it
would have created a second, competing notion of a correction that is already
canonical on `main`. The landed mechanism was audited against the Task Spec's
requirements instead:

| Spec requirement | Landed mechanism (PR #991) | Audit result |
| --- | --- | --- |
| No silent fallback to stale baked migrations | `run_migrator.py` compares the effective (image-baked) migration source against the checkout's by SHA-256 over `versions/*.py` **and** `env.py`, and aborts before Alembic is invoked on any difference | **Satisfied** |
| No reliance on an image tag alone as revision proof | The proof is content-based (SHA-256 of the migration source), not tag-based | **Satisfied** |
| No introduction of a second migration authority | The checkout's tree is mounted read-only at `/source-migrations` for **comparison only**; it is never executed from. `/app/guardian` is not shadowed by a host bind on the migrator | **Satisfied** |
| No unsupported symlink substitution | The `backend/migrations` symlink is left as it is; the correction adds a side mount, not a symlink swap | **Satisfied** |
| Preserve the migration graph | No revision was added, removed or modified | **Satisfied** |
| Preserve migration ordering and startup dependencies | `backend` depends on `migrator` with `condition: service_completed_successfully`; unchanged | **Satisfied** |
| Avoid macOS Docker Desktop VirtioFS/provenance failures | The migration source Alembic executes from stays on the container filesystem; the host bind is read only through directory listing and file reads | **Satisfied** |
| Fail visibly when consistency cannot be established | The migrator exits non-zero, logs the offending revisions, and the dependent backend never starts | **Satisfied** |

What the merged receipt explicitly **did not** claim is what this task supplies.
It records the correction as *"a code/test-level repair with a real stale-image
refusal check, **not a passing stock Gate B**"*, and it records the `env.py`
extension of the coherence proof as **unit/contract-tested only**, never
re-executed at runtime (§6.6 of that receipt). Both gaps are closed here, at
the current tip.

## 5. Static validation

Run from the task worktree at `68c9e5236`:

| Check | Command | Result |
| --- | --- | --- |
| Compose configuration resolves | `docker compose -f docker-compose.yml config` | exit **0**; the effective migrator carries `CODEXIFY_SOURCE_MIGRATIONS_DIR: /source-migrations` and the read-only side mount with `create_host_path: false` |
| Documentation corpus | `python3 scripts/validate_docs.py` | `Docs validation passed.` (exit 0) |
| Whitespace hygiene | `git diff --check` | exit **0** |
| Stock Compose contract suite | `pytest tests/ops/test_stock_compose_migrator_contract.py tests/ops/test_source_compose_supported_profile_contract.py` | **25 passed** |
| Single-head / revision-uniqueness contract | `pytest tests/migration/test_alembic_revision_uniqueness.py` | **4 passed** |

## 6. The proof image, and why it was assembled rather than built

**This host cannot build `backend/Dockerfile` from source, and the reason is
recorded rather than worked around silently.**

- The repository's Dockerfile stages two runtime scripts with a heredoc
  (`RUN mkdir -p /app_staging/backend && python - <<'PY' … PY`). Heredocs in
  `RUN` are a **BuildKit-only** Dockerfile feature. Docker's legacy builder
  silently drops the heredoc body: the staged directory is created but empty,
  and the later `COPY --from=builder /app_staging/…` step fails with
  `stat app_staging/wait_for_db.py: file does not exist`. Reproduced twice on
  this host, including with `--no-cache` and with the heredoc verified by hand
  to work in the base image.
- BuildKit itself cannot run here: `buildx` records builder activity by
  **renaming** a temporary file, and this session's sandbox denies `rename(2)`
  outright (verified for plain and dot-prefixed files, in the home directory
  and in `/tmp`). Every `buildx build` therefore aborts with
  `failed to update builder last activity time: … operation not permitted`.

The matching image was therefore assembled from parts that are each
independently checkable:

| Component | Identity | Provenance |
| --- | --- | --- |
| Base | `codexify-qualification/stock-gate-b:e50f5756e-amngz1pe` = `sha256:6ddfa13b31f77e4b05bbd0892092ca343e567d3e7978ca85aac665a59288e98b`, created `2026-11-04T17:02:14Z` | The **same repository `backend/Dockerfile`**, built with BuildKit from source revision `97778bedf` |
| Overlay | `COPY guardian /app/guardian` and `COPY backend /app/backend` from the evaluated checkout | The evaluated revision's trees, verbatim |

The equivalence argument is checkable rather than asserted:

- `backend/Dockerfile` and `backend/requirements.txt` are **byte-identical**
  between `97778bedf` and the evaluated revision
  (`git diff --stat 97778bedf 68c9e5236 -- backend/requirements.txt
  backend/Dockerfile` is empty), so the base's dependency, apt and
  generated-script layers are the layers this revision's Dockerfile produces.
- The **only** image-relevant trees that differ between the two revisions are
  `guardian/` and `backend/` — both overlaid verbatim
  (`git diff --stat 97778bedf 68c9e5236 -- guardian backend scripts plugins
  codex_runner` lists six changed files, all inside `guardian/` or
  `backend/`; `scripts/`, `plugins/` and `codex_runner/` are unchanged).

Verification performed **inside the assembled image**, before any startup was
judged:

| Check | Result |
| --- | --- |
| SHA-256 manifest of the image's `/app/guardian/db/migrations` versus the checkout's | **identical** — 140 files, `diff` empty |
| SHA-256 manifest of the revision files (`versions/*.py`) and `env.py` versus the checkout's | **identical** — 136 files, `diff` empty |
| SHA-256 of the image's `/app/backend/scripts/docker/run_migrator.py` versus the checkout's | **identical** — `da6e78f52d09601c8c0e2ff889fe0c8bb8c2c302eaa5c72923d8a485e21f55cb` |
| Generated runtime scripts present in the image | `/app/entrypoint.py`, `/app/wait_for_db.py` present and executable |
| Resulting image | `codexify-backend-runtime:stock-gate-b-20261105` = `sha256:f62354f7fc7e579e9c6337224ace8602cdc55ddcd30c2fb34f20ffa0fac26e6d`, created `2026-11-05T20:01:36Z`, 4,817,652,401 bytes |

**Known limits of this provenance.** The base's apt layer was installed on
2026-11-04 and the base `python:3.11.14-slim` digest is whatever that build
resolved; a from-scratch build on another date could differ in package
versions. Neither bears on the invariant under test, which is decided purely by
the SHA-256 content comparison between the baked migration source and the
checkout's. The proof does **not** claim this image is byte-identical to a
from-scratch build of the repository Dockerfile on this date; it claims the
migration source and the migrator script in it are byte-identical to the
evaluated checkout, which is what the invariant is about, and that is verified
above rather than assumed.

## 7. Gate B runtime proof

### 7.1 Method

Each case was a separate disposable Compose project, created with
`-p <project>` so that its volumes, network and container names were scoped to
it and could not collide with the live Private Preview project. Loopback
ports were chosen per case (`15933/18999/17474/17687` and successors) and
verified free beforehand.

### 7.2 Case A — matching image built for the evaluated revision (PASS)

Project `cxfstockgateb`; image
`codexify-backend-runtime:stock-gate-b-20261105`;
`docker compose -p cxfstockgateb -f docker-compose.yml up -d db migrator
backend` → **exit 0**.

| Verification point | Observed |
| --- | --- |
| Migrator exit status | **0** |
| Effective migrator source path | `/app/guardian/db/migrations` (image-baked), from `alembic.ini script_location=%(here)s/../guardian/db/migrations` |
| Effective backend source path | `/app/backend` and `/app/guardian`, both bind-mounted from this checkout |
| Expected Alembic head | `a7d4c9e2f1b3` (135 revision files, single head) |
| Actual Alembic head | `['a7d4c9e2f1b3']` |
| Coherence proof | `Migration source is coherent (135 revisions)` |
| Alembic invocation | `python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads` |
| Migrator's own readback | `Verified alembic_version == a7d4c9e2f1b3` |
| **Direct PostgreSQL readback** | `to_regclass('public.alembic_version')` → `alembic_version`; `select version_num` → `a7d4c9e2f1b3`; `select count(*)` → **1** |
| Public tables after migration | 140 |
| Backend startup outcome | `cxfstockgateb-backend-1` → **running, health=healthy**; `GET /ping` → **HTTP 200** `{"status":"Guardian awake!"}` |
| Backend's own schema observation | `[Backend] OK: alembic_version=a7d4c9e2f1b3` |
| Startup ordering | The backend started only after the migrator container exited 0 (`service_completed_successfully`) |

### 7.3 Case B — stale pre-baked image (PASS: refusal)

Project `cxfstockgatebstale`; image `codexify-backend-runtime:latest`
(`sha256:22d9f5f1…`, created `2026-10-29T13:02:16Z`, the pre-baked tag, read
but never rebuilt); `docker compose up` → **exit 1**.

| Verification point | Observed |
| --- | --- |
| Migrator exit status | **1** |
| Baked head in that image | `['3a91d7c4e8b2']` — 128 revisions, seven behind the checkout |
| Diagnosis | `the migration source does not describe this checkout (effective_revisions=128, source_revisions=135, missing_from_source=[], extra_in_source=['a3115f64dda8_…', 'a7d4c9e2f1b3_…', 'b7e2c4a1d903_…', 'c8e42a91d307_…', 'd86f2a4b1c90_…', 'd91e4fa6702b_…', 'e42c7d0b9135_…'], content_mismatches=[], environment_mismatches=[], errors=[]); rebuild the backend image from this checkout before starting the stack` |
| Alembic invoked? | **No** — the comparison aborted before `alembic upgrade` |
| **Direct PostgreSQL readback** | `to_regclass('public.alembic_version')` → **ABSENT**; `select version_num` → *relation does not exist* — **nothing was migrated** |
| Backend startup outcome | **Never.** The container was created and left in state `Created`; `GET /ping` → connection refused (HTTP `000`) |
| Ordering held | `service_completed_successfully` prevented the application from starting after the migrator's non-zero exit |

The seven revisions the refusal names are exactly the seven the pre-baked
image lacks.

### 7.4 Case C1 — same head, different revision content (PASS: refusal)

Project `cxfstockgatebc1`; image
`codexify-qualification/stock-gate-b:e50f5756e-amngz1pe`
(`sha256:6ddfa13b31f7…`, the 2026-11-04 BuildKit build of the same Dockerfile
from `97778bedf`, read but never rebuilt); `docker compose up` → **exit 1**.

| Verification point | Observed |
| --- | --- |
| Migrator exit status | **1** |
| Baked head | `['a7d4c9e2f1b3']` — **the same head**, 135 revisions |
| Diagnosis | `the migration source does not describe this checkout (effective_revisions=135, source_revisions=135, missing_from_source=[], extra_in_source=[], content_mismatches=['a7d4c9e2f1b3_add_music_projects_table.py'], environment_mismatches=[], errors=[])` |
| Alembic invoked? | **No** |
| **Direct PostgreSQL readback** | `alembic_version` → **ABSENT**; nothing migrated |
| Backend startup outcome | **Never** — container left in state `Created`; `/ping` → `000` |

This is the stronger of the two mismatch shapes: the revision count and the
head are **identical**, so a head-count or head-identity check would have
accepted this image. Only the content comparison caught it. The named file is
the one revision whose content changed between `97778bedf` and the evaluated
revision.

### 7.5 Case C2 — same head, different migration environment (PASS: refusal)

Project `cxfstockgatebc2`; image
`codexify-backend-runtime:stock-gate-b-20261105` (the matching image), with the
checkout's `guardian/db/migrations/env.py` deliberately altered — one appended
comment line, SHA-256
`6ed44c28fd7e875ff93c597e20dc5d11d38b69b1e712e3033d6aa2a6fee32bb9` — so that
the read-only comparison source differs from the baked migration environment
while the head stays `a7d4c9e2f1b3` and the revision count stays 135.
`docker compose up` → **exit 1**.

| Verification point | Observed |
| --- | --- |
| Migrator exit status | **1** |
| Baked head | `['a7d4c9e2f1b3']` — unchanged |
| Diagnosis | `the migration environment does not describe this checkout (env.py differs between the effective migration source and the checkout); rebuild the backend image from this checkout before starting the stack` |
| Alembic invoked? | **No** |
| **Direct PostgreSQL readback** | `alembic_version` → **ABSENT**; nothing migrated |
| Backend startup outcome | **Never** — container left in state `Created`; `/ping` → `000` |
| Checkout restored afterwards | `guardian/db/migrations/env.py` SHA-256 back to `87febb98cbeb83e27b84efeca715e98349f302f73cef669ed2bd3fa0306884fc`, matching `HEAD`; `git status` clean apart from this receipt |

This case exists because the merged receipt recorded the `env.py` extension of
the coherence proof as **unit/contract-tested only** and never re-executed at
runtime (§6.6 there). It has now been executed at runtime, at the current tip.

### 7.6 What this establishes, and what it does not

**Establishes.** On the stock Compose path, with the ordinary invocation and
the ordinary Compose file:

1. the migrator reaches the evaluated checkout's single Alembic head
   `a7d4c9e2f1b3` and applies it;
2. the database holds exactly one `alembic_version` record equal to that head,
   confirmed by a readback taken directly from PostgreSQL rather than from the
   container's exit code;
3. the backend starts against that schema and reports healthy, serving
   `/ping` with HTTP 200;
4. a stale image, a same-head image with different revision content, and a
   same-head source with a different migration environment each fail closed
   **before any migration is applied** and **before the application starts**;
   the refusal names the specific divergence.

**Does not establish.** Any qualification of the stock startup. Gate A–H
coverage, provider-ledger evidence, browser behaviour, retrieval provenance
and restart recovery were **not** executed here. The stock startup's own
qualification identity (`supported-compose-stock`) still does not exist, and
this receipt does not create it.

## 8. Boundaries preserved

- **The source-matched launcher** (`scripts/whooshd_docker_smoke_up.sh`) was
  not modified, not invoked, and its behaviour is unchanged.
- **`docker-compose.runtime.yml`** was not modified and was not run; it
  remains a separate image-based distribution surface with its own migrator
  that declares no volumes.
- **No unrelated service, provider, queue, identity authority or runtime
  credential was altered.** The only environment file written was a synthetic
  local-only `.env` inside the task worktree.
- **No schema revision was added, removed or modified.** The `env.py`
  alteration in Case C2 was a transient mutation of the checkout's comparison
  source, reverted in the same run and verified by SHA-256.
- **The qualification registry and rubrics were not touched**, and no
  registry status was written.
- **The Private Preview was not operated on.** It was inspected read-only:
  its 13 containers remained up for the whole run with unchanged image
  digests, and `codexify-backend-runtime:latest` still resolves to
  `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55`.
  Its database was never connected to.
- **No shared container was stopped, no shared volume was removed, no Docker
  Desktop restart, prune or disk compaction was performed.** Only the four
  disposable proof projects and the proof image — all created by this task —
  were removed.
- **No release gate was moved.**

## 9. Residue after the run

| Item | State |
| --- | --- |
| Compose projects `cxfstockgateb`, `cxfstockgatebstale`, `cxfstockgatebc1`, `cxfstockgatebc2` | removed with `down -v --remove-orphans` |
| Proof containers, volumes and networks | none remain |
| Proof image `codexify-backend-runtime:stock-gate-b-20261105` | removed (`sha256:f62354f7fc7e…`); the base image it was built on was retained |
| `codexify-backend-runtime:latest` | unchanged, never rebuilt |
| `codexify-qualification/stock-gate-b:e50f5756e-amngz1pe` | unchanged, never rebuilt |
| Host filesystem | `/Volumes/Dev_SSD` 931 GiB total, 61 GiB available after the run |

## 10. Custody and collisions

- **Another executor is implementing the same correction on a separate
  branch.** The local-only, unpushed branch
  `codex/stock-compose-migration-source` (head observed at `edea2690d`; the
  branch has since advanced, in
  `/Users/chriscastillo/.codex/worktrees/3164/Codexify-main`) carries a
  different mechanism for the same invariant — an inline Python program in
  `docker-compose.yml` that asserts the execution path, compares SHA-256 over
  the migration trees, requires one head, runs the migrator and reads
  `alembic_version` back — plus a `supported-compose-stock` rubric, a
  qualification registry entry and a qualification run receipt. It is **not**
  based on `origin/main`, it is **not** pushed, and it is **not** a
  superset of what merged PR #991 already landed. It was **not** touched,
  merged, cherry-picked or pushed by this task. Its registry, rubric and
  qualification receipts are outside this Task Spec's scope, and this receipt
  deliberately creates none of them.
- **This task's own worktree lost its Git registration twice** to another
  executor's worktree reclamation on this shared host — the first to an
  operator-approved 163-path reclamation that also removed `/private/tmp/cxf-fix-fence`
  from the previous task, and the second, mid-task, to a further removal of
  this task's administrative directory. Both times the branch ref and the
  working files survived and the worktree was re-registered; the branch
  `fix/stock-compose-migration-source-gate-b-20261105` points at
  `68c9e5236` and now carries the receipt below.
- **The environment blocks `rename(2)` and `unlink(2)` on `/Volumes/Dev_SSD`.**
  This is why BuildKit could not run (§6), why `git worktree add` could not
  complete three tracked files under `.claude/commands/` (the worktree was
  registered by hand and those three paths marked skip-worktree), and why
  `git checkout --` could not restore the mutated `env.py` in Case C2 (it was
  restored by writing `HEAD`'s content back and verifying the SHA-256).

## 11. Deferred qualification work

Not done, and not claimed:

- The `supported-compose-stock` rubric, run and receipt — a separate task
  with its own identity, as the Task Spec's non-goals require.
- Gate A–H coverage of the stock startup beyond the migration gates.
- The current-tip supported-Compose qualification for the source-matched
  launcher.
- Any release-gate promotion.

## 12. Remaining release blockers

Unchanged by this task, and recorded here so this receipt is not read as
moving any of them:

- The stock Compose startup is now **self-consistent and proven at
  `68c9e5236`**, but it is still **not qualified**: it has no rubric, no run
  receipt and no registry entry.
- The live Preview database remains behind the head, and the Preview lane has
  not been advanced by this task.
- The current-tip supported-Compose qualification is still missing.
- **Release remains HOLD.**

## Appendix — reproduction

```bash
# evaluated revision
cd <checkout>
git rev-parse HEAD                     # 68c9e52361c5b6169dd18d5d44b39495f7a15f49

# single-head expectation
python3 -c "import ast,pathlib; …"    # 135 revision files, one head: a7d4c9e2f1b3

# stock startup, disposable project and database
docker compose -p <project> -f docker-compose.yml up -d db migrator backend
docker compose -p <project> -f docker-compose.yml logs migrator
docker exec <project>-db-1 psql -U codexify -d Codexify -Atc \
  "select version_num, count(*) over () from alembic_version;"
```

The per-case container logs, the exact Compose invocations, the direct
PostgreSQL readbacks, the in-image SHA-256 manifests and the teardown record
were captured to `/tmp/cxf-gate-b/case{A-matching,B-stale,C1-content-mismatch,C2-env-mismatch}.log`
during the run. That directory is a scratch location on the host and is not
part of the repository; the decisive observations from it are transcribed in
§7 above.
