# Codexify Solo Operator Automation Runbook

Purpose: Canonical operating runbook for command bus and cron in the current local-Docker setup.
Last updated: 2026-02-27
Source anchors:
- `docs/guardian/command-bus-auth-cli-automations.md`
- `guardian/routes/command_bus.py`
- `guardian/command_bus/invoke.py`
- `guardian/routes/tools.py`
- `guardian/routes/cron.py`
- `guardian/cron/scheduler.py`
- `guardian/workers/cron_worker.py`
- `guardian/cron/executor.py`
- `tests/routes/test_command_bus_phase1_invoke.py`
- `tests/routes/test_cron_routes.py`

## Runtime Truths (Current Baseline)

1. Deployment baseline is local Docker (`docker compose`) only.
2. No API changes are required for this bootcamp.
3. Cron `job_type` currently supports `noop | webhook`.
4. Allowed schedules: `@hourly`, `@daily`, `@weekly`, `@monthly`, or `*/N * * * *`.
5. Webhook jobs block localhost/private targets by default policy.
6. `/api/tools/*` is compatibility surface with in-memory job status (`JOBS` map).
7. `/api/cron/*` stores durable job/run records in Postgres.
8. Important nuance: `POST /api/cron/jobs/{job_id}/trigger` currently creates a `queued` run row but does not enqueue execution by itself; running scheduler + cron worker is required for state transitions.

## Canonical Interfaces

1. `GET /api/guardian/commands/manifest`
2. `POST /api/guardian/commands/invoke`
3. `GET /api/guardian/commands/runs/{run_id}/events`
4. `POST /api/cron/jobs`
5. `GET /api/cron/jobs`
6. `POST /api/cron/jobs/{job_id}/trigger`
7. `GET /api/cron/jobs/{job_id}/runs`

## Operational Drill Set (Exact)

Use this sequence for teaching sessions and recurring refresh:

```bash
# 0) Bootstrap env for shell session
set -a; source .env; set +a

# 1) Core health
docker compose ps
curl -sS http://localhost:8888/ping
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/health

# 2) Command bus surface
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/guardian/commands/manifest

# 3) Cron surface
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/cron/jobs

# 4) Create no-op cron job
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  http://localhost:8888/api/cron/jobs \
  -d '{"name":"solo-check","schedule":"@hourly","job_type":"noop","payload":{},"is_enabled":true}'
```

If you want scheduled runs to execute continuously, run these processes separately:

```bash
python -c "from guardian.cron.scheduler import run_forever; run_forever()"
python -m guardian.workers.cron_worker
```

## Bootstrap and Core Health

```bash
set -a; source .env; set +a

docker compose ps
curl -sS http://localhost:8888/ping
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/health
```

Pass condition:
- `/ping` responds.
- Authenticated `/health` responds.
- Expected containers are running.

## Command Bus Drill (Manifest -> Invoke -> Run Events)

```bash
BASE_URL="http://localhost:8888"
USER_ID="${CODEXIFY_SINGLE_USER_ID:-local}"

# 1) Fetch manifest
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "$BASE_URL/api/guardian/commands/manifest"

# 2) Pick a safe read command id (GET /ping)
CMD_ID="$(
  curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
    "$BASE_URL/api/guardian/commands/manifest" \
  | jq -r '.commands[] | select(.method=="GET" and .path_template=="/ping") | .command_id' \
  | head -n1
)"

# 3) Invoke
RESP="$(
  curl -sS -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    -H "X-User-Id: $USER_ID" \
    "$BASE_URL/api/guardian/commands/invoke" \
    -d "{\"invoke_version\":\"1.0\",\"command_id\":\"$CMD_ID\",\"actor\":{\"kind\":\"human\",\"id\":\"$USER_ID\"},\"arguments\":{\"path_params\":{},\"query\":{},\"headers\":{}}}"
)"

echo "$RESP" | jq
RUN_ID="$(echo "$RESP" | jq -r '.run_id')"

# 4) Stream run events
curl -N -sS -H "X-API-Key: $GUARDIAN_API_KEY" -H "X-User-Id: $USER_ID" \
  "$BASE_URL/api/guardian/commands/runs/$RUN_ID/events?after_seq=0"
```

Expected event progression for read command:
- `run.created`
- `run.started`
- `run.completed`

## Cron Drill (Create -> Trigger -> Observe)

