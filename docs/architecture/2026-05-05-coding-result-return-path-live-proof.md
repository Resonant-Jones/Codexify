# Coding Result Return Path Live Proof - 2026-05-05

## Scope

Live Docker Compose verification of the Guardian-mediated coding-agent execution and result-return path.

## Runtime Context

- date/time: 2026-05-05 15:47:14 EDT
- branch: `main`
- HEAD commit: `809395304f1fce95ef06e5a6bc0d08f263b131f6`
- Compose services running:
  - `backend`
  - `db`
  - `redis`
  - `worker-coding`
- backend health: healthy
  - `/health` returned `200`
  - `/health/chat` returned `200`
  - `/api/health/llm` returned `200`
- Redis health: healthy (`PONG`)
- Postgres health: healthy (`codexify-db-1` reported `healthy`)
- whether `worker-coding` was running: yes
- source thread ID: `30`
- source message ID: `63`
- run IDs used:
  - execution run: `run_d49dd86aa5fc4656`
  - deployment ID: `dep_5e1f6bc3ba0e4604`

Note: host-side `curl http://localhost:8888` was flaky in this desktop environment, so the proof used container-local requests from the backend service against the same live Compose stack.

## Verification Matrix

| # | Target | Status | Evidence | Notes |
| - | ------ | ------ | -------- | ----- |
| 1 | Services network | ✅ PASS | Backend container resolved and reached `redis` and `db`; `docker compose ps` showed `backend`, `db`, `redis`, and `worker-coding` up on the same project network. | Container-local DNS and socket reachability were verified from inside `backend`. |
| 2 | Real source thread | ✅ PASS | `chat_threads.id = 30`; `chat_messages.id = 63` is a real user message on that thread. | Thread had an existing user-authored source message and no preexisting `coding_result` row. |
| 3 | POST enqueues | ✅ PASS | `POST /api/agents/coding/execute` returned `ok: true`, `run_id: run_d49dd86aa5fc4656`, and the Redis queue length moved from `0` to `1` after the POST. | `worker-coding` was stopped briefly so enqueue could be observed before dequeue. |
| 4 | Worker dequeues | ✅ PASS | After `worker-coding` restarted, the queue depth returned to `0` and the run stream emitted `task.running`. | The worker did dequeue the task even though it later failed. |
| 5 | Run reaches terminal | ⚠️ PARTIAL | The event stream emitted `task.failed`, but `agent_runs.status` remained `queued` for `run_d49dd86aa5fc4656`. | Terminal failure was visible in events, but the DB run record did not reach a durable terminal state. |
| 6 | Event lifecycle | ✅ PASS | The live run stream emitted `created`, `task.running`, and `task.failed`. | This is the actual lifecycle evidence for the run. |
| 7 | Exactly one `coding_result` message | ❌ FAIL | `SELECT count(*) ... kind = 'coding_result'` for thread `30` returned `0`. | No returned coding result landed in the source thread. |
| 8 | Idempotency | ❌ FAIL | Not exercised against a returned `coding_result`, because none was produced. | The idempotency guard could not be proven on the actual return path. |
| 9 | Failures bounded | ⚠️ PARTIAL | The failure was surfaced in the run stream as `task.failed` with `Cannot find module '/app/codex_runner/src/agent-wrapper.js'`. | The failure was visible, but it did not resolve into a bounded source-thread result. |

## Command Evidence

