# Tester stack reactivation proof

**Result:** `TESTER_REACTIVATION_WORKER_FAILURE`

**ADR impact:** Aligned with ADR-074 and the existing Tester lifecycle/operator
contracts; no ADR change.

## Scope and stop condition

This task was authorized to perform exactly one canonical Tester activation from
the corrected operator authority and prove a healthy idle runtime. The one
activation command completed, and its lifecycle-owned dependency one-shots
completed successfully. The first post-start worker gate then observed a
`worker-chat` import crash and a missing heartbeat. The task therefore stopped
at the first causal worker failure. No repair, rebuild, manual restart, second
activation, authentication, chat, inference, DeepSeek request, Watchdog action,
or cleanup lifecycle was performed.

The bounded proof window was:

```text
ACTIVATION_WINDOW_START_UTC=2026-08-27T18:25:23Z
CANONICAL_COMMAND_STARTED_UTC=2026-08-27T18:26:01Z
FIRST_WORKER_FAILURE_OBSERVED_UTC=2026-08-27T18:27:21Z
FINAL_READ_ONLY_OBSERVATION_UTC=2026-08-27T18:30:06Z
```

The first causal blocker was:

```text
TESTER_REACTIVATION_WORKER_FAILURE
```

## Prerequisite and proof-task checkout

The required authority-reconciliation commit was verified before activation:

```text
git cat-file -e 62b97e33f005e184bbdfe402a7ae54eb3606ce12^{commit}: PASS
git merge-base --is-ancestor 62b97e33f005e184bbdfe402a7ae54eb3606ce12 HEAD: PASS
```

The proof-task checkout was:

```text
root: /Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD before proof: 62b97e33f005e184bbdfe402a7ae54eb3606ce12
status before proof: clean; ahead 1 of origin/codex/diagnose-tester-fresh-chroma-failure
```

No source file, supported profile, Compose definition, Whoosh’d file, Watchdog
file, or `docs/architecture/00-current-state.md` was changed.

## Authoritative Tester root and environment

The canonical lifecycle was traced read-only:

```text
make tester-up
  -> bash scripts/ops/codexify_tester.sh up
  -> Compose project: codexify_tester
  -> env: /Volumes/Dev_SSD/Codexify-main/.env.tester
  -> files:
     docker-compose.yml
     docker-compose.tester.yml
     docker-compose.whooshd-deepseek.yml
```

The installed LaunchAgent pins `CODEXIFY_TESTER_REPO_ROOT` to
`/Volumes/Dev_SSD/Codexify-main`; the lifecycle script deterministically derives
the authoritative env path from that root. The ignored proof-worktree copy at
`/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.env.tester` remains
non-authoritative and was not read for runtime configuration, edited, or
staged. Its stale provider/profile/model posture was not used.

The active source repository was:

```text
remote: https://github.com/Resonant-Jones/Codexify.git
branch: main
HEAD: 1c597042e314a9a409ddd384225a2cbb723f7528
status: main...origin/main [ahead 3, behind 18]
pre-existing dirty paths: deleted 2026-08-26 daily log, modified
2026-08-25 image-retention proof, untracked 2026-08-27 Google Drive proof
```

Those unrelated paths were preserved. The active env authority immediately
before activation was read without printing secrets:

```text
LLM_PROVIDER=local
CODEXIFY_SUPPORTED_PROFILE=v1-whooshd-deepseek-web
LOCAL_CHAT_MODEL=qwen3.8-27b-4bit
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=deepseek
DEEPSEEK_CHAT_MODEL=deepseek-v4-flash
LOCAL_PROVIDER_VENDOR=whooshd (effective overlay)
LOCAL_BASE_URL=http://host.docker.internal:8000/v1 (effective overlay)
```

The active env file remained owner `chriscastillo`, group `staff`, mode `0600`.

## Pre-activation runtime state

Before the canonical command:

```text
Tester desired-up marker: absent
Tester project network: absent
Tester service containers: absent
127.0.0.1:8889 listener: absent
```

The existing Compose-owned volumes were present and were not deleted,
recreated, pruned, renamed, or manually mutated:

```text
codexify_tester_pg_data
codexify_tester_neo4j_data
codexify_tester_codexify_cli_home
codexify_tester_codexify_tailscale_test_state
codexify_tester_hf_cache
codexify_tester_frontend_pnpm_store
codexify_tester_corepack_cache
```

The canonical PostgreSQL volume was:

```text
name: codexify_tester_pg_data
created: 2026-07-25T19:13:17Z
Compose project label: codexify_tester
service mount: codexify_tester_pg_data -> /var/lib/postgresql/data (rw)
```

The locally available backend image was
`codexify-backend-runtime:latest` (image ID prefix `afaca31e244e`).