```bash
BASE_URL="http://localhost:8888"

# 1) List jobs
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE_URL/api/cron/jobs"

# 2) Create no-op job
CREATE_RESP="$(
  curl -sS -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    "$BASE_URL/api/cron/jobs" \
    -d '{"name":"solo-check","schedule":"@hourly","job_type":"noop","payload":{},"is_enabled":true}'
)"

echo "$CREATE_RESP" | jq
JOB_ID="$(echo "$CREATE_RESP" | jq -r '.id')"

# 3) Trigger ad hoc run row
TRIGGER_RESP="$(
  curl -sS -X POST \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    "$BASE_URL/api/cron/jobs/$JOB_ID/trigger"
)"

echo "$TRIGGER_RESP" | jq

# 4) Inspect run history
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "$BASE_URL/api/cron/jobs/$JOB_ID/runs" | jq
```

Expected result from trigger drill right now:
- New run row appears with `status: queued`.

## Cron Execution Path (Queued -> Running -> Succeeded)

Run scheduler and worker in separate terminals when you need continuous execution:

```bash
python -c "from guardian.cron.scheduler import run_forever; run_forever()"
python -m guardian.workers.cron_worker
```

Then create an enabled cron job and observe:
(Use `BASE_URL` and `JOB_ID` from the cron drill above.)

```bash
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "$BASE_URL/api/cron/jobs/$JOB_ID/runs"
```

Expected transitions for scheduler-enqueued runs:
- `queued` -> `running` -> `succeeded` (or `failed`)

## Daily Operating Loop (20 Minutes)

1. 0-4 min: Core health and auth
   - `docker compose ps`
   - `/ping` and authenticated `/health`
2. 4-8 min: Queue and workers
   - Worker container status and latest worker logs
3. 8-12 min: Active blockers
   - List stalled tasks/runs and one root-cause hypothesis each
4. 12-16 min: Single top priority
   - Choose one concrete deliverable for today
5. 16-20 min: Single risk
   - Record one execution risk and one mitigation action

Daily note template:

```text
Top priority:
Top blocker:
Top risk:
Health status:
First action now:
```

## Weekly Review Loop (90 Minutes)

1. 0-15 min: Runtime health retrospective (incidents, failures, recoveries)
2. 15-35 min: Architecture drift review (docs vs current code)
3. 35-55 min: Stale docs cleanup and source-anchor refresh
4. 55-75 min: Build next-week board
5. 75-90 min: Prioritize top-3 and make explicit kill/defer decisions

Weekly output must include:
- `Top-3 priorities`
- `Kill list`
- `Defer list`
- `Known risks for next week`

## Failure Drills (Required)

1. Worker down recovery
   - Stop the cron worker process.
   - Create/queue run.
   - Confirm run remains queued.
   - Restart worker and verify completion.
2. Queue unavailable
   - Bring Redis down and confirm queue-dependent flows fail fast.
   - Restore Redis and verify normal flow.
3. Bad auth
   - Omit or corrupt `X-API-Key`; verify `401` and no side effects.
4. Validation failure
   - Use invalid cron schedule; verify `422` with schedule guidance.
5. Policy failure
   - Create webhook job to localhost/private target; verify policy rejection.

Use `docs/Ops/SOLO_OPERATOR_FAILURE_SIGNATURES.md` as the canonical triage table.

## Acceptance Scenarios

1. Happy path: create `noop` job, inspect `queued` run row, then verify `queued -> running -> succeeded` once scheduler+worker path is active.
2. Scheduler path: enabled due job auto-generates run rows when scheduler is running.
3. Auth failure: missing/wrong `X-API-Key` returns auth error with no side effects.
4. Validation failure: invalid schedule returns `422` with clear message.
5. Policy failure: webhook to localhost/private target is rejected.
6. Recovery drill: stop cron worker, confirm queued/stalled state, restart worker, confirm completion.

## Single Source of Truth Rule

1. In-repo docs are canonical.
2. External tools (Notion, boards, notes) are mirrors.
3. If mirror content conflicts with repo docs, fix the mirror.

## Operating Baseline Before New Feature Work

All conditions should be true:

1. `/ping` and authenticated `/health` pass.
2. Core workers are healthy.
3. One command bus read invocation completes with events.
4. One cron job lifecycle is observable in run history.
5. Current failures and mitigations are documented in the failure-signatures page.
