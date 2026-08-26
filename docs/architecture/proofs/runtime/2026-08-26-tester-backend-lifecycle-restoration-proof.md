**Result:** `BLOCKED: TESTER_BACKEND_RESTART_OTHER_FAILURE`

**Backend health observation:** successful, but PASS is withheld because the
single canonical Compose backend start transitively executed the explicitly
forbidden one-shot migrator/seed path.

**ADR impact:** Aligned with existing Tester runtime doctrine and ADR-074; no
ADR change.

## Scope and boundary

This task restored the existing Postgres container and attempted one start of
the existing Tester backend. It did not rebuild, recreate, reconfigure, migrate
by direct command, qualify Guardian, execute Qwen, invoke DeepSeek, or perform
Watchdog work. The backend is now healthy, but the task cannot claim its strict
PASS because `docker compose start backend` automatically started declared
stopped one-shot dependencies, including `migrator` and `seed_defaults`.

The original diagnosis remains `TESTER_BACKEND_EXTERNAL_TERMINATION`; its
initiating actor remains unattributed.

```text
TESTER_POSTGRES_START_ATTEMPTS=1
TESTER_BACKEND_START_ATTEMPTS=1
WORKER_CHAT_RESTARTS_DURING_BACKEND_RESTORATION=0
WHOOSHD_RESTARTS_DURING_BACKEND_RESTORATION=0
MODEL_INVOCATIONS_DURING_BACKEND_RESTORATION=0
DEEPSEEK_REQUESTS_DURING_BACKEND_RESTORATION=0
WATCHDOG_ACTIVITY_DURING_BACKEND_RESTORATION=0
MANUAL_REDIS_CHROMA_MODEL_MUTATIONS=0
```

No frontend was started. No Guardian Qwen health/catalog qualification or
completion endpoint was called; the only backend HTTP probe was `/health`.

## Lineage and active runtime identity

- Required predecessor: `cb9779c629b02eb5d0a5072272d34ec23df54ebe`
  (`Diagnose tester backend exit 255`); `git cat-file -e` and
  `git merge-base --is-ancestor` passed.
- Task checkout: `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main`,
  branch `codex/diagnose-tester-fresh-chroma-failure`, at
  `cb9779c629b02eb5d0a5072272d34ec23df54ebe` before this proof.
- Actual active Tester source: `/Volumes/Dev_SSD/Codexify-main`, branch `main`,
  `6b383badb1eb5c5301df0c92c88215e605bf9fff`, clean, remote
  `https://github.com/Resonant-Jones/Codexify.git`.
- Compose project: `codexify_tester` using
  `docker-compose.yml`, `docker-compose.tester.yml`,
  `docker-compose.whooshd-deepseek.yml`, and `.env.tester`.

The backend remained the original container
`codexify_tester-backend-1`, image
`sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf`,
with the active source bind-mounted at `/app/backend`, `/app/guardian`,
`/app/codexify`, `/app/config`, and the existing data/model paths.

## Pre-restoration state and minimum prerequisites

At task start: backend and Postgres were `exited (255)` with restart count 0;
Redis was `running (healthy)` with restart count 0; `worker-chat` was running
with restart count 0; frontend and Neo4j were exited 255. Migrator, model-prep,
and graph-init were exited 0 from the prior lifecycle.

The active Compose definition declares backend dependencies of `db:
service_healthy`, `migrator`, `model-prep`, and `graph-init` completed
successfully. `graph-init` itself depends on healthy Neo4j, making Neo4j a
transitive startup prerequisite for this existing Compose contract. Redis is
not in backend `depends_on`, but was verified healthy and reachable from the
Compose network because it is required by the already-running worker/completion
topology. Frontend is unrelated to backend HTTP startup.

Redis verification was read-only: health was `healthy`, restart count remained
0, and a socket probe from `worker-chat` reached `redis:6379`.

## Postgres restoration

The existing `codexify_tester-db-1` container was started exactly once with
the active Compose project. Its original volume remained attached:

```text
volume: codexify_tester_pg_data
target: /var/lib/postgresql/data
volume mountpoint: /var/lib/docker/volumes/codexify_tester_pg_data/_data
```

After the start, Postgres was `running`, health `healthy`, restart count 0,
and `pg_isready -h localhost -U codexify -d Codexify` reported accepting
connections. Logs show PostgreSQL automatic WAL recovery from the prior
interruption and then `database system is ready to accept connections`; the
existing data directory was not initialized or replaced. No volume was
created/removed, and no direct query, migration, stamp, seed, or repair command
was run by this task.

## Backend identity and single start