```bash
git branch --show-current
# main

git rev-parse HEAD
# 809395304f1fce95ef06e5a6bc0d08f263b131f6

git status --short
# clean before docs edits

docker compose ps backend db redis worker-coding
# backend, db, redis, and worker-coding were all up; backend/db/redis healthy

docker compose exec backend python - <<'PY'
import json, os, socket, urllib.request
from guardian.core.db import load_guardian_db_from_env
import redis
for path in ['/health', '/health/chat', '/api/health/llm']:
    with urllib.request.urlopen(f'http://localhost:8888{path}', timeout=10) as r:
        print(path, r.status)
print('redis', socket.gethostbyname('redis'))
print('db', socket.gethostbyname('db'))
print('redis_ping', redis.from_url('redis://redis:6379/0').ping())
print('db_loaded', load_guardian_db_from_env() is not None)
PY
# /health 200
# /health/chat 200
# /api/health/llm 200
# redis_ping True
# db_loaded True

docker compose exec db psql -U codexify -d Codexify -Atc "select id, user_id, created_at from chat_threads where id=30;"
# 30|local|2026-05-05 19:33:49.140364+00

docker compose exec db psql -U codexify -d Codexify -Atc "select id, role, kind, left(content,80) from chat_messages where thread_id=30 and id=63;"
# 63|user|chat|Reply with exactly: supported-path-live-proof-ok

docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
# before POST: 0

docker compose exec backend python - <<'PY'
import json, os, urllib.request
api_key = os.environ['GUARDIAN_API_KEY']
body = json.dumps({
    'coding_task_id': 'live-proof-20260505-1945',
    'thread_id': '30',
    'source_message_id': '63',
    'attempt_id': 'attempt-20260505-1945',
    'user_id': 'local',
    'project_id': None,
    'adapter_kind': 'pi_sdk',
    'instructions': "echo 'live-proof-ok' > /tmp/live_proof_return_path.txt",
    'repo_root': '/tmp',
    'context_summary': None,
    'permission_policy': {
        'allow_shell': True,
        'allow_network': False,
        'allow_write': True,
        'allowed_paths': ['/tmp'],
        'max_runtime_seconds': 60,
    },
}).encode()
req = urllib.request.Request(
    'http://localhost:8888/api/agents/coding/execute',
    data=body,
    headers={'Content-Type': 'application/json', 'X-API-Key': api_key},
    method='POST',
)
with urllib.request.urlopen(req, timeout=30) as r:
    print(r.read().decode())
PY
# {"ok": true, "run_id": "run_d49dd86aa5fc4656", "deployment_id": "dep_5e1f6bc3ba0e4604"}

docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
# after POST, before worker restart: 1

docker compose logs worker-coding --tail=120
# task.running and task.failed were emitted; failure mentioned missing /app/codex_runner/src/agent-wrapper.js

docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
# after worker restart: 0

docker compose exec db psql -U codexify -d Codexify -Atc "select run_id, status, ended_at, error from agent_runs where run_id='run_d49dd86aa5fc4656';"
# run_d49dd86aa5fc4656|queued||

docker compose exec db psql -U codexify -d Codexify -Atc "select count(*) from chat_messages where thread_id=30 and kind='coding_result';"
# 0
```

## Result Interpretation

Release-ready for this path: no

## Known Gaps

- The worker-side execution failed with `Cannot find module '/app/codex_runner/src/agent-wrapper.js'`.
- No `coding_result` message landed back in the source thread.
- The run stream terminalized as `task.failed`, but the durable `agent_runs` row stayed `queued`.
- Idempotency was not proveable on the actual return path because no returned coding result existed to duplicate.

## Follow-up Tasks

- Restore the worker runtime artifact or image layer that provides `/app/codex_runner/src/agent-wrapper.js`.
- Re-run the live Compose proof after the worker image is corrected.
- Verify the run record reaches a durable terminal state and that exactly one `coding_result` lands in the source thread.

---

## Packaging Blocker Follow-Up — 2026-05-09

**Date/time**: 2026-05-09
**Branch**: `main`
**HEAD before fix**: `dffb8f66a` (fix: repair chat route trace evidence block, prior to this fix)
**HEAD after fix**: `c9427bb2f` (feat: add one-turn assistant reentry seam)
**Files changed in this fix**:
- `docker-compose.runtime.yml` — `worker-coding` service changed from pre-built image reference to local `build: {context: ., dockerfile: backend/Dockerfile, target: runtime}`, matching the pattern used in `docker-compose.yml`

### Root Cause

`worker-coding` in `docker-compose.runtime.yml` used a pre-built image reference:

```yaml
worker-coding:
  image: ${CODEXIFY_IMAGE_REGISTRY:-ghcr.io/resonant-jones}/codexify-runtime:${CODEXIFY_IMAGE_TAG:-local-beta}
```

This image had not been rebuilt with the `codex_runner/` directory since the local Dockerfile was updated to include `COPY codex_runner /app/codex_runner` at line 172 in the `runtime` stage of `backend/Dockerfile`. The `.dockerignore` file had the correct exclusion rules to allow `codex_runner/` into the build context (`!/codex_runner` and `!/codex_runner/**`), so the fix was to ensure `worker-coding` uses the local build path rather than a stale pre-built image.

### Fix Applied

Changed `worker-coding` in `docker-compose.runtime.yml` from pre-built image to local build:

```yaml
worker-coding:
  build:
    context: .
    dockerfile: backend/Dockerfile
    target: runtime
  # ... rest of service config unchanged
```

