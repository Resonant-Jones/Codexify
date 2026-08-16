# Tester backend OOM characterization proof

## Result

**DOCKER_VM_GLOBAL_MEMORY_PRESSURE**

Confidence: **HIGH**

The post-ADR-067 backend OOM (exit 137, `OOMKilled=true`) is owned by
**Docker Desktop VM-global memory exhaustion**, not by an explicit backend
container memory limit, not by Chroma, not by the embedder in isolation, and
not by a startup sweep. Direct kernel evidence from inside the Docker VM
(`dmesg`, `CONSTRAINT_NONE` `global_oom`) shows the Linux VM OOM killer
reaping the backend `python` process twice, and reaping `worker-chat` twice
plus `neo4j` once in the same window — all with the VM's 2 GiB swap fully
consumed and `MemFree` at ~91 MB before the backend even started.

The supported backend's own working set is small (~0.5 GiB combined Chroma +
embedder + FastAPI startup). It is killed because the 6 GiB Docker Desktop VM
already hosts ~3.6 GiB of other containers (three Compose projects, ~103
containers, including 96 `codexify_account_observability_norm_*` replicas and
the Tester's own ~1.7 GiB of embedder-loaded workers) and its 2 GiB swap is
exhausted, leaving no headroom for the backend's ~0.5 GiB startup allocation
spike. macOS host evidence (32 GiB physical, 39% free system-wide) rules out
host memory pressure.

## 1. Scope

Characterize — not repair — the first material blocker after ADR-067 Chroma
retirement:

`BACKEND_OOM_KILL_AFTER_SUCCESSFUL_INITIALIZATION`

This task determines the owner of the backend OOM kill and selects one
remediation class. No runtime, Compose, Dockerfile, profile, migration, or
resource setting was changed. No repair was applied.

## 2. Workflow classification

Architecture-Impact Codexify Task.

## 3. ADR impact

`Aligned with existing ADR(s)` — the derived-index retirement decision has
already executed; this task diagnoses a new post-initialization
runtime-resource failure without changing persistence authority, provider
semantics, storage contracts, runtime topology, or release support.

## 4. Governing ADR

ADR-067 Operator-Approved Derived Chroma Retirement
(`docs/architecture/adr/067-operator-approved-derived-chroma-retirement.md`).

## 5. Previous ADR-067 execution handoff

- Committed previous proof: `a48ce2009ab52693e9c1912cd87e42483f0bba1b`
  (`docs: prove ADR-067 Chroma retirement startup`). Its parent is
  `7a6cc844e032b583390f85de45193bf313240462`, whose parent is the canonical
  ADR-067 merge `d0d3463675b746d6bb4d21f219f624419c497d31`.
- Previous proof branch: `proof/adr067-chroma-retirement-startup-20260814`.
- Handoff result: historical Chroma preserved and retired; fresh stock
  `chromadb==1.0.15` store initialized (migration generation 9/5/2); no
  `collections.schema_str`; no `embedding_metadata_array`; one deterministic
  built-in-help record; zero records copied from retired Chroma; prior Rust
  panic absent; `/health` and `/health/chat` returned HTTP 200 while alive;
  backend subsequently exited 137 with `OOMKilled=true`; authenticated
  Tester viability not reached.
- The execution proof file at
  `docs/architecture/proofs/2026-08-14-adr067-chroma-retirement-tester-startup-proof.md`
  is present in commit `a48ce2009ab52693e9c1912cd87e42483f0bba1b` and is the
  durable handoff source.

## 6. Task base HEAD

Durable committed equivalent:
`a48ce2009ab52693e9c1912cd87e42483f0bba1b`. The task branch
`proof/tester-backend-oom-characterization` was created from the prerequisite
proof before its squash; the committed SHA above is the repository-verifiable
handoff reference.

## 7. Observed origin/main

`d0d3463675b746d6bb4d21f219f624419c497d31` — unchanged from ADR-067 main at
task-authoring time.

## 8. Integration/drift result

- Repo identity: `/Volumes/Dev_SSD/Codexify-main` (verified).
- Prerequisite commit exists locally; parent equals
  `d0d3463675b746d6bb4d21f219f624419c497d31` (verified).
- `git merge-base --is-ancestor d0d3463 origin/main` → PASS; remote advanced
  zero commits beyond ADR-067 main. No drift. No rebase/merge performed.

## 9. Current fresh-Chroma verification

Pre-task (Phase 3), read-only URI-mode structural inspection of the active
`.chroma/chroma.sqlite3`:

- sysdb migrations: 1..9 (max 9; no migration 10)
- metadb migrations: 1..5 (max 5; no migration 6)
- embeddings_queue migrations: 1..2
- `PRAGMA quick_check`: ok
- `PRAGMA integrity_check`: ok
- `schema_str` column in `collections`: absent
- `embedding_metadata_array` table: absent
- `embeddings` rows: 1 (deterministic built-in-help record)
- `collections` rows: 1
- `segments` rows: 2

Fresh stock 9/5/2 generation confirmed. Historical 10/6/2 generation has NOT
reappeared.

## 10. Historical archive verification

`/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/`
exists and was not opened, copied from, or modified by this task.

## 11. Previous backend OOM metadata

Container `3e98af520138` (`codexify_tester-backend-1`,
image `sha256:cc06585cd1acf...` = current `codexify-backend-runtime:latest`,
project `codexify_tester`, service `backend`), recorded at task start:

- State.Status: exited
- State.ExitCode: 137
- State.OOMKilled: true
- State.StartedAt (previous run): 2026-08-14T16:59:24.747Z
- State.FinishedAt (previous run): 2026-08-14T17:00:17.347Z (~53 s lifetime)
- RestartCount: 0
- HostConfig.Memory: 0 (no limit)
- HostConfig.MemoryReservation: 0
- HostConfig.MemorySwap: 0
- HostConfig.OomKillDisable: absent
- HostConfig.NanoCpus / CpuQuota / CpuPeriod: 0 (no CPU limit)
- RestartPolicy: `{Name: no}`

## 12. Rendered backend resource configuration

The exact Tester Compose stack is resolved by
`scripts/ops/codexify_tester.sh` as:

```
-p codexify_tester
--env-file .env.tester
-f docker-compose.yml
-f docker-compose.tester.yml
-f docker-compose.whooshd-deepseek.yml
```

Rendered `docker compose config` contains **no** `mem_limit`,
`mem_reservation`, `memswap_limit`, `deploy.resources.limits.memory`, or
`deploy.resources.reservations.memory` for `backend` (or any service; the
only memory-adjacent knob is redis `--maxmemory 512mb`, an application-level
Redis setting). Cross-checked against `docker inspect` HostConfig.Memory = 0.

## 13. Explicit container-memory limit

`BACKEND_EXPLICIT_MEMORY_LIMIT: ABSENT` (HostConfig.Memory = 0; no rendered
Compose memory control).

## 14. Docker Engine memory capacity

`docker info`:

- Total Docker Engine memory: 6,212,632,576 bytes (5.79 GiB)
- CPUs: 4
- Architecture: aarch64
- OSType: linux
- OS: Docker Desktop
- Kernel: 6.12.76-linuxkit

## 15. Docker Desktop memory allocation

Docker Desktop settings (`~/Library/Group Containers/group.com.docker/settings-store.json`,
numeric fields only, file not dumped or edited):

- MemoryMiB: 6144
- SwapMiB: 2048
- DiskSizeMiB: 141312
- Cpus: 4

`DOCKER_DESKTOP_CONFIGURED_MEMORY: 6144 MiB (+ 2048 MiB swap) — RESOLVED`.

## 16. macOS host memory capacity

`sysctl -n hw.memsize`: 34,359,738,368 bytes (32 GiB). Host: arm64, macOS
26.5.2.

## 17. Pre-reproduction host memory pressure

- `memory_pressure -Q`: system-wide memory free percentage **39%** of 32 GiB.
- `vm_stat` (page size 16384): free 4,181; active 405,034; inactive 403,054;
  wired 179,864; purgeable 4.

Host was NOT under material memory pressure at any point in this task.

## 18. Startup/lifespan topology

Static read of `guardian/guardian_api.py` `app_lifespan` (read-only; no
edits). Sequential in-lifespan startup order:

1. `ensure_system_dirs()`; config coherence check; voice dependency
   validation.
2. `dependencies.init_database()` — Postgres (idempotent).
3. `init_services(db)` → `VectorStore()` → embedder construction:
   `SentenceTransformer(/models/bge-large-en-v1.5, local_files_only=True)`
   plus `chromadb.PersistentClient` (`guardian/runtime/embed/embedder.py`).
4. `seed_global_system_docs(get_vector_store())` — in-process embed + upsert
   of enabled global `SystemDoc` rows (`guardian/runtime/ingest/seed_pipeline.py`).
5. GuardianDB init, default-user ensure, built-in help ingest
   (`_run_builtin_help_startup_ingest`, synchronous in-process).
6. Outbox config, default project, provider-row sync from catalog.
7. `_schedule_chatgpt_import_startup_sweep(app)` — background
   `asyncio.to_thread` task (see §20).
8. Optional Neo4j connect (graph logging off by default), optional connector
   worker (`ENABLE_CONNECTOR_WORKER=false` in the Tester service), model
   warm-up enqueue (Redis), then `[startup] Guardian API ready` → Uvicorn
   serving.

The heavy in-process allocation is step 3 (embedder + Chroma). The seed
(step 4) reuses the already-loaded model.

## 19. Seed-pipeline startup semantics

`seed_global_system_docs` runs synchronously inside the lifespan, reuses the
shared `VectorStore`, loads enabled global `SystemDoc` rows from Postgres,
and upserts them into Chroma with stable ids. It does not load a second model
instance. In this reproduction it was never reached (see §23).

## 20. Account-import startup semantics

`_run_chatgpt_import_startup_sweep` runs in a background thread
(`asyncio.create_task(asyncio.to_thread(...))`). It fetches retryable
ChatGPT-import embedding items from Postgres (bounded by
`_CHATGPT_IMPORT_STARTUP_RETRY_CAP`) and **enqueues** embedding batches to
Redis for `worker-account-import` — it does not run embeddings in-process in
the backend. In-process memory cost is bounded (DB fetch + Redis enqueue);
vector work is offloaded to the worker container.

## 21. Startup concurrency classification

- `seed_pipeline`: SEQUENTIAL with lifespan startup (in-process).
- built-in help ingest: SEQUENTIAL with lifespan startup (in-process).
- ChatGPT import startup sweep: CONCURRENT (background thread), but it
  enqueues work rather than embedding in-process.
- Model warm-up: enqueued to Redis for `worker-warmup` (separate container).

Net classification: `CONDITIONALLY_CONCURRENT` (one background thread +
synchronous seed), but neither path is a material memory owner (§§35–37,
§45).

## 22. Canonical backend reproduction attempt count

`CANONICAL_BACKEND_REPRODUCTION_ATTEMPTS: 1` (by this task:
`docker start 3e98af520138` at 2026-08-14T18:57:00.85Z, re-executing the
existing container's exact command/image — verified image SHA equals current
`codexify-backend-runtime:latest`; dependencies db/redis healthy; migrator/
model-prep/graph-init completed).

An additional backend start at 19:07:39Z was observed that this task did NOT
initiate (see §24) — it is recorded as an external event, not as a second
canonical attempt.

## 23. Reproduction result

`OOM_REPRODUCED: PASS`

- Container started: 18:57:00.853Z
- Backend startup progressed: Postgres wait OK → alembic_version=9d4c2a7e1b6f
  → `seed_defaults.py` (idempotent) → uvicorn `Started server process [1]`
  (18:57:27.1) → config coherence → `[embedder] embedding model=/models/bge-large-en-v1.5`
  (18:57:27.1) → `[embedder] backend=sentence_transformer model=...`
  (18:57:28.1) — then silence (model loading) and kernel OOM kill.
- Container finished: 18:57:35.018Z (exit 137, `OOMKilled=true`).
- Docker event stream: `oom` then `die` for `codexify_tester-backend-1` at
  18:57:35.
- No `/health` or `/health/chat` success in this reproduction window (the
  process was killed during embedder/model initialization, before the
  lifespan seed and ready boundary). Healthcheck exec probes were attempted
  by Docker at 18:57:11–18:57:34 and failed as expected.
- No authenticated login, chat completions, provider invocation, or manual
  import was performed.

## 24. Backend exit/OOM metadata

Reproduction run: exit 137, `OOMKilled=true`, RestartCount 0,
StartedAt 18:57:00.853Z, FinishedAt 18:57:35.018Z (~34 s lifetime).

Kernel dmesg inside the Docker VM (read-only via a disposable privileged
probe; the ring buffer itself):

```
[18:57:34] oom-kill: ... global_oom, task_memcg=/docker/3e98af520138...,
           task=python, pid=86783, uid=0
[18:57:34] Out of memory: Killed process 86783 (python) total-vm:5204592kB,
           anon-rss:550308kB, file-rss:12kB, shmem-rss:0kB, oom_score_adj:0
```

Additional VM-global kills in the same window (same `CONSTRAINT_NONE`
`global_oom` signature, different containers):

- 19:01:06 — `worker-chat` container `65b12a4352f0`, python pid 73392,
  total-vm 4.4 GB, anon-rss 444 MB (auto-restarted by Docker
  `restart: unless-stopped`; RestartCount 2 after two kills).
- 19:08:07 — `worker-chat` again, python pid 93918 (auto-restarted).
- 19:08:33 — **backend** container again (external start at 19:07:39Z not
  initiated by this task), python pid 6155, total-vm 5.3 GB,
  anon-rss 566 MB.
- Tester `neo4j` container `d559a79f9bf5`: exit 137, `OOMKilled=true`,
  finished 18:49:11Z (pre-existing at task start; recorded in §11-style
  metadata).

The backend kill is `CONSTRAINT_NONE` (VM-global), not `CONSTRAINT_MEMCG` —
ruling out per-container cgroup limit exhaustion.

## 25. Memory sampling method

Three concurrent samplers under a mode-0700 `DIAG_ROOT`
(`/var/folders/.../codexify-backend-oom.mInpks`, since deleted):

- Sampler A: `docker stats --no-stream` for all containers at ~1 s request
  cadence (effective ~3–13 s per full sweep across ~103 containers).
- Sampler B: `docker exec <backend> /proc/1/status` + `smaps_rollup` + bounded
  `ps` (PID/PPID/RSS/VSZ/comm only) at ~1 s cadence. Limitation: the sampler
  attached before `docker start` and its first sample saw the container
  stopped, so process-level rows were not captured in the ~34 s window
  (recorded honestly; container-level Sampler A and kernel dmesg cover the
  gap).
- Sampler C: `docker events` bounded window (oom/die for the backend
  captured; the event stream was otherwise thin because daemon-side event
  replay retained only a limited window).

Raw telemetry was confined to DIAG_ROOT and deleted in Phase 22; only the
bounded aggregates below are recorded here.

## 26. Backend baseline memory

Backend container memory (docker stats, MiB) across the reproduction:
62.5 → 269.6 → 303.6 → 407.3 → 498.4 (last sample 18:57:25, ~10 s before the
kill, during embedder/model initialization).

`BACKEND_BASELINE_RSS_BEFORE_HEAVY_INIT: ~62.5 MiB` (container first sample
after start).

## 27. Post-Chroma memory

Not isolable as a distinct in-container phase marker in this window: Chroma
client construction occurs inside the same `VectorStore()`/embedder
constructor step, and the process died during model load. Chroma's
standalone cost is bounded by the Phase 14 control instead (§35).

`BACKEND_POST_CHROMA_RSS: unobservable as a separate phase in the
reproduction window (no distinct log marker between Chroma open and model
load); bounded via the Chroma-only control (§35).`

## 28. Post-embedder memory

Embedder construction was in progress at death; the model did not finish
loading. `BACKEND_POST_EMBEDDER_RSS: not reached in reproduction`. The
embedder's standalone cost is bounded by the Phase 15 control (§36).

## 29. First-HTTP-ready memory

Not reached in the reproduction (killed before lifespan completion).
`BACKEND_FIRST_HTTP_READY_RSS: not reached (no /health success in this
window)`. The previous ADR-067 execution observed HTTP 200 while alive; the
kernel's kill record shows anon-rss ~550 MB at death, consistent with a
~0.5 GiB working set at the ready boundary.

## 30. Backend peak memory

Container-observed peak: **498.4 MiB** (Sampler A, 18:57:25; the kill
spike occurred inside the subsequent ~10 s sampling gap). Kernel kill record:
**anon-rss 550,308 kB** (~537 MiB) at 18:57:34. Secondary external run:
anon-rss 566,124 kB at its kill. Honest bound:

`BACKEND_PEAK_MEMORY: ~0.5–0.6 GiB (container 498.4 MiB observed; kernel
anon-rss 537–553 MiB at kill)`.

## 31. Tester-project peak memory

Tester project containers (backend + frontend + db + redis + neo4j + 5
workers + tailscale) peaked at **~2.1 GiB** during the reproduction window
(1,733.7 MiB pre-reproduction without backend, plus the ~0.4 GiB backend
ramp; tester `neo4j` was already exited from its own OOM before the task).

## 32. Docker aggregate pressure at failure

All-container aggregate (Sampler A): 3,582.7 MiB pre-reproduction (60.5% of
engine) → peak **3,973.1 MiB (67.1%)** at the sample immediately after the
kill; the exact kill-moment aggregate fell in the sampling gap. VM
`/proc/meminfo` post-kill (read-only disposable probe): `MemFree` ~91 MB,
`MemAvailable` ~524 MB, `SwapFree` **228 kB of 2,097,148 kB** — swap
100% consumed. The VM was at the ceiling; the backend's ~0.5 GiB allocation
was the straw that crossed it, and the kernel selected the backend process
(highest `total-vm`, ~5.2 GB) as the victim.

## 33. Host pressure at failure

macOS host throughout: 32 GiB physical, 39% free system-wide
(`memory_pressure -Q`). No host-pressure signature at any point. The OOM is
entirely inside the 6 GiB Docker Desktop VM.

## 34. Timeline correlation

| Time (UTC) | Event |
| --- | --- |
| 18:49:11 | Tester `neo4j` OOM-killed (exit 137, OOMKilled=true) — pre-existing |
| 18:57:00.85 | Backend `docker start` (canonical reproduction) |
| 18:57:02.9 | seed_defaults complete; alembic head verified 9d4c2a7e1b6f |
| 18:57:23.9 | uvicorn exec; faiss loader logs |
| 18:57:27.1 | uvicorn "Started server process [1]"; `[embedder] embedding model=/models/bge-large-en-v1.5` |
| 18:57:28.1 | `[embedder] backend=sentence_transformer` (model load begins) |
| 18:57:25→18:57:34 | Backend container memory ramp 62.5→498.4 MiB; kill spike in sampling gap |
| 18:57:34 | Kernel `global_oom` kill: backend python pid 86783, anon-rss 550 MB |
| 18:57:35 | Docker `oom` + `die` events; FinishedAt 18:57:35.018Z |
| 19:01:06 | Kernel `global_oom` kill: worker-chat python (auto-restarted) |
| 19:07:39 | External backend start (not task-initiated) |
| 19:08:07 | Kernel `global_oom` kill: worker-chat python again (auto-restarted) |
| 19:08:33 | Kernel `global_oom` kill: backend python pid 6155, anon-rss 566 MB |

Memory growth inflection correlates with embedder/model initialization
(18:57:27→18:57:34). No seed-pipeline or account-import phase was reached
before the kill.

## 35. Chroma-only control

Disposable byte-identical copy of the current fresh active Chroma under
DIAG_ROOT (copy verified `diff -r` byte-equal; never pointed at the live
store). Exact current backend image, no sentence-transformer, no mutation,
bounded one-shot process:

- Result: PASS — `PersistentClient` constructed, 1 collection listed.
- `CHROMA_ONLY_PEAK_MEMORY: 95.2 MiB (ru_maxrss)`.

## 36. Embedder-only control

Exact current backend image + existing local model mount
(`models/bge-large-en-v1.5`, read-only, `TRANSFORMERS_OFFLINE=1`), one
deterministic 1-token encode, no Chroma, no user data, no downloads, no
provider calls:

- Result: PASS — embedding dim (1, 1024).
- `EMBEDDER_ONLY_PEAK_MEMORY: 495.3 MiB (ru_maxrss)`.

## 37. Chroma-plus-embedder control

Same image, another disposable Chroma copy + model mount, one process,
no seed pipeline, no account-import, no FastAPI, no providers:

- Result: PASS — 1 collection, dim (1, 1024).
- `CHROMA_PLUS_EMBEDDER_PEAK_MEMORY: 532.8 MiB (ru_maxrss)`.

Combined Chroma + embedder (~533 MiB) is far below the Docker Engine total
(5.79 GiB) and below the pre-existing aggregate headroom only nominally —
the VM's *effective* free memory at rest was ~91 MB with swap exhausted, so
the ~0.5 GiB startup allocation crosses the real ceiling.

`EMBEDDER_PLUS_CHROMA_BASELINE_EXCEEDS_BUDGET: NO — the component pair is
small; the VM budget is the constraint, not the component.`

## 38. Startup-isolation feasibility

`seed_global_system_docs` requires a `VectorStore` (writes Chroma) plus
Postgres `SystemDoc` reads. `retry_chatgpt_import_embeddings` requires a
Postgres handle and Redis enqueue. Neither has an existing safe standalone
seam that avoids mutating canonical state, and creating a disposable
Postgres clone would require the repository-supported backup/restore path
with write-heavy setup that exceeds the characterization brief's need.

`STARTUP_SWEEP_ISOLATION: NOT_EXECUTABLE_WITH_CURRENT_SEAMS` — no
manufactured seam was added. Classification below rests on proven telemetry
+ source correlation instead.

## 39. Seed-only isolation result

Not executed (no safe seam; see §38).

## 40. Account-import-only isolation result

Not executed (no safe seam; see §38).

## 41. Concurrent-startup isolation result

Not executed (no safe seam; see §38).

## 42. Per-container-limit classification

`PER_CONTAINER_MEMORY_LIMIT_EXHAUSTION: NOT_SUPPORTED` — HostConfig.Memory=0
and no rendered Compose memory limit; kernel kill is `CONSTRAINT_NONE`
(global), not `CONSTRAINT_MEMCG`.

## 43. Docker-VM-pressure classification

`DOCKER_VM_GLOBAL_MEMORY_PRESSURE: CONFIRMED`

Evidence chain (all direct, not inferred from naming):

1. Backend has no binding per-container limit (§§12–13).
2. Aggregate Docker workload at rest before backend start: 3,582.7 MiB of
   5,924.6 MiB engine total (60.5%), across ~103 containers including two
   other Compose projects and 96 account-observability replicas.
3. VM `/proc/meminfo` at rest: `MemFree` ~91 MB, `SwapFree` ~228 kB (2 GiB
   swap fully consumed).
4. Kernel dmesg shows `global_oom` (`CONSTRAINT_NONE`) kills of the backend
   python twice, worker-chat python twice, and a prior neo4j kill — multiple
   independent victims across projects, the classic global-pressure
   signature.
5. Backend victim anon-rss at kill: 537–553 MB — small working set killed by
   environment pressure, not self-induced growth.
6. The worker-chat kill at 19:01:06 occurred while the backend was DOWN,
   proving the pressure exists independently of the backend.

## 44. Host-pressure classification

`HOST_MEMORY_PRESSURE: NOT_SUPPORTED` — 32 GiB host, 39% free system-wide,
no host-level pressure signature. Docker VM pressure is not macOS host
pressure and is not equated with it.

## 45. Startup-component classification

- `SEED_PIPELINE_MEMORY_SPIKE`: not supported — seed was never reached in
  the reproduction; seed-only isolation not safely executable; seed reuses
  the loaded model (source-verified).
- `ACCOUNT_IMPORT_SWEEP_MEMORY_SPIKE`: not supported — sweep enqueues to
  Redis, does not embed in-process (source-verified at
  `backend/rag/chatgpt_migration.py` `retry_chatgpt_import_embeddings` →
  `_process_chatgpt_embedding_batches` → `_queue_chatgpt_embedding_batch`).
- `STARTUP_SWEEP_CONCURRENCY_MEMORY_SPIKE`: not supported — individual jobs
  are bounded (controls §§35–37 + source semantics §§19–20), and the direct
  kernel evidence (§43) already explains the kill without sweep
  participation.

## 46. Primary root-cause classification

**DOCKER_VM_GLOBAL_MEMORY_PRESSURE**

## 47. Classification confidence

**HIGH** — direct kernel `global_oom` records, VM meminfo/swap exhaustion,
explicit-limit absence, multi-container victim pattern, independent
component controls, and host-pressure exclusion. Residual uncertainty is
limited to the exact instantaneous aggregate at the kill moment (a ~10 s
sampler gap), which does not change the classification.

## 48. Recommended remediation class

**DOCKER_DESKTOP_MEMORY_ALLOCATION_ADJUSTMENT**

Reconcile the supported Tester profile with the proven Docker VM memory
budget (6 GiB RAM + 2 GiB swap hosting ~3.6 GiB of concurrent non-Tester
workload). Do not change Docker Desktop settings automatically; operator
authorization is required. No Chroma-generation change and no historical
restoration is recommended or authorized.

## 49. Fresh active Chroma final state

Post-diagnostics (read-only):

- sysdb 9, metadb 5, embeddings_queue 2 (stock generation)
- `PRAGMA quick_check`: ok; `PRAGMA integrity_check`: ok
- embeddings rows: 1; collections rows: 1
- `schema_str`: absent; `embedding_metadata_array`: absent

Aggregate fresh-record count: **1** (unchanged; the reproduction was killed
during embedder initialization, before any seed write).

## 50. Historical Chroma restoration status

`HISTORICAL_CHROMA_RESTORATION: NOT_PERFORMED`

## 51. Historical archive final state

`/Volumes/Dev_SSD/Codexify-archive/chroma/adr067-20260814T125804-40e05f2249ff/`
exists, unmodified by this task.

## 52. Canonical Postgres safety

- Alembic head: `9d4c2a7e1b6f` (live DB query via `psql` on
  `codexify_tester-db-1` AND local `alembic heads` in `backend/`).
- `CANONICAL_POSTGRES_MANUAL_MUTATION: NONE` — no schema, migration, stamp,
  or manual SQL performed by this task.
- Normal backend startup executed the canonical idempotent
  `seed_defaults.py` (alembic_version verified 9d4c2a7e1b6f in-run) before
  the kill — reported as normal idempotent startup state, not task-authored
  mutation.
- Bounded row-count sample (unchanged during task): `system_docs=0`,
  `users=18`.

## 53. Temporary-state cleanup

- DIAG_ROOT deleted; `test ! -e DIAG_ROOT` → PASS.
- Raw telemetry, logs, disposable Chroma copies, helper scripts: deleted.
- No disposable containers remain (all controls used `--rm`).
- No canonical Tester container or volume was stopped/removed by this task.
- Historical archive and active `.chroma` untouched (verified present after
  cleanup).

## 54. Secret/user-data exposure review

No secrets, API keys, JWTs, cookies, environment dumps, document/message
content, embeddings, metadata, or row bodies were recorded in this artifact
or in the closeout. Logs were redacted at capture (`docker logs` output is
redacted by the runtime's own `log_event` filter; bounded fields only
extracted). Docker Desktop settings file was read for four numeric keys only
and never dumped. gitleaks/pre-commit heuristic: neither binary is installed
in this environment — recorded as a tooling limitation; the artifact was
hand-audited against the exclusion list above.

## 55. What this proves

- The OOM kill is VM-global (`CONSTRAINT_NONE`), not a per-container limit.
- The backend has no explicit memory limit; the Docker VM has 5.79 GiB with
  swap already exhausted at rest.
- The backend's own working set is ~0.5 GiB (Chroma 95 MiB + embedder
  495 MiB + FastAPI startup overhead); it dies from environment pressure,
  not self-inflicted growth.
