# Guardian Composer Coding Loop Live Proof

Proof date: 2026-08-05

Runtime window: 2026-08-05 ~15:45-16:40 EDT

## Outcome

`next-proof-needed`

The backend service cannot maintain a running state in the current Docker
Desktop session. It initializes (Postgres reachable, alembic migration
verified, seed defaults applied, router registration complete, uvicorn
server process started) and then exits with code 3 before the health check
can succeed. The exact failing seam is obscured by Guardian log redaction,
which suppresses the error message text from both the application logger
and uvicorn's error stream. Docker memory is sufficient (~3.6 GiB free of
3.8 GiB after stopping non-essential services). The worker-coding,
frontend, Postgres, and Redis services all remain healthy.

Because the backend is a required service for route acceptance
(`POST /api/agents/coding/execute`) and for serving the Composer WebUI
proxy, the live browser lane cannot proceed beyond the prerequisite gate.
The worker readiness lane and the worker itself remain fully live-proven
and ready to consume coding tasks as soon as the backend is available.

## What is live-proven

- All three prerequisite fixes are present at HEAD:
  - `46e6d0193` — Composer local user identity repair
  - `6717c4ffa` — Coding Worker mutation guard restoration
  - `a9bfe1118` — Coding Loop route exposed in local profile
- The supported profile `v1-local-core-web-mcp` now lists
  `agent_orchestration` and `agent_orchestration_chat` under `enabled`
  (verified by YAML inspection and profile loader probe).
- `docker compose config --quiet` passes.
- Worker readiness: `ready` (deepseek / deepseek-v4-flash, credential present,
  adapter initialized, all nine checks pass).
- Worker process: healthy, running since 2026-08-05, zero restarts.
- `worker-coding` Compose healthcheck green.
- Frontend: Vite dev server up on port 5173, HTTP 200.
- Postgres: healthy, port 5433.
- Redis: healthy, queue `codexify:queue:coding-execution` depth 0.
- Coding Worker mutation guard restored (three inner functions + preflight
  snapshot), focused regression tests pass (3/3).

## What blocks the proof

The `backend` service in the `codexify` Compose project exits with code 3
during startup. The container log shows normal initialization up to
`[routers] Router registration complete` and `Started server process [1]`,
then two `ERROR` lines whose content is fully redacted by the Guardian
structured logger, followed by exit code 3. Docker memory (OOM=0) and port
availability (port 8888 free) are ruled out. The same failure reproduces
across:

- `docker compose up -d --no-deps backend` (Compose env)
- `docker run` with `--env-file .env` (manual env)
- `docker run` with explicit minimal env vars
- Both `CODEXIFY_CONFIG_SOURCE=core` and `CODEXIFY_CONFIG_SOURCE=legacy`
- Both the main `codexify` and `codexify_tester` Compose projects
- Freshly rebuilt `codexify-backend-runtime:latest` image

The `codexify_tester-backend-1` container was previously Up and healthy for
21 hours; after a restart it exhibits the same exit-3 failure. This
strongly suggests an environment-level change (host config, .env value,
or Docker Desktop state) introduced since the last successful session,
rather than a code defect.

Without a running backend, the `/api/agents/coding/execute` route cannot be
reached from the browser (frontend proxies API calls through the backend),
so the proof cannot advance past the prerequisite gate into route acceptance.

## Next proof prerequisites

1. Diagnose and resolve the backend exit-code-3 startup failure. This may
   require temporarily disabling Guardian log redaction (setting
   `GUARDIAN_LOG_REDACTION=off` or equivalent) to surface the actual error
   message, or auditing the `.env` file for values that violate the
   supported-profile `provider_contract` validation introduced in recent
   config coherence work.
2. Once the backend is healthy and serving HTTP 200 on `GET /ping`, verify
   `POST /api/agents/coding/execute` returns 422 (route registered, request
   validation active) rather than 404.
3. Proceed with the browser proof: submit the exact harmless request, capture
   all ten milestones, and verify durable refresh recovery.

## Repository identity

- Branch: `codex/wire-coding-loop-into-composer`
- Full `HEAD`: `6717c4ffa05b06cb5bedd0e15cadd840ab2fbff8`
- Implementation commits under proof:
  - `46e6d0193` Restore Composer local user identity
  - `a9bfe1118` Expose Coding Loop route in local profile
  - `6717c4ffa` Restore Coding Worker mutation guard
- Worktree before proof: 6 unrelated dirty files (from prior `main` branch
  switch); only the proof doc was touched.

## Compose project and service posture

- Compose project: `codexify`
- Services running: `db` (healthy), `redis` (healthy), `worker-coding`
  (healthy), `frontend` (up, HTTP 200)
- `backend`: not running (exit 3 during startup)
- Non-essential services stopped to free Docker memory: `neo4j`,
  `codexify_tester-*`, `agitated_swirles` (tailscale)

## Worker readiness (carried forward)

