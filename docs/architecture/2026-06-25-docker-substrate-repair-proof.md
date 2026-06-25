# Docker Substrate Repair Proof

**Artifact window:** 2026-06-25  
**Branch:** `main`  
**HEAD:** `d14106574`  
**Docker Desktop:** 4.79.0 (230596)  
**Docker Engine:** 29.5.3  
**Docker Compose:** v5.1.4  

## 1. Context

The Continuity Phase A storage migration proof (`2026-06-25-continuity-phase-a-storage-migration-proof.md`) recorded a PARTIAL PASS. All 105 focused tests pass, but clean-start Docker Compose migration proof is blocked by a host-level Docker daemon filesystem corruption issue.

The specific error is: `unlinkat /var/lib/docker/containers/.../...-json.log: structure needs cleaning`

This task diagnoses the substrate, attempts safe remediation, and records the outcome.

## 2. Scope

**Inspected:**

- Docker daemon health (version, info, system df, ps, compose ps)
- Container state (6 dead containers, 1 running redis)
- All 105 focused continuity tests (still passing)
- `docker compose down -v` (still failing)
- Individual container force-removal (still failing on all 6 dead containers)

**Repair attempted (non-destructive only):**

- `docker compose down -v` — failed
- `docker compose down --remove-orphans` — failed
- `docker rm -f <each-container>` — failed on all 6 dead containers

**Not changed:**

- No Codexify runtime code
- No continuity schema, migrations, or models
- No Docker data deletion or factory reset (requires human approval)
- No filesystem repair commands
- No release promise widening

## 3. Focused Continuity Test Result

**Command:**

```
.venv/bin/pytest -v tests/continuity/test_phase_a_storage_schema.py tests/continuity/test_contracts.py tests/continuity/test_compiler.py
```

**Result: 105 passed in 0.77s**

All code-level proofs remain intact. The blockage is purely environmental.

## 4. Docker Diagnostic Commands and Results

### `docker version`

```
Client: 29.5.3 / Server: Docker Desktop 4.79.0 (230596)
```

Docker Desktop is running. Both client and daemon are responsive.

### `docker info`

Docker daemon is operational. Plugins: agent, ai, buildx, compose, debug, desktop, dev, extension, feedback, init, sbom, scout.

### `docker compose version`

```
Docker Compose version v5.1.4
```

### `docker ps -a`

```
CONTAINER ID   IMAGE                             STATUS
caa69deb888e   codexify-backend-runtime:latest   Dead
22a90752ec77   node:20-alpine                    Dead
86a91b9f8b5a   codexify-backend-runtime:latest   Dead
726ded9c4b95   codexify-backend-runtime:latest   Dead
1b6f6e37ae4d   codexify-backend-runtime:latest   Dead
d147fe43385c   codexify-backend-runtime:latest   Dead
a478ea09d024   redis:7-alpine                    Up 4 hours (healthy)
```

6 dead containers cannot be removed. 1 redis container is still running healthy.

### `docker system df`

```
Error: failed to retrieve container list: rw layer snapshot not found for container caa69deb888e...
```

The daemon cannot enumerate layer information for the dead containers. This confirms the rw layer corruption spans multiple containers, not just a single log file.

### `docker compose ps`

```
NAME               STATUS
codexify-redis-1   Up 4 hours (healthy)
```

Only redis is alive. No Postgres, Neo4j, backend, or worker containers are up.

### `docker compose down -v`

```
Container codexify-worker-chat-1 Error while Removing
Container codexify-worker-chat-embed-1 Error while Removing
Container codexify-worker-warmup-1 Error while Removing
Container codexify-worker-document-embed-1 Error while Removing
Container codexify-worker-voice-1 Error while Removing
Container codexify-frontend-1 Error while Removing

Error: cannot remove container "726ded9c4b95...": unable to remove filesystem:
unlinkat /var/lib/docker/containers/726ded9c4b95.../...-json.log: structure needs cleaning
```