Immediately before the backend start, the source remained at
`6b383badb1eb5c5301df0c92c88215e605bf9fff` and the existing container still
referenced image `sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf`.
The non-secret posture remained `local / qwen3.8-27b-4bit`, vendor `whooshd`,
base URL `http://host.docker.internal:8000/v1`, profile
`v1-whooshd-deepseek-web`, Redis host `redis:6379`, and Postgres host `db`.
No configuration changed.

One bounded non-inference Whoosh'd GET immediately before the start returned
the exact single model ID `qwen3.8-27b-4bit`; no restart or registry operation
was performed. The runtime still advertises `adapter=stub`, so executable
inference remains unproven.

The one backend lifecycle command was:

```text
docker compose --project-name codexify_tester --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml start backend
```

It began the existing backend container at
`2026-08-26T15:34:56.359647755Z`; no rebuild or recreation occurred. Compose
also started the stopped declared one-shot dependencies before the backend:

| Container | Start | Finish | Result |
| --- | --- | --- | --- |
| model-prep | `15:34:42.102364638Z` | `15:34:42.518987055Z` | exit 0 |
| migrator | `15:34:42.616520638Z` | `15:34:44.208537014Z` | exit 0 |
| graph-init | `15:34:54.240333837Z` | `15:34:55.847565672Z` | exit 0 |
| neo4j | `15:34:42.122809263Z` | running healthy | transitive dependency |

The migrator log explicitly contains `alembic ... upgrade heads` and
`Running seed defaults`. This was an automatic Compose dependency fan-out,
not a separately issued command, but it violates this task's explicit
no-migrator/no-seeding boundary. Therefore the strict lifecycle PASS is
withheld and the permitted classification is:

```text
BLOCKED: TESTER_BACKEND_RESTART_OTHER_FAILURE
```

No second backend start, retry, rollback, or cleanup lifecycle operation was
performed after this boundary was observed.

## Backend health result

The single backend start itself succeeded:

```text
state=running
restart_count=0
health=healthy
listener=127.0.0.1:8889 (Docker proxy PID 58541)
GET http://127.0.0.1:8889/health -> HTTP 200
```

The response reported `status=ok`, profile
`v1-whooshd-deepseek-web`, `valid=true`, no profile mismatches, and selected
provider `local`. This is only the canonical base startup/readiness proof; no
LLM-health, catalog, chat-health, completion, or inference endpoint was called.

## Boundary accounting and deferred action

The frontend remained stopped. Neo4j was started only because it is a
transitive prerequisite of the active backend `graph-init` dependency; it was
not independently restored as a feature. The canonical Whoosh'd registry and
process were untouched. The only Whoosh'd operation in this task was the
bounded inventory GET described above.

No model request, warmup, chat message, completion, DeepSeek request, Watchdog
attempt, GitHub I/O, Command Bus action, Build Loop action, Redis flush, Chroma
operation, Postgres data operation, or model-artifact operation occurred.

The task checkout's unrelated
`guardian/workers/watchdog_review_worker.py` remained untouched and unstaged;
`docs/architecture/00-current-state.md` remained unchanged.

The backend is usable for the next separately authorized qualification, but
this proof must not be treated as `TESTER_BACKEND_LIFECYCLE_RESTORED` because
the one start command reran the forbidden migrator/seed path. The next slice
requires an explicit decision on the Compose dependency fan-out (or a
canonical no-dependency existing-container start) before another lifecycle
proof is claimed. No second backend attempt is authorized by this task.

## Validation

```text
git cat-file -e cb9779c629b02eb5d0a5072272d34ec23df54ebe^{commit}
git merge-base --is-ancestor cb9779c629b02eb5d0a5072272d34ec23df54ebe HEAD
git -C /Volumes/Dev_SSD/Codexify-main status --short --branch
git -C /Volumes/Dev_SSD/Codexify-main rev-parse HEAD
docker compose --project-name codexify_tester ... config --no-interpolate
docker compose --project-name codexify_tester ... ps -a
docker inspect [backend, db, redis, worker-chat, neo4j, frontend]
docker volume inspect codexify_tester_pg_data
docker exec codexify_tester-worker-chat-1 python -c 'redis socket probe'
docker exec codexify_tester-db-1 pg_isready -h localhost -U codexify -d Codexify
docker compose --project-name codexify_tester ... start db
docker compose --project-name codexify_tester ... start backend
docker logs --timestamps --since 2026-08-26T15:34:37Z codexify_tester-backend-1
docker logs --timestamps --since 2026-08-26T15:34:37Z codexify_tester-migrator-1
lsof -nP -iTCP:8889 -sTCP:LISTEN
curl --max-time 5 http://127.0.0.1:8889/health
python3 scripts/validate_docs.py
git diff --check
```

`python3 scripts/validate_docs.py` passed and `git diff --check` passed before
staging. Only this proof file is task-attributable.