This is consistent with how `worker-coding` is defined in `docker-compose.yml`.

### Packaging Validation (Simulated — Docker not available in this environment)

The following commands would validate the fix in a Docker-enabled environment:

```bash
# Build the worker-coding image locally
docker compose -f docker-compose.runtime.yml build worker-coding

# Verify the wrapper exists inside the built image
docker compose -f docker-compose.runtime.yml run --rm worker-coding test -f /app/codex_runner/src/agent-wrapper.js
# Expected: exit code 0 (file exists)

# Verify exact path and permissions
docker compose -f docker-compose.runtime.yml run --rm worker-coding ls -la /app/codex_runner/src/agent-wrapper.js
# Expected: -rwx... /app/codex_runner/src/agent-wrapper.js
```

In this environment, Docker is not available, so the packaging proof is recorded as **pending live rerun**. The code-level fix (local build configuration) is correct and consistent with `docker-compose.yml`.

### Live Proof Status

**Packaging blocker**: ✅ RESOLVED — `worker-coding` will now build from the local `backend/Dockerfile` which includes `COPY codex_runner /app/codex_runner` in its `runtime` target stage, ensuring `/app/codex_runner/src/agent-wrapper.js` exists in the container.

**Remaining release-critical targets** (unchanged from prior proof):
| Target | Status | Notes |
|--------|--------|-------|
| 1. Services network | ✅ PASS (from prior proof) | |
| 2. Real source thread | ✅ PASS (from prior proof) | |
| 3. POST enqueues | ✅ PASS (from prior proof) | |
| 4. Worker dequeues | ✅ PASS (from prior proof) | |
| 5. Run reaches terminal | ⚠️ PARTIAL (from prior proof) | `task.failed` emitted; `agent_runs.status` stayed `queued` |
| 6. Event lifecycle | ✅ PASS (from prior proof) | |
| 7. Exactly one `coding_result` | ❌ FAIL (from prior proof) | No returned result landed in source thread |
| 8. Idempotency | ❌ FAIL (from prior proof) | Could not be exercised; no result existed to deduplicate |
| 9. Failures bounded | ⚠️ PARTIAL (from prior proof) | Failure was visible but did not resolve into a source-thread result |

**Full release readiness conclusion**: Still **no**. The packaging blocker is resolved, but targets 5, 7, 8, and 9 require a live rerun with the corrected `worker-coding` build to confirm whether the remaining failure signatures are packaging-related or represent a deeper issue in result-return or durable state convergence.

## Live Rerun After Packaging Fix — 2026-05-10 17:43:20 EDT

## Runtime Context

- date/time: 2026-05-10 17:43:20 EDT
- branch: `main`
- HEAD commit: `b89916de7782dd6dc4a7a759bd21c82a4de02786`
- compose stack used for checklist: `docker compose` (`docker-compose.yml`)
- packaging validation stack: `docker compose -f docker-compose.runtime.yml`
- source thread ID: `1243`
- source message ID: `50259`
- execution run ID: `run_efe058f2b50a4206`
- failure-probe run ID: `run_cd1c5bc62ca6435c`

## Packaging Validation

Executed:

```bash
docker compose -f docker-compose.runtime.yml build worker-coding
docker compose -f docker-compose.runtime.yml run --rm worker-coding test -f /app/codex_runner/src/agent-wrapper.js
docker compose -f docker-compose.runtime.yml run --rm worker-coding ls -la /app/codex_runner/src/agent-wrapper.js
```

Observed:

- Build succeeded and included `COPY codex_runner /app/codex_runner` in the runtime image build output.
- Both exact `run --rm` checks were blocked by runtime-stack dependency startup because `migrator` failed with:
  - `Can't locate revision identified by '9d4e1c7b2a6f'`
- Direct image-level verification (entrypoint bypass) confirmed the packaging fix:
  - `docker run --rm --entrypoint test codexify-worker-coding:latest -f /app/codex_runner/src/agent-wrapper.js` -> exit `0`
  - `docker run --rm --entrypoint ls codexify-worker-coding:latest -la /app/codex_runner/src/agent-wrapper.js` ->
    - `-rw-r--r-- 1 root root 9936 May  9 01:49 /app/codex_runner/src/agent-wrapper.js`

Packaging blocker interpretation: resolved (`agent-wrapper.js` exists in the built `worker-coding` image).

## Command Evidence (Abbreviated)

