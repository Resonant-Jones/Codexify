# Qualification capacity preflight — `69ef035a4`

> **Release posture: HOLD.** This receipt records host-capacity measurement and
> readiness evidence for a *future* qualification. It does not authorize a
> qualification run, does not qualify any surface, and does not change any
> release-support classification.

## Result

**Capacity readiness: PASS, conditional on an immediate pre-build capacity
re-check.** The development volume holds **30 GiB free** at the measured state,
which covers the estimated peak additional requirement of the QUAL-COMPOSE-02
build and disposable runtime plus a documented safety reserve.

**No cleanup operation was performed by this task.** The only reclamation this
task was authorized to perform — age-bounded BuildKit cache pruning — had
**nothing to reclaim**: the BuildKit cache reported `0 B` across `0` records at
the pre-operation measurement. The reclaimable pools that remain (images
8.114 GB, volumes 4.892 GB, containers 1.791 GB) are outside this task's
authorization and were left untouched.

| Question | Disposition |
| --- | --- |
| Free space on `/Volumes/Dev_SSD` at pre-operation measurement | **30 GiB free**, 97% capacity (931 Gi total, 900 Gi used) |
| `Docker.raw` backing location and size | `/Volumes/Dev_SSD/offload/docker/Docker.raw` (symlinked from Docker Desktop); 128 GiB logical, **55 GiB allocated** |
| BuildKit cache at pre-operation measurement | **0 B, 0 records** — nothing to reclaim |
| Builder identity | One usable named builder, `desktop-linux` (driver `docker`, BuildKit v0.34.0) |
| Active use of that builder | **Confirmed in use by another actor**; ownership of its cache not attributable |
| Bytes recovered by this task | **0** |
| Bytes recovered by another actor, baseline → pre-operation | **+22.6 GiB** host free space; **not** from Docker cache reclamation (see [§4](#4-verified-recovered-capacity)) |
| Private Preview | **Unchanged** — 18 containers, 8 labelled volumes, 1 network, backend image `sha256:22d9f5f1…e6e5c55` |
| Qualification readiness | **PASS**, conditional — see [§5](#5-qualification-readiness) |
| Full qualification claimed | **No** |

## Scope and boundary

- **Frozen future qualification SHA:** `69ef035a4320724b9a53279d2fabd6bac0c6e98f`
  (`fix(knowledge-graph): rebind the adr-index node to the revision main holds (#987)`).
- **Branch:** `docs/qual-capacity-01-preflight`, created from `origin/main` at the
  frozen SHA. It is the only branch touched by this task.
- **Authorized file:** this receipt only. No application code, Compose
  configuration, migration, existing architecture document, or CI definition was
  modified.
- **Task kind:** bounded operator maintenance. The primary evidence is
  read-only Docker inventory and actual filesystem capacity measurement.
- **Release posture:** HOLD throughout. This receipt changes no release-support
  classification and lifts no gate.

This task does **not** start QUAL-COMPOSE-02. It establishes only whether the
host can carry that qualification.

## Required pre-read

Read at the frozen SHA:

1. [`docs/architecture/00-current-state.md`](../../00-current-state.md) — release truth and active blockers.
2. [`docs/architecture/adr/adr-index.md`](../../adr/adr-index.md) — ADR entrypoint and reading order.
3. [`docs/architecture/README.md`](../../README.md) — KB navigation and Beta boundary entry order.
4. [`docs/architecture/adr/069-codexify-beta-runtime-support-boundary.md`](../../adr/069-codexify-beta-runtime-support-boundary.md) — Beta doctrine and release classes.
5. [`docs/qualification/rubrics/supported-compose.md`](../../../qualification/rubrics/supported-compose.md) — the rubric QUAL-COMPOSE-02 will execute.
6. Docker BuildKit `buildx prune` reference documentation and Docker Desktop
   resource-management guidance, for the prune-filter and free-space semantics
   used below.

Two facts from the pre-read govern the estimate in [§5](#5-qualification-readiness):
the supported profile `v1-local-core-web-mcp` requires `frontend`, `backend`,
`db`, `redis`, `worker-chat`, `worker-document-embed`, and `migrator` — with
`neo4j` and `graph-init` **optional** — and ADR-069's authority hierarchy keeps
release interpretation in `00-current-state.md`, which this task does not touch.

## 1. Read-only inventory

All measurements taken on the host with `DOCKER_CONTEXT=desktop-linux`.

### Host filesystem

```
$ df -h /Volumes/Dev_SSD
/dev/disk7s1   931Gi   900Gi    30Gi    97%     15M   313M    5%   /Volumes/Dev_SSD
```

Three consecutive samples returned identical values.

### `Docker.raw` backing file

```
$ ls -l ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
... Docker.raw -> /Volumes/Dev_SSD/offload/docker/Docker.raw

$ stat -f "logical=%z bytes" /Volumes/Dev_SSD/offload/docker/Docker.raw
logical=137438953472 bytes            # 128 GiB logical

$ du -h /Volumes/Dev_SSD/offload/docker/Docker.raw
55G                                     # actual allocation on the volume
```

Docker Desktop's data therefore lives on the development volume, not on the
system volume.

### Docker resource usage

```
$ docker system df
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          25        9         28.73GB   8.114GB (28%)
Containers      34        27        4.838GB   1.791GB (37%)
Local Volumes   111       29        14.6GB    4.892GB (33%)
Build Cache     0         0         0B        0B
```

Reclaimable-versus-non-reclaimable BuildKit cache, from both the builder-level
and the daemon-level view:

```
$ docker buildx du
ID        RECLAIMABLE   SIZE      LAST ACCESSED
Reclaimable:	0B
Total:		0B

$ docker builder du
Reclaimable:	0B
Total:		0B
```

**The BuildKit cache was already empty.** The task baseline recorded
`29.46 GB` total with `115` records and `12.54 GB` private reclaimable; at the
pre-operation measurement the same builder reports `0 B` across `0` records.
This change happened between two measurements in the same working session and
**no mutating command was issued by this agent** — see
[§2](#2-ownership-and-activity-gate).

### BuildKit builder identities

```
$ docker buildx ls
NAME/NODE           DRIVER/ENDPOINT     STATUS    BUILDKIT   PLATFORMS
desktop-linux*      docker
 \_ desktop-linux    \_ desktop-linux   running   v0.34.0    linux/amd64 (+2), linux/arm64, linux/ppc64le, linux/s390x, (2 more)
default                                 error

Cannot load builder default: failed to connect to the docker API at unix:///var/run/docker.sock
```

Exactly one usable named builder exists: `desktop-linux`, driver `docker`,
BuildKit `v0.34.0`, running. The `default` builder is the implicit legacy
builder and is in `error` state because it targets a Unix socket that does not
exist on this host; it holds no cache. Enumerating with the workspace-local
`BUILDX_CONFIG` yields the identical single-builder result, so builder identity
is not affected by `BUILDX_CONFIG`.

No build or BuildKit containers were running:

```
$ docker ps --format '{{.Names}}\t{{.Image}}' | grep -Ei 'build|buildkit'
(no output)
```

### Private Preview inventory

| Resource class | Count | Identity |
| --- | --- | --- |
| Containers (project-labelled) | 18 | all `codexify_private_preview-*` |
| Volumes (project-labelled) | 8 | `codexify_private_preview_pg_data`, `_neo4j_data`, `_hf_cache`, `_frontend_pnpm_store`, `_e2e_pnpm_store`, `_e2e_frontend_src_node_modules`, `_corepack_cache`, `_codexify_cli_home` |
| Networks (project-labelled) | 1 | `codexify_private_preview_default` |
| Backend image | — | `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55` |
| Postgres volume | — | `codexify_private_preview_pg_data` |

Observed sizes of the Preview's named volumes, used as the footprint reference
in [§5](#5-qualification-readiness):

| Volume | Size |
| --- | --- |
| `codexify_private_preview_hf_cache` | 4.019 GB |
| `codexify_private_preview_chroma` | 1.933 GB (4 links) |
| `codexify_private_preview_pg_data` | 885.4 MB |
| `codexify_private_preview_e2e_pnpm_store` | 570.3 MB |
| `codexify_private_preview_neo4j_data` | 541.4 MB |
| `codexify_private_preview_corepack_cache` | 18.22 MB |
| `codexify_private_preview_frontend_pnpm_store` | 0 B |
| `codexify_private_preview_e2e_frontend_src_node_modules` | 16.26 kB |
| `codexify_private_preview_codexify_cli_home` | 36 B |

## 2. Ownership and activity gate

**Finding: another actor is actively using the shared `desktop-linux` builder.
Its cache ownership cannot be established, so active use cannot be excluded.**

Evidence:

1. **A concurrent executor is running Docker workloads on this host.**
   `codexify-audit-origin-pg-20261103` was created at `2026-11-03 14:53:43
   -0500` and was up 23 minutes at inventory time. Six
   `codexify_account_observability_norm_*` Postgres containers created between
   `11:14:51` and `11:15:03` were up 4 hours. `codexify-guardian-dispatch-pg`
   was up 9 hours.

2. **The BuildKit cache was reclaimed by someone other than this agent.**
   `docker system df` reported `29.46 GB` across `115` cache records earlier in
   the same working session; the pre-operation measurement reports `0 B` across
   `0` records. Every command this agent ran against Docker in that interval
   was read-only (`docker system df`, `docker builder du`, `docker buildx ls`,
   `docker buildx du`, `docker ps`, `docker images`, `docker volumes`).

3. **Resource counts moved during this task's own inventory**, consistent with
   a live multi-actor environment: containers `32 → 34`, local volumes
   `109 → 111`.

The `desktop-linux` builder is Docker Desktop's integrated builder and is shared
by every actor on this host that runs `docker build`. There is no per-actor
builder namespace, so a cache record's owner cannot be determined from the
builder's state. Under the task's ownership gate, this means the reclaimable
cache of this builder could not be shown to be unused.

**No executor was paused, interrupted, or terminated.**

## 3. Bounded reclamation

### Operations performed

**None.** No Docker mutating command was issued by this task.

### Operations withheld, with reasons

| Operation | Status | Reason |
| --- | --- | --- |
| `docker buildx prune --filter "until=24h"` (age-bounded, no `--all`) | **Withheld** | The target is empty — `docker buildx du` reports `Total 0 B`, `0` records. There is nothing to reclaim. Independently, the ownership gate in [§2](#2-ownership-and-activity-gate) could not exclude another actor's active use of this builder, so mutating it would not have been safe. |
| `docker builder prune --all` | **Prohibited** | Explicitly prohibited by the task. |
| `docker system prune` | **Prohibited** | Explicitly prohibited by the task. |
| `docker image prune` (8.114 GB reclaimable; 3 dangling images) | **Withheld — out of scope** | Images are outside this task's authorization. Deleting them would also destroy the `codexify-backend-runtime` and `codexify-worker-coding-runtime` tags the Private Preview serves from. |
| `docker volume prune` (4.892 GB reclaimable) | **Withheld — out of scope** | Volumes are outside this task's authorization, and runtime persistence is never disposable. The reclaimable volume pool includes anonymous `node_modules` volumes that belong to other actors' containers. |
| `docker container prune` (1.791 GB reclaimable) | **Withheld — out of scope** | Containers are outside this task's authorization; the pool includes other executors' live containers. |
| Truncating or resetting `Docker.raw` | **Prohibited and unnecessary** | Explicitly prohibited. Also physically unnecessary: the file's allocation is unchanged at 55 GiB, and the capacity that returned to the host did not come from it ([§4](#4-verified-recovered-capacity)). |

The age-bounded filter syntax used here (`--filter "until=24h"`, with multiple
`--filter` flags ANDed) and the `--builder` selector are the documented
mechanism for targeted, age-limited cache pruning as opposed to broad garbage
collection.

## 4. Verified recovered capacity

**Bytes recovered by this task: 0.**

The capacity that returned to the volume between the task baseline and this
task's pre-operation measurement was **not** recovered by this task, and — per
the task's instruction not to equate Docker's reported reclaimed cache with
actual host filesystem capacity — it was **not** recovered by Docker either.

| Measure | Baseline (earlier this session) | Pre-operation | Post-operation | Delta |
| --- | --- | --- | --- | --- |
| Host free space on `/Volumes/Dev_SSD` | 7.4 GiB (100% capacity) | **30 GiB** (97%) | 30 GiB (97%) | +22.6 GiB — **by another actor, not by this task** |
| `Docker.raw` allocation | 55 GiB | 55 GiB | 55 GiB | **unchanged** |
| Docker-reported build cache | 29.46 GB / 115 records | 0 B / 0 records | 0 B / 0 records | −29.46 GB — **reclaimed by another actor** |
| Build cache reclaimable *now* | 12.54 GB private | 0 B | 0 B | — |
| Images / volumes / containers reclaimable | — | 8.114 / 4.892 / 1.791 GB | unchanged | **untouched by this task** |

The decisive observation is that `Docker.raw`'s allocation on the volume stayed
at **55 GiB** across the entire interval while the host gained **22.6 GiB** of
free space. If the 29.46 GB of build cache had been released as physical
host space out of `Docker.raw`, the file's allocation would have fallen. It did
not. The recovered host capacity therefore came from non-Docker deletion
elsewhere on the volume by another actor.

**Remaining reclaimable cache: 0 B.** The reclaimable pools that remain
(images 8.114 GB, volumes 4.892 GB, containers 1.791 GB) were not touched and
are recorded here only as measured state.

### Concurrent-resource verification

Every resource this task could have disturbed was re-verified after the
measurement window and is unchanged:

| Resource | Identity |
| --- | --- |
| Private Preview containers | 18 (project-labelled) |
| Private Preview volumes | 8 (project-labelled) |
| Private Preview networks | 1 (`codexify_private_preview_default`) |
| Private Preview backend image | `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55` |
| Private Preview Postgres volume | `codexify_private_preview_pg_data` |
| Other actors' live containers | `codexify-audit-origin-pg-20261103`, 6× `codexify_account_observability_norm_*`, `codexify-guardian-dispatch-pg`, 2× `cfy-bootstrap-proof-*`, 2× `codexify_chat_*` — all left running |

No container, image, volume, network, builder, or build record belonging to
another actor or to the Private Preview was deleted, stopped, pruned, or
otherwise modified by this task.

## 5. Qualification readiness

### Estimated peak additional disk requirement for QUAL-COMPOSE-02

Components are grounded in measurements from this host rather than assumed.

**Build (persistent):**

| Component | Estimate | Basis |
| --- | --- | --- |
| Backend runtime image | **4.64 GB** | Observed size of `codexify-backend-runtime:latest`, built from `backend/Dockerfile` target `runtime` |
| BuildKit cache for one backend build | **≤ 6 GB** | Bounded from this host's observed accumulation of 29.46 GB across 115 cache records (≈ 256 MB/record); one backend build is on the order of 15–25 records → 4–6 GB |
| Frontend image | **0** | `frontend` runs the stock `node:20-alpine` (194 MB, already present) with a `.:/app` bind mount. **No frontend image is built.** |

**Disposable runtime (persistent for the run):**

| Component | Estimate | Basis |
| --- | --- | --- |
| `pg_data` | 885 MB | Observed `codexify_private_preview_pg_data` |
| `hf_cache` | 0 – 4.02 GB | Conditional. The Preview's 4.019 GB came from `model-prep`/optional `worker-warmup`. The embedding model `bge-large-en-v1.5` is bind-mounted from the host `./models/…` (present on disk, untracked by git), so a supported-profile run need not populate the cache. |
| `frontend_pnpm_store` + `corepack_cache` | ≤ 590 MB | Observed 0 B + 18.22 MB for the Preview; `e2e_pnpm_store` observed at 570.3 MB |
| Anonymous `node_modules` volumes | ~120 MB | 2 × ~60 MB, recreated per frontend container |
| `neo4j_data` | **0** | `neo4j` and `graph-init` are **optional** services in `v1-local-core-web-mcp`, not required by the profile |

**Totals:**

| Scenario | Peak additional requirement |
| --- | --- |
| Upper bound (`hf_cache` fully populated) | ≈ **16.3 GB** |
| Likely (`hf_cache` near-empty) | ≈ **10.3 GB** |

**Safety reserve: 10 GB.** Justified by direct observation: a concurrent actor
moved **22.6 GiB** of host capacity on this volume within the same working
session, and Docker Desktop requires headroom for its own compaction.

### Verdict

| Quantity | Value |
| --- | --- |
| Estimated peak additional requirement (upper bound) | 16.3 GB |
| Documented safety reserve | 10 GB |
| **Required** | **26.3 GB** |
| **Available (measured)** | **30 GiB ≈ 32.2 GB** |
| Margin (upper bound) | **+5.9 GB** |
| Margin (likely case) | +11.9 GB |

**Capacity readiness: PASS — conditional.**

Sufficient physical free space is established for the estimated requirement
plus the documented reserve. The condition is explicit and must be honoured by
QUAL-COMPOSE-02:

> **Immediately before the build, re-measure `df -h /Volumes/Dev_SSD`. If free
> space is below 26.3 GB, the qualification must not start.**

This precondition is not a formality. The volume's free space was observed at
**7.4 GiB earlier in the same session** and at **30 GiB** later, with the
difference caused by another actor's deletions rather than by any operation of
this task. The host's capacity is demonstrably volatile under a concurrent
executor, so the 30 GiB figure is a measurement of the current state, not a
floor that will hold.

## Validation

```
$ python scripts/validate_docs.py
Docs validation passed: required architecture docs, README links, and source headings verified.

$ git diff --check
(no output)
```

No application tests apply. This is operator maintenance; the primary proof is
the read-only Docker inventory and the actual filesystem capacity measurements
recorded above.

## ADR impact

**None.**

No ADR is added, amended, or superseded. ADR-069's supported-runtime and
release-authority boundaries are preserved: the Beta release classes are
unchanged, `docs/architecture/00-current-state.md` remains release authority,
and no support posture is widened. This receipt is evidence under
`docs/architecture/proofs/` and, per ADR-069's Evidence vs Support Doctrine,
evidence does not redefine support posture.

## What this receipt does not claim

- It does **not** qualify the supported Compose runtime, at any revision.
- It does **not** authorize starting QUAL-COMPOSE-02.
- It does **not** lift the release gate, which remains **HOLD**.
- It does **not** assert that the supported path's Gate B migrator defect is
  fixed. The migrator remediation landed in PR #982 (`00c3a4163`), but the
  stock-path Gate B re-run is a separate proof against the frozen SHA.
- It does **not** claim the registry has absorbed any receipt; `supported-compose`
  remains `HOLD` with a `tested_commit_not_in_tip_lineage` blocker.
- It does **not** record any cleanup as having been performed by this task.

## Remaining blocker

**None for capacity.** The measured volume carries sufficient free space for
the estimated QUAL-COMPOSE-02 requirement plus reserve, subject to the
mandatory pre-build re-check in [§5](#5-qualification-readiness).

The blockers that remain open for QUAL-COMPOSE-02 are not capacity blockers
and are not addressed here: the stock-path Gate B migrator defect requires a
re-run against the frozen SHA `69ef035a4`, and the qualification registry has
not yet absorbed a run receipt for the `supported-compose` surface.
