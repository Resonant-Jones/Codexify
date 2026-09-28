# AxisNode Local Provider Target Configuration Correction

Date: 2026-09-23
Tracking: Codexify #815
Outcome: `PROVIDER_CONFIG_CORRECTED`
Provider target state: `PROVIDER_TARGET_CONFIGURED_SERVICE_ABSENT`

## Scope and authority

This is a machine-local static configuration proof, not a provider health,
Guardian startup, or Scout continuity proof. The canonical checkout was
`feature/ums-continued` at `3df7896e401dcdfc54da065058f7073a5b29bdd8`
before this receipt commit. That commit contains the preceding local-auth
correction receipt.

| Surface | Identity |
| --- | --- |
| Compose project | `codexify` |
| Database service/container | `db` / `codexify-db-1` |
| Existing durable volume | `codexify_pg_data` |
| Database | `Codexify` |
| Backend service/container | `backend` / `codexify-backend-1` |
| Supported profile | `v1-local-core-web-mcp` |
| Guardian auth mode | `local` |

The database's resolved Compose volume remained `pg_data` mounted at
`/var/lib/postgresql/data`; the Docker-managed volume identity for that Compose
project is `codexify_pg_data`. No persistence or container operation was
performed.

## Exact machine-local correction

The active `.env` is Git-ignored and had exactly one active
`LOCAL_BASE_URL=http://100.127.148.28:8000/v1` assignment. Only that line was
changed, byte-for-byte, to
`LOCAL_BASE_URL=http://host.docker.internal:8000/v1`. All other `.env` bytes
were preserved, and `.env` was not staged or committed.

The targeted `docker compose config --format json` projection was:

| Field | Before | After |
| --- | --- | --- |
| Compose project | `codexify` | `codexify` |
| Backend `GUARDIAN_AUTH_MODE` | `local` | `local` |
| Backend `CODEXIFY_SUPPORTED_PROFILE` | `v1-local-core-web-mcp` | `v1-local-core-web-mcp` |
| Backend `LLM_PROVIDER` | `local` | `local` |
| Backend `LOCAL_BASE_URL` | `http://100.127.148.28:8000/v1` | `http://host.docker.internal:8000/v1` |
| Backend `LOCAL_DOCKER_FALLBACK_BASE_URL` | `http://100.127.148.28:8000/v1` | same |
| Database volume source/target | `pg_data` at `/var/lib/postgresql/data` | same |

The machine-local `LOCAL_CHAT_MODEL` remained
`gemma-4-e4b-it-4bit`; `LOCAL_EMBED_MODEL` remained
`/models/bge-large-en-v1.5`. Neither alias was changed.

## Governing source and static validation

The current `config/supported_profiles/v1-local-core-web-mcp.yaml` requires
`LOCAL_BASE_URL=http://host.docker.internal:8000/v1`. The local-provider
router reads `LOCAL_BASE_URL` as its primary target when no explicit endpoint
chain is configured. Its Docker-host fallback is opt-in, applies to a loopback
primary URL, and does not relax the supported-profile URL comparison.
`LOCAL_DOCKER_FALLBACK_BASE_URL` is not independently constrained by this
profile's provider contract.

`docker compose config --quiet` passed after the edit. The targeted Compose
projection matches the selected profile for `LOCAL_BASE_URL`, auth mode, and
provider selection. No existing standalone, non-starting supported-profile
validator was found in Make or `scripts/ops/`; no live or newly invented
validator was run. This does not establish full startup coherence or provider
reachability.

## Host and remaining #815 gates

The ordinary AxisNode Terminal check `lsof -nP -iTCP:8000 -sTCP:LISTEN`
returned no listener. This classifies the configured provider target as
`PROVIDER_TARGET_CONFIGURED_SERVICE_ABSENT`; it does not invalidate the static
URL correction. The final `docker ps` listed only the pre-existing
`codexify-redis-1` container as running, and `tailscale serve status` returned
`No serve config`. No provider, backend, database, or worker was started by
this task. No database row was read, no migration ran, no provider API or
health endpoint was called, and no Tailscale or Scout action was taken.
Provider readiness remains unproven.

A separate #815 task must identify or restore the expected local provider
service before claiming full provider readiness. Guardian startup
qualification against the existing database volume remains separately bounded
if the backend can start without live inference. Guardian health,
protected-route auth behavior, private HTTPS, and Scout's protected continuity
read remain separate gates. This receipt does not close #815 or change
Beta/release support.