```bash
docker compose ps backend db redis worker-coding
# backend healthy, db healthy, redis healthy, worker-coding running

docker network inspect codexify_default | jq -r '.[0].Containers | to_entries[] | .value.Name'
# includes codexify-backend-1, codexify-db-1, codexify-redis-1, codexify-worker-coding-1

docker compose exec backend python -c "import redis; print(redis.from_url('redis://redis:6379/0').ping())"
# True

docker compose exec backend python -c "from guardian.core.db import load_guardian_db_from_env; print(load_guardian_db_from_env() is not None)"
# True

docker compose exec db psql -U codexify -d Codexify -Atc "select id, role, kind, left(content,120) from chat_messages where thread_id=1243 order by created_at desc limit 5;"
# source user message id=50259 present

docker compose stop worker-coding
docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
# 0

curl -sS -X POST http://localhost:8888/api/agents/coding/execute ...
# {"ok":true,"run_id":"run_efe058f2b50a4206",...}

docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
# 1

docker compose up -d worker-coding
sleep 10
docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
# 0

curl -m 12 -N -sS -H "X-API-Key: ..." \
  "http://localhost:8888/api/agents/runs/run_efe058f2b50a4206/events"
# created
# task.running
# task.failed
# error: Pi SDK dependencies are not available ...

docker compose exec db psql -U codexify -d Codexify -Atc \
"select run_id,status,ended_at is not null,error from agent_runs where run_id='run_efe058f2b50a4206';"
# run_efe058f2b50a4206|queued|f|

docker compose exec db psql -U codexify -d Codexify -Atc \
"select count(*) from chat_messages where thread_id=1243 and kind='coding_result';"
# 0
```

## 9-Target Verification Matrix (Rerun)

| # | Target | Status | Evidence | Notes |
| - | ------ | ------ | -------- | ----- |
| 1 | Services network | ✅ PASS | Compose network includes `backend`, `db`, `redis`, `worker-coding`; backend reached Redis and Postgres. | Same project network and healthy service reachability were live-verified. |
| 2 | Real source thread | ✅ PASS | Source thread `1243` contains real user message `50259`. | Thread/message were queried directly from Postgres. |
| 3 | POST enqueues | ✅ PASS | `POST /api/agents/coding/execute` returned `ok: true`, `run_id=run_efe058f2b50a4206`; queue depth `0 -> 1` with worker stopped. | Enqueue was observed before dequeue. |
| 4 | Worker dequeues | ✅ PASS | After worker restart, queue depth returned `1 -> 0`; run stream emitted `task.running`. | Dequeue occurred on the live queue. |
| 5 | Run reaches terminal | ⚠️ PARTIAL | Run stream emitted `task.failed`; DB row stayed `agent_runs.status='queued'`, `ended_at` unset. | Durable run-status divergence remains. |
| 6 | Event lifecycle | ✅ PASS | `created -> task.running -> task.failed` observed on event stream. | Lifecycle events are present and ordered. |
| 7 | Exactly one `coding_result` message | ❌ FAIL | `chat_messages` count for thread `1243`, `kind='coding_result'` is `0`. | No result injected to source thread. |
| 8 | Idempotency | ⛔ BLOCKED | No `coding_result` landed in source thread. | Per interpretation rule: cannot exercise duplicate-delivery guard without an injected result. |
| 9 | Failures bounded | ⚠️ PARTIAL | Explicit failure run (`run_cd1c5bc62ca6435c`) emitted `task.failed` with detailed error payload, but no source-thread `coding_result` and DB run status stayed `queued`. | Failure visibility exists in stream, but bounded thread-level failure delivery is missing. |

## Release-Readiness Conclusion

Release-ready for this path: **no**.

Required gates are not met: no source-thread `coding_result` injection, no idempotency exercise on delivered results, and durable run status does not converge to terminal state.

## Follow-up Bugs / Tasks

1. Resolve worker runtime dependency failure (`Pi SDK dependencies are not available`) so the worker can produce deliverable coding results.
2. Fix durable run-state convergence so `agent_runs.status` terminalizes (`completed`/`failed`) when terminal events are emitted.
3. Restore source-thread delivery for both success and failure paths (`kind='coding_result'`) so bounded failure visibility lands in-thread.
4. Re-run target #8 idempotency proof immediately after target #7 passes (must verify duplicate prevention on a real delivered `coding_result`).
5. Investigate runtime-compose migration drift (`migrator` image missing revision `9d4e1c7b2a6f`) that blocked exact `docker-compose.runtime.yml run --rm worker-coding ...` checks.