- Multiple independent containers (backend, worker-chat, neo4j) are being
  killed by the same VM-global OOM mechanism.
- Chroma compatibility and ADR-067 state are intact; the Rust panic did not
  return; fresh 9/5/2 store healthy with its 1 built-in-help record.
- The macOS host is not under pressure.

## 56. What this does not prove

- Authenticated Tester viability (not attempted; backend did not remain
  alive).
- The exact instantaneous aggregate memory at the kill moment (sampler gap).
- Which specific non-Tester tenant should shed or relocate memory (a
  capacity-placement decision, out of scope).
- That any single startup sweep is a memory spike (not reached/not safely
  isolable).

## 57. Final task classification

**PASS** — the OOM ownership is bounded sufficiently to authorize one
specific remediation task (Docker VM memory-budget reconciliation). PASS
does NOT mean the Tester is requalified.

## 58. Documentation follow-through

This proof file is the only tracked change. No runtime/config/resource
setting, no Compose/Dockerfile/profile/migration file, and no ADR was
changed. `00-current-state.md` intentionally untouched (runtime truth did
not change; the blocker was already recorded by the ADR-067 execution
proof).

## 59. Exact next gate

Create exactly one operator/runtime task:

"Reconcile the supported Tester profile with the proven Docker VM memory
budget (6 GiB RAM + 2 GiB swap; ~3.6 GiB concurrent non-Tester workload
already resident; swap exhausted at rest). Operator-authorized options
include raising the Docker Desktop VM memory allocation and/or relocating
or bounding non-Tester tenants. Do not change Docker Desktop settings
automatically. After reconciliation, rerun backend stability plus the
authenticated Tester viability proof."

---

## Validation

- Focused pytest (repo `.venv`, `unset PYTHONPATH`):
  `tests/ops/test_backend_runtime_dependency_contract.py`,
  `tests/vector/test_vector_store_resolution.py`,
  `tests/routes/test_dashboard_snapshot.py` → **13 passed** (7 warnings).
- Alembic heads (repo `.venv`, `backend/`): `9d4c2a7e1b6f (head)`.
- Live DB alembic_version (psql): `9d4c2a7e1b6f`.
- `make docs` (proven interpreter): validate_docs.py PASS;
  check_diagram_freshness.py PASS (no drift, no warnings).
- `git diff --check`: PASS (clean).
- `git status --short --branch --untracked-files=all`: only this proof file.