An unrelated out-of-band capsule-builder container observed during the prior
task was explicitly excluded and left untouched:

```text
name: codexify-strace-capsule-builder-lbk0ba
image: sha256:2508fe43e87e...
Compose labels: project=codexify_tester, service=migrator
created: 2026-08-27T18:07:10Z
command: long-lived sleep loop only
mount: /Volumes/Dev_SSD/codexify-strace-capsule.lbk0bA/builder -> /work (rw)
```

It was no longer present at the activation preflight. It was not included in
the canonical lifecycle command and was not stopped, restarted, inspected for
application contents, or otherwise changed.

## Whoosh’d prerequisite

The existing Whoosh’d runtime was checked read-only before activation. The
launchd plist was valid and still declared the approved adapter configuration:

```text
listener: 127.0.0.1:8000, PID 30366
WHOOSHD_ADAPTER=mlx_vlm
WHOOSHD_MLX_VLM_ENABLED=true
WHOOSHD_MLX_VLM_MODEL=/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
WHOOSHD_MODEL_REGISTRY_PATH=/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml
```

The source-level factory check, run with bytecode writing disabled, returned:

```text
WHOOSHD_CURRENT_EXECUTION_ADAPTER=mlx_vlm
WHOOSHD_CURRENT_ADAPTER_CLASS=MlxVlmAdapter
WHOOSHD_CURRENT_ADAPTER_KIND=mlx_vlm
WHOOSHD_CURRENT_ADAPTER_NAME=mlx-vlm
WHOOSHD_CURRENT_ENABLED=True
STUB_FALLBACK=False
```

Read-only HTTP checks returned Whoosh’d ready with queue depth 0 and exactly
one public model:

```text
GET /health: HTTP 200; status=ready; model_lifecycle=ready; queue_depth=0; active_jobs=0
GET /v1/models: HTTP 200; ids=[qwen3.8-27b-4bit]; count=1; engine=mlx_vlm; owner=whooshd
```

No Whoosh’d lifecycle action occurred.

## Exactly one canonical activation

From `/Volumes/Dev_SSD/Codexify-main`, the exact command was issued once:

```text
make tester-up
```

The command exited 0. It created the `codexify_tester_default` network and the
canonical service containers. No equivalent Compose command or second
`make tester-up` was issued.

The lifecycle-owned one-shot results were:

| One-shot | Container | Exit | Evidence |
| --- | --- | ---: | --- |
| model-prep | `codexify_tester-model-prep-1` | 0 | completed; no retry |
| migrator | `codexify_tester-migrator-1` | 0 | ran `seed_defaults`, then `[Migrator] Done` |
| seed defaults | owned by migrator | 0 | six redacted INFO records, no error |
| graph-init | `codexify_tester-graph-init-1` | 0 | applied constraints/seed nodes, then Done |

These were normal lifecycle-owned startup actions. No one-shot was invoked
manually or rerun.

## First causal failure

The first post-start status check at `2026-08-27T18:27:21Z` found
`worker-chat` in a restart loop while all core dependencies were healthy. The
worker container was:

```text
id: 6228850a7360...
image: codexify-backend-runtime:latest
restart policy: unless-stopped
restart count at diagnosis: 9
```

The existing worker log showed the first causal application error:

```text
File "/app/guardian/workers/chat_worker.py", line 31, in <module>
  from guardian.context.broker import ContextBroker
ModuleNotFoundError: No module named 'guardian.context'

Subsequent automatic attempts also reported:
ModuleNotFoundError: No module named 'guardian.utils'
```

At that same first check, `/health/chat` reported:

```text
ok=false
status=unhealthy
redis=ok
worker.status=dead
worker.reason=missing
queue.depth=0
provider=local
model=qwen3.8-27b-4bit
completion_service.status_reason=worker_heartbeat_missing
```

This is the first causal blocker and is classified as
`TESTER_REACTIVATION_WORKER_FAILURE`. Docker later restarted the container and
a final read-only check saw a fresh heartbeat, but that automatic recovery does
not erase the first failed worker startup under the task’s stop-on-first-failure
rule. No worker restart, image rebuild, source edit, or lifecycle retry was
performed by this task.

## Runtime state observed after the activation

The resulting Compose project was `codexify_tester`. At final read-only
observation, the dependency and application containers were present:

