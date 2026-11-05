# Docker qualification capacity readiness — 2026-11-05

> **Release posture: HOLD.** This receipt records a live host-capacity
> measurement and a qualification-readiness verdict. It does **not** execute the
> `supported-compose-stock` qualification, does **not** qualify any surface,
> does **not** promote any release status, and — because no reclamation was
> required — performs **no** disk reclamation and **no** change to Docker's
> persistent state.

## Result

**Qualification capacity verdict: GO.** The host volume and the Docker VM both
carry the capacity the stock Compose qualification needs, with margin, and
Private Preview is healthy and unmodified.

**No reclamation was executed.** The capacity threshold is already satisfied,
so the operator-approval gate in the task specification was never exercised and
no Docker object was deleted, pruned, compacted, or reset. The one mutation
this task performed was retiring **its own** merged worktree (see
[§7](#7-what-this-task-changed)).

| Question | Disposition |
| --- | --- |
| Host volume free capacity | **68 GiB** free of 931 GiB on `/Volumes/Dev_SSD` (93% capacity) — threshold is ≥ 30 GiB |
| Docker VM free capacity | **39.2 GiB** available inside the guest (125.7 GiB disk, 80.1 GiB used) |
| `Docker.raw` allocation | **80.3 GiB allocated** of a **128 GiB logical maximum**, at `/Volumes/Dev_SSD/offload/docker/Docker.raw` |
| Docker guest filesystem | **Read-write** (verified by write probe) |
| Reclamation required | **No** — capacity is already above the threshold |
| Reclamation executed | **None** |
| Private Preview | **Healthy and unmodified** — 19 containers, 9 named volumes, PostgreSQL revision `3a91d7c4e8b2`, image digests unchanged |
| Docker Desktop / engine | Docker Desktop 4.98.0, engine client/server 29.9.2, context `desktop-linux` |
| Qualification executed | **No** — out of scope for this task |
| Release gate | **HOLD** (unchanged) |

## 1. Scope and boundary

- **Starting repository SHA:** `68c9e52361c5b6169dd18d5d44b39495f7a15f49`
  (`origin/main` at task start). PR #991 (stock Compose migration-source
  repair) and PR #1000 (frontend test stabilization) are merged into it.
- **Branch:** `docs/docker-capacity-readiness-20261105`, created from
  `origin/main` in an isolated worktree. The only file staged by this task is
  this receipt.
- **Not touched:** application code, Compose files, migrations, qualification
  rubrics or registry, release-authority documents, Docker configuration, the
  Private Preview deployment, and every other agent's worktree.

## 2. Storage inventory (measured, read-only)

### 2.1 Host filesystem

```
$ df -h /Volumes/Dev_SSD
Filesystem     Size  Used Avail Capacity  Mounted on
/dev/disk7s1   931Gi  862Gi   68Gi     93%  /Volumes/Dev_SSD
```

The macOS system volume (`/System/Volumes/Data`) carries a separate **26 GiB**
free and is the appropriate destination for any backup that must not live on
the Docker data volume.

The previous reported headroom for this volume was 13–15 GiB. It has been
**remeasured**, not assumed: the volume now carries **68 GiB free**. The
difference is not Docker reclamation — `Docker.raw`'s allocation did not
shrink — it is non-Docker deletion elsewhere on the volume (the repository's
`.worktrees/` population fell from 120 entries to 44 between measurements).

### 2.2 Docker Desktop and context

| Property | Value |
| --- | --- |
| Docker Desktop version | **4.98.0** (`/Applications/Docker.app`, `CFBundleShortVersionString`) |
| Engine client / server | **29.9.2 / 29.9.2** |
| Docker context | **`desktop-linux`** (endpoint `unix:///Users/chriscastillo/.docker/run/docker.sock`) |
| Engine root dir (inside the VM) | `/var/lib/docker`, storage driver `overlayfs` |
| VM memory | 8,320,229,376 bytes (7.75 GiB) |

### 2.3 `Docker.raw`: actual location, logical maximum, allocated size

The configured location was **resolved, not assumed**. Docker Desktop's default
path is a symlink onto the development volume:

```
$ ls -l ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
lrwxr-xr-x  ... Docker.raw -> /Volumes/Dev_SSD/offload/docker/Docker.raw

$ ls -l /Volumes/Dev_SSD/offload/docker/Docker.raw
-rw-r--r--@ 1 chriscastillo staff 137438953472 Nov  5 14:05 Docker.raw   # 128 GiB logical maximum

$ ls -klsh /Volumes/Dev_SSD/offload/docker/Docker.raw
84211912 -rw-r--r-- 1 chriscastillo staff 128G Nov  5 14:05 Docker.raw   # 84,211,912 KB allocated
```

| Measure | Value |
| --- | --- |
| Logical maximum (what the UI and `ls -l` show) | **128 GiB** (137,438,953,472 bytes) |
| **Physically allocated on the host** | **80.3 GiB** (84,211,912 KB — APFS sparse allocation) |
| Guest filesystem capacity | 125.7 GiB total, 80.1 GiB used, **39.2 GiB available** |

The logical maximum is **not** the binding constraint. The guest disk has
39.2 GiB free inside a 125.7 GiB volume, so the qualification's build and
runtime data fit inside the VM without needing the host allocation to grow.

### 2.4 Docker storage by category (`docker system df`)

| Category | Total | Active | Size | Reclaimable |
| --- | --- | --- | --- | --- |
| Images | 30 | 11 | 38.18 GB | **12.42 GB (32%)** |
| Containers | 83 | 45 | 5.349 GB | 2.082 GB (38%) |
| Local volumes | 186 | 77 | 21.13 GB | 8.623 GB (40%) |
| Build cache | 50 | 0 | 12.83 GB | 1.089 GB |

### 2.5 Reclaimable storage — identified candidates (none executed)

Everything in this table was measured and left untouched. Ownership is stated
because the reclaimable pools contain other lanes' objects.

| Candidate | Size | Containers | Ownership | Disposition |
| --- | --- | --- | --- | --- |
| `codexify-backend-runtime:src-69ef035a4320` | 4.65 GB (4.443 GB unique) | 0 | previous qualification's build | identified, **not** deleted |
| `codexify-probe:ctx` | 212 MB | 0 | probe image | identified, **not** deleted |
| dangling `c472d1052af8` | 558 MB | 0 | dangling | identified, **not** deleted |
| dangling `3a8bad717539` | 1.45 GB | 0 | dangling | identified, **not** deleted |
| dangling `29c58a6f5f2e` | 758 MB | 0 | dangling | identified, **not** deleted |
| dangling `13017d24b83e` | 2.47 GB | 0 | dangling | identified, **not** deleted |
| `codexify-qualification/stock-gate-b:e50f5756e-amngz1pe` | 4.79 GB | **7** | **in use by another actor** | **excluded — not mine, not removable** |
| `codexify-backend-runtime:latest` | 4.64 GB | **10** | **Private Preview** | **excluded — must not be touched** |
| Build cache records | 12.83 GB (1.089 GB reclaimable) | 0 | shared | identified, **not** pruned |
| Stopped containers / unused volumes | 2.082 GB / 8.623 GB reclaimable | — | mixed ownership, **not attributable** | **excluded — unidentified removal is forbidden** |

### 2.6 Active containers and project ownership

83 containers exist, 45 running. Project attribution of the running set
includes the Private Preview (13 long-running services), the
`codexify-qualification/stock-gate-b` stack owned by another actor (7
containers), and assorted agent-owned proof containers. No container belonging
to the Private Preview or to another actor was stopped, restarted, or removed by
this task.

## 3. Private Preview protection — before-state inventory

### 3.1 Identity and health

| Resource | Identity / state |
| --- | --- |
| Compose project | `codexify_private_preview` (all containers, volumes and the network are project-labelled) |
| Long-running services | 13 up: `backend`, `worker-chat`, `worker-warmup`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`, `worker-account-import`, `db`, `worker-coding`, `neo4j`, `redis`, `frontend`, `private-preview-origin` |
| Health | `db` **healthy**, `backend` **healthy**, `worker-coding` **healthy**, `neo4j` **healthy**, `redis` **healthy**; the remaining services have no healthcheck and are Up 24 hours |
| One-shot services | `migrator`, `graph-init`, `model-prep`, `e2e`, `auth-posture` — all **Exited (0)**; they were re-run by the Preview's own lane ~4 minutes before this measurement, so the previously reported "two exited one-shot services" condition has been superseded by that lane's own successful run. **This task did not run them.** |
| PostgreSQL Alembic revision | **`3a91d7c4e8b2`** — unchanged |
| Image digest (backend, worker-chat, worker-warmup, worker-chat-embed, worker-document-embed, worker-voice, worker-account-import, model-prep, migrator) | `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55` |
| Image digest (worker-coding) | `sha256:a3177274d0b5e90e4db762f6723b312ed57b6c1bf2f2aaa69995ce9ab735229b` |

### 3.2 Named volumes (identity and size)

| Volume | Links | Size |
| --- | --- | --- |
| `codexify_private_preview_pg_data` | 1 | 885.4 MB |
| `codexify_private_preview_hf_cache` | 8 | 4.019 GB |
| `codexify_private_preview_chroma` | 4 | 1.933 GB |
| `codexify_private_preview_neo4j_data` | 1 | 541.4 MB |
| `codexify_private_preview_e2e_pnpm_store` | 1 | 570.3 MB |
| `codexify_private_preview_corepack_cache` | 1 | 18.22 MB |
| `codexify_private_preview_frontend_pnpm_store` | 1 | 0 B |
| `codexify_private_preview_codexify_cli_home` | 3 | 36 B |
| `codexify_private_preview_e2e_frontend_src_node_modules` | 1 | 16.26 kB |
| **Total** | | **≈ 7.97 GB** |

### 3.3 Backup and recovery evidence

| Question | Answer |
| --- | --- |
| Does a **current backup artifact** exist? | **No.** A bounded search of the development volume for `*.dump`, `*.dump.gz`, `*pg_dump*`, `*.backup` found only unrelated source-file backups (`guardian/guardian_api.py.backup`). |
| Is there a **documented, independently restorable** backup procedure? | **Yes** — `scripts/ops/private_preview_backup_restore_proof.sh`. It takes a checkpoint backup under `CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR`, then verifies it by restoring into a scratch `codexify_restore` database and restoring the original service state. |
| Is there a destination with free capacity **outside** the `Docker.raw` constraint? | **Yes** — the macOS system volume has 26 GiB free, and the development volume has 68 GiB free outside `/Volumes/Dev_SSD/offload/docker`. A backup written *inside* `Docker.raw` would consume the guest's own 39.2 GiB and would not be independently restorable, so it must not go there. |
| Recovery dependencies | Preview PostgreSQL data (`codexify_private_preview_pg_data`), Neo4j store, Chroma store, the `hf_cache`, the backend/worker image digests above, and the repo's backup-restore proof script. |

No backup was created by this task: no reclamation was executed, and writing a
new backup is only warranted immediately before an operation that risks
Docker's persistent state.

### 3.4 Guest writable state

```
$ docker run --rm alpine:3 sh -c 'echo probe > /w.txt && cat /w.txt && echo GUEST_WRITABLE_OK'
probe
GUEST_WRITABLE_OK
```

The read-only guest filesystem reported during STOCK-MIGRATOR-01 is **resolved**.

## 4. Capacity requirement calculation

The requirement is grounded in the **measured** consumption of the previous
qualification and of the STOCK-MIGRATOR-01 stock-path proof on this same host
(`docs/architecture/proofs/runtime/2026-11-03-qualification-capacity-preflight.md`
§5 and the STOCK-MIGRATOR-01 receipt).

| Component | Estimate | Basis |
| --- | --- | --- |
| Backend runtime image (build, persistent) | 4.64 GB | measured size of `codexify-backend-runtime:latest` built from `backend/Dockerfile` target `runtime`; the STOCK-MIGRATOR-01 source-matched image measured 4,798,730,552 bytes |
| BuildKit cache for one backend build | ≤ 6 GB | measured on this host: the cache grew from 7.605 GB to 12.83 GB during STOCK-MIGRATOR-01's single build (≈ 5.2 GB for one build) |
| Frontend image | 0 | the stock path runs `node:20-alpine` (194 MB, already present) with a bind mount — no frontend image is built |
| `pg_data` for a fresh qualified database | ≈ 0.9 GB | observed `codexify_private_preview_pg_data` (885.4 MB) |
| `hf_cache` | 0 – 4.02 GB | conditional; the embedding model is bind-mounted from the host, so a run need not populate the cache |
| pnpm / corepack / node_modules volumes | ≤ 0.71 GB | observed 0 B + 18.22 MB + 570.3 MB + ~120 MB |
| `neo4j_data` | 0 | `neo4j` and `graph-init` are optional in `v1-local-core-web-mcp` |
| Transient container/log growth during the run | 2 – 5 GB | upper bound for disposable container writable layers and logs |
| **Projected peak requirement** | **≈ 18.3 – 21.3 GB** | sum of the above |

### 4.1 Threshold assessment

| Threshold component | Required | Measured | Met? |
| --- | --- | --- | --- |
| Host free capacity | ≥ 30 GiB | **68 GiB** | **Yes**, +38 GiB over the threshold and +47 GiB over the projected peak |
| Docker VM free capacity | ≥ projected peak (≈ 21 GB) | **39.2 GiB** | **Yes**, ≈ 18 GiB headroom after the projected peak |
| Preview continuity reserve | Preview's own data must be untouched and present | 7.97 GB of volumes + Preview images intact | **Yes** — the qualification uses a separate Compose project, separate volumes and its own image tag; it does not rebuild `codexify-backend-runtime:latest` |
| Image-build headroom | room for one 4.64 GB image + ≤ 6 GB cache | included in the projected peak | **Yes** |
| Transient growth room | 2 – 5 GB | included in the projected peak | **Yes** |

**The projected requirement (≈ 18.3 – 21.3 GB) does not exceed the 30 GiB
threshold**, so the threshold stands at 30 GiB and is met with a wide margin.
The earlier preflight's stricter precondition (26.3 GB, re-measured
immediately before a build) remains a valid *additional* guard for the future
qualification task.

### 4.2 Capacity volatility

Host free space on this volume is demonstrably volatile under concurrent
actors: it was observed at 7.4 GiB, then 30 GiB, then 1.3 GiB, then 68 GiB
within a day, and the changes came from non-Docker deletion by other actors,
not from Docker reclamation. The 68 GiB figure is a **measurement of the
current state, not a floor**. The qualification task must therefore re-measure
`df -h /Volumes/Dev_SSD` immediately before its build and must not start below
the projected requirement plus the 30 GiB threshold.

## 5. Reclamation mechanism — selection and why nothing was executed

The mechanism was selected by the specified priority order, and then found
unnecessary:

**A. Are deleted image layers already reclaimable without deleting other
objects?** Partly, and the answer does not apply here. Docker's own
documentation is explicit that *space is only freed when images are deleted*,
and the FAQ's supported reclamation trigger is
`docker run --privileged --pid=host docker/desktop-reclaim-space`, which
compacts the guest filesystem so the host allocation shrinks. The measured
allocation (80.3 GiB allocated of a 128 GiB logical maximum) already reflects
that mechanism for past deletions; the guest itself has 39.2 GiB free, so the
allocation is not the binding constraint and there is nothing to reclaim for
capacity reasons.

**B. Docker Desktop's supported disk-space reclamation.** Available
(Settings → Resources → Advanced → Disk image size, and the
`docker/desktop-reclaim-space` helper), but both are privileged mutations of
Docker's persistent state, and reducing the *maximum* size deletes the disk
image and every container and image in it — explicitly out of scope. Neither is
needed.

**C. Other identified, operator-owned, independently recoverable storage.**
The repository's `.worktrees/` population is the non-Docker lever: it fell from
120 entries to 44 during this task's measurement window, which is where the
~55 GiB of host capacity came from. This task retired **its own** merged
worktree (see [§7](#7-what-this-task-changed)). Global worktree deletion and
any cleanup of another agent's active worktree are forbidden and were not
performed.

**Conclusion:** the threshold is already satisfied, so **no reclamation
mechanism was executed** and the operator-approval gate was not exercised. No
Docker object, image, volume, container, build record, or disk image was
deleted, pruned, compacted, resized, or reset.

### 5.1 Conditional proposal, held for explicit approval

Should capacity be consumed again before the qualification, this is the exact
proposal that would be submitted for approval. **It is not authorized and was
not executed.**

- **Command / supported action:** delete the six *identified, unused* images
  listed in [§2.5](#25-reclaimable-storage--identified-candidates-none-executed)
  (`codexify-backend-runtime:src-69ef035a4320`, `codexify-probe:ctx`, and the
  four dangling images), then trigger Docker's supported reclamation with
  `docker run --privileged --pid=host docker/desktop-reclaim-space`.
- **Resources affected:** ~10.1 GB of image data with **zero containers**
  referencing them. No Private Preview image, volume, container or network is in
  scope; the images referenced by running containers
  (`codexify-backend-runtime:latest`, `codexify-qualification/stock-gate-b:*`)
  are excluded.
- **Expected reclaimed capacity:** ≈ 10.1 GB of guest space, plus whatever
  host allocation the supported reclamation returns (the host allocation is
  currently 80.3 GiB of a 128 GiB maximum, so at most ~10 GB can come back).
- **Possible interruption:** the privileged reclamation briefly touches the
  guest filesystem; it does not stop running containers, but it is a
  privileged operation and Docker Desktop may report the VM as busy.
- **Backup and restoration evidence:** before this action, take a Preview
  checkpoint with `scripts/ops/private_preview_backup_restore_proof.sh` using
  `CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR` pointing **outside** `Docker.raw`
  (the macOS system volume has 26 GiB free; the development volume has 68 GiB
  free outside the Docker data directory), and confirm the script's restore
  verification passes.
- **Rollback:** the deleted images are rebuildable from their sources
  (`backend/Dockerfile` for the runtime image); the affected images are not
  referenced by any container, so no running service depends on them. The
  Preview is not touched and needs no rollback.
- **Preview impact:** none expected. The Preview's backend image
  (`sha256:22d9f5f1…e6e5c55`), its 9 volumes and its running containers are
  all outside the proposal's scope.
- **Failure modes:** the privileged helper may fail if the guest filesystem is
  busy (retry after the VM is idle); an interrupted reclaim leaves the
  allocation unchanged (no data loss); an accidental inclusion of an
  in-use image would fail with "image is being used by running container"
  rather than deleting it.

## 6. Verification of the outcome

| Verification | Result |
| --- | --- |
| Docker guest filesystem read-write | **Yes** — write probe succeeded in an ephemeral container |
| Host capacity meets the readiness threshold | **Yes** — 68 GiB free ≥ 30 GiB |
| Docker VM capacity meets the readiness threshold | **Yes** — 39.2 GiB available ≥ ≈ 21 GB projected peak |
| Private Preview expected persistent volumes exist | **Yes** — all 9 present with identical names, links and sizes |
| Preview application health unchanged | **Yes** — `db`, `backend`, `worker-coding`, `neo4j`, `redis` healthy; 13 long-running services Up 24 h |
| Preview image identities unchanged | **Yes** — `sha256:22d9f5f1…e6e5c55` and `sha256:a3177274…b735229b` |
| Preview database revision unchanged | **Yes** — `3a91d7c4e8b2` |
| No unintended Compose project started | **Yes** — this task started no containers |
| No Preview migrations executed | **Yes** — the Preview's migrator was not run by this task; the database revision is unchanged |
| `Docker.raw` allocation before / after | **80.3 GiB / 80.3 GiB — unchanged** (nothing was reclaimed) |
| Host free before / after | **68 GiB / 68 GiB** (no reclamation; the worktree retirement below returned no measurable bytes because those trees were APFS clones sharing blocks) |

## 7. What this task changed

**One mutation, both of it mine, neither of it Docker state:**

- Retired this task lineage's own merged worktree
  `.worktrees/frontend-flake-01` (branch `fix/frontend-test-async-stability`,
  merged into `origin/main` as `bf9f2b54`) with `git worktree remove --force`.
  It measured 2.24 GiB apparent but returned **no measurable host bytes**: its
  dependency trees were APFS clones sharing blocks with the other copies.
  This is targeted removal of a merged worktree owned by this task — not global
  worktree deletion, and no other agent's worktree was touched.

Nothing else was deleted, pruned, compacted, resized, stopped, or restarted.

## 8. Remaining risks

1. **Host capacity is volatile.** The 68 GiB is a current measurement, not a
   floor; concurrent actors have moved this volume between 1.3 GiB and 68 GiB
   in a day. The qualification task must re-measure immediately before its
   build and must not start below the projected requirement plus 30 GiB.
2. **No retained Preview backup.** The restore *procedure* exists and is
   exercised by `scripts/ops/private_preview_backup_restore_proof.sh`, but no
   current dump artifact exists on the volume. If any operation against
   Docker's persistent state is proposed later, a checkpoint backup must be
   taken first, outside `Docker.raw`.
3. **The `Docker.raw` allocation does not shrink on its own.** 80.3 GiB of the
   128 GiB maximum is still allocated. This is not currently binding (the guest
   has 39.2 GiB free), but it means host capacity is consumed by Docker's
   allocation even when the guest is comparatively empty.
4. **Two other actors' stacks hold resources this task did not and could not
   attribute** — `codexify-qualification/stock-gate-b:*` (7 containers) and
   assorted proof containers. Any future reclamation must re-derive ownership
   at that time; the current reclaimable pools (2.08 GB of stopped containers,
   8.62 GB of unused volumes) contain unidentified objects and are therefore
   **not** removable under this task's rules.
5. **Reclaimed capacity is not self-sustaining.** The ~55 GiB that returned
   came from worktree deletion by another actor, not from Docker — so it can
   be consumed again by new worktrees.

## 9. Validation

```
$ python scripts/validate_docs.py
Docs validation passed: required architecture docs, README links, and source headings verified.

$ git diff --check
(no output)
```

No automated application tests apply: this is operator maintenance. The
primary proof is the read-only Docker inventory and the filesystem capacity
measurements recorded above.

## 10. ADR impact

**None.** No ADR is added, amended, or superseded. ADR-069's supported-runtime
and release-authority boundaries are preserved: the Beta release classes are
unchanged, `docs/architecture/00-current-state.md` remains release authority,
and no support posture is widened. This receipt is evidence under
`docs/architecture/proofs/`, and under ADR-069's Evidence vs Support Doctrine,
evidence does not redefine support posture.

## 11. What this receipt does not claim

- It does **not** qualify the stock Compose runtime, at any revision.
- It does **not** authorize or begin `supported-compose-stock`.
- It does **not** claim any reclamation was performed against Docker's
  persistent state — none was, and none was needed.
- It does **not** create, edit, or project any qualification receipt or
  registry entry.
- It does **not** lift the release gate, which remains **HOLD**.
- It does **not** assert the host's 68 GiB will still be free when the
  qualification runs; that must be re-measured.

## 12. Next proof needed

`supported-compose-stock` qualification, as an independent task, with the
precondition from [§4.2](#42-capacity-volatility): re-measure
`df -h /Volumes/Dev_SSD` and the guest's available space immediately before
the build, and do not start below the projected requirement plus the 30 GiB
threshold. The release posture remains **HOLD** throughout.