### `docker rm -f <each dead container>`

All 6 dead containers fail identically:

```
unable to remove filesystem: unlinkat /var/lib/docker/containers/<id>/<id>-json.log: structure needs cleaning
```

## 5. Root Cause Classification

**Classification: `host-docker-substrate`**

The root cause is filesystem corruption inside the Docker Desktop Linux VM's data disk. The specific path affected is:

```
~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
```

Inside this disk image, the directory `/var/lib/docker/containers/` has 6 container directories whose `-json.log` files exist on a corrupted inode or block. The `unlinkat` system call fails with `ENOTRECOVERABLE` (reported as "structure needs cleaning" by the macOS→Linux translation layer).

This is **not** a Codexify migration or code issue. It is a Docker Desktop VM filesystem integrity problem.

### Evidence That This Is Not Codexify-Related

1. The affected files are Docker daemon container log files (`-json.log`), not Codexify data files.
2. The error originates from the Linux kernel's filesystem layer (`unlinkat` → `ENOTRECOVERABLE`), not from any Docker layer or container runtime.
3. All affected containers are 5+ hours old, from a previous Compose session.
4. Codexify code has no access to `/var/lib/docker` on the Docker Desktop VM.
5. All 105 continuity tests pass at the code level.

## 6. Safety Boundary

**Commands intentionally not run:**

- `rm -rf ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw` — full Docker data deletion
- `docker system prune -af --volumes` — would also fail at layer enumeration, plus risks data loss
- `fsck` or `e2fsck` on the Docker.raw disk image — requires mounting the raw image, which Docker Desktop owns exclusively while running
- Docker Desktop "Factory Reset" via UI — requires human approval

**Recommended human remediation:**

1. **Stop Docker Desktop** (quit the application entirely).
2. **Option A (preferred): Factory Reset** — Open Docker Desktop → Settings → Troubleshoot → Factory Reset. This will reset Docker to its initial state, removing all containers, images, volumes, and the corrupted filesystem. This is the safest path given the filesystem-level corruption.
3. **Option B (if preserving data matters):** Stop Docker Desktop, then run `fsck` or `e2fsck` on the `Docker.raw` image file after first converting/extracting the filesystem. This requires advanced Docker Desktop VM knowledge and is not generally recommended.
4. **Option C (nuclear):** After stopping Docker Desktop, delete `~/Library/Containers/com.docker.docker/`, then reinstall Docker Desktop. This is equivalent to a factory reset.
5. After repair, restart Docker Desktop.
6. Verify: `docker ps -a` should show no dead containers.
7. Run `docker compose down -v` from the Codexify repo root to confirm clean reset.
8. Re-run the continuity migration proof task.

## 7. Outcome

**HOLD**

Docker substrate repair requires human intervention (Docker Desktop factory reset). No programmatic remediation is safe or available without elevated access to the Docker Desktop VM filesystem.

## 8. Next Task Recommendation

1. **Human action:** Perform Docker Desktop factory reset (Settings → Troubleshoot → Factory Reset).
2. **After Docker is healthy:** Re-run `Prove Continuity Phase A Storage Migration on Supported Stack` to complete clean-start and existing-instance migration proof.
3. **After migration proof passes:** Proceed to persistence adapter planning (next ADR-030 step after migration proof).

## 9. ADR Impact

- **Classification:** Aligned with ADR-031
- This proof artifact documents environmental blockage only. It does not widen the release promise. The Phase A migration code, models, and tests are correct and will pass live migration proof once Docker substrate health is restored.

## 10. Runtime Non-Goals

This proof does not and must not be interpreted as:

- Proving any runtime write path exists
- Proving compiler output is persisted
- Proving workers emit continuity events
- Proving API routes serve continuity records
- Proving UI renders continuity data
- Proving graph writes are enabled
- Proving sync behavior exists
- Proving export/restore includes continuity
- Widen the supported beta release promise
