# AxisNode Local Guardian Auth Configuration Correction

Date: 2026-09-23
Tracking: Codexify #815
Outcome: `AUTH_CORRECTED`
Provider classification: `PROVIDER_CONFIG_BLOCKED`

## Scope and runtime identity

This receipt records a machine-local configuration correction, not a Guardian
startup or Scout live-read proof. The canonical checkout was
`feature/ums-continued` at `a05189d8c6e0f631f78c564e8beab2a9a04a383c`
before the documentation commit.

| Surface | Observed identity |
| --- | --- |
| Compose project | `codexify` |
| Database service/container | `db` / `codexify-db-1` |
| Existing durable volume | `codexify_pg_data`, mounted at `/var/lib/postgresql/data` |
| Database name | `Codexify` |
| Backend service/container | `backend` / `codexify-backend-1` |
| Supported profile | `v1-local-core-web-mcp` |

The host inventory showed the existing `codexify_pg_data` volume labeled for
the `codexify` Compose project and `pg_data` Compose volume. The resolved Compose
database service continued to mount `pg_data` at `/var/lib/postgresql/data`.
No project, database, or volume change was made.

## Auth correction and Compose resolution

The active, Git-ignored `.env` had exactly one
`GUARDIAN_AUTH_MODE=remote` assignment. It was changed byte-for-byte to
`GUARDIAN_AUTH_MODE=local`; all other `.env` bytes were preserved. `.env` was
not staged or committed.

The targeted `docker compose config --format json` projection returned:

| Field | Before | After |
| --- | --- | --- |
| Compose project | `codexify` | `codexify` |
| Backend `GUARDIAN_AUTH_MODE` | `remote` | `local` |
| Backend `CODEXIFY_SUPPORTED_PROFILE` | `v1-local-core-web-mcp` | `v1-local-core-web-mcp` |
| Backend `LLM_PROVIDER` | `local` | `local` |
| DB volume source and target | `pg_data` at `/var/lib/postgresql/data` | same |

`docker compose config --quiet` passed after the correction. This validates
Compose resolution only; it does not run Guardian's startup checks.

## Separate provider configuration blocker

The current `.env` and resolved backend configuration still select:

```text
LOCAL_BASE_URL=http://100.127.148.28:8000/v1
LOCAL_DOCKER_FALLBACK_BASE_URL=http://100.127.148.28:8000/v1
```

The active `v1-local-core-web-mcp` manifest requires
`LOCAL_BASE_URL=http://host.docker.internal:8000/v1`. Guardian's supported
profile validator compares that value and reports drift before startup can be
claimed successful. The fallback URL is recorded as current routing context;
it is not a separate enforced manifest field in this comparison. An older
Guardian coding-loop receipt also recorded the Tailscale-address mismatch,
but the current `.env` and Compose render are the evidence that it persists
today. No provider URL was changed in this task.

## Boundary and remaining #815 gates

No service was started, no database contents were read, no migration was run,
and no volume was mounted or modified for inspection. Tailscale Serve, Tester,
Scout, credentials, and current release claims were untouched. The existing
thread and message rows remain unproven.

The next atomic task must correct or explicitly resolve the provider target
against the supported profile before attempting canonical backend startup.
Only a later runtime task may start the existing store, prove Guardian health
and protected-route auth behavior, establish private HTTPS, and perform the
Scout read-only continuity proof. This receipt does not close #815.