```text
backend: running, healthy, id=50cc2735f267..., image=codexify-backend-runtime:latest
db: running, healthy, id=7abf4ec323d4..., image=postgres:15
redis: running, healthy, id=3e03c6b86500..., image=redis:7-alpine
neo4j: running, healthy, id=9c9ab09e94e5..., image=neo4j:5
frontend: running, id=6cd447b20a56...
worker-chat: running after automatic restart, id=6228850a7360...
worker-chat-embed: running, id=7f8e7c15851c...
worker-document-embed: running, id=d333cac5701d...
worker-warmup: running, id=4e6dcd6733de...
worker-account-import: running, id=ff84c57b61cf...
tailscale-codexify-test: running, id=9c7a9d05fe17...
```

The backend identity and preserved volume were:

```text
backend port: 127.0.0.1:8889 -> 8888/tcp
backend source mounts: /Volumes/Dev_SSD/Codexify-main/guardian -> /app/guardian,
  /Volumes/Dev_SSD/Codexify-main/backend -> /app/backend,
  /Volumes/Dev_SSD/Codexify-main/config -> /app/config (ro)
db mount: codexify_tester_pg_data -> /var/lib/postgresql/data
```

`GET http://127.0.0.1:8889/health` returned HTTP 200 with
`status=ok`, valid profile `v1-whooshd-deepseek-web`, and the expected release
hold. `GET /health/chat` later returned healthy with Redis `ok`, provider
`local`, model `qwen3.8-27b-4bit`, fresh heartbeat, and queue depth 0; this is
recorded as recovered post-state only and does not change the blocked result.

The LLM catalog remained non-inference coherent:

```text
local: authorized=true, available=true, model=qwen3.8-27b-4bit
deepseek: authorized=true, available=true, model=deepseek-v4-flash
```

No request was sent to either provider.

## Whoosh’d post-state

The Whoosh’d process was not restarted. Post-activation read-only checks still
returned:

```text
PID/listener: 30366 on 127.0.0.1:8000
adapter: mlx_vlm
adapter class: MlxVlmAdapter
stub fallback: false
GET /health: ready; queue_depth=0; active_jobs=0
GET /v1/models: exactly qwen3.8-27b-4bit; engine=mlx_vlm; owner=whooshd
```

The Whoosh’d generation-log scan had the same cumulative generation-request
match count before and after the activation (`8`); no generation endpoint was
issued by this task.

## Execution and persistence boundary

Task-issued action counts were:

```text
TESTER_STACK_ACTIVATION_ATTEMPTS=1
TESTER_SERVICE_LIFECYCLE_ACTIONS=1
MIGRATOR_INVOCATIONS=1 (canonical; exit 0)
SEED_INVOCATIONS=1 (migrator-owned; exit 0)
MODEL_PREP_INVOCATIONS=1 (canonical; exit 0)
GRAPH_INIT_INVOCATIONS=1 (canonical; exit 0)
WHOOSHD_LIFECYCLE_ACTIONS=0
MODEL_INVOCATIONS_DURING_TESTER_REACTIVATION=0
AUTHENTICATION_OPERATIONS=0
PROOF_THREADS_CREATED=0
USER_MESSAGES_CREATED=0
COMPLETION_REQUESTS=0
DEEPSEEK_REQUESTS_DURING_TESTER_REACTIVATION=0
WATCHDOG_ACTIVITY_DURING_TESTER_REACTIVATION=0
MANUAL_POSTGRES_MUTATIONS=0
MANUAL_REDIS_MUTATIONS=0
MANUAL_CHROMA_MUTATIONS=0
MANUAL_NEO4J_MUTATIONS=0
MANUAL_MODEL_ARTIFACT_MUTATIONS=0
```

The one-shot migration, seed, model-prep, and graph-init operations above were
normal lifecycle-owned startup behavior. No manual SQL, Redis command, Chroma
operation, Neo4j operation, artifact replacement, provider request, or model
generation was performed. The desired-up marker is present because the one
canonical `up` command owns that desired-state transition. The stack was left
running; no `tester-down`, Compose stop/down, or cleanup command was issued.

## Validation and documentation

The following checks passed in the proof-task checkout:

```text
git cat-file -e 62b97e33f005e184bbdfe402a7ae54eb3606ce12^{commit}
git merge-base --is-ancestor 62b97e33f005e184bbdfe402a7ae54eb3606ce12 HEAD
python3 scripts/validate_docs.py
git diff --check
```

Only this proof artifact was changed in the proof-task checkout. The active
Tester source retains its pre-existing dirty paths only; `.env.tester` remains
ignored and unstaged. `docs/architecture/00-current-state.md` remains
unchanged.

## Deferred next slice

Do not rerun activation in this task. The independent next task must diagnose
the `codexify-backend-runtime:latest`/bind-mounted Guardian worker import
coherence under operator authority, then perform a separately authorized
single reactivation proof. Only after a clean idle baseline with no initial
worker failure is proven may the one-attempt authenticated ordinary Qwen
completion task be rerun. Watchdog qualification remains deferred.
