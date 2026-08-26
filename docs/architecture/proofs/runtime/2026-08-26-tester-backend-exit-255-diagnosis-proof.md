# Tester backend exit-255 diagnosis proof

**Result:** `TESTER_BACKEND_EXIT_255_CAUSE_IDENTIFIED`

**First causal classification:** `TESTER_BACKEND_EXTERNAL_TERMINATION`

**ADR impact:** Aligned with ADR-074 and existing operator-truth doctrine; no ADR change.

## Scope and execution boundary

This proof diagnoses the already-stopped Tester backend. It does not start,
restart, recreate, rebuild, or otherwise modify the backend, image, active
Tester source, `.env.tester`, Postgres, Redis, Chroma, Whoosh'd, launchd,
DeepSeek, or Watchdog. The diagnostic window ended at `2026-08-26T15:03:10Z`.

```text
TESTER_BACKEND_DIAGNOSTIC_RESTARTS=0
WORKER_CHAT_RESTARTS_DURING_BACKEND_DIAGNOSIS=0
WHOOSHD_RESTARTS_DURING_BACKEND_DIAGNOSIS=0
MODEL_INVOCATIONS_DURING_BACKEND_DIAGNOSIS=0
DEEPSEEK_REQUESTS_DURING_BACKEND_DIAGNOSIS=0
WATCHDOG_ACTIVITY_DURING_BACKEND_DIAGNOSIS=0
MANUAL_POSTGRES_REDIS_CHROMA_MODEL_MUTATIONS=0
```

No Guardian health/catalog qualification, completion, chat task, provider request,
DeepSeek request, Watchdog operation, GitHub I/O, Command Bus action, or Build Loop
action was issued.

## Prerequisite and active identities

- Required predecessor: `747ad54462b92240ba88bd869bc72d2c14f6704e`
  (`Qualify Guardian Qwen health`); `git cat-file -e` and
  `git merge-base --is-ancestor` passed.
- Task checkout: `codex/diagnose-tester-fresh-chroma-failure` at
  `747ad54462b92240ba88bd869bc72d2c14f6704e`, `ahead 1, behind 12`.
- Actual active source: `/Volumes/Dev_SSD/Codexify-main`, `main`,
  `6b383badb1eb5c5301df0c92c88215e605bf9fff`,
  `main...origin/main [behind 17]`, clean, remote
  `https://github.com/Resonant-Jones/Codexify.git`.

The active Compose project is `codexify_tester`, using `docker-compose.yml`,
`docker-compose.tester.yml`, `docker-compose.whooshd-deepseek.yml`, and
`.env.tester`. Relevant containers are `codexify_tester-backend-1`,
`codexify_tester-db-1`, `codexify_tester-redis-1`, and
`codexify_tester-worker-chat-1`.

## Backend identity and stopped lifecycle

```text
container ID: 475bb0079346fe3e7454f2056fa1d451b73fb742472a5bbf4bdc1b91acffa8e5
configured image: codexify-backend-runtime:latest
actual image ID: sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf
image created: 2026-08-25T14:05:41.611173001Z
working directory: /app
state: exited; exit code: 255
started: 2026-08-25T14:22:20.523380588Z
finished: 2026-08-26T10:02:41.971699042Z
restart count: 0; restart policy: no
OOM killed: false; container error: empty
health state: starting; retained health-log entries: 0
```

The container has no PID and no listener remains on `127.0.0.1:8889`.
The actual image remains the current `codexify-backend-runtime:latest` image
(`sha256:2508...`). Its historical `com.docker.compose.image` label names
`sha256:2d02...`, now absent from Docker. That is stale image-tag lineage only:
the container was pinned to `sha256:2508...`, with no evidence that the label
caused exit 255.

## Startup code, source coherence, and logs

The immutable `python -c` entrypoint only fails early when a required embeddings
directory is missing; that path emits an error and exits `1`. Its effective
`LOCAL_EMBEDDINGS_REQUIRED=0` value rules it out. It then executes the
bind-mounted script `/app/backend/scripts/docker/run_backend.py` from:

```text
/Volumes/Dev_SSD/Codexify-main/backend  -> /app/backend
/Volumes/Dev_SSD/Codexify-main/guardian -> /app/guardian and /app/codexify
/Volumes/Dev_SSD/Codexify-main/config   -> /app/config (read-only)
```

The script orders Postgres wait, required-table/Alembic schema probe, default
seed, then `execve` of Uvicorn for `guardian.guardian_api:app`. The independent
migrator completed successfully (`exit=0`,
`2026-08-25T14:22:18.880132379Z` to `14:22:20.205513921Z`).

The backend remained started for about 19 hours 40 minutes. That rules out
container-creation failure and the immediate embedding precheck. The timestamped
backend Docker logs from `2026-08-26T09:55:00Z` onward contained no retained
records; a bounded final-tail search found no error, traceback, shutdown line,
or `CODEXIFY_STARTUP_FAILURE_RECEIPT`.

`guardian.guardian_api` wraps only unhandled application-lifespan startup
exceptions in that receipt boundary. Its absence does not prove every inner
phase succeeded, but it excludes a recorded unhandled lifespan-startup error as
the available first-cause evidence. The last evidence-backed successful phase is
**container process launch/long-running lifecycle after the entrypoint**; the
first failed phase is **external lifecycle termination**, not application startup.

## First causal evidence

The backend did not stop in isolation. Four unrelated long-lived services exited
`255` in the same approximately 38 ms interval, all with empty Docker error
fields and `OOMKilled=false`:

| Service | Finished at (UTC) | Exit | Restart policy |
| --- | --- | --- | --- |
| backend | `10:02:41.971699042` | `255` | `no` |
| db (Postgres) | `10:02:41.970122000` | `255` | `no` |
| frontend | `10:02:42.008126209` | `255` | `no` |
| neo4j | `10:02:42.007834709` | `255` | `no` |

Services with `unless-stopped` began new lifecycles about three seconds later:

| Service | Prior finished at (UTC) | Current started at (UTC) | State |
| --- | --- | --- | --- |
| redis | `10:02:41.991051667` | `10:02:45.053482419` | running, healthy |
| tailscale-codexify-test | `10:02:41.986467750` | `10:02:45.079078002` | running |
| worker-chat | `10:02:42.007793542` | `10:02:45.078666210` | running |

Redis logs record a fresh server start at `10:02:45.412Z`; `worker-chat` records
a new startup at `10:03:18Z`. These are consequences of the project-level
lifecycle event, not backend startup evidence.

An import, profile validation, migration/schema check, Chroma startup, provider
validation, database reachability, HTTP bind conflict, or entrypoint return cannot
independently produce this synchronized multi-image transition. The narrow
classification is `TESTER_BACKEND_EXTERNAL_TERMINATION`. Docker retained no event
that identifies the initiating operator, Docker-engine, or host event, so none is
claimed.

## Effective configuration and dependency boundary

The failed backend's non-secret effective configuration was:

| Setting | Value |
| --- | --- |
| `CODEXIFY_SUPPORTED_PROFILE` | `v1-whooshd-deepseek-web` |
| `CODEXIFY_CONFIG_SOURCE` / `LLM_PROVIDER` | `core` / `local` |
| local model | `qwen3.8-27b-4bit` |
| local vendor/base URL | `whooshd` / `http://host.docker.internal:8000/v1` |
| cloud/local-only/egress | `true` / `false` / `deepseek` |
| database | `postgresql://<redacted>@db:5432/Codexify` |
| Redis | `redis://redis:6379/0` |
| vector store | `chroma`, `./.chroma`, `codexify_vault_supported` |

The active profile contract and local-provider validation require this local
Whoosh'd posture and `LOCAL_BASE_URL`; the observed values meet those static
requirements. `VectorStore` is constructed only after configuration and database
initialization. No Chroma/vector failure appears in the failed-lifecycle evidence,
so no Chroma investigation or mutation was opened.

Postgres is stopped as part of the simultaneous lifecycle; no database query,
migration, seed, stamp, or repair was run. Redis is now running and healthy; no
Redis mutation was run. Migrator and graph-init remain exit `0` from the original
lifecycle.

Whoosh'd remains launchd `running`, active count `1`, runs `1`, PID `50696`. One
non-inference inventory GET returned exact `qwen3.8-27b-4bit` with `mlx_vlm` /
`mlx` metadata. A later three-second inventory GET timed out with the PID unchanged;
no restart, follow-up repair, model request, or inference was attempted because it
is not causal to the already-recorded backend stop.

```text
WHOOSHD_EXECUTION_ADAPTER=stub
QWEN_REAL_INFERENCE_STATUS=UNPROVEN
```

## Deferred repair seam

The owning surface is the active `codexify_tester` **Compose/Docker lifecycle**,
not Guardian source, Tester configuration, the backend image, Chroma, provider
routing, or model authority.

A separate operator-authorized repair task must first establish the cause and
intent of the external Docker/Compose interruption, then restore only stopped
long-lived prerequisites (at minimum Postgres and backend) from their existing
configuration and image. It may authorize at most one bounded backend
startup/recreate attempt and must stop after proving direct backend HTTP
availability and startup health. It must not fold Guardian health/catalog
qualification, Qwen inference, DeepSeek, Watchdog, or source repair into that
lifecycle task.

## Worktree, release truth, and validation

At preflight and before this proof was written, the task checkout had no changed
or staged files. `guardian/workers/watchdog_review_worker.py` was absent from the
diff and staging area; this diagnosis did not edit, stage, restore, or reformat it.
`docs/architecture/00-current-state.md` remains unchanged. This is branch/runtime
diagnostic evidence only and does not claim current-main supported-Compose closure.

```text
git cat-file -e 747ad54462b92240ba88bd869bc72d2c14f6704e^{commit}
git merge-base --is-ancestor 747ad54462b92240ba88bd869bc72d2c14f6704e HEAD
git status --short --branch; git rev-parse HEAD; git branch --show-current
git -C /Volumes/Dev_SSD/Codexify-main status --short --branch
git -C /Volumes/Dev_SSD/Codexify-main rev-parse HEAD
git -C /Volumes/Dev_SSD/Codexify-main branch --show-current
git -C /Volumes/Dev_SSD/Codexify-main remote -v
docker compose --project-name codexify_tester ... ps -a
docker inspect [Tester backend and dependency containers]
docker logs --timestamps --since 2026-08-26T09:55:00Z codexify_tester-backend-1
docker logs --timestamps --tail 160 codexify_tester-worker-chat-1
docker logs --timestamps --tail 120 codexify_tester-redis-1
docker events --since 2026-08-26T09:55:00Z --until 2026-08-26T10:10:00Z
docker image inspect codexify-backend-runtime:latest sha256:2508...
curl --max-time 3 http://127.0.0.1:8000/v1/models
launchctl print system/com.resonant.whooshd
```

`python3 scripts/validate_docs.py` passed. `git diff --check` passed before
staging. The narrow proof commit is recorded in the task closeout.
