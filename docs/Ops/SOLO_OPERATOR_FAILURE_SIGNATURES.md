# Codexify Solo Operator Failure Signatures

Purpose: Fast triage reference for recurring failures in local Docker operations.
Last updated: 2026-02-27
Source anchors:
- `guardian/routes/cron.py`
- `guardian/cron/scheduler.py`
- `guardian/workers/cron_worker.py`
- `guardian/routes/command_bus.py`
- `guardian/command_bus/invoke.py`
- `guardian/routes/tools.py`
- `guardian/core/dependencies.py`
- `docs/architecture/config-and-ops.md`

## Signature Table

| Symptom | Expected signal | Likely cause | First recovery step |
|---|---|---|---|
| `401 Missing API key` or `401 Invalid API key` | Response body from protected endpoint | Missing or wrong `X-API-Key` | Reload env: `set -a; source .env; set +a` and retry |
| Command invoke fails with `actor_claim_not_permitted` | `POST /api/guardian/commands/invoke` returns 403 | `actor.id` does not match authenticated subject | Align `actor.id` with `X-User-Id` or single-user id |
| Command invoke returns `status=blocked` and `phase1_write_blocked` | Invoke response + run events show `run.blocked` | Write commands are blocked in current command-bus phase | Use read-only drills for baseline; use `/api/cron/*` for durable automation |
| Command invoke returns `status=blocked` and `recursion_guard_blocked` | Invoke response error string | Attempted to invoke command-bus routes through command bus | Invoke a non-command-bus route (for example `/ping`) |
| Cron create returns `422 Invalid schedule` | Response detail includes allowed schedule formats | Unsupported schedule string | Use `@hourly`, `@daily`, `@weekly`, `@monthly`, or `*/N * * * *` |
| Cron webhook create returns `403` mentioning `LOCAL_ONLY_MODE` | Response detail from `/api/cron/jobs` | Outbound webhook egress denied by policy | Keep baseline on `noop` jobs unless egress policy is intentionally opened |
| Cron webhook create returns `422` forbidden host | Response detail: forbidden target host | Local/private/metadata host blocked by webhook policy | Use a permitted public host or stay with `noop` |
| Cron webhook create returns `422` allowlist error | Response detail: host not in `CRON_WEBHOOK_ALLOWLIST` | Allowlist is configured and target host not included | Add exact host to `CRON_WEBHOOK_ALLOWLIST` or change target |
| Cron run stays `queued` indefinitely | `GET /api/cron/jobs/{job_id}/runs` shows no transition | Scheduler/worker path not running; trigger only made DB row | Start scheduler + cron worker processes and re-check runs |
| Queue-backed flows report `queue_unavailable` | API response or backend logs | Redis unavailable | Bring Redis back and verify with `docker compose ps` |
| UI works but automation calls fail | Browser/UI visible, API calls fail | Backend unhealthy or auth mismatch | Validate `/ping`, `/health`, then inspect backend logs |

## Recovery Commands

```bash
# Baseline process and health checks
docker compose ps
curl -sS http://localhost:8888/ping
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/health

# Set these from previous API responses when drilling
# JOB_ID=<cron job id>
# RUN_ID=<command run id>

# Cron run visibility
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/cron/jobs
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8888/api/cron/jobs/$JOB_ID/runs"

# Command bus visibility
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/guardian/commands/manifest
curl -N -sS -H "X-API-Key: $GUARDIAN_API_KEY" -H "X-User-Id: ${CODEXIFY_SINGLE_USER_ID:-local}" \
  "http://localhost:8888/api/guardian/commands/runs/$RUN_ID/events?after_seq=0"
```