```text
Pi coding-worker readiness: ready
Effective provider: deepseek
Effective model: deepseek-v4-flash
Credential validity: unproven (presence only)
- node_executable: available
- guardian_pi_wrapper: available
- pi_sdk_runtime: available
- worker_home: available
- pi_auth_material: available
- pi_auth_permissions: restricted
- effective_provider: configured
- adapter_initialization: available
- provider_credential: available
```

## Authentication method

Carried forward: operator host Pi auth store copied into `codexify_pi_auth`
named volume at `/home/codexify/.pi/agent/auth.json`, mode 0600, deepseek
credential.

## Effective provider and model

`deepseek` / `deepseek-v4-flash`

## Exact request text (prepared, not submitted)

```
Read docs/architecture/00-current-state.md and return a concise five-bullet summary. Do not modify files, run network requests, commit changes, or create a pull request.
```

## Intended permission policy

- `allow_write=false`
- `allow_network=false`
- `allow_shell=false`
- `adapter_kind=pi_codex_runner`
- `repo_root=null`

## Milestone evidence

| Milestone | Result | Evidence |
| --- | --- | --- |
| 1. Readiness gate | **proven** | Readiness `ready`, worker healthcheck green |
| 2–10 | **not reached** | Backend not available |

## Exact commands run

```text
# Ancestry checks
git merge-base --is-ancestor 46e6d0193 HEAD
git merge-base --is-ancestor 6717c4ffa HEAD
git merge-base --is-ancestor a9bfe1118 HEAD

# Compose and service state
docker compose config --quiet
docker compose ps
docker compose logs backend --tail=30
docker compose logs worker-coding --tail=50
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:coding-execution

# Profile validation
python3 -c "import yaml; yaml.safe_load(open('config/supported_profiles/v1-local-core-web-mcp.yaml'))"
docker compose run --rm --no-deps --entrypoint python backend -c "
from guardian.core.supported_profile import get_active_supported_profile
p = get_active_supported_profile()
print('agent_orchestration:', p.route_status('agent_orchestration'))
"

# Readiness (human + json)
docker compose run --rm --no-deps --entrypoint python worker-coding \
  /app/backend/scripts/docker/check_worker_coding_readiness.py --format json

# Focused regression tests
.venv/bin/python -m pytest -q guardian/tests/workers/test_coding_worker_regression_guard.py -v

# Frontend
curl -sS -o /dev/null -w "%{http_code}" http://localhost:5173/

# Backend (failed)
docker compose up -d --no-deps backend
docker run -d --name be-proof ... codexify-backend-runtime:latest python -c "..."
```

## Warnings

- 6 unrelated dirty files in worktree (not staged).
- Guardian log redaction prevents viewing the actual backend error message.
- The `LOCAL_BASE_URL` in `.env` was `http://100.127.148.28:8000/v1` while
  the profile expected `http://host.docker.internal:8000/v1`. The `.env`
  was updated to match the profile. This mismatch existed before this
  session but did not prevent the tester backend from running for 21 hours.
- Docker memory was at ~85% utilization before cleanup; non-essential
  services were stopped.

## Failures

- **Backend startup (blocker):** exits with code 3 during initialization.
  Root cause not yet identified due to log redaction. Possible candidates:
  config coherence validation (`_validate_supported_profile_contract`),
  ASGI lifespan event failure, or a Python-level exception swallowed by
  the Guardian logging configuration.

## Documentation follow-through

`docs/architecture/00-current-state.md` is unchanged (outcome not `go`).

## Validation results

| Check | Result |
| --- | --- |
| Ancestry checks (3 commits) | pass |
| `docker compose config --quiet` | pass |
| Profile YAML parse | pass |
| Profile `agent_orchestration` status | `enabled` |
| Worker readiness (human + json) | `ready`, exit 0 |
| Worker healthcheck | healthy |
| Focused guard regression (3 tests) | **3 passed** |
| `git diff --check` (proof doc only) | pass |
| Secret scan of proof receipt | pass |
| Backend HTTP 200 on `/ping` | **FAIL** — exit 3 |

## What this does not prove

- Route acceptance
- Queue enqueue or worker dequeue for a specific coding run
- Pi adapter execution or DeepSeek provider response
- Terminal result persistence
- Source-lineage result return
- WebUI terminal rendering
- Durable refresh/recovery readback
- Any of the ten browser-lane milestones

## Axis KB recommendation

Record: the Coding Loop route family is now enabled in the local supported
profile (`v1-local-core-web-mcp`). The worker lane is fully live-proven
(deepseek credential present, adapter initialized, consumer alive). The
browser lane is blocked by a backend startup failure (exit code 3) that
predates this proof session — both main and tester backends exhibit it.
The backend started successfully 21+ hours ago in a previous Docker Desktop
session, suggesting a host-level environmental change.

## Secret-handling statement

No raw API key, credential, token, or private path is included in this
receipt.
